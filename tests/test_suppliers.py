"""Registering, reading and changing suppliers.

Covers cases SU-01 to SU-55 in TEST_CASES.md.

Which fields are required: name, email and hourly rate. Skills and availability
may be left out -- the specification marks only those three as required.
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
from tests.factories import CreatorFactory, SupplierFactory

pytestmark = pytest.mark.django_db

VALID_SUPPLIER = {
    "name": "Xena",
    "email": "xena@example.com",
    "skills": ["editing"],
    "hourly_rate": "45.00",
}


@pytest.mark.case("SU-01")
def test_registering_a_supplier_with_every_field_returns_the_stored_record(api):
    body = assert_created(
        api.post(
            endpoints.SUPPLIERS,
            {**VALID_SUPPLIER, "availability_status": "available"},
            format="json",
        )
    )

    assert body["name"] == "Xena"
    assert body["email"] == "xena@example.com"
    assert body["skills"] == ["editing"]
    assert body["hourly_rate"] == "45.00"
    assert body["availability_status"] == "available"


@pytest.mark.case("SU-02,SU-03")
@pytest.mark.parametrize(
    "omitted, field, expected",
    [
        pytest.param("skills", "skills", [], id="skills-default-to-empty"),
        pytest.param(
            "availability_status",
            "availability_status",
            "available",
            id="availability-defaults-to-available",
        ),
    ],
)
def test_optional_fields_fall_back_to_sensible_defaults(api, omitted, field, expected):
    body = {k: v for k, v in VALID_SUPPLIER.items() if k != omitted}

    created = assert_created(api.post(endpoints.SUPPLIERS, body, format="json"))

    assert created[field] == expected


@pytest.mark.case("SU-06,SU-07")
def test_skills_are_tidied_without_losing_their_order(api):
    """Trimmed, lowercased, duplicates removed, order kept.

    Order carries intent -- a supplier lists their strongest skill first -- so
    sorting them would throw information away for no reason.
    """
    body = assert_created(
        api.post(
            endpoints.SUPPLIERS,
            {
                **VALID_SUPPLIER,
                "skills": [" Video-Editing ", "video-editing", "THUMBNAILS"],
            },
            format="json",
        )
    )

    assert body["skills"] == ["video-editing", "thumbnails"]


@pytest.mark.case("SU-09,SU-10,SU-11")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "sent, stored",
    [
        pytest.param("0.01", "0.01", id="smallest-allowed"),
        pytest.param("9999999999.99", "9999999999.99", id="largest-allowed"),
        pytest.param(45, "45.00", id="whole-number"),
        pytest.param("45.5", "45.50", id="one-decimal-place"),
    ],
)
def test_an_hourly_rate_is_accepted_at_the_edges_of_what_is_allowed(api, sent, stored):
    body = assert_created(
        api.post(
            endpoints.SUPPLIERS, {**VALID_SUPPLIER, "hourly_rate": sent}, format="json"
        )
    )

    assert body["hourly_rate"] == stored


@pytest.mark.case("SU-14,SU-15,SU-16")
@pytest.mark.parametrize("missing", ["name", "email", "hourly_rate"])
def test_name_email_and_rate_are_required(api, missing):
    body = {k: v for k, v in VALID_SUPPLIER.items() if k != missing}

    assert_field_error(
        api.post(endpoints.SUPPLIERS, body, format="json"), missing, code="required"
    )


@pytest.mark.case("SU-18,SU-19,SU-20,SU-21,SU-25")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "rate, expected_code",
    [
        pytest.param("0", "min_value", id="zero"),
        pytest.param("-5", "min_value", id="negative"),
        pytest.param("-0.01", "min_value", id="just-below-zero"),
        pytest.param("0.001", "max_decimal_places", id="three-decimal-places"),
        pytest.param("99999999999.99", "max_digits", id="too-many-digits"),
        pytest.param("forty five", "invalid", id="text"),
        pytest.param(True, "invalid", id="true-false"),
        pytest.param("", "invalid", id="empty-text"),
        pytest.param(None, "null", id="no-value"),
    ],
)
def test_an_unusable_hourly_rate_is_refused(api, rate, expected_code):
    """Business rule 10: never a raw database error.

    Every one of these is a 400 naming the field, with a message about the
    amount rather than about digits and decimal places.
    """
    response = api.post(
        endpoints.SUPPLIERS, {**VALID_SUPPLIER, "hourly_rate": rate}, format="json"
    )

    assert_field_error(response, "hourly_rate", code=expected_code)


@pytest.mark.case("SU-26,SU-27,SU-28")
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("on-holiday", id="not-one-of-the-values"),
        pytest.param("Available", id="wrong-capitals"),
        pytest.param("", id="empty-text"),
    ],
)
def test_an_availability_value_outside_the_allowed_set_is_refused(api, value):
    response = api.post(
        endpoints.SUPPLIERS,
        {**VALID_SUPPLIER, "availability_status": value},
        format="json",
    )

    assert_field_error(response, "availability_status", code="invalid_choice")


@pytest.mark.case("SU-29,SU-30,SU-31,SU-32,SU-33,SU-34,SU-35")
@pytest.mark.parametrize(
    "skills",
    [
        pytest.param("editing", id="plain-text-not-a-list"),
        pytest.param({"a": 1}, id="nested-values-not-a-list"),
        pytest.param([123], id="a-number-entry"),
        pytest.param(["editing", ""], id="an-empty-entry"),
        pytest.param(["   "], id="an-entry-of-only-spaces"),
        pytest.param([f"skill-{i}" for i in range(26)], id="twenty-six-entries"),
        pytest.param(["x" * 51], id="an-over-long-entry"),
    ],
)
def test_a_malformed_skills_list_is_refused(api, skills):
    """Blank entries are refused, not silently dropped.

    Quietly discarding an empty entry would hide a bug in whatever built the
    request. Normalisation canonicalises valid input; it does not repair invalid
    input.
    """
    response = api.post(
        endpoints.SUPPLIERS, {**VALID_SUPPLIER, "skills": skills}, format="json"
    )

    assert_field_error(response, "skills")


@pytest.mark.case("SU-08,SU-12,SU-13")
@pytest.mark.parametrize(
    "skills",
    [
        pytest.param([f"skill-{i}" for i in range(25)], id="twenty-five-the-maximum"),
        pytest.param(["x" * 50], id="fifty-characters-the-maximum"),
        pytest.param([], id="none-at-all"),
    ],
)
def test_a_skills_list_is_accepted_at_the_edges_of_what_is_allowed(api, skills):
    body = assert_created(
        api.post(
            endpoints.SUPPLIERS, {**VALID_SUPPLIER, "skills": skills}, format="json"
        )
    )

    assert len(body["skills"]) == len(skills)


@pytest.mark.case("SU-36,SU-37,SU-39")
@pytest.mark.rule("BR-10")
@pytest.mark.parametrize(
    "second_email, expected_code",
    [
        pytest.param("xena@example.com", "unique", id="duplicate-identical"),
        pytest.param("XENA@Example.com", "unique", id="duplicate-other-capitals"),
        pytest.param("xena.example.com", "invalid", id="malformed"),
    ],
)
def test_an_email_must_be_valid_and_unused(api, second_email, expected_code):
    assert_created(api.post(endpoints.SUPPLIERS, VALID_SUPPLIER, format="json"))

    response = api.post(
        endpoints.SUPPLIERS, {**VALID_SUPPLIER, "email": second_email}, format="json"
    )

    assert_field_error(response, "email", code=expected_code)


@pytest.mark.case("SU-38")
def test_a_creator_and_a_supplier_may_share_an_email_address(api):
    """Creators and suppliers are separate lists.

    The same person may be both, so the same address may appear once in each.
    """
    CreatorFactory(email="both@example.com")

    assert_created(
        api.post(
            endpoints.SUPPLIERS,
            {**VALID_SUPPLIER, "email": "both@example.com"},
            format="json",
        )
    )


@pytest.mark.case("SU-40,SU-41,SU-42,SU-43")
def test_suppliers_can_be_read_individually_and_as_a_list(api):
    first = SupplierFactory()
    second = SupplierFactory()

    body = assert_ok(api.get(endpoints.supplier(first.id)))
    assert body["email"] == first.email

    listing = assert_page(api.get(endpoints.SUPPLIERS), count=2, returned=2)
    assert [item["id"] for item in listing["results"]] == [second.id, first.id]

    assert_not_found(api.get(endpoints.supplier(999999)))


@pytest.mark.case("SU-44,SU-47,SU-49,SU-51")
@pytest.mark.parametrize(
    "changes, field, expected",
    [
        pytest.param(
            {"availability_status": "inactive"},
            "availability_status",
            "inactive",
            id="stop-taking-work",
        ),
        pytest.param({"hourly_rate": "60.00"}, "hourly_rate", "60.00", id="rate"),
        pytest.param({"skills": ["Animation"]}, "skills", ["animation"], id="skills"),
        pytest.param({"name": "Renamed"}, "name", "Renamed", id="name"),
    ],
)
def test_a_supplier_can_be_changed(api, supplier, changes, field, expected):
    body = assert_ok(api.patch(endpoints.supplier(supplier.id), changes, format="json"))

    assert body[field] == expected


@pytest.mark.case("SU-51")
def test_changing_one_field_leaves_the_others_alone(api, supplier):
    body = assert_ok(
        api.patch(endpoints.supplier(supplier.id), {"availability_status": "inactive"})
    )

    assert body["availability_status"] == "inactive"
    assert body["name"] == supplier.name
    assert body["email"] == supplier.email
    assert body["hourly_rate"] == str(supplier.hourly_rate)
    assert body["skills"] == supplier.skills


@pytest.mark.case("SU-46,SU-48")
@pytest.mark.parametrize(
    "changes, field",
    [
        pytest.param({"availability_status": "sleeping"}, "availability_status", id="bad-availability"),
        pytest.param({"hourly_rate": "0"}, "hourly_rate", id="rate-of-zero"),
        pytest.param({"hourly_rate": "-1"}, "hourly_rate", id="negative-rate"),
        pytest.param({"skills": "editing"}, "skills", id="skills-not-a-list"),
    ],
)
def test_an_invalid_change_is_refused_and_nothing_is_stored(api, supplier, changes, field):
    before = {
        "availability_status": supplier.availability_status,
        "hourly_rate": supplier.hourly_rate,
        "skills": supplier.skills,
    }

    assert_field_error(
        api.patch(endpoints.supplier(supplier.id), changes, format="json"), field
    )

    supplier.refresh_from_db()
    assert supplier.availability_status == before["availability_status"]
    assert supplier.hourly_rate == before["hourly_rate"]
    assert supplier.skills == before["skills"]


@pytest.mark.case("SU-50")
def test_changing_an_email_to_one_already_taken_is_refused(api):
    SupplierFactory(email="taken@example.com")
    second = SupplierFactory(email="mine@example.com")

    assert_field_error(
        api.patch(endpoints.supplier(second.id), {"email": "taken@example.com"}),
        "email",
        code="unique",
    )

    second.refresh_from_db()
    assert second.email == "mine@example.com"


@pytest.mark.case("SU-52")
def test_a_supplier_cannot_be_deleted(api, supplier):
    """Retiring is done by going inactive, not by erasing the record.

    A supplier's reviews are the creators' statements about them, so removing
    the supplier would remove other people's records too. See D-4 in
    DECISIONS.md.
    """
    assert_method_not_allowed(api.delete(endpoints.supplier(supplier.id)))

    assert_ok(api.get(endpoints.supplier(supplier.id)))


@pytest.mark.case("SU-53")
def test_changing_a_supplier_that_does_not_exist_reports_not_found(api):
    assert_not_found(api.patch(endpoints.supplier(999999), {"name": "Nobody"}))


@pytest.mark.case("SU-54,SU-55")
@pytest.mark.rule("BR-05")
@pytest.mark.parametrize("availability", ["available", "inactive"])
def test_availability_does_not_stop_a_supplier_applying(
    api, open_gig, availability
):
    """Business rule 5 puts the availability check at hiring time, not here.

    An inactive supplier may still apply. Adding the obvious-looking check to
    the apply endpoint would break the rule in the direction nobody tests: it
    would silently prevent a case the specification explicitly permits.
    """
    supplier = SupplierFactory(availability_status=availability)

    body = assert_created(
        api.post(
            endpoints.apply_to(open_gig.id),
            {"supplier_id": supplier.id, "proposed_rate": "420.00"},
        )
    )

    assert body["status"] == "pending"
