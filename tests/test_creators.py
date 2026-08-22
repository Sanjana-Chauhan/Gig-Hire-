"""Creating, reading and changing creators.

Covers cases CR-01 to CR-38 in TEST_CASES.md.
"""

import pytest

from tests import endpoints
from tests.assertions import (
    assert_created,
    assert_field_error,
    assert_method_not_allowed,
    assert_not_found,
    assert_ok,
    assert_page,
)
from tests.factories import CreatorFactory

pytestmark = pytest.mark.django_db

VALID_CREATOR = {
    "name": "Ada",
    "email": "ada@example.com",
    "channel_name": "AdaCodes",
}


@pytest.mark.case("CR-01")
def test_creating_a_creator_with_every_field_returns_the_stored_record(api):
    body = assert_created(api.post(endpoints.CREATORS, VALID_CREATOR))

    assert body["name"] == "Ada"
    assert body["email"] == "ada@example.com"
    assert body["channel_name"] == "AdaCodes"
    assert body["id"] is not None
    assert body["created_at"] is not None


@pytest.mark.case("CR-02")
def test_an_email_is_stored_lowercased_and_trimmed(api):
    body = assert_created(
        api.post(endpoints.CREATORS, {**VALID_CREATOR, "email": " Ada@Example.COM "})
    )

    assert body["email"] == "ada@example.com"


@pytest.mark.case("CR-03")
@pytest.mark.parametrize("field", ["name", "channel_name"])
def test_a_text_field_accepts_its_maximum_length(api, field):
    body = assert_created(
        api.post(endpoints.CREATORS, {**VALID_CREATOR, field: "x" * 150})
    )

    assert body[field] == "x" * 150


@pytest.mark.case("CR-22")
def test_an_unrecognised_field_is_ignored_rather_than_rejected(api):
    body = assert_created(
        api.post(endpoints.CREATORS, {**VALID_CREATOR, "nickname": "Adz"})
    )

    assert "nickname" not in body


@pytest.mark.case("CR-05,CR-06,CR-07")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize("missing", ["name", "email", "channel_name"])
def test_every_field_is_required(api, missing):
    body = {key: value for key, value in VALID_CREATOR.items() if key != missing}

    assert_field_error(api.post(endpoints.CREATORS, body), missing, code="required")


@pytest.mark.case("CR-08")
def test_an_empty_request_reports_every_missing_field_at_once(api):
    """All three problems come back together, not one at a time.

    Reporting only the first would make a caller fix and resubmit three times to
    learn what a single response could have told them.
    """
    response = api.post(endpoints.CREATORS, {})

    assert response.status_code == 400
    assert set(response.data) == {"name", "email", "channel_name"}


@pytest.mark.case("CR-09,CR-10,CR-11")
@pytest.mark.parametrize(
    "value, expected_code",
    [
        pytest.param("", "blank", id="empty-text"),
        pytest.param("   ", "blank", id="only-spaces"),
        pytest.param(None, "null", id="no-value-at-all"),
    ],
)
def test_a_name_must_have_content(api, value, expected_code):
    response = api.post(
        endpoints.CREATORS, {**VALID_CREATOR, "name": value}, format="json"
    )

    assert_field_error(response, "name", code=expected_code)


@pytest.mark.case("CR-18")
def test_a_name_longer_than_the_limit_is_refused(api):
    response = api.post(endpoints.CREATORS, {**VALID_CREATOR, "name": "x" * 151})

    assert_field_error(response, "name", code="max_length")


@pytest.mark.case("CR-12,CR-13,CR-14")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "email",
    ["not-an-email", "ada@", "@example.com", "ada example.com", "ada@@example.com"],
)
def test_a_malformed_email_is_refused(api, email):
    response = api.post(endpoints.CREATORS, {**VALID_CREATOR, "email": email})

    assert_field_error(response, "email", code="invalid")


@pytest.mark.case("CR-15,CR-16,CR-17")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "second_email",
    [
        pytest.param("ada@example.com", id="identical"),
        pytest.param("ADA@Example.com", id="different-capitals"),
        pytest.param("  ada@example.com  ", id="surrounded-by-spaces"),
    ],
)
def test_a_duplicate_email_is_refused_as_a_field_error_not_a_database_error(
    api, second_email
):
    """Business rule 10: never a raw database error.

    A duplicate must come back as 400 naming the email field. A 409 would mean
    the check reached the database instead of being caught at the boundary, and
    the message would be a constraint name rather than something a person can
    act on.
    """
    assert_created(api.post(endpoints.CREATORS, VALID_CREATOR))

    response = api.post(endpoints.CREATORS, {**VALID_CREATOR, "email": second_email})

    assert_field_error(response, "email", code="unique")


@pytest.mark.case("CR-19,CR-20,CR-21")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(True, id="true-false"),
        pytest.param(["Ada"], id="a-list"),
        pytest.param({"first": "Ada"}, id="nested-values"),
    ],
)
def test_a_value_that_is_not_text_is_refused(api, value):
    response = api.post(
        endpoints.CREATORS, {**VALID_CREATOR, "name": value}, format="json"
    )

    assert_field_error(response, "name", code="invalid")


@pytest.mark.interpretation("I13")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("['hello']", id="text-that-looks-like-a-list"),
        pytest.param('{"a": 1}', id="text-that-looks-like-a-structure"),
        pytest.param("123", id="digits-written-as-text"),
        pytest.param("Ada & Co.", id="text-with-punctuation"),
    ],
)
def test_text_containing_punctuation_or_digits_is_valid_text(api, value):
    """Anything genuinely text is accepted, whatever it looks like.

    ``"['hello']"`` is a string that happens to contain brackets. Refusing it
    would mean second-guessing what people may call themselves. The distinction
    that matters is text versus structure, not text versus tidy text.
    """
    body = assert_created(
        api.post(endpoints.CREATORS, {**VALID_CREATOR, "name": value}, format="json")
    )

    assert body["name"] == value


@pytest.mark.case("CR-23")
def test_a_creator_can_be_read_back_by_id(api, creator):
    body = assert_ok(api.get(endpoints.creator(creator.id)))

    assert body["id"] == creator.id
    assert body["email"] == creator.email


@pytest.mark.case("CR-24,CR-25")
@pytest.mark.parametrize(
    "creator_id", [999999, "abc"], ids=["unknown-id", "not-a-number"]
)
def test_reading_a_creator_that_does_not_exist_reports_not_found(api, creator_id):
    assert_not_found(api.get(endpoints.creator(creator_id)))


@pytest.mark.case("CR-26")
def test_listing_creators_when_there_are_none_returns_an_empty_page(api):
    """An empty collection is a success, not an error."""
    assert_page(api.get(endpoints.CREATORS), count=0, returned=0)


@pytest.mark.case("CR-27")
def test_creators_are_listed_newest_first(api):
    first = CreatorFactory()
    second = CreatorFactory()

    body = assert_page(api.get(endpoints.CREATORS), count=2, returned=2)

    assert [item["id"] for item in body["results"]] == [second.id, first.id]


@pytest.mark.case("CR-28,CR-29,CR-30,CR-31")
@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"name": "Ada Renamed"}, id="name"),
        pytest.param({"channel_name": "NewChannel"}, id="channel-name"),
        pytest.param({"email": "renamed@example.com"}, id="email"),
        pytest.param(
            {"name": "N", "email": "n@example.com", "channel_name": "NC"},
            id="all-three-together",
        ),
    ],
)
def test_a_creator_can_be_changed(api, creator, changes):
    """Ordinary account maintenance is allowed.

    The specification lists no creator endpoints at all, so this is an addition
    (A-2 in DECISIONS.md). Without it a creator who rebrands or changes email
    would have to start again and abandon their gig history.
    """
    body = assert_ok(api.patch(endpoints.creator(creator.id), changes))

    for field, value in changes.items():
        assert body[field] == value


@pytest.mark.case("CR-32")
def test_changing_one_field_leaves_the_others_alone(api, creator):
    body = assert_ok(api.patch(endpoints.creator(creator.id), {"name": "Only Name"}))

    assert body["name"] == "Only Name"
    assert body["email"] == creator.email
    assert body["channel_name"] == creator.channel_name


@pytest.mark.case("CR-33")
def test_changing_an_email_to_a_malformed_one_is_refused(api, creator):
    original = creator.email

    response = api.patch(endpoints.creator(creator.id), {"email": "not-an-email"})

    assert_field_error(response, "email", code="invalid")
    creator.refresh_from_db()
    assert creator.email == original


@pytest.mark.case("CR-34,CR-35")
@pytest.mark.parametrize(
    "casing",
    ["ada@example.com", "ADA@Example.com"],
    ids=["same", "different-capitals"],
)
def test_changing_an_email_to_one_already_taken_is_refused(api, casing):
    CreatorFactory(email="ada@example.com")
    second = CreatorFactory(email="ben@example.com")

    response = api.patch(endpoints.creator(second.id), {"email": casing})

    assert_field_error(response, "email", code="unique")
    second.refresh_from_db()
    assert second.email == "ben@example.com"


@pytest.mark.case("CR-36")
def test_changing_a_creator_that_does_not_exist_reports_not_found(api):
    assert_not_found(api.patch(endpoints.creator(999999), {"name": "Nobody"}))


@pytest.mark.case("CR-37")
def test_a_creator_cannot_be_deleted(api, creator):
    """Deleting a creator would put their whole gig history at risk.

    Their gigs are protected, so a delete would either fail at the database or
    silently destroy history. Not exposing it at all is the honest answer -- see
    D-4 in DECISIONS.md.
    """
    assert_method_not_allowed(api.delete(endpoints.creator(creator.id)))

    assert_ok(api.get(endpoints.creator(creator.id)))


@pytest.mark.case("CR-38")
def test_a_newly_created_creator_can_post_a_gig(api):
    """The reason the creator endpoints had to be added at all.

    Every gig needs a creator, and the specification provides no way to make
    one. This test is the proof that the API is usable from an empty database.
    """
    creator = assert_created(api.post(endpoints.CREATORS, VALID_CREATOR))

    gig = assert_created(
        api.post(
            endpoints.GIGS,
            {
                "creator": creator["id"],
                "title": "Edit episode 12",
                "description": "Cut to ten minutes.",
                "budget": "500.00",
                "category": "editing",
            },
        )
    )

    assert gig["creator"] == creator["id"]
    assert gig["status"] == "open"
