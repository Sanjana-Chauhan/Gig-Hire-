"""A supplier may hold at most three live agreements.

Covers cases CP-01 to CP-15 and WL-01 to WL-06 in TEST_CASES.md, and business
rule 4.

"Live" means active -- neither completed nor terminated. Applications never
count, however many a supplier has.

This rule matters more than its size suggests: it is the only rule in the
specification with no database-level backstop. "At most three rows matching a
condition" is not something a database constraint can express, so every other
rule has a second line of defence and this one does not. A bug here corrupts
data silently -- a supplier with four live agreements looks exactly like one with
three until somebody counts.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_conflict, assert_created, assert_ok
from tests.factories import ContractFactory, SupplierFactory

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-04")]

MAXIMUM = 3


def live_count(api, supplier_id):
    body = assert_ok(api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier_id}"))
    return sum(1 for item in body["results"] if item["status"] == "active")


@pytest.mark.case("CP-01,CP-02,CP-03")
@pytest.mark.parametrize("nth", [1, 2, 3], ids=["first", "second", "third-the-limit"])
def test_a_supplier_can_be_hired_up_to_the_limit(
    api, supplier, give_live_agreements, nth
):
    """Three is allowed. The rule is "no more than three", not "fewer than three".

    Off-by-one lives exactly here, which is why each step is checked rather than
    only the refusal.
    """
    give_live_agreements(supplier, nth)

    assert live_count(api, supplier.id) == nth


@pytest.mark.case("CP-04,CP-05")
def test_a_fourth_live_agreement_is_refused_and_nothing_is_written(
    api, supplier, give_live_agreements, open_gig, apply_to_gig
):
    give_live_agreements(supplier, MAXIMUM)
    bid = apply_to_gig(open_gig, supplier)

    response = api.post(endpoints.accept(bid["id"]))

    detail = assert_conflict(response, "workload_cap_reached")
    assert str(MAXIMUM) in detail["detail"]
    assert live_count(api, supplier.id) == MAXIMUM
    assert assert_ok(api.get(endpoints.gig(open_gig.id)))["status"] == "open"
    listing = assert_ok(api.get(endpoints.applications_for(open_gig.id)))
    assert listing["results"][0]["status"] == "pending"


@pytest.mark.case("CP-06")
def test_the_limit_does_not_drift_across_repeated_attempts(
    api, supplier, give_live_agreements, creator, apply_to_gig
):
    from tests.factories import GigFactory

    give_live_agreements(supplier, MAXIMUM)

    for _ in range(3):
        gig = GigFactory(creator=creator)
        bid = apply_to_gig(gig, supplier)
        assert_conflict(api.post(endpoints.accept(bid["id"])), "workload_cap_reached")

    assert live_count(api, supplier.id) == MAXIMUM


@pytest.mark.case("CP-07,CP-08")
def test_finishing_a_job_frees_a_slot(
    api, supplier, give_live_agreements, open_gig, apply_to_gig
):
    """Completing must free capacity, or a supplier is capped for ever.

    The case a less careful suite misses: it is easy to test that the fourth
    hire is refused and never check that finishing one lets it through.
    """
    agreements = give_live_agreements(supplier, MAXIMUM)
    assert_ok(api.post(endpoints.complete(agreements[0]["id"])))
    bid = apply_to_gig(open_gig, supplier)

    assert_created(api.post(endpoints.accept(bid["id"])))

    assert live_count(api, supplier.id) == MAXIMUM
    all_agreements = assert_ok(
        api.get(f"{endpoints.CONTRACTS}?supplier_id={supplier.id}")
    )
    assert all_agreements["count"] == MAXIMUM + 1


@pytest.mark.case("CP-09")
def test_finished_agreements_never_count_towards_the_limit(
    api, supplier, give_finished_agreements, open_gig, apply_to_gig
):
    give_finished_agreements(supplier, MAXIMUM)
    bid = apply_to_gig(open_gig, supplier)

    assert_created(api.post(endpoints.accept(bid["id"])))


@pytest.mark.case("CP-10,CP-11,CP-12")
@pytest.mark.parametrize(
    "active, completed, terminated, can_be_hired",
    [
        pytest.param(2, 1, 1, True, id="two-live-under-the-limit"),
        pytest.param(3, 5, 2, False, id="three-live-at-the-limit"),
        pytest.param(0, 3, 3, True, id="none-live-all-finished"),
    ],
)
def test_only_live_agreements_are_counted(
    api, open_gig, apply_to_gig, give_live_agreements, give_finished_agreements,
    active, completed, terminated, can_be_hired,
):
    """Terminated agreements are built directly, of necessity.

    No endpoint in the specification can produce a terminated agreement -- that
    is open question Q2 in DECISIONS.md -- so this is one of the few places a
    factory has to stand in for the API. The live agreements are still made by
    hiring, so the count under test is a real one.
    """
    supplier = SupplierFactory()

    # Order matters in the setup: the agreements that will be completed have to
    # be made and completed *first*, so each one frees its slot again. Building
    # the live ones first would fill the supplier up and the setup itself would
    # hit the limit it is trying to test around.
    give_finished_agreements(supplier, completed)
    for _ in range(terminated):
        ContractFactory(supplier=supplier, status="terminated")
    give_live_agreements(supplier, active)

    assert live_count(api, supplier.id) == active

    bid = apply_to_gig(open_gig, supplier)
    response = api.post(endpoints.accept(bid["id"]))

    if can_be_hired:
        assert_created(response)
    else:
        assert_conflict(response, "workload_cap_reached")


@pytest.mark.case("WL-01,WL-02,WL-06")
@pytest.mark.interpretation("I18")
def test_pending_bids_never_count_towards_the_limit(
    api, creator, supplier, apply_to_gig, open_gig
):
    """Applying is free; only being hired consumes capacity.

    Counting bids would punish suppliers for bidding widely, which is exactly
    what a marketplace wants them to do.
    """
    from tests.factories import GigFactory

    for _ in range(10):
        apply_to_gig(GigFactory(creator=creator), supplier)
    assert live_count(api, supplier.id) == 0

    bid = apply_to_gig(open_gig, supplier)
    assert_created(api.post(endpoints.accept(bid["id"])))

    assert live_count(api, supplier.id) == 1


@pytest.mark.case("CP-13,CP-14")
def test_one_supplier_at_the_limit_does_not_block_another(
    api, supplier, other_supplier, give_live_agreements, open_gig, apply_to_gig
):
    give_live_agreements(supplier, MAXIMUM)
    bid = apply_to_gig(open_gig, other_supplier)

    assert_created(api.post(endpoints.accept(bid["id"])))


@pytest.mark.case("CP-15")
def test_the_limit_counts_work_from_every_creator(
    api, supplier, other_creator, give_live_agreements, apply_to_gig
):
    """The limit is about the supplier's total workload, not per creator.

    A second creator cannot hire a supplier who is already full, even though
    that creator has never hired them before.
    """
    from tests.factories import GigFactory

    give_live_agreements(supplier, MAXIMUM)
    other_gig = GigFactory(creator=other_creator)
    bid = apply_to_gig(other_gig, supplier)

    assert_conflict(api.post(endpoints.accept(bid["id"])), "workload_cap_reached")
