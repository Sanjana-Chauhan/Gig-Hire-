"""How a supplier's availability is worked out.

Covers cases SU-56 to SU-65 in TEST_CASES.md, and interpretations I3 and I4 in
DECISIONS.md.

The specification lists ``busy`` as a value but never gives it a meaning -- rule
5 blocks only ``inactive``, so as written ``busy`` affects nothing. We read it as
"holding the maximum number of live agreements", which is how marketplaces
normally present availability, and the service maintains it.

Every state in this module is reached by actually hiring people. Setting the
field directly would produce a supplier who *claims* to be busy while holding no
work -- a state the service can never reach, so a test built on it would prove
nothing.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_conflict, assert_created, assert_field_error, assert_ok

pytestmark = pytest.mark.django_db

MAXIMUM_LIVE_AGREEMENTS = 3


@pytest.mark.case("SU-56")
@pytest.mark.interpretation("I4")
def test_a_new_supplier_is_available(api, supplier):
    body = assert_ok(api.get(endpoints.supplier(supplier.id)))

    assert body["availability_status"] == "available"


@pytest.mark.case("SU-57,SU-58")
@pytest.mark.interpretation("I3")
@pytest.mark.parametrize("agreements", [1, 2], ids=["one-job", "two-jobs"])
def test_a_supplier_below_the_limit_stays_available(
    api, supplier, give_live_agreements, agreements
):
    give_live_agreements(supplier, agreements)

    body = assert_ok(api.get(endpoints.supplier(supplier.id)))

    assert body["availability_status"] == "available"


@pytest.mark.case("SU-59")
@pytest.mark.interpretation("I3")
def test_a_supplier_reaching_the_limit_becomes_busy(api, supplier, give_live_agreements):
    """Three live agreements is what "busy" means.

    This is why the reading resolves rule 5 rather than contradicting it: a busy
    supplier is already blocked by the workload rule, so rule 5 needs no change.
    """
    give_live_agreements(supplier, MAXIMUM_LIVE_AGREEMENTS)

    body = assert_ok(api.get(endpoints.supplier(supplier.id)))

    assert body["availability_status"] == "busy"


@pytest.mark.case("SU-60,SU-61")
@pytest.mark.interpretation("I3")
def test_finishing_a_job_makes_a_busy_supplier_available_again(
    api, supplier, give_live_agreements
):
    agreements = give_live_agreements(supplier, MAXIMUM_LIVE_AGREEMENTS)
    assert assert_ok(api.get(endpoints.supplier(supplier.id)))["availability_status"] == "busy"

    assert_ok(api.post(endpoints.complete(agreements[0]["id"])))

    body = assert_ok(api.get(endpoints.supplier(supplier.id)))
    assert body["availability_status"] == "available"


@pytest.mark.case("SU-61")
@pytest.mark.interpretation("I3")
def test_being_hired_again_makes_the_supplier_busy_again(
    api, supplier, give_live_agreements, hire
):
    agreements = give_live_agreements(supplier, MAXIMUM_LIVE_AGREEMENTS)
    assert_ok(api.post(endpoints.complete(agreements[0]["id"])))

    hire(supplier)

    body = assert_ok(api.get(endpoints.supplier(supplier.id)))
    assert body["availability_status"] == "busy"


@pytest.mark.case("SU-62")
@pytest.mark.rule("BR-04")
def test_a_busy_supplier_cannot_be_hired(api, busy_supplier, open_gig, apply_to_gig):
    application = apply_to_gig(open_gig, busy_supplier)

    response = api.post(endpoints.accept(application["id"]))

    assert_conflict(response, "workload_cap_reached")


@pytest.mark.case("SU-63")
@pytest.mark.interpretation("I3")
def test_a_supplier_who_chose_to_be_inactive_stays_inactive(
    api, supplier, give_live_agreements
):
    """The service never overrides the supplier's own decision.

    Someone who steps away while carrying three jobs should still be inactive
    when one of them finishes -- otherwise finishing work would silently opt
    them back in.
    """
    agreements = give_live_agreements(supplier, MAXIMUM_LIVE_AGREEMENTS)
    assert_ok(api.patch(endpoints.supplier(supplier.id), {"availability_status": "inactive"}))

    assert_ok(api.post(endpoints.complete(agreements[0]["id"])))

    body = assert_ok(api.get(endpoints.supplier(supplier.id)))
    assert body["availability_status"] == "inactive"


@pytest.mark.case("SU-65")
def test_hiring_one_supplier_does_not_change_another(
    api, supplier, other_supplier, give_live_agreements
):
    give_live_agreements(supplier, MAXIMUM_LIVE_AGREEMENTS)

    body = assert_ok(api.get(endpoints.supplier(other_supplier.id)))

    assert body["availability_status"] == "available"


@pytest.mark.case("SU-26a,SU-45")
@pytest.mark.interpretation("I3")
@pytest.mark.parametrize("when", ["registering", "updating"])
def test_a_client_cannot_set_busy_itself(api, supplier, when):
    """``busy`` is derived, so setting it by hand would be overwritten.

    Refusing it with an explanation is better than accepting a value the next
    hire silently replaces.
    """
    if when == "registering":
        response = api.post(
            endpoints.SUPPLIERS,
            {
                "name": "New",
                "email": "new@example.com",
                "skills": [],
                "hourly_rate": "10.00",
                "availability_status": "busy",
            },
            format="json",
        )
    else:
        response = api.patch(
            endpoints.supplier(supplier.id), {"availability_status": "busy"}
        )

    assert_field_error(response, "availability_status")


@pytest.mark.interpretation("I3")
@pytest.mark.parametrize("value", ["available", "inactive"])
def test_a_client_may_choose_available_or_inactive(api, supplier, value):
    body = assert_ok(
        api.patch(endpoints.supplier(supplier.id), {"availability_status": value})
    )

    assert body["availability_status"] == value
