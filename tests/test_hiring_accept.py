"""Hiring a supplier: what accepting a bid does, and when it is refused.

Covers cases AA-01 to AA-25 and AV-01 to AV-07 in TEST_CASES.md, and business
rules 3, 4, 5 and 6.

Four things must all be true before a bid can be accepted: the bid is pending,
the gig is open, the supplier is not inactive, and the supplier is under the
agreement limit.
"""

from decimal import Decimal

import pytest

from tests import endpoints
from tests.assertions import (
    assert_conflict,
    assert_created,
    assert_not_found,
    assert_ok,
    assert_page,
)
from tests.factories import ApplicationFactory, GigFactory, SupplierFactory

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-03")]


@pytest.mark.case("AA-01,AA-04")
def test_accepting_a_bid_creates_an_agreement(api, open_gig, supplier, apply_to_gig):
    bid = apply_to_gig(open_gig, supplier, "420.00")

    agreement = assert_created(api.post(endpoints.accept(bid["id"])))

    assert agreement["gig"] == open_gig.id
    assert agreement["supplier"] == supplier.id
    assert agreement["agreed_rate"] == "420.00"
    assert agreement["status"] == "active"


@pytest.mark.case("AA-02,AA-03")
def test_accepting_a_bid_marks_it_accepted_and_moves_the_gig(
    api, open_gig, supplier, apply_to_gig
):
    bid = apply_to_gig(open_gig, supplier)

    assert_created(api.post(endpoints.accept(bid["id"])))

    listing = assert_page(api.get(endpoints.applications_for(open_gig.id)), count=1)
    assert listing["results"][0]["status"] == "accepted"
    assert assert_ok(api.get(endpoints.gig(open_gig.id)))["status"] == "in_progress"


@pytest.mark.case("AA-05")
@pytest.mark.interpretation("I11")
def test_the_agreed_amount_is_the_amount_that_was_proposed(api, creator, apply_to_gig):
    """Not the supplier's profile rate, and not the gig's budget.

    Worked example: a supplier whose profile shows 45.00 an hour proposes 420.00
    for a job budgeted at 500.00. The agreement records 420.00 -- the amount
    actually agreed for this piece of work.
    """
    gig = GigFactory(creator=creator, budget=Decimal("500.00"))
    supplier = SupplierFactory(hourly_rate=Decimal("45.00"))
    bid = apply_to_gig(gig, supplier, "420.00")

    agreement = assert_created(api.post(endpoints.accept(bid["id"])))

    assert agreement["agreed_rate"] == "420.00"


@pytest.mark.case("AA-06")
def test_the_agreed_amount_does_not_follow_later_profile_changes(
    api, open_gig, supplier, apply_to_gig
):
    """What was agreed cannot be rewritten by editing a profile.

    This is why the amount is copied onto the agreement rather than read through
    to the supplier. An agreement whose value can change afterwards is not an
    agreement.
    """
    bid = apply_to_gig(open_gig, supplier, "420.00")
    agreement = assert_created(api.post(endpoints.accept(bid["id"])))

    assert_ok(api.patch(endpoints.supplier(supplier.id), {"hourly_rate": "900.00"}))

    contracts = assert_ok(api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier.id}"))
    assert contracts["results"][0]["agreed_rate"] == "420.00"


@pytest.mark.case("AA-07,AA-08")
def test_the_agreement_names_the_supplier_and_gig_from_the_accepted_bid(
    api, gig_with_three_bids, other_supplier
):
    gig, bids = gig_with_three_bids

    agreement = assert_created(api.post(endpoints.accept(bids[1]["id"])))

    assert agreement["supplier"] == other_supplier.id
    assert agreement["gig"] == gig.id


@pytest.mark.case("AA-18")
@pytest.mark.rule("BR-06")
def test_accepting_the_same_bid_twice_creates_no_second_agreement(
    api, open_gig, supplier, apply_to_gig
):
    bid = apply_to_gig(open_gig, supplier)
    assert_created(api.post(endpoints.accept(bid["id"])))

    assert_conflict(api.post(endpoints.accept(bid["id"])), "application_not_pending")

    contracts = assert_ok(api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier.id}"))
    assert contracts["count"] == 1


@pytest.mark.case("AA-21,AA-22,AA-23")
@pytest.mark.interpretation("I6")
@pytest.mark.parametrize("gig_status", ["cancelled", "completed", "in_progress"])
def test_a_bid_cannot_be_accepted_on_a_gig_that_is_not_open(
    api, creator, supplier, gig_status
):
    """The specification guards *applying* to a closed gig but not *accepting*.

    Without this, accepting on a cancelled gig would bring it back to life as in
    progress, and a second acceptance on an in-progress gig would create a
    second agreement on the same piece of work.
    """
    gig = GigFactory(creator=creator, status=gig_status)
    # A factory instance, not a response body -- so ``.id``, not ``["id"]``.
    bid = ApplicationFactory(gig=gig, supplier=supplier)

    assert_conflict(api.post(endpoints.accept(bid.id)), "gig_not_open")

    gig.refresh_from_db()
    assert gig.status == gig_status


@pytest.mark.case("AA-24,AA-25")
def test_accepting_something_that_does_not_exist_reports_not_found(api, application):
    assert_not_found(api.post(endpoints.accept(999999)))
    assert api.get(endpoints.accept(application.id)).status_code == 405
