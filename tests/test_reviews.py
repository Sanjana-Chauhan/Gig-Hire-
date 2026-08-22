"""Leaving reviews on a finished agreement.

Covers cases RV-01 to RV-49 in TEST_CASES.md, and business rules 9 and 10.

Two rules: a review can only be left on a completed agreement, and each of the
two kinds may be left only once per agreement.
"""

import pytest

from tests import endpoints
from tests.assertions import (
    assert_conflict,
    assert_created,
    assert_field_error,
    assert_method_not_allowed,
    assert_not_found,
    assert_ok,
    assert_page,
)
from tests.factories import ContractFactory

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-09")]

KINDS = ["creator_on_supplier", "supplier_on_creator"]


@pytest.fixture
def finished_agreement(api, supplier, hire):
    """An agreement that has been carried out and marked complete."""
    agreement = hire(supplier)
    return assert_ok(api.post(endpoints.complete(agreement["id"])))


@pytest.mark.case("RV-01")
@pytest.mark.parametrize("kind", KINDS)
def test_a_review_can_be_left_on_a_completed_agreement(api, finished_agreement, kind):
    body = assert_created(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": kind, "rating": 5, "comment": "Fast and clean."},
        )
    )

    assert body["contract"] == finished_agreement["id"]
    assert body["reviewer_type"] == kind
    assert body["rating"] == 5
    assert body["comment"] == "Fast and clean."


@pytest.mark.case("RV-02")
def test_an_agreement_still_being_worked_on_cannot_be_reviewed(api, supplier, hire):
    agreement = hire(supplier)

    response = api.post(
        endpoints.reviews_for(agreement["id"]),
        {"reviewer_type": "creator_on_supplier", "rating": 5},
    )

    assert_conflict(response, "contract_not_completed")
    assert_page(api.get(endpoints.reviews_for(agreement["id"])), count=0)


@pytest.mark.case("RV-03")
def test_a_terminated_agreement_can_never_be_reviewed(api, supplier):
    """As specified, and flagged.

    How a job went wrong is often the most useful signal a marketplace has, and
    rule 9 makes it impossible to record. Currently moot anyway, because nothing
    can produce a terminated agreement -- open questions Q2 and Q3 in
    DECISIONS.md.
    """
    agreement = ContractFactory(supplier=supplier, status="terminated")

    response = api.post(
        endpoints.reviews_for(agreement.id),
        {"reviewer_type": "creator_on_supplier", "rating": 5},
    )

    assert_conflict(response, "contract_not_completed")


@pytest.mark.case("RV-04,RV-05")
def test_both_sides_can_review_the_same_agreement(api, finished_agreement):
    """One review per direction, so two on one agreement is correct."""
    for kind in KINDS:
        assert_created(
            api.post(
                endpoints.reviews_for(finished_agreement["id"]),
                {"reviewer_type": kind, "rating": 4},
            )
        )

    assert_page(api.get(endpoints.reviews_for(finished_agreement["id"])), count=2)


@pytest.mark.case("RV-06,RV-07,RV-08")
@pytest.mark.parametrize("kind", KINDS)
def test_the_same_kind_of_review_cannot_be_left_twice(api, finished_agreement, kind):
    """A creator cannot pile on, and neither can a supplier.

    Note this is an unconditional rule, unlike the one-live-bid rule on
    applications: there is no such thing as a withdrawn review, so no state
    retires an old one and lets a new one through.
    """
    assert_created(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": kind, "rating": 5},
        )
    )

    response = api.post(
        endpoints.reviews_for(finished_agreement["id"]),
        {"reviewer_type": kind, "rating": 1},
    )

    assert_conflict(response, "duplicate_review")
    listing = assert_page(
        api.get(endpoints.reviews_for(finished_agreement["id"])), count=1
    )
    assert listing["results"][0]["rating"] == 5


@pytest.mark.case("RV-09")
def test_the_limit_is_per_agreement_not_per_platform(
    api, supplier, other_supplier, hire
):
    first = hire(supplier)
    second = hire(other_supplier)
    for agreement in [first, second]:
        assert_ok(api.post(endpoints.complete(agreement["id"])))

    for agreement in [first, second]:
        assert_created(
            api.post(
                endpoints.reviews_for(agreement["id"]),
                {"reviewer_type": "creator_on_supplier", "rating": 5},
            )
        )


@pytest.mark.case("RV-10 to RV-14")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize("rating", [1, 2, 3, 4, 5])
def test_every_rating_from_one_to_five_is_accepted(api, finished_agreement, rating):
    """Both ends of the range included.

    Testing only the values outside the range would pass against an
    implementation that also wrongly refused 1 and 5.
    """
    body = assert_created(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": rating},
        )
    )

    assert body["rating"] == rating


@pytest.mark.case("RV-15,RV-16,RV-17,RV-18,RV-28")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "rating, expected_code",
    [
        pytest.param(0, "min_value", id="zero-just-below-the-range"),
        pytest.param(6, "max_value", id="six-just-above-the-range"),
        pytest.param(-1, "min_value", id="negative"),
        pytest.param(10, "max_value", id="ten"),
        pytest.param(999999999999, "max_value", id="absurdly-large"),
    ],
)
def test_a_rating_outside_one_to_five_is_refused(
    api, finished_agreement, rating, expected_code
):
    response = api.post(
        endpoints.reviews_for(finished_agreement["id"]),
        {"reviewer_type": "creator_on_supplier", "rating": rating},
    )

    assert_field_error(response, "rating", code=expected_code)


@pytest.mark.case("RV-19,RV-21,RV-25,RV-26")
@pytest.mark.parametrize(
    "rating, expected_code",
    [
        pytest.param(3.5, "invalid", id="a-half-star"),
        pytest.param("abc", "invalid", id="text"),
        pytest.param(True, "invalid", id="true-false"),
        pytest.param(None, "null", id="no-value"),
    ],
)
def test_a_rating_that_is_not_a_whole_number_is_refused(
    api, finished_agreement, rating, expected_code
):
    """3.5 is refused; 4.0 is not -- see the next test.

    The rule being applied is "must represent a whole number", not "must be
    typed as one".
    """
    response = api.post(
        endpoints.reviews_for(finished_agreement["id"]),
        {"reviewer_type": "creator_on_supplier", "rating": rating},
        format="json",
    )

    assert_field_error(response, "rating", code=expected_code)


@pytest.mark.case("RV-20,RV-22,RV-23,RV-24")
@pytest.mark.parametrize(
    "rating",
    [
        pytest.param(4.0, id="four-point-zero"),
        pytest.param("4", id="four-as-text"),
        pytest.param("4.0", id="four-point-zero-as-text"),
        pytest.param("  4  ", id="four-with-spaces-around-it"),
    ],
)
def test_a_value_that_represents_a_whole_number_is_accepted(
    api, finished_agreement, rating
):
    """Worth pinning deliberately rather than discovering by accident.

    A test written on the assumption that ``4.0`` is refused would fail against
    correct behaviour, so the accepted forms are stated explicitly.
    """
    body = assert_created(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": rating},
            format="json",
        )
    )

    assert body["rating"] == 4


@pytest.mark.case("RV-29,RV-30,RV-31,RV-32,RV-33")
@pytest.mark.parametrize(
    "kind",
    [
        pytest.param("creator_on_creator", id="not-one-of-the-two"),
        pytest.param("Creator_On_Supplier", id="wrong-capitals"),
        pytest.param("", id="empty-text"),
        pytest.param(1, id="a-number"),
    ],
)
def test_a_reviewer_kind_outside_the_two_allowed_is_refused(
    api, finished_agreement, kind
):
    response = api.post(
        endpoints.reviews_for(finished_agreement["id"]),
        {"reviewer_type": kind, "rating": 4},
        format="json",
    )

    assert_field_error(response, "reviewer_type", code="invalid_choice")


@pytest.mark.case("RV-27,RV-29")
@pytest.mark.parametrize("missing", ["reviewer_type", "rating"])
def test_the_kind_and_the_rating_are_both_required(api, finished_agreement, missing):
    body = {"reviewer_type": "creator_on_supplier", "rating": 4}
    del body[missing]

    assert_field_error(
        api.post(endpoints.reviews_for(finished_agreement["id"]), body),
        missing,
        code="required",
    )


@pytest.mark.case("RV-34,RV-36,RV-38,RV-40,RV-41")
@pytest.mark.parametrize(
    "comment, stored",
    [
        pytest.param("Fast and clean.", "Fast and clean.", id="ordinary-text"),
        pytest.param("", "", id="empty-text"),
        pytest.param(123, "123", id="a-number-becomes-text"),
        pytest.param("x" * 10000, "x" * 10000, id="very-long"),
        pytest.param("Line one\nLine two", "Line one\nLine two", id="line-breaks"),
    ],
)
def test_a_comment_is_stored_exactly_as_sent(api, finished_agreement, comment, stored):
    body = assert_created(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 4, "comment": comment},
            format="json",
        )
    )

    assert body["comment"] == stored


@pytest.mark.case("RV-35,RV-37,RV-39")
def test_a_comment_may_be_left_out_but_not_sent_as_no_value(api, finished_agreement):
    """Left out gives empty text, so there is one way to say "no comment".

    A field that could be either absent or explicitly empty would force every
    consumer to handle two representations of the same fact.
    """
    body = assert_created(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 4},
        )
    )
    assert body["comment"] == ""

    assert_field_error(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": "supplier_on_creator", "rating": 4, "comment": None},
            format="json",
        ),
        "comment",
        code="null",
    )


@pytest.mark.case("RV-39")
def test_a_comment_that_is_not_text_is_refused(api, finished_agreement):
    assert_field_error(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 4, "comment": ["a"]},
            format="json",
        ),
        "comment",
        code="invalid",
    )


@pytest.mark.case("RV-42,RV-43,RV-44,RV-46")
def test_reviews_can_be_read_back_for_one_agreement_only(
    api, finished_agreement, other_supplier, hire
):
    for kind in KINDS:
        assert_created(
            api.post(
                endpoints.reviews_for(finished_agreement["id"]),
                {"reviewer_type": kind, "rating": 4},
            )
        )
    unrelated = hire(other_supplier)

    assert_page(api.get(endpoints.reviews_for(finished_agreement["id"])), count=2)
    assert_page(api.get(endpoints.reviews_for(unrelated["id"])), count=0)


@pytest.mark.case("RV-45,RV-47")
@pytest.mark.parametrize("method", ["get", "post"])
def test_reviewing_an_agreement_that_does_not_exist_reports_not_found(api, method):
    """Not an empty list.

    An empty list would tell a caller with a typo in the address that the
    agreement simply has no reviews -- a different and wrong answer.
    """
    url = endpoints.reviews_for(999999)

    if method == "get":
        assert_not_found(api.get(url))
    else:
        assert_not_found(
            api.post(url, {"reviewer_type": "creator_on_supplier", "rating": 4})
        )


@pytest.mark.case("RV-48")
def test_the_agreement_comes_from_the_address_not_the_request_body(
    api, finished_agreement
):
    """One source of identity.

    Accepting the agreement in the body as well would let the two disagree, and
    then the endpoint needs a rule about which wins, a test for the mismatch, and
    a decision about silent redirection.
    """
    body = assert_created(
        api.post(
            endpoints.reviews_for(finished_agreement["id"]),
            {"reviewer_type": "creator_on_supplier", "rating": 4, "contract": 999999},
        )
    )

    assert body["contract"] == finished_agreement["id"]


@pytest.mark.case("RV-49")
def test_reviews_cannot_be_deleted(api, finished_agreement):
    assert_method_not_allowed(
        api.delete(endpoints.reviews_for(finished_agreement["id"]))
    )
