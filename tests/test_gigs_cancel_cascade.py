"""Cancelling a gig turns down the bids still waiting on it.

Covers cases GU-46 to GU-54 in TEST_CASES.md, and interpretation I9 in
DECISIONS.md.

The specification never says what happens to pending applications when a gig is
cancelled. Leaving them pending would show live bids for work that no longer
exists, and every one of those suppliers would wait for an answer that could not
come -- because an application on a cancelled gig can never be accepted.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_ok
from tests.factories import ApplicationFactory

pytestmark = [pytest.mark.django_db, pytest.mark.interpretation("I9")]


def statuses_on(api, gig_id):
    """Every application on a gig, as {id: status}."""
    body = assert_ok(api.get(endpoints.applications_for(gig_id)))
    return {item["id"]: item["status"] for item in body["results"]}


@pytest.mark.case("GU-46")
def test_cancelling_a_gig_turns_down_its_pending_bids(api, gig_with_three_bids):
    gig, bids = gig_with_three_bids

    assert_ok(api.patch(endpoints.gig(gig.id), {"status": "cancelled"}))

    after = statuses_on(api, gig.id)
    assert all(after[bid["id"]] == "rejected" for bid in bids)


@pytest.mark.case("GU-51")
def test_the_gig_and_its_bids_change_together(api, gig_with_three_bids):
    """Never a gig cancelled with a bid still pending, or the reverse.

    Both writes happen in one transaction, so no caller can observe a
    half-finished cancellation.
    """
    gig, _ = gig_with_three_bids

    body = assert_ok(api.patch(endpoints.gig(gig.id), {"status": "cancelled"}))

    assert body["status"] == "cancelled"
    assert "pending" not in statuses_on(api, gig.id).values()


@pytest.mark.case("GU-47,GU-48,GU-49")
def test_bids_that_were_already_finished_are_left_exactly_as_they_were(
    api, open_gig, supplier, other_supplier, third_supplier, apply_to_gig
):
    """A withdrawn bid stays withdrawn -- it does not become rejected.

    Built as a mixed set on purpose: a gig can hold applications in several
    states at once, and only the pending ones should move.
    """
    already_rejected = ApplicationFactory(gig=open_gig, supplier=supplier, status="rejected")
    already_withdrawn = ApplicationFactory(
        gig=open_gig, supplier=other_supplier, status="withdrawn"
    )
    still_pending = apply_to_gig(open_gig, third_supplier)

    assert_ok(api.patch(endpoints.gig(open_gig.id), {"status": "cancelled"}))

    after = statuses_on(api, open_gig.id)
    assert after[already_rejected.id] == "rejected"
    assert after[already_withdrawn.id] == "withdrawn"
    assert after[still_pending["id"]] == "rejected"


@pytest.mark.case("GU-47,GU-48")
def test_finished_bids_are_not_re_stamped(
    api, open_gig, supplier, other_supplier, apply_to_gig
):
    """Their "last changed" date must not move.

    Nothing about them changed, so re-saving them would destroy the answer to
    "when was this rejected?" -- and that is a question support gets asked.
    """
    already_rejected = ApplicationFactory(gig=open_gig, supplier=supplier, status="rejected")
    before = already_rejected.updated_at
    apply_to_gig(open_gig, other_supplier)

    assert_ok(api.patch(endpoints.gig(open_gig.id), {"status": "cancelled"}))

    already_rejected.refresh_from_db()
    assert already_rejected.updated_at == before


@pytest.mark.case("GU-50")
def test_cancelling_a_gig_with_no_bids_works(api, open_gig):
    body = assert_ok(api.patch(endpoints.gig(open_gig.id), {"status": "cancelled"}))

    assert body["status"] == "cancelled"


@pytest.mark.case("GU-52,GU-53")
def test_cancelling_neither_adds_nor_removes_bids_and_creates_no_agreement(
    api, gig_with_three_bids
):
    gig, bids = gig_with_three_bids

    assert_ok(api.patch(endpoints.gig(gig.id), {"status": "cancelled"}))

    assert len(statuses_on(api, gig.id)) == len(bids)
    contracts = assert_ok(api.get(f"{endpoints.CONTRACTS}?creator_id={gig.creator_id}"))
    assert contracts["count"] == 0


@pytest.mark.case("GU-54")
def test_cancelling_an_already_cancelled_gig_changes_nothing(api, gig_with_three_bids):
    gig, _ = gig_with_three_bids
    assert_ok(api.patch(endpoints.gig(gig.id), {"status": "cancelled"}))
    first_pass = statuses_on(api, gig.id)

    assert_ok(api.patch(endpoints.gig(gig.id), {"status": "cancelled"}))

    assert statuses_on(api, gig.id) == first_pass
