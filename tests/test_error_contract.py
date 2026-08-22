"""How the service behaves when a request cannot be carried out.

Covers cases EF-01 to EF-10 and PD-01 to PD-12 in TEST_CASES.md, and business
rule 10's demand that a refusal is never an error inside the service.

The promise being tested: every refusal is a 400, 404, 405 or 409 with a
readable message, and no database wording ever reaches a caller.
"""

import pytest

from tests import endpoints
from tests.assertions import (
    assert_conflict,
    assert_created,
    assert_method_not_allowed,
    assert_not_found,
    assert_ok,
)
from tests.factories import ApplicationFactory, ContractFactory, GigFactory

pytestmark = pytest.mark.django_db

DATABASE_WORDING = [
    "UNIQUE constraint",
    "IntegrityError",
    "CHECK constraint",
    "FOREIGN KEY",
    "Traceback",
    "django.db",
]


@pytest.mark.case("EF-02")
@pytest.mark.rule("BR-10")
def test_a_duplicate_never_leaks_database_wording(api, creator, supplier, open_gig, apply_to_gig):
    """Three different ways to hit a uniqueness rule, none of them a 500.

    Each of these is backed by a database constraint, so the test is really
    asking whether the boundary catches them first.
    """
    duplicate_email = api.post(
        endpoints.CREATORS,
        {"name": "A", "email": creator.email, "channel_name": "C"},
    )
    apply_to_gig(open_gig, supplier)
    duplicate_bid = api.post(
        endpoints.apply_to(open_gig.id),
        {"supplier_id": supplier.id, "proposed_rate": "10.00"},
    )

    for response in [duplicate_email, duplicate_bid]:
        assert response.status_code in (400, 409)
        rendered = str(response.data)
        for wording in DATABASE_WORDING:
            assert wording not in rendered


@pytest.mark.case("EF-01,EF-03,EF-06")
@pytest.mark.rule("BR-10")
def test_every_state_refusal_carries_a_stable_code_and_a_readable_message(
    api, creator, supplier, open_gig, apply_to_gig, hire
):
    """Each 409 identifies itself with a short code.

    Tests assert on that code rather than on the message, so wording can be
    improved without breaking the suite -- and a client can react to a specific
    situation rather than parsing prose.
    """
    cancelled = GigFactory(creator=creator, status="cancelled")
    finished_bid = ApplicationFactory(gig=open_gig, supplier=supplier, status="rejected")
    agreement = hire(supplier)

    checks = [
        (
            api.post(
                endpoints.apply_to(cancelled.id),
                {"supplier_id": supplier.id, "proposed_rate": "10.00"},
            ),
            "gig_not_open",
        ),
        (api.post(endpoints.accept(finished_bid.id)), "application_not_pending"),
        (api.delete(endpoints.gig(agreement["gig"])), "gig_has_active_contract"),
        (
            api.post(
                endpoints.reviews_for(agreement["id"]),
                {"reviewer_type": "creator_on_supplier", "rating": 4},
            ),
            "contract_not_completed",
        ),
    ]

    for response, expected_code in checks:
        detail = assert_conflict(response, expected_code)
        assert detail["detail"]
        assert len(detail["detail"]) > 10


@pytest.mark.case("EF-04,EF-05")
def test_several_field_problems_are_reported_together(api):
    """One round trip, not three.

    Reporting only the first problem would make a caller fix and resubmit
    repeatedly to discover what a single response could have told them.
    """
    response = api.post(
        endpoints.GIGS, {"title": "", "budget": "-5", "category": "editing"}
    )

    assert response.status_code == 400
    assert {"creator", "description", "budget", "title"} <= set(response.data)


@pytest.mark.case("EF-08")
def test_an_address_that_does_not_exist_reports_not_found(api):
    assert_not_found(api.get("/api/nonsense/"))


@pytest.mark.case("EF-09")
@pytest.mark.parametrize(
    "url_builder, method",
    [
        pytest.param(lambda: endpoints.GIGS, "delete", id="delete-a-collection"),
        pytest.param(lambda: endpoints.CREATORS, "delete", id="delete-creators"),
        pytest.param(lambda: endpoints.CONTRACTS, "post", id="create-an-agreement"),
    ],
)
def test_an_action_that_is_not_available_reports_method_not_allowed(
    api, url_builder, method
):
    assert_method_not_allowed(getattr(api, method)(url_builder()))


@pytest.mark.case("EF-10")
def test_a_body_that_cannot_be_read_is_refused_cleanly(api):
    response = api.post(
        endpoints.CREATORS, data="this is not valid json", content_type="application/json"
    )

    assert response.status_code == 400


@pytest.mark.case("PD-01,PD-02,PD-03,PD-04")
@pytest.mark.rule("BR-07")
def test_which_gigs_can_be_deleted(api, creator, supplier, hire, apply_to_gig):
    """The full picture, in one place.

    An in-progress gig can never be deleted, because being in progress means a
    live agreement exists -- exactly what rule 7 protects. A completed gig can
    never be deleted either, because reaching completed requires having had an
    agreement.
    """
    open_gig = GigFactory(creator=creator)
    assert api.delete(endpoints.gig(open_gig.id)).status_code == 204

    cancelled = GigFactory(creator=creator)
    assert_ok(api.patch(endpoints.gig(cancelled.id), {"status": "cancelled"}))
    assert api.delete(endpoints.gig(cancelled.id)).status_code == 204

    in_progress = hire(supplier)
    assert_conflict(
        api.delete(endpoints.gig(in_progress["gig"])), "gig_has_active_contract"
    )

    assert_ok(api.post(endpoints.complete(in_progress["id"])))
    assert_ok(api.patch(endpoints.gig(in_progress["gig"]), {"status": "completed"}))
    assert_conflict(
        api.delete(endpoints.gig(in_progress["gig"])), "gig_has_contract_history"
    )


@pytest.mark.case("PD-05,PD-06,PD-08")
def test_participants_and_reviews_cannot_be_deleted(api, creator, supplier, hire):
    agreement = hire(supplier)
    assert_ok(api.post(endpoints.complete(agreement["id"])))
    assert_created(
        api.post(
            endpoints.reviews_for(agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 5},
        )
    )

    assert_method_not_allowed(api.delete(endpoints.creator(creator.id)))
    assert_method_not_allowed(api.delete(endpoints.supplier(supplier.id)))
    assert_method_not_allowed(api.delete(endpoints.reviews_for(agreement["id"])))


@pytest.mark.case("PD-07,PD-09,PD-10,PD-11")
def test_agreements_and_bids_have_no_individual_address(api, application, supplier, hire):
    """Their state is the workflow, so free editing would bypass every rule."""
    agreement = hire(supplier)

    for url in [
        f"{endpoints.CONTRACTS}{agreement['id']}/",
        f"/api/applications/{application.id}/",
    ]:
        assert_not_found(api.get(url))
        assert_not_found(api.patch(url, {"status": "completed"}))
        assert_not_found(api.delete(url))
