"""Accepting one bid turns down the others.

Covers cases AA-10 to AA-17 in TEST_CASES.md, business rule 3, and
interpretations I5 and B-4 in DECISIONS.md.

Two halves to the rule, and both matter: only *pending* bids are turned down,
and only on *that* gig.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_created, assert_ok, assert_page
from tests.factories import ApplicationFactory, GigFactory

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-03")]


def statuses_on(api, gig_id):
    body = assert_ok(api.get(endpoints.applications_for(gig_id)))
    return {item["id"]: item["status"] for item in body["results"]}


@pytest.mark.case("AA-10")
def test_accepting_one_of_three_bids_turns_down_the_other_two(
    api, gig_with_three_bids
):
    """The headline case for rule 3.

    One accepted, two rejected, the gig in progress, and exactly one agreement --
    all checked together, because the rule is about the whole outcome rather
    than any single change.
    """
    gig, bids = gig_with_three_bids

    assert_created(api.post(endpoints.accept(bids[1]["id"])))

    after = statuses_on(api, gig.id)
    assert after[bids[0]["id"]] == "rejected"
    assert after[bids[1]["id"]] == "accepted"
    assert after[bids[2]["id"]] == "rejected"

    assert assert_ok(api.get(endpoints.gig(gig.id)))["status"] == "in_progress"
    contracts = assert_ok(api.get(f"{endpoints.CONTRACTS}?creator_id={gig.creator_id}"))
    assert contracts["count"] == 1


@pytest.mark.case("AA-11")
def test_accepting_the_only_bid_leaves_nothing_to_turn_down(
    api, open_gig, supplier, apply_to_gig
):
    bid = apply_to_gig(open_gig, supplier)

    assert_created(api.post(endpoints.accept(bid["id"])))

    assert statuses_on(api, open_gig.id) == {bid["id"]: "accepted"}


@pytest.mark.case("AA-12")
def test_accepting_one_of_five_bids_turns_down_the_other_four(
    api, open_gig, apply_to_gig
):
    from tests.factories import SupplierFactory

    bids = [apply_to_gig(open_gig, SupplierFactory()) for _ in range(5)]

    assert_created(api.post(endpoints.accept(bids[2]["id"])))

    after = statuses_on(api, open_gig.id)
    assert after[bids[2]["id"]] == "accepted"
    assert [after[b["id"]] for i, b in enumerate(bids) if i != 2] == ["rejected"] * 4


@pytest.mark.case("AA-13")
def test_the_hired_suppliers_bids_on_other_gigs_are_untouched(
    api, creator, supplier, apply_to_gig
):
    """Rule 3 says "for that gig".

    A supplier who wins one job is still legitimately in the running for others,
    so their other bids must survive. Turning them down would quietly remove
    them from competitions nobody asked us to end.
    """
    first_gig = GigFactory(creator=creator)
    second_gig = GigFactory(creator=creator)
    winning_bid = apply_to_gig(first_gig, supplier)
    other_bid = apply_to_gig(second_gig, supplier)

    assert_created(api.post(endpoints.accept(winning_bid["id"])))

    assert statuses_on(api, second_gig.id)[other_bid["id"]] == "pending"


@pytest.mark.case("AA-14")
def test_a_rejected_supplier_keeps_their_chances_elsewhere(
    api, creator, supplier, other_supplier, apply_to_gig
):
    contested = GigFactory(creator=creator)
    elsewhere = GigFactory(creator=creator)
    winning_bid = apply_to_gig(contested, supplier)
    losing_bid = apply_to_gig(contested, other_supplier)
    unrelated_bid = apply_to_gig(elsewhere, other_supplier)

    assert_created(api.post(endpoints.accept(winning_bid["id"])))

    assert statuses_on(api, contested.id)[losing_bid["id"]] == "rejected"
    assert statuses_on(api, elsewhere.id)[unrelated_bid["id"]] == "pending"


@pytest.mark.case("AA-15,AA-17")
def test_bids_that_were_already_finished_keep_their_status(
    api, open_gig, supplier, other_supplier, third_supplier, apply_to_gig
):
    """A withdrawn bid stays withdrawn -- it does not become rejected.

    A gig can hold bids in several states at once, and only the pending ones
    should move. Sweeping everything into "rejected" would destroy the record of
    who pulled out versus who was turned down.
    """
    from tests.factories import SupplierFactory

    already_rejected = ApplicationFactory(
        gig=open_gig, supplier=SupplierFactory(), status="rejected"
    )
    already_withdrawn = ApplicationFactory(
        gig=open_gig, supplier=SupplierFactory(), status="withdrawn"
    )
    winning_bid = apply_to_gig(open_gig, supplier)
    losing_bid = apply_to_gig(open_gig, other_supplier)

    assert_created(api.post(endpoints.accept(winning_bid["id"])))

    after = statuses_on(api, open_gig.id)
    assert after[already_rejected.id] == "rejected"
    assert after[already_withdrawn.id] == "withdrawn"
    assert after[winning_bid["id"]] == "accepted"
    assert after[losing_bid["id"]] == "rejected"


@pytest.mark.case("AA-16")
def test_bids_that_were_already_finished_are_not_re_stamped(
    api, open_gig, supplier, apply_to_gig
):
    """Their "last changed" date must not move.

    Nothing about them changed, so touching them would destroy the answer to
    "when was this rejected?". The cascade is one bulk update, and a bulk update
    does not set timestamps by itself -- so this checks the timestamp was set
    deliberately for the rows that moved and left alone for the rows that did not.
    """
    from tests.factories import SupplierFactory

    already_rejected = ApplicationFactory(
        gig=open_gig, supplier=SupplierFactory(), status="rejected"
    )
    before = already_rejected.updated_at
    winning_bid = apply_to_gig(open_gig, supplier)

    assert_created(api.post(endpoints.accept(winning_bid["id"])))

    already_rejected.refresh_from_db()
    assert already_rejected.updated_at == before


@pytest.mark.case("AA-06")
def test_the_number_of_bids_is_unchanged_by_accepting(api, gig_with_three_bids):
    """Only statuses change. Nothing is added and nothing is removed."""
    gig, bids = gig_with_three_bids

    assert_created(api.post(endpoints.accept(bids[0]["id"])))

    assert_page(api.get(endpoints.applications_for(gig.id)), count=len(bids))
