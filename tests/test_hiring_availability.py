"""Availability is checked when hiring, not when applying.

Covers cases AV-01 to AV-07 in TEST_CASES.md, and business rule 5.

This is the deliberate edge case in the specification: a supplier who was
available when they applied can be blocked later. The timing is part of the
requirement, not an implementation detail -- "validate as early as possible" is
good advice that is wrong here, and moving the check to the apply endpoint would
silently prevent a case the specification explicitly permits.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_conflict, assert_created, assert_ok, assert_page

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-05")]


@pytest.mark.case("AV-01,AV-02")
def test_a_supplier_who_goes_inactive_after_applying_cannot_be_hired(
    api, open_gig, supplier, apply_to_gig
):
    """The exact sequence the specification describes.

    Available when applying, inactive by the time the creator accepts. The bid
    must stay pending, the gig must stay open, and no agreement may appear --
    a refusal has to write nothing at all.
    """
    bid = apply_to_gig(open_gig, supplier)
    assert_ok(
        api.patch(endpoints.supplier(supplier.id), {"availability_status": "inactive"})
    )

    assert_conflict(api.post(endpoints.accept(bid["id"])), "supplier_not_hireable")

    listing = assert_page(api.get(endpoints.applications_for(open_gig.id)), count=1)
    assert listing["results"][0]["status"] == "pending"
    assert assert_ok(api.get(endpoints.gig(open_gig.id)))["status"] == "open"
    contracts = assert_ok(api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier.id}"))
    assert contracts["count"] == 0


@pytest.mark.case("AV-03")
def test_hiring_works_once_the_supplier_is_available_again(
    api, open_gig, supplier, apply_to_gig
):
    """The bid survives the refusal, so it can still be accepted later.

    This is why a refused hire must leave the bid pending rather than rejecting
    it: the situation is temporary.
    """
    bid = apply_to_gig(open_gig, supplier)
    assert_ok(
        api.patch(endpoints.supplier(supplier.id), {"availability_status": "inactive"})
    )
    assert_conflict(api.post(endpoints.accept(bid["id"])), "supplier_not_hireable")

    assert_ok(
        api.patch(endpoints.supplier(supplier.id), {"availability_status": "available"})
    )
    agreement = assert_created(api.post(endpoints.accept(bid["id"])))

    assert agreement["status"] == "active"
    assert assert_ok(api.get(endpoints.gig(open_gig.id)))["status"] == "in_progress"


@pytest.mark.case("AV-04")
def test_a_supplier_inactive_from_the_start_may_apply_but_not_be_hired(
    api, open_gig, inactive_supplier, apply_to_gig
):
    """Applying is allowed, hiring is not.

    Two different answers for the same supplier, which is the whole point of
    rule 5 putting the check at accept-time.
    """
    bid = apply_to_gig(open_gig, inactive_supplier)

    assert bid["status"] == "pending"
    assert_conflict(api.post(endpoints.accept(bid["id"])), "supplier_not_hireable")


@pytest.mark.case("AV-06")
def test_being_hired_does_not_make_an_under_loaded_supplier_unavailable(
    api, open_gig, supplier, apply_to_gig
):
    """One job does not make a supplier busy.

    Availability tracks the agreement limit, so a supplier holding one job out
    of three allowed is still available.
    """
    bid = apply_to_gig(open_gig, supplier)
    assert_created(api.post(endpoints.accept(bid["id"])))

    body = assert_ok(api.get(endpoints.supplier(supplier.id)))
    assert body["availability_status"] == "available"


@pytest.mark.case("AV-07")
def test_one_bidder_being_inactive_does_not_block_hiring_another(
    api, open_gig, supplier, inactive_supplier, apply_to_gig
):
    """Only the supplier actually being hired is checked."""
    unavailable_bid = apply_to_gig(open_gig, inactive_supplier)
    good_bid = apply_to_gig(open_gig, supplier)

    assert_created(api.post(endpoints.accept(good_bid["id"])))

    listing = assert_page(api.get(endpoints.applications_for(open_gig.id)), count=2)
    statuses = {item["id"]: item["status"] for item in listing["results"]}
    assert statuses[good_bid["id"]] == "accepted"
    assert statuses[unavailable_bid["id"]] == "rejected"
