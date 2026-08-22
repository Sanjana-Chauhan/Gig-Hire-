"""Creating and reading gigs.

Covers cases GC-01 to GC-40 and GR-01 to GR-07 in TEST_CASES.md.
"""

import pytest

from tests import endpoints
from tests.assertions import (
    assert_created,
    assert_field_error,
    assert_not_found,
    assert_ok,
)
from tests.factories import GigFactory

pytestmark = pytest.mark.django_db


def gig_body(creator, **overrides):
    return {
        "creator": creator.id,
        "title": "Edit episode 12",
        "description": "Cut a forty-minute recording down to ten minutes.",
        "budget": "500.00",
        "category": "editing",
        **overrides,
    }


@pytest.mark.case("GC-01,GC-02")
def test_creating_a_gig_returns_the_stored_record_and_starts_it_open(api, creator):
    body = assert_created(api.post(endpoints.GIGS, gig_body(creator)))

    assert body["creator"] == creator.id
    assert body["title"] == "Edit episode 12"
    assert body["budget"] == "500.00"
    assert body["status"] == "open"


@pytest.mark.case("GC-03")
@pytest.mark.interpretation("I13")
def test_a_category_is_tidied_before_it_is_stored(api, creator):
    """Stored in one canonical form so filtering can find it later.

    Without this, "Editing", "editing" and " editing " would be three separate
    categories and a filter for any one of them would miss the others.
    """
    body = assert_created(
        api.post(endpoints.GIGS, gig_body(creator, category="  Editing "))
    )

    assert body["category"] == "editing"


@pytest.mark.case("GC-04,GC-05,GC-06,GC-07,GC-08")
@pytest.mark.parametrize(
    "overrides, field, expected",
    [
        pytest.param({"budget": "0.01"}, "budget", "0.01", id="smallest-budget"),
        pytest.param({"budget": 500}, "budget", "500.00", id="whole-number-budget"),
        pytest.param({"title": "x" * 200}, "title", "x" * 200, id="longest-title"),
        pytest.param({"category": "y" * 50}, "category", "y" * 50, id="longest-category"),
        pytest.param(
            {"description": "z" * 10000}, "description", "z" * 10000,
            id="very-long-description",
        ),
    ],
)
def test_a_gig_is_accepted_at_the_edges_of_what_is_allowed(
    api, creator, overrides, field, expected
):
    body = assert_created(api.post(endpoints.GIGS, gig_body(creator, **overrides)))

    assert body[field] == expected


@pytest.mark.case("GC-09,GC-10,GC-11,GC-12,GC-13")
@pytest.mark.parametrize(
    "missing", ["creator", "title", "description", "budget", "category"]
)
def test_every_gig_field_is_required(api, creator, missing):
    body = {k: v for k, v in gig_body(creator).items() if k != missing}

    assert_field_error(api.post(endpoints.GIGS, body), missing, code="required")


@pytest.mark.case("GC-14")
def test_an_empty_request_reports_all_five_missing_fields_at_once(api):
    response = api.post(endpoints.GIGS, {})

    assert response.status_code == 400
    assert set(response.data) == {
        "creator", "title", "description", "budget", "category",
    }


@pytest.mark.case("GC-15,GC-16,GC-17")
@pytest.mark.parametrize(
    "creator_value, expected_code",
    [
        pytest.param(999999, "does_not_exist", id="unknown-creator"),
        pytest.param("abc", "incorrect_type", id="not-a-number"),
        pytest.param(None, "null", id="no-value"),
    ],
)
def test_a_gig_must_name_a_creator_that_exists(api, creator, creator_value, expected_code):
    """400, not 404.

    The bad value is inside the request body, so the request is what is wrong.
    A 404 would be claiming the address does not exist, which it does.
    """
    body = {**gig_body(creator), "creator": creator_value}

    response = api.post(endpoints.GIGS, body, format="json")

    assert response.status_code == 400
    assert "creator" in response.data


@pytest.mark.case("GC-18,GC-19,GC-20,GC-21,GC-22,GC-23,GC-24")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "budget, expected_code",
    [
        pytest.param("0", "min_value", id="zero"),
        pytest.param("-100", "min_value", id="negative"),
        pytest.param("10.001", "max_decimal_places", id="three-decimal-places"),
        pytest.param("99999999999.99", "max_digits", id="too-many-digits"),
        pytest.param("five hundred", "invalid", id="text"),
        pytest.param(True, "invalid", id="true-false"),
        pytest.param("", "invalid", id="empty-text"),
        pytest.param(None, "null", id="no-value"),
    ],
)
def test_an_unusable_budget_is_refused(api, creator, budget, expected_code):
    response = api.post(
        endpoints.GIGS, gig_body(creator, budget=budget), format="json"
    )

    assert_field_error(response, "budget", code=expected_code)


@pytest.mark.case("GC-25,GC-26,GC-27,GC-28,GC-29,GC-30")
@pytest.mark.parametrize(
    "overrides, field, expected_code",
    [
        pytest.param({"title": ""}, "title", "blank", id="empty-title"),
        pytest.param({"title": "    "}, "title", "blank", id="title-of-spaces"),
        pytest.param({"title": "x" * 201}, "title", "max_length", id="title-too-long"),
        pytest.param({"description": ""}, "description", "blank", id="empty-description"),
        pytest.param(
            {"category": "y" * 51}, "category", "max_length", id="category-too-long"
        ),
        pytest.param({"title": ["Edit"]}, "title", "invalid", id="title-is-a-list"),
    ],
)
def test_an_unusable_text_field_is_refused(
    api, creator, overrides, field, expected_code
):
    response = api.post(
        endpoints.GIGS, gig_body(creator, **overrides), format="json"
    )

    assert_field_error(response, field, code=expected_code)


@pytest.mark.case("GC-32,GC-33")
def test_a_gig_may_be_created_as_open(api, creator):
    body = assert_created(api.post(endpoints.GIGS, gig_body(creator, status="open")))

    assert body["status"] == "open"


@pytest.mark.case("GC-34,GC-35,GC-36")
@pytest.mark.interpretation("S5")
@pytest.mark.parametrize("status", ["in_progress", "completed", "cancelled"])
def test_a_gig_cannot_be_created_in_any_state_but_open(api, creator, status):
    """Refused with an explanation, not silently ignored.

    A gig marked in progress with nobody hired and no agreement is a state that
    several later rules assume cannot exist. Making the field read-only would
    also have protected that, but read-only fields are dropped in silence -- so
    a caller sending "completed" would get a success response for a gig that was
    actually open and still taking applications.
    """
    response = api.post(endpoints.GIGS, gig_body(creator, status=status))

    assert_field_error(response, "status")
    assert status in str(response.data["status"])


@pytest.mark.case("GC-37,GC-38,GC-39")
@pytest.mark.parametrize(
    "status", ["nonsense", "OPEN", ""], ids=["not-a-status", "wrong-capitals", "empty"]
)
def test_a_status_outside_the_allowed_set_is_refused(api, creator, status):
    response = api.post(endpoints.GIGS, gig_body(creator, status=status))

    assert_field_error(response, "status", code="invalid_choice")


@pytest.mark.case("GR-01,GR-07")
def test_a_gig_can_be_read_back_and_names_its_creator_by_id(api, open_gig):
    """The creator comes back as a plain id, not a nested block.

    That matches the specification, and it means listing gigs never has to
    fetch the creator table -- so the number of queries does not grow with the
    number of gigs on the page.
    """
    body = assert_ok(api.get(endpoints.gig(open_gig.id)))

    assert body["id"] == open_gig.id
    assert body["creator"] == open_gig.creator_id
    assert isinstance(body["creator"], int)


@pytest.mark.case("GR-02,GR-03")
def test_reading_a_gig_that_does_not_exist_reports_not_found(api, open_gig):
    assert_not_found(api.get(endpoints.gig(999999)))

    api.delete(endpoints.gig(open_gig.id))
    assert_not_found(api.get(endpoints.gig(open_gig.id)))


@pytest.mark.case("GR-04,GR-05,GR-06")
@pytest.mark.parametrize("status", ["in_progress", "completed", "cancelled"])
def test_a_gig_can_be_read_in_any_state(api, creator, status):
    """Reading is always allowed, whatever the gig's state.

    Built with the factory on purpose: this checks only that the record can be
    read, so the route the gig took to reach that state is irrelevant here. The
    routes themselves are tested in test_gigs_transitions.py.
    """
    gig = GigFactory(creator=creator, status=status)

    body = assert_ok(api.get(endpoints.gig(gig.id)))

    assert body["status"] == status
