"""Listing agreements, and marking one complete.

Covers cases CL-01 to CL-18 and CC-01 to CC-14 in TEST_CASES.md.
"""

import pytest

from tests import endpoints
from tests.assertions import (
    assert_conflict,
    assert_method_not_allowed,
    assert_not_found,
    assert_ok,
    assert_page,
)
from tests.factories import ContractFactory, GigFactory, SupplierFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def three_agreements(api, creator, other_creator, supplier, other_supplier, hire):
    """Three agreements across two creators and two suppliers.

    Supplier X works for Creator A and Creator B; Supplier Y works for Creator A.
    Enough overlap that a filter returning the wrong set is visible.
    """
    return {
        "x_for_a": hire(supplier, creator=creator),
        "x_for_b": hire(supplier, creator=other_creator),
        "y_for_a": hire(other_supplier, creator=creator),
    }


@pytest.mark.case("CL-01")
def test_listing_agreements_with_no_filter_returns_all_of_them(api, three_agreements):
    """Every agreement on the platform, including the rate agreed on each.

    Faithful to the specification, which writes the filters as optional -- and
    worth stating plainly: with no sign-in, that makes every supplier's pricing
    history readable by anyone. See B-12 and Q1 in DECISIONS.md.
    """
    assert_page(api.get(endpoints.CONTRACTS), count=3, returned=3)


@pytest.mark.case("CL-02,CL-03")
def test_agreements_can_be_filtered_by_supplier(
    api, three_agreements, supplier, other_supplier
):
    assert_page(api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier.id}"), count=2)
    assert_page(
        api.get(f"{endpoints.CONTRACTS}?supplier_id={other_supplier.id}"), count=1
    )


@pytest.mark.case("CL-04,CL-05")
def test_agreements_can_be_filtered_by_creator(
    api, three_agreements, creator, other_creator
):
    """The creator is reached through the gig, not stored on the agreement."""
    assert_page(api.get(f"{endpoints.CONTRACTS}?creator_id={creator.id}"), count=2)
    assert_page(api.get(f"{endpoints.CONTRACTS}?creator_id={other_creator.id}"), count=1)


@pytest.mark.case("CL-06,CL-07")
@pytest.mark.parametrize(
    "supplier_key, creator_key, expected",
    [
        pytest.param("supplier", "creator", 1, id="an-overlap-of-one"),
        pytest.param("other_supplier", "other_creator", 0, id="no-overlap"),
    ],
)
def test_both_filters_must_be_satisfied_together(
    api, three_agreements, request, supplier_key, creator_key, expected
):
    supplier = request.getfixturevalue(supplier_key)
    creator = request.getfixturevalue(creator_key)

    response = api.get(
        f"{endpoints.CONTRACTS}?supplier_id={supplier.id}&creator_id={creator.id}"
    )

    assert_page(response, count=expected)


@pytest.mark.case("CL-08,CL-09,CL-10")
@pytest.mark.parametrize(
    "query",
    ["?supplier_id=999999", "?creator_id=999999"],
    ids=["unknown-supplier", "unknown-creator"],
)
def test_a_filter_that_matches_nothing_returns_an_empty_page(
    api, three_agreements, query
):
    """A number matching nothing is a valid question with the answer "none".

    Contrast with a filter that is not a number at all, which is the caller's
    mistake and gets a 400.
    """
    assert_page(api.get(f"{endpoints.CONTRACTS}{query}"), count=0, returned=0)


@pytest.mark.case("CL-11,CL-12")
@pytest.mark.parametrize("field", ["supplier_id", "creator_id"])
def test_a_filter_that_is_not_a_number_is_refused(api, three_agreements, field):
    response = api.get(f"{endpoints.CONTRACTS}?{field}=abc")

    assert response.status_code == 400
    assert field in response.data


@pytest.mark.case("CL-13")
@pytest.mark.parametrize("query", ["?supplier_id=", "?creator_id="])
def test_an_empty_filter_is_treated_as_no_filter(api, three_agreements, query):
    assert_page(api.get(f"{endpoints.CONTRACTS}{query}"), count=3)


@pytest.mark.case("CL-14")
def test_completing_an_agreement_does_not_hide_it_from_the_list(api, three_agreements):
    assert_ok(api.post(endpoints.complete(three_agreements["x_for_a"]["id"])))

    assert_page(api.get(endpoints.CONTRACTS), count=3)


@pytest.mark.case("CL-15,CL-16,CL-17")
def test_agreement_listings_page(api, three_agreements, supplier):
    assert_page(api.get(f"{endpoints.CONTRACTS}?page_size=2"), count=3, returned=2)
    assert_not_found(api.get(f"{endpoints.CONTRACTS}?page_size=2&page=3"))
    assert_page(
        api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier.id}&page_size=1"),
        count=2,
        returned=1,
    )


@pytest.mark.case("CC-01")
def test_an_agreement_can_be_marked_complete(api, supplier, hire):
    agreement = hire(supplier)

    body = assert_ok(api.post(endpoints.complete(agreement["id"])))

    assert body["status"] == "completed"


@pytest.mark.case("CC-02")
def test_completing_an_agreement_twice_is_refused(api, supplier, hire):
    """Not a silent success.

    Reporting success for something that did not happen would tell the caller
    the work was just signed off when in fact it was signed off last week -- and
    if the agreement had been terminated instead, that answer would be simply
    wrong.
    """
    agreement = hire(supplier)
    assert_ok(api.post(endpoints.complete(agreement["id"])))

    assert_conflict(api.post(endpoints.complete(agreement["id"])), "contract_not_active")


@pytest.mark.case("CC-03")
def test_a_terminated_agreement_cannot_be_completed(api, supplier):
    """Built directly, because no endpoint can produce a terminated agreement.

    That is open question Q2 in DECISIONS.md. The rule under test is still worth
    checking, but it guards a state real callers cannot reach.
    """
    agreement = ContractFactory(supplier=supplier, status="terminated")

    assert_conflict(api.post(endpoints.complete(agreement.id)), "contract_not_active")


@pytest.mark.case("CC-04,CC-05")
@pytest.mark.interpretation("I8")
def test_completing_an_agreement_leaves_the_gig_for_the_creator_to_close(
    api, supplier, hire
):
    """Two deliberate steps, not one.

    The specification names ``in_progress`` to ``completed`` as an allowed change
    on the gig. If completing the agreement did it automatically, that named
    transition could never be used -- and the creator would lose the ability to
    sign off separately from the supplier declaring the work delivered.
    """
    agreement = hire(supplier)

    assert_ok(api.post(endpoints.complete(agreement["id"])))

    assert assert_ok(api.get(endpoints.gig(agreement["gig"])))["status"] == "in_progress"

    body = assert_ok(api.patch(endpoints.gig(agreement["gig"]), {"status": "completed"}))
    assert body["status"] == "completed"


@pytest.mark.case("CC-06")
def test_the_gig_cannot_be_closed_before_its_agreement(api, supplier, hire):
    """The order cannot be reversed."""
    agreement = hire(supplier)

    assert_conflict(
        api.patch(endpoints.gig(agreement["gig"]), {"status": "completed"}),
        "gig_has_active_contract",
    )


@pytest.mark.case("CC-07,CC-08,CC-09")
def test_completing_something_that_does_not_exist_reports_not_found(api, supplier, hire):
    agreement = hire(supplier)

    assert_not_found(api.post(endpoints.complete(999999)))
    assert api.get(endpoints.complete(agreement["id"])).status_code == 405
    assert_ok(api.post(endpoints.complete(agreement["id"]), None, format="json"))


@pytest.mark.case("CC-11,CC-12,CC-13,CC-14")
def test_agreements_cannot_be_created_changed_or_deleted_directly(api, supplier, hire):
    """An agreement exists only because someone was hired.

    Exposing a way to create one by hand would be an invitation to bypass rule 3
    -- the gig would not move, competing bids would not be turned down, and the
    agreement limit would not be checked.

    The individual-agreement address does not exist at all, so changing or
    deleting one reports not found rather than method-not-allowed.
    """
    agreement = hire(supplier)

    assert_method_not_allowed(
        api.post(endpoints.CONTRACTS, {"gig": 1, "supplier": 1, "agreed_rate": "5.00"})
    )

    individual = f"{endpoints.CONTRACTS}{agreement['id']}/"
    assert_not_found(api.get(individual))
    assert_not_found(api.patch(individual, {"agreed_rate": "1.00"}))
    assert_not_found(api.delete(individual))
