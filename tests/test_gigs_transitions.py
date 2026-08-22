"""The gig lifecycle: status changes and frozen fields.

Covers cases GU-01 to GU-45 in TEST_CASES.md, business rule 8, and
interpretation I7 in DECISIONS.md.

The specification gives two example status changes out of sixteen possible
moves. The full table is swept below, illegal cells included -- those are where
the bugs live.
"""

import itertools

import pytest

from tests import endpoints
from tests.assertions import assert_conflict, assert_field_error, assert_ok
from tests.factories import GigFactory

pytestmark = pytest.mark.django_db

STATUSES = ["open", "in_progress", "completed", "cancelled"]

#: The moves the transition table permits. Everything else must be refused.
#: Same-to-same is a no-op and allowed; it changes nothing and claims nothing.
PERMITTED_MOVES = {
    ("open", "open"),
    ("open", "cancelled"),
    ("in_progress", "in_progress"),
    ("in_progress", "completed"),
    ("in_progress", "cancelled"),
    ("completed", "completed"),
    ("cancelled", "cancelled"),
}


@pytest.mark.case("GU-01,GU-02,GU-04,GU-05,GU-06")
@pytest.mark.rule("BR-08")
@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"budget": "1000.00"}, id="budget"),
        pytest.param({"category": "design"}, id="category"),
        pytest.param({"title": "Edit episode 13"}, id="title"),
        pytest.param({"description": "A different brief."}, id="description"),
        pytest.param(
            {"budget": "750.00", "category": "design", "title": "New"},
            id="several-at-once",
        ),
    ],
)
def test_every_field_can_be_changed_while_the_gig_is_open(api, open_gig, changes):
    body = assert_ok(api.patch(endpoints.gig(open_gig.id), changes))

    for field, value in changes.items():
        assert body[field] == value


@pytest.mark.case("GU-03")
def test_a_category_is_tidied_on_update_as_well_as_on_create(api, open_gig):
    body = assert_ok(api.patch(endpoints.gig(open_gig.id), {"category": "  Design "}))

    assert body["category"] == "design"


@pytest.mark.case("GU-07,GU-08,GU-09")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize("budget", ["0", "-1", "lots"])
def test_an_unusable_budget_is_still_refused_while_the_gig_is_open(
    api, open_gig, budget
):
    original = open_gig.budget

    assert_field_error(api.patch(endpoints.gig(open_gig.id), {"budget": budget}), "budget")

    open_gig.refresh_from_db()
    assert open_gig.budget == original


@pytest.mark.case("GU-24,GU-25,GU-26,GU-27,GU-28,GU-29,GU-32,GU-33,GU-34,GU-35,GU-36,GU-37,GU-38,GU-39")
@pytest.mark.rule("BR-08")
@pytest.mark.interpretation("I7")
@pytest.mark.parametrize(
    "start, target", list(itertools.product(STATUSES, STATUSES))
)
def test_the_complete_status_transition_table(api, creator, start, target):
    """All sixteen from/to combinations, in one sweep.

    Enumerating the cross product rather than the cases someone thought of is
    the point: a hand-written list would quietly omit a cell, and the omitted
    cell is usually the interesting one.

    Built with the factory so a gig can be placed in any starting state without
    the workflow that would normally get it there. What the workflow itself does
    is covered in test_hiring_accept.py; this checks only which moves the
    transition table allows.
    """
    gig = GigFactory(creator=creator, status=start)

    response = api.patch(endpoints.gig(gig.id), {"status": target})

    if (start, target) in PERMITTED_MOVES:
        body = assert_ok(response)
        assert body["status"] == target
    else:
        assert_conflict(response, "invalid_status_transition")
        gig.refresh_from_db()
        assert gig.status == start


@pytest.mark.case("GU-43,GU-44")
@pytest.mark.parametrize("status", ["finished", ""], ids=["not-a-status", "empty-text"])
def test_a_status_outside_the_allowed_set_is_refused(api, open_gig, status):
    assert_field_error(
        api.patch(endpoints.gig(open_gig.id), {"status": status}),
        "status",
        code="invalid_choice",
    )


@pytest.mark.case("GU-12")
def test_changing_a_gig_that_does_not_exist_reports_not_found(api):
    response = api.patch(endpoints.gig(999999), {"title": "Nobody"})

    assert response.status_code == 404


@pytest.mark.case("GU-13,GU-14,GU-15,GU-16,GU-17,GU-18")
@pytest.mark.rule("BR-08")
@pytest.mark.parametrize("status", ["in_progress", "completed", "cancelled"])
@pytest.mark.parametrize(
    "field, value", [("budget", "999.00"), ("category", "design")]
)
def test_budget_and_category_freeze_once_the_gig_leaves_open(
    api, creator, status, field, value
):
    """Six combinations: three states, two frozen fields.

    409 rather than 400: while the gig was open these fields were perfectly
    editable, so the request is not malformed -- it is late.
    """
    gig = GigFactory(creator=creator, status=status)
    original = getattr(gig, field)

    response = api.patch(endpoints.gig(gig.id), {field: value})

    assert_conflict(response, "gig_fields_immutable")
    gig.refresh_from_db()
    assert getattr(gig, field) == original


@pytest.mark.case("GU-19")
def test_sending_both_frozen_fields_names_both_in_the_message(api, creator):
    gig = GigFactory(creator=creator, status="in_progress")

    response = api.patch(
        endpoints.gig(gig.id), {"budget": "999.00", "category": "design"}
    )

    detail = assert_conflict(response, "gig_fields_immutable")["detail"]
    assert "budget" in detail
    assert "category" in detail


@pytest.mark.case("GU-20")
@pytest.mark.interpretation("S2")
def test_a_frozen_field_is_refused_even_when_the_value_is_unchanged(api, creator):
    """Refused because the field was *sent*, not because the value differs.

    "You may not send this field now" is a simpler and more predictable rule
    than "you may send it if the value happens to match". The permissive version
    would make the answer depend on data the caller may not have fresh, and give
    two callers different answers for identical requests.
    """
    gig = GigFactory(creator=creator, status="in_progress", budget="500.00")

    response = api.patch(endpoints.gig(gig.id), {"budget": "500.00"})

    assert_conflict(response, "gig_fields_immutable")


@pytest.mark.case("GU-21,GU-22,GU-23")
@pytest.mark.parametrize("status", ["in_progress", "completed", "cancelled"])
@pytest.mark.parametrize(
    "field, value",
    [("title", "Corrected typo"), ("description", "A clearer brief.")],
)
def test_title_and_description_stay_editable_after_the_gig_leaves_open(
    api, creator, status, field, value
):
    """Rule 8 names only budget and category.

    Read literally, so fixing a typo in a brief stays possible. Whether that was
    deliberate is open question Q4 in DECISIONS.md.
    """
    gig = GigFactory(creator=creator, status=status)

    body = assert_ok(api.patch(endpoints.gig(gig.id), {field: value}))

    assert body[field] == value


@pytest.mark.case("GU-40,GU-41")
@pytest.mark.rule("BR-08")
@pytest.mark.parametrize("target", ["completed", "cancelled"])
def test_a_gig_cannot_be_closed_while_its_agreement_is_live(
    api, supplier, hire, target
):
    """The agreement has to be dealt with first.

    Reached by actually hiring someone, so the gig is in progress for the reason
    the service says it is: a live agreement exists.
    """
    agreement = hire(supplier)

    response = api.patch(endpoints.gig(agreement["gig"]), {"status": target})

    assert_conflict(response, "gig_has_active_contract")
    assert assert_ok(api.get(endpoints.gig(agreement["gig"])))["status"] == "in_progress"


@pytest.mark.case("GU-42")
@pytest.mark.rule("BR-08")
def test_a_gig_can_be_completed_once_its_agreement_is_complete(api, supplier, hire):
    agreement = hire(supplier)
    assert_ok(api.post(endpoints.complete(agreement["id"])))

    body = assert_ok(api.patch(endpoints.gig(agreement["gig"]), {"status": "completed"}))

    assert body["status"] == "completed"


@pytest.mark.case("GU-45")
def test_a_gig_being_worked_on_cannot_be_abandoned(api, supplier, hire):
    """The gap behind open question Q2, shown rather than described.

    A supplier who takes a job and disappears leaves the creator with no way
    out: cancelling needs no live agreement, the only way to clear one is to
    mark it complete, and nothing can end an agreement that failed. Marking it
    complete would record work that was never delivered.
    """
    agreement = hire(supplier)

    assert_conflict(
        api.patch(endpoints.gig(agreement["gig"]), {"status": "cancelled"}),
        "gig_has_active_contract",
    )

    # The only door that opens is the one that claims success.
    assert_ok(api.post(endpoints.complete(agreement["id"])))
    assert_ok(api.patch(endpoints.gig(agreement["gig"]), {"status": "completed"}))
