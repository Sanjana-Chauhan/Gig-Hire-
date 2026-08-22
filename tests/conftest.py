"""Shared fixtures.

Two kinds live here, and the difference is the point:

* **Record fixtures** (``creator``, ``supplier``, ``open_gig``) build rows with
  factories. Fast, and safe because these shapes are ones the API produces too.
* **Workflow fixtures** (``hire``, ``busy_supplier``, ``completed_agreement``)
  build state by *calling the API*. Slower, and the only way to be sure the
  state is one the real service can actually reach.

Every fixture is function-scoped, so no test can see another test's data and the
suite gives the same result in any order. Nothing is shared and nothing is
mutated across tests.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from tests import endpoints
from tests.assertions import assert_created, assert_ok
from tests.factories import (
    ApplicationFactory,
    CreatorFactory,
    GigFactory,
    SupplierFactory,
)


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------


@pytest.fixture
def api() -> APIClient:
    """A client that talks to the API over the request/response cycle.

    Every test goes through this rather than calling service functions directly.
    That is deliberate: the service layer being correct is not the promise this
    project makes to a caller -- the promise is about status codes, response
    bodies and error messages, and only a request exercises those.
    """
    return APIClient()


# ---------------------------------------------------------------------------
# Records -- built with factories
# ---------------------------------------------------------------------------


@pytest.fixture
def creator():
    """A creator who can post gigs."""
    return CreatorFactory()


@pytest.fixture
def other_creator():
    """A second, unrelated creator, for checking that data does not leak."""
    return CreatorFactory()


@pytest.fixture
def supplier():
    """An available supplier."""
    return SupplierFactory()


@pytest.fixture
def other_supplier():
    """A second available supplier, for competing-bid scenarios."""
    return SupplierFactory()


@pytest.fixture
def third_supplier():
    """A third supplier, so a gig can have three competing bids."""
    return SupplierFactory()


@pytest.fixture
def inactive_supplier():
    """A supplier who is not taking work."""
    return SupplierFactory(availability_status="inactive")


@pytest.fixture
def open_gig(creator):
    """An open gig belonging to ``creator``, budget 500.00, category "editing"."""
    return GigFactory(creator=creator)


@pytest.fixture
def application(open_gig, supplier):
    """A single pending application on ``open_gig`` from ``supplier``."""
    return ApplicationFactory(gig=open_gig, supplier=supplier)


# ---------------------------------------------------------------------------
# Workflow state -- built through the API
# ---------------------------------------------------------------------------


@pytest.fixture
def apply_to_gig(api):
    """Submit an application through the API and return the response body.

    Used where a test needs a pending application that is definitely one the
    apply endpoint produced, rather than one a factory invented.
    """

    def _apply(gig, supplier, proposed_rate="420.00"):
        response = api.post(
            endpoints.apply_to(gig.id),
            {"supplier_id": supplier.id, "proposed_rate": proposed_rate},
        )
        return assert_created(response)

    return _apply


@pytest.fixture
def hire(api, apply_to_gig):
    """Hire ``supplier`` for a fresh gig, through the API. Returns the agreement.

    Creates a gig, applies, and accepts -- so the resulting state is one the real
    workflow reached: the gig is in progress, the agreement is active, and the
    supplier's availability has been recalculated.

    Building this with ContractFactory instead would produce an agreement on a
    still-open gig, which the service can never do, and any test relying on it
    would be checking a fiction.
    """

    def _hire(supplier, *, creator=None, proposed_rate="420.00"):
        gig = GigFactory(creator=creator) if creator else GigFactory()
        application = apply_to_gig(gig, supplier, proposed_rate)
        response = api.post(endpoints.accept(application["id"]))
        return assert_created(response)

    return _hire


@pytest.fixture
def give_live_agreements(hire):
    """Put a supplier on ``count`` live agreements. Returns the agreements.

    Used by the workload-limit tests. Goes through hiring each time, so the
    supplier's availability ends up wherever the service puts it -- which for a
    count of three means "busy".
    """

    def _give(supplier, count):
        return [hire(supplier) for _ in range(count)]

    return _give


@pytest.fixture
def give_finished_agreements(api, hire):
    """Give a supplier ``count`` completed agreements. Returns them.

    Each one is completed immediately after being made, rather than hiring
    ``count`` times and completing afterwards. That ordering is required, not
    stylistic: hiring four times in a row would hit the three-agreement limit
    during the setup, and the test would fail for a reason that has nothing to
    do with what it is checking.
    """

    def _give(supplier, count):
        finished = []
        for _ in range(count):
            agreement = hire(supplier)
            finished.append(assert_ok(api.post(endpoints.complete(agreement["id"]))))
        return finished

    return _give


@pytest.fixture
def busy_supplier(supplier, give_live_agreements):
    """A supplier carrying the maximum number of live agreements.

    Reached by hiring three times rather than by setting the field, because
    "busy" is worked out by the service from the agreement count. Setting the
    field directly would produce a supplier who *claims* to be busy while
    holding no work, which is not a state the service produces.
    """
    give_live_agreements(supplier, 3)
    supplier.refresh_from_db()
    return supplier


@pytest.fixture
def completed_agreement(api, hire, supplier):
    """An agreement that has been carried out and marked complete."""
    agreement = hire(supplier)
    return assert_ok(api.post(endpoints.complete(agreement["id"])))


@pytest.fixture
def gig_with_three_bids(api, open_gig, supplier, other_supplier, third_supplier,
                        apply_to_gig):
    """An open gig with three competing pending applications.

    Returns ``(gig, [application, application, application])`` in the order the
    bids were submitted. The central fixture for the cascade tests.
    """
    bids = [
        apply_to_gig(open_gig, supplier, "420.00"),
        apply_to_gig(open_gig, other_supplier, "390.00"),
        apply_to_gig(open_gig, third_supplier, "450.00"),
    ]
    return open_gig, bids


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


@pytest.fixture
def small_page(settings):
    """Shrink the page size to 2 for pagination tests.

    Crossing a page boundary then needs three records instead of twenty-one,
    which keeps the pagination tests fast and their intent obvious. Possible
    only because the pagination class reads its size per request rather than
    freezing it at import.
    """
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "PAGE_SIZE": 2}
    return 2


@pytest.fixture
def money():
    """Build a Decimal the way the API returns one, for exact comparisons."""
    return lambda value: Decimal(str(value)).quantize(Decimal("0.01"))
