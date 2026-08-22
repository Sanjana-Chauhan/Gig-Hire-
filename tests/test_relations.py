"""Links between records, and what happens when one is removed.

Covers cases RE-01 to RE-38 in TEST_CASES.md.

The pattern worth noticing: when the missing thing is named **inside the request
body** the answer is 400, because the request is what is wrong. When it is named
**in the address** the answer is 404, because the thing being asked for does not
exist. Getting that backwards is a small thing that misleads every client.
"""

import pytest
from django.db.models import ProtectedError

from tests import endpoints
from tests.assertions import assert_created, assert_not_found, assert_ok, assert_page
from tests.factories import ApplicationFactory, GigFactory

pytestmark = pytest.mark.django_db


@pytest.mark.case("RE-01,RE-02")
@pytest.mark.parametrize(
    "what",
    [
        pytest.param("gig-names-a-creator", id="gig-creator"),
        pytest.param("bid-names-a-supplier", id="application-supplier"),
    ],
)
def test_a_link_named_in_the_request_body_must_exist_and_gives_400(
    api, creator, open_gig, what
):
    if what == "gig-names-a-creator":
        response = api.post(
            endpoints.GIGS,
            {
                "creator": 999999,
                "title": "t",
                "description": "d",
                "budget": "10.00",
                "category": "editing",
            },
        )
        field = "creator"
    else:
        response = api.post(
            endpoints.apply_to(open_gig.id),
            {"supplier_id": 999999, "proposed_rate": "10.00"},
        )
        field = "supplier_id"

    assert response.status_code == 400
    assert field in response.data


@pytest.mark.case("RE-03,RE-04,RE-05,RE-06")
def test_a_link_named_in_the_address_must_exist_and_gives_404(api, supplier):
    assert_not_found(
        api.post(
            endpoints.apply_to(999999),
            {"supplier_id": supplier.id, "proposed_rate": "10.00"},
        )
    )
    assert_not_found(
        api.post(
            endpoints.reviews_for(999999),
            {"reviewer_type": "creator_on_supplier", "rating": 4},
        )
    )
    assert_not_found(api.post(endpoints.complete(999999)))
    assert_not_found(api.post(endpoints.accept(999999)))


@pytest.mark.case("RE-07,RE-08,RE-09")
@pytest.mark.parametrize(
    "scenario",
    ["creator-with-gigs", "supplier-with-bids", "supplier-with-agreements"],
)
def test_a_record_others_depend_on_cannot_be_quietly_removed(
    api, creator, supplier, open_gig, apply_to_gig, hire, scenario
):
    """Checked at the database, because no endpoint exposes these deletes.

    That is the point: the protection is not "we did not build the button", it
    is that the data itself refuses. A future management command or admin action
    cannot destroy the history by accident.
    """
    if scenario == "creator-with-gigs":
        target = creator
    elif scenario == "supplier-with-bids":
        apply_to_gig(open_gig, supplier)
        target = supplier
    else:
        hire(supplier)
        target = supplier

    with pytest.raises(ProtectedError):
        target.delete()


@pytest.mark.case("RE-10")
@pytest.mark.interpretation("I14")
def test_deleting_a_gig_removes_its_bids(api, open_gig, supplier, apply_to_gig):
    apply_to_gig(open_gig, supplier)

    assert api.delete(endpoints.gig(open_gig.id)).status_code == 204

    assert_not_found(api.get(endpoints.applications_for(open_gig.id)))


@pytest.mark.case("RE-11,RE-12,RE-13")
def test_an_agreement_and_its_reviews_can_never_be_orphaned(api, supplier, hire):
    """Rule 7 in one test, from the other direction.

    Rather than checking that the delete is refused, this checks the property the
    refusal exists to protect: an agreement always points at a gig that exists,
    and a review always points at an agreement that exists.
    """
    agreement = hire(supplier)
    assert_ok(api.post(endpoints.complete(agreement["id"])))
    assert_created(
        api.post(
            endpoints.reviews_for(agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 5},
        )
    )

    api.delete(endpoints.gig(agreement["gig"]))

    assert_ok(api.get(endpoints.gig(agreement["gig"])))
    assert_page(api.get(endpoints.reviews_for(agreement["id"])), count=1)


@pytest.mark.case("RE-32,RE-33")
def test_values_the_service_owns_cannot_be_chosen_by_the_caller(api, creator):
    """An id and a creation date are the service's to assign.

    A caller supplying them is ignored rather than refused, which is the
    conventional behaviour for values that are not part of the input contract.
    """
    body = assert_created(
        api.post(
            endpoints.GIGS,
            {
                "id": 999,
                "created_at": "2000-01-01T00:00:00Z",
                "creator": creator.id,
                "title": "t",
                "description": "d",
                "budget": "10.00",
                "category": "editing",
            },
        )
    )

    assert body["id"] != 999
    assert not body["created_at"].startswith("2000")


@pytest.mark.case("RE-34")
def test_a_bid_cannot_be_created_already_accepted(api, open_gig, supplier):
    """Otherwise rule 3 could be bypassed entirely.

    An accepted bid with no agreement and an open gig is exactly the
    half-finished state the whole workflow exists to prevent.
    """
    body = assert_created(
        api.post(
            endpoints.apply_to(open_gig.id),
            {
                "supplier_id": supplier.id,
                "proposed_rate": "10.00",
                "status": "accepted",
            },
        )
    )

    assert body["status"] == "pending"


@pytest.mark.case("RE-36")
def test_the_changed_date_moves_when_a_record_changes(api, open_gig):
    before = assert_ok(api.get(endpoints.gig(open_gig.id)))

    after = assert_ok(api.patch(endpoints.gig(open_gig.id), {"title": "Changed"}))

    assert after["updated_at"] > before["updated_at"]
    assert after["created_at"] == before["created_at"]


@pytest.mark.case("RE-37")
def test_a_bid_turned_down_by_the_cascade_gets_a_new_changed_date(
    api, gig_with_three_bids
):
    """It really did change, so its timestamp should say so.

    The counterpart to the test that already-finished bids keep their old
    timestamp: the cascade is one bulk update, and a bulk update does not set
    timestamps by itself, so both halves need checking.
    """
    gig, bids = gig_with_three_bids
    before = bids[1]["updated_at"]

    assert_created(api.post(endpoints.accept(bids[0]["id"])))

    listing = assert_ok(api.get(endpoints.applications_for(gig.id)))
    turned_down = next(i for i in listing["results"] if i["id"] == bids[1]["id"])
    assert turned_down["status"] == "rejected"
    assert turned_down["updated_at"] > before
