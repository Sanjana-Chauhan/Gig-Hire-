"""The complete journey, from an empty database to both reviews left.

Covers case E2E-01 in TEST_CASES.md.

Every other module builds some of its setup with factories, which is fast and
correct for preconditions the workflow does not own. This module builds
*everything* through the API, so that one test proves the service is usable end
to end by a real client -- including the parts that only exist because the
specification omitted them, like creating a creator.

If a factory ever drifts out of step with what the API actually produces, this is
the test that notices.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_conflict, assert_created, assert_ok, assert_page

pytestmark = [pytest.mark.django_db, pytest.mark.smoke]


@pytest.mark.case("E2E-01")
def test_the_whole_hiring_journey_through_the_api(api):
    # 1-3. The cast. Nothing exists before this point.
    creator = assert_created(
        api.post(
            endpoints.CREATORS,
            {"name": "Ada", "email": "ada@example.com", "channel_name": "AdaCodes"},
        )
    )
    winner = assert_created(
        api.post(
            endpoints.SUPPLIERS,
            {
                "name": "Xena",
                "email": "xena@example.com",
                "skills": ["Video-Editing", "thumbnails"],
                "hourly_rate": "45.00",
            },
            format="json",
        )
    )
    runner_up = assert_created(
        api.post(
            endpoints.SUPPLIERS,
            {
                "name": "Yuri",
                "email": "yuri@example.com",
                "skills": ["editing"],
                "hourly_rate": "38.00",
            },
            format="json",
        )
    )
    assert winner["skills"] == ["video-editing", "thumbnails"]

    # 4. The work, posted with an untidy category.
    gig = assert_created(
        api.post(
            endpoints.GIGS,
            {
                "creator": creator["id"],
                "title": "Edit episode 12",
                "description": "Cut a forty-minute recording down to ten minutes.",
                "budget": "500.00",
                "category": "  Editing ",
            },
        )
    )
    assert gig["status"] == "open"
    assert gig["category"] == "editing"

    # 5-6. Two bids, one above and one below the eventual agreement.
    winning_bid = assert_created(
        api.post(
            endpoints.apply_to(gig["id"]),
            {"supplier_id": winner["id"], "proposed_rate": "420.00"},
        )
    )
    losing_bid = assert_created(
        api.post(
            endpoints.apply_to(gig["id"]),
            {"supplier_id": runner_up["id"], "proposed_rate": "390.00"},
        )
    )
    assert_page(api.get(endpoints.applications_for(gig["id"])), count=2)

    # 7-12. Hiring: agreement created, gig moved, other bid turned down.
    agreement = assert_created(api.post(endpoints.accept(winning_bid["id"])))
    assert agreement["status"] == "active"
    # The amount agreed for the job -- not the 45.00 profile rate, not the 500.00 budget.
    assert agreement["agreed_rate"] == "420.00"

    statuses = {
        item["id"]: item["status"]
        for item in assert_ok(api.get(endpoints.applications_for(gig["id"])))["results"]
    }
    assert statuses[winning_bid["id"]] == "accepted"
    assert statuses[losing_bid["id"]] == "rejected"
    assert assert_ok(api.get(endpoints.gig(gig["id"])))["status"] == "in_progress"

    # 13-15. What is refused while the work is under way.
    assert_conflict(
        api.post(
            endpoints.reviews_for(agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 5},
        ),
        "contract_not_completed",
    )
    assert_conflict(
        api.patch(endpoints.gig(gig["id"]), {"budget": "600.00"}),
        "gig_fields_immutable",
    )
    assert_conflict(api.delete(endpoints.gig(gig["id"])), "gig_has_active_contract")

    # 16-17. Both filters find the one agreement.
    assert_page(
        api.get(f"{endpoints.CONTRACTS}?supplier_id={winner['id']}"), count=1
    )
    assert_page(
        api.get(f"{endpoints.CONTRACTS}?creator_id={creator['id']}"), count=1
    )

    # 18-20. Finishing: the agreement first, then the creator signs the gig off.
    assert (
        assert_ok(api.post(endpoints.complete(agreement["id"])))["status"] == "completed"
    )
    assert assert_ok(api.get(endpoints.gig(gig["id"])))["status"] == "in_progress"
    assert (
        assert_ok(api.patch(endpoints.gig(gig["id"]), {"status": "completed"}))["status"]
        == "completed"
    )

    # 21-24. Both sides review, and neither can review twice.
    assert_created(
        api.post(
            endpoints.reviews_for(agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 5, "comment": "Fast."},
        )
    )
    assert_created(
        api.post(
            endpoints.reviews_for(agreement["id"]),
            {"reviewer_type": "supplier_on_creator", "rating": 4, "comment": "Clear."},
        )
    )
    assert_conflict(
        api.post(
            endpoints.reviews_for(agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 1},
        ),
        "duplicate_review",
    )
    assert_page(api.get(endpoints.reviews_for(agreement["id"])), count=2)

    # 25. The reputation record survives a delete attempt.
    assert_conflict(api.delete(endpoints.gig(gig["id"])), "gig_has_contract_history")
    assert_page(api.get(endpoints.reviews_for(agreement["id"])), count=2)

    # 26-27. The supplier is free to work again.
    final_supplier = assert_ok(api.get(endpoints.supplier(winner["id"])))
    assert final_supplier["availability_status"] == "available"
    live = [
        item
        for item in assert_ok(
            api.get(f"{endpoints.CONTRACTS}?supplier_id={winner['id']}")
        )["results"]
        if item["status"] == "active"
    ]
    assert live == []
