"""Deleting gigs, and what must survive when a delete is refused.

Covers cases GD-01 to GD-09 in TEST_CASES.md, business rule 7, and deviation S1
in DECISIONS.md.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_conflict, assert_created, assert_not_found, assert_ok

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-07")]


@pytest.mark.case("GD-01")
def test_a_gig_nobody_has_applied_to_can_be_deleted(api, open_gig):
    response = api.delete(endpoints.gig(open_gig.id))

    assert response.status_code == 204
    assert_not_found(api.get(endpoints.gig(open_gig.id)))


@pytest.mark.case("GD-02")
@pytest.mark.interpretation("I14")
def test_deleting_a_gig_takes_its_bids_with_it(
    api, open_gig, supplier, other_supplier, apply_to_gig
):
    """A bid means nothing without its gig.

    It carries no money and no reputation, unlike an agreement or a review.
    Protecting bids instead would make the delete endpoint unusable, since any
    gig that had ever received one would be undeletable.
    """
    apply_to_gig(open_gig, supplier)
    apply_to_gig(open_gig, other_supplier)

    assert api.delete(endpoints.gig(open_gig.id)).status_code == 204

    assert_not_found(api.get(endpoints.applications_for(open_gig.id)))


@pytest.mark.case("GD-03,GD-04")
def test_a_gig_with_a_live_agreement_cannot_be_deleted_and_nothing_is_lost(
    api, supplier, hire
):
    agreement = hire(supplier)

    assert_conflict(
        api.delete(endpoints.gig(agreement["gig"])), "gig_has_active_contract"
    )

    assert_ok(api.get(endpoints.gig(agreement["gig"])))
    contracts = assert_ok(api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier.id}"))
    assert contracts["count"] == 1
    assert contracts["results"][0]["status"] == "active"


@pytest.mark.case("GD-05")
@pytest.mark.interpretation("S1")
def test_a_gig_with_a_finished_agreement_also_cannot_be_deleted(api, supplier, hire):
    """Stricter than the rule as written, and deliberately so.

    Rule 7 forbids deleting a gig only while its agreement is *live*, which read
    strictly would allow deleting one whose agreement is finished -- taking the
    agreement and its reviews with it. The same sentence forbids exactly that, so
    the literal permission contradicts the rule's own intent.

    A different message from the live-agreement case, so a caller knows which
    situation they are in.
    """
    agreement = hire(supplier)
    assert_ok(api.post(endpoints.complete(agreement["id"])))

    assert_conflict(
        api.delete(endpoints.gig(agreement["gig"])), "gig_has_contract_history"
    )

    assert_ok(api.get(endpoints.gig(agreement["gig"])))


@pytest.mark.case("GD-06")
def test_reviews_survive_a_refused_delete(api, supplier, hire):
    """The whole point of rule 7: reputation cannot be destroyed by a delete."""
    agreement = hire(supplier)
    assert_ok(api.post(endpoints.complete(agreement["id"])))
    for kind in ["creator_on_supplier", "supplier_on_creator"]:
        assert_created(
            api.post(
                endpoints.reviews_for(agreement["id"]),
                {"reviewer_type": kind, "rating": 5},
            )
        )

    assert_conflict(
        api.delete(endpoints.gig(agreement["gig"])), "gig_has_contract_history"
    )

    reviews = assert_ok(api.get(endpoints.reviews_for(agreement["id"])))
    assert reviews["count"] == 2


@pytest.mark.case("GD-07")
def test_a_cancelled_gig_that_never_reached_an_agreement_can_be_deleted(api, open_gig):
    assert_ok(api.patch(endpoints.gig(open_gig.id), {"status": "cancelled"}))

    assert api.delete(endpoints.gig(open_gig.id)).status_code == 204


@pytest.mark.case("GD-08,GD-09")
def test_deleting_a_gig_that_is_not_there_reports_not_found(api, open_gig):
    assert_not_found(api.delete(endpoints.gig(999999)))

    assert api.delete(endpoints.gig(open_gig.id)).status_code == 204
    assert_not_found(api.delete(endpoints.gig(open_gig.id)))
