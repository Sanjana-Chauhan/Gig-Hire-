"""Hiring either succeeds completely or leaves nothing behind.

Covers cases CA-01 to CA-06 in TEST_CASES.md, and the atomicity requirement in
business rule 3.

Accepting a bid does four things: marks the bid accepted, turns down the
competing bids, moves the gig to in progress, and creates the agreement. The
specification says these must be one operation, with "no partial states if
something fails mid-way".

Wrapping code in a transaction and *observing* it roll back are different
things, so the failure is forced on purpose. That technique -- injecting a fault
at the point most likely to leave inconsistent state, then asserting nothing
moved -- is the only way to test a rollback path, because real conditions rarely
trigger one on demand.
"""

from unittest import mock

import pytest

from tests import endpoints
from tests.assertions import assert_conflict, assert_created, assert_ok, assert_page

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-03")]


def statuses_on(api, gig_id):
    body = assert_ok(api.get(endpoints.applications_for(gig_id)))
    return {item["id"]: item["status"] for item in body["results"]}


def agreements_for(api, creator_id):
    return assert_ok(api.get(f"{endpoints.CONTRACTS}?creator_id={creator_id}"))["count"]


@pytest.mark.case("CA-01,CA-02")
def test_a_failure_at_the_last_step_undoes_every_earlier_step(
    api, gig_with_three_bids
):
    """The fault is injected as late as possible, on purpose.

    By the time the gig update runs, the agreement has been created, the bid has
    been accepted and the competing bids have been turned down. If the
    transaction works, all four of those disappear. If it does not, this is
    exactly the half-finished state the specification forbids.
    """
    gig, bids = gig_with_three_bids
    before = agreements_for(api, gig.creator_id)

    with mock.patch(
        "apps.gigs.models.Gig.save", side_effect=RuntimeError("injected failure")
    ):
        with pytest.raises(RuntimeError):
            api.post(endpoints.accept(bids[0]["id"]))

    gig.refresh_from_db()
    assert gig.status == "open"
    assert set(statuses_on(api, gig.id).values()) == {"pending"}
    assert agreements_for(api, gig.creator_id) == before


@pytest.mark.case("CA-03")
def test_the_service_still_works_after_a_failed_attempt(api, gig_with_three_bids):
    """A rolled-back transaction must leave nothing broken behind.

    If the failed attempt had left the connection in a bad state, this second
    acceptance would fail too -- which is how a missing savepoint shows up.
    """
    gig, bids = gig_with_three_bids

    with mock.patch(
        "apps.gigs.models.Gig.save", side_effect=RuntimeError("injected failure")
    ):
        with pytest.raises(RuntimeError):
            api.post(endpoints.accept(bids[0]["id"]))

    agreement = assert_created(api.post(endpoints.accept(bids[0]["id"])))

    assert agreement["status"] == "active"
    assert statuses_on(api, gig.id)[bids[1]["id"]] == "rejected"


@pytest.mark.case("CA-04")
@pytest.mark.rule("BR-05")
def test_a_refusal_on_availability_writes_nothing_at_all(
    api, gig_with_three_bids, supplier
):
    """A refused hire must leave the bid pending, not half-processed.

    The guards all run before any write, so this passes for a stronger reason
    than the transaction: nothing was ever attempted.
    """
    gig, bids = gig_with_three_bids
    assert_ok(
        api.patch(endpoints.supplier(supplier.id), {"availability_status": "inactive"})
    )
    before = agreements_for(api, gig.creator_id)

    assert_conflict(api.post(endpoints.accept(bids[0]["id"])), "supplier_not_hireable")

    gig.refresh_from_db()
    assert gig.status == "open"
    assert set(statuses_on(api, gig.id).values()) == {"pending"}
    assert agreements_for(api, gig.creator_id) == before


@pytest.mark.case("CA-05")
@pytest.mark.rule("BR-04")
def test_a_refusal_on_the_agreement_limit_writes_nothing_at_all(
    api, gig_with_three_bids, apply_to_gig, give_live_agreements
):
    """A fourth bidder who is already at the limit.

    Built with a supplier of its own rather than the ``busy_supplier`` fixture:
    that fixture shares the ``supplier`` fixture, who is already one of the three
    bidders here, and a second bid from the same supplier would be refused for
    the wrong reason.
    """
    from tests.factories import SupplierFactory

    gig, bids = gig_with_three_bids
    at_the_limit = SupplierFactory()
    give_live_agreements(at_the_limit, 3)
    extra_bid = apply_to_gig(gig, at_the_limit)
    before = agreements_for(api, gig.creator_id)

    assert_conflict(api.post(endpoints.accept(extra_bid["id"])), "workload_cap_reached")

    gig.refresh_from_db()
    assert gig.status == "open"
    assert statuses_on(api, gig.id)[extra_bid["id"]] == "pending"
    assert agreements_for(api, gig.creator_id) == before


@pytest.mark.case("CA-06")
def test_a_successful_hire_neither_adds_nor_removes_bids(api, gig_with_three_bids):
    gig, bids = gig_with_three_bids

    assert_created(api.post(endpoints.accept(bids[0]["id"])))

    assert_page(api.get(endpoints.applications_for(gig.id)), count=3)
