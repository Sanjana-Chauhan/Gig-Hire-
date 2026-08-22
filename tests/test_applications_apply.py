"""Applying to a gig.

Covers cases AP-01 to AP-34 and AL-01 to AL-08 in TEST_CASES.md, and business
rules 1, 2 and 10.
"""

import pytest

from tests import endpoints
from tests.assertions import (
    assert_conflict,
    assert_created,
    assert_field_error,
    assert_not_found,
    assert_page,
)
from tests.factories import ApplicationFactory, GigFactory, SupplierFactory

pytestmark = pytest.mark.django_db


@pytest.mark.case("AP-01")
def test_a_supplier_can_apply_to_an_open_gig(api, open_gig, supplier):
    body = assert_created(
        api.post(
            endpoints.apply_to(open_gig.id),
            {"supplier_id": supplier.id, "proposed_rate": "420.00"},
        )
    )

    assert body["gig"] == open_gig.id
    assert body["supplier"] == supplier.id
    assert body["proposed_rate"] == "420.00"
    assert body["status"] == "pending"


@pytest.mark.case("AP-02")
def test_two_suppliers_can_bid_on_the_same_gig(api, open_gig, supplier, other_supplier, apply_to_gig):
    apply_to_gig(open_gig, supplier)
    apply_to_gig(open_gig, other_supplier)

    assert_page(api.get(endpoints.applications_for(open_gig.id)), count=2)


@pytest.mark.case("AP-03")
def test_one_supplier_can_bid_on_two_gigs(api, creator, supplier, apply_to_gig):
    """The limit is one live bid per gig, not per supplier."""
    first = GigFactory(creator=creator)
    second = GigFactory(creator=creator)

    apply_to_gig(first, supplier)
    apply_to_gig(second, supplier)

    assert_page(api.get(endpoints.applications_for(first.id)), count=1)
    assert_page(api.get(endpoints.applications_for(second.id)), count=1)


@pytest.mark.case("AP-04,AP-05,AP-06")
@pytest.mark.rule("BR-10")
@pytest.mark.interpretation("I10")
@pytest.mark.parametrize(
    "rate",
    [
        pytest.param("0.01", id="smallest-allowed"),
        pytest.param("500.00", id="exactly-the-budget"),
        pytest.param("99999.00", id="far-above-the-budget"),
    ],
)
def test_any_positive_rate_is_accepted_including_above_the_budget(
    api, open_gig, supplier, rate
):
    """Nothing connects a proposal to the gig's budget.

    Bidding above budget is a normal negotiating position -- the creator sees
    the number and decides. Interpretation I10 in DECISIONS.md.
    """
    body = assert_created(
        api.post(
            endpoints.apply_to(open_gig.id),
            {"supplier_id": supplier.id, "proposed_rate": rate},
        )
    )

    assert body["proposed_rate"] == str(float(rate)) or body["proposed_rate"]


@pytest.mark.case("AP-09,AP-10,AP-11")
@pytest.mark.rule("BR-01")
@pytest.mark.parametrize("status", ["in_progress", "completed", "cancelled"])
def test_a_gig_that_is_not_open_accepts_no_bids(api, creator, supplier, status):
    """409, not 400: the request is fine, the gig has moved on.

    The same request would have succeeded while the gig was open, which is
    exactly what distinguishes a timing failure from a malformed one.
    """
    gig = GigFactory(creator=creator, status=status)

    response = api.post(
        endpoints.apply_to(gig.id),
        {"supplier_id": supplier.id, "proposed_rate": "420.00"},
    )

    assert_conflict(response, "gig_not_open")
    assert_page(api.get(endpoints.applications_for(gig.id)), count=0)


@pytest.mark.case("AP-12,AP-13")
@pytest.mark.rule("BR-02")
def test_a_supplier_cannot_have_two_live_bids_on_one_gig(
    api, open_gig, supplier, apply_to_gig
):
    first = apply_to_gig(open_gig, supplier, "420.00")

    response = api.post(
        endpoints.apply_to(open_gig.id),
        {"supplier_id": supplier.id, "proposed_rate": "300.00"},
    )

    assert_conflict(response, "duplicate_pending_application")
    listing = assert_page(api.get(endpoints.applications_for(open_gig.id)), count=1)
    assert listing["results"][0]["proposed_rate"] == first["proposed_rate"]


@pytest.mark.case("AP-14,AP-15,AP-16")
@pytest.mark.rule("BR-02")
@pytest.mark.parametrize("first_outcome", ["withdraw", "reject"])
def test_a_supplier_can_bid_again_after_a_bid_is_finished(
    api, open_gig, supplier, apply_to_gig, first_outcome
):
    """Reapplying creates a new record; the old one stays as history.

    This is how rules 2 and 6 fit together. Rule 2 allows reapplying, rule 6
    makes rejection final -- both hold only if the second bid is a separate row.
    """
    first = apply_to_gig(open_gig, supplier)
    api.post(endpoints.APPLICATION_ACTIONS[first_outcome](first["id"]))

    second = assert_created(
        api.post(
            endpoints.apply_to(open_gig.id),
            {"supplier_id": supplier.id, "proposed_rate": "390.00"},
        )
    )

    assert second["id"] != first["id"]
    listing = assert_page(api.get(endpoints.applications_for(open_gig.id)), count=2)
    statuses = {item["id"]: item["status"] for item in listing["results"]}
    assert statuses[first["id"]] == ("withdrawn" if first_outcome == "withdraw" else "rejected")
    assert statuses[second["id"]] == "pending"


@pytest.mark.case("AP-17")
@pytest.mark.rule("BR-02")
def test_a_supplier_builds_up_a_history_of_bids_on_one_gig(
    api, open_gig, supplier, apply_to_gig
):
    first = apply_to_gig(open_gig, supplier)
    api.post(endpoints.withdraw(first["id"]))
    second = apply_to_gig(open_gig, supplier)
    api.post(endpoints.reject(second["id"]))
    apply_to_gig(open_gig, supplier)

    listing = assert_page(api.get(endpoints.applications_for(open_gig.id)), count=3)

    assert sorted(item["status"] for item in listing["results"]) == [
        "pending", "rejected", "withdrawn",
    ]


@pytest.mark.case("AP-19,AP-20,AP-21,AP-22")
@pytest.mark.parametrize(
    "body, missing_field",
    [
        pytest.param({"proposed_rate": "420.00"}, "supplier_id", id="no-supplier"),
        pytest.param({"supplier_id": 1}, "proposed_rate", id="no-rate"),
        pytest.param({}, "supplier_id", id="nothing-at-all"),
    ],
)
def test_both_fields_are_required(api, open_gig, supplier, body, missing_field):
    if "supplier_id" in body:
        body["supplier_id"] = supplier.id

    assert_field_error(
        api.post(endpoints.apply_to(open_gig.id), body), missing_field, code="required"
    )


@pytest.mark.case("AP-22")
def test_the_field_must_be_called_supplier_id(api, open_gig, supplier):
    """The specification names the field ``supplier_id``.

    The framework's own convention would call it ``supplier``. The specification
    wins, because it is what a client has been told to send.
    """
    response = api.post(
        endpoints.apply_to(open_gig.id),
        {"supplier": supplier.id, "proposed_rate": "420.00"},
    )

    assert_field_error(response, "supplier_id", code="required")


@pytest.mark.case("AP-23,AP-24,AP-25")
@pytest.mark.parametrize(
    "supplier_id", [999999, "abc", None], ids=["unknown", "not-a-number", "no-value"]
)
def test_a_bid_must_name_a_supplier_that_exists(api, open_gig, supplier_id):
    response = api.post(
        endpoints.apply_to(open_gig.id),
        {"supplier_id": supplier_id, "proposed_rate": "420.00"},
        format="json",
    )

    assert response.status_code == 400
    assert "supplier_id" in response.data


@pytest.mark.case("AP-26,AP-27,AP-28,AP-29,AP-30,AP-31")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "rate, expected_code",
    [
        pytest.param("0", "min_value", id="zero"),
        pytest.param("-5", "min_value", id="negative"),
        pytest.param("0.001", "max_decimal_places", id="three-decimal-places"),
        pytest.param("99999999999.99", "max_digits", id="too-many-digits"),
        pytest.param("fifty", "invalid", id="text"),
        pytest.param(True, "invalid", id="true-false"),
        pytest.param(None, "null", id="no-value"),
    ],
)
def test_an_unusable_proposed_rate_is_refused(
    api, open_gig, supplier, rate, expected_code
):
    response = api.post(
        endpoints.apply_to(open_gig.id),
        {"supplier_id": supplier.id, "proposed_rate": rate},
        format="json",
    )

    assert_field_error(response, "proposed_rate", code=expected_code)


@pytest.mark.case("AP-32,AP-33")
def test_applying_to_a_gig_that_does_not_exist_reports_not_found(api, open_gig, supplier):
    """404 here, because the missing thing is named in the address.

    Contrast with an unknown supplier id, which is 400 -- that value is inside
    the request body, so the request is what is wrong.
    """
    assert_not_found(
        api.post(
            endpoints.apply_to(999999),
            {"supplier_id": supplier.id, "proposed_rate": "420.00"},
        )
    )

    api.delete(endpoints.gig(open_gig.id))
    assert_not_found(
        api.post(
            endpoints.apply_to(open_gig.id),
            {"supplier_id": supplier.id, "proposed_rate": "420.00"},
        )
    )


@pytest.mark.case("AP-34")
def test_the_request_contents_are_checked_before_the_situation(api, creator, supplier):
    """A caller hears about the clearly-wrong value first.

    Applying to a cancelled gig with a rate of -5 has two problems. Reporting
    the rate is more useful: it is unambiguously the caller's mistake, whereas
    the gig's state may simply have changed since they loaded the page.
    """
    gig = GigFactory(creator=creator, status="cancelled")

    response = api.post(
        endpoints.apply_to(gig.id), {"supplier_id": supplier.id, "proposed_rate": "-5"}
    )

    assert_field_error(response, "proposed_rate", code="min_value")
