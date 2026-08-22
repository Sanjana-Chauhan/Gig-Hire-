"""Factories for building test data.

These build *records*, not *states*. That distinction matters:

``ContractFactory()`` will happily create an agreement whose gig is still ``open``
and whose supplier is still ``available`` -- a combination the real workflow can
never produce, because hiring someone moves the gig to ``in_progress`` and may
move the supplier to ``busy``. A test built on that shortcut can pass against a
service that is actually broken.

So the rule followed throughout the suite:

* factories for preconditions the hiring workflow does not own -- a creator
  exists, a supplier exists, a gig is open;
* the API for anything the workflow does own -- agreements, cascaded rejections,
  a supplier being busy.

The workflow factories below (ApplicationFactory and beyond) exist for the
handful of cases where a state genuinely cannot be reached through the API at
all, such as a terminated agreement. Each use is commented at the call site.
"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.accounts.enums import AvailabilityStatus
from apps.accounts.models import Creator, Supplier
from apps.gigs.enums import GigStatus
from apps.gigs.models import Gig
from apps.hiring.enums import ApplicationStatus, ContractStatus, ReviewerType
from apps.hiring.models import Application, Contract, Review


class CreatorFactory(DjangoModelFactory):
    """A creator who posts gigs."""

    class Meta:
        model = Creator

    # Sequences rather than fixed values: email is unique, so a fixed value
    # would make the second creator in any test fail for the wrong reason.
    name = factory.Sequence(lambda n: f"Creator {n}")
    email = factory.Sequence(lambda n: f"creator{n}@example.com")
    channel_name = factory.Sequence(lambda n: f"Channel {n}")


class SupplierFactory(DjangoModelFactory):
    """A supplier who applies to gigs. Available by default."""

    class Meta:
        model = Supplier

    name = factory.Sequence(lambda n: f"Supplier {n}")
    email = factory.Sequence(lambda n: f"supplier{n}@example.com")
    # LazyFunction, not a plain list: a plain list literal would be shared by
    # every instance the factory ever built, so one test mutating it would
    # change another test's data.
    skills = factory.LazyFunction(lambda: ["editing"])
    hourly_rate = Decimal("45.00")
    availability_status = AvailabilityStatus.AVAILABLE


class GigFactory(DjangoModelFactory):
    """An open gig. Creates its own creator unless one is passed in."""

    class Meta:
        model = Gig

    creator = factory.SubFactory(CreatorFactory)
    title = factory.Sequence(lambda n: f"Edit episode {n}")
    description = "Cut a forty-minute recording down to ten minutes."
    budget = Decimal("500.00")
    category = "editing"
    status = GigStatus.OPEN


class ApplicationFactory(DjangoModelFactory):
    """A pending application.

    Safe to use directly: a pending application is exactly what the apply
    endpoint produces, so nothing about this shape is unreachable.
    """

    class Meta:
        model = Application

    gig = factory.SubFactory(GigFactory)
    supplier = factory.SubFactory(SupplierFactory)
    proposed_rate = Decimal("420.00")
    status = ApplicationStatus.PENDING


class ContractFactory(DjangoModelFactory):
    """An agreement, built directly.

    **Prefer the ``hire`` fixture.** This bypasses the hiring workflow, so the
    gig it points at is still ``open`` and its supplier's availability has not
    been recalculated. Use it only where the state genuinely cannot be reached
    through the API -- principally ``terminated``, which no endpoint can
    produce -- and say so at the call site.
    """

    class Meta:
        model = Contract

    gig = factory.SubFactory(GigFactory)
    supplier = factory.SubFactory(SupplierFactory)
    agreed_rate = Decimal("420.00")
    status = ContractStatus.ACTIVE


class ReviewFactory(DjangoModelFactory):
    """A review. Prefer posting through the API where the rules matter."""

    class Meta:
        model = Review

    contract = factory.SubFactory(ContractFactory)
    reviewer_type = ReviewerType.CREATOR_ON_SUPPLIER
    rating = 5
    comment = ""
