"""Creator and Supplier: the two parties to a hiring transaction."""

from django.db import models

from apps.accounts.constants import (
    MAX_CHANNEL_NAME_LENGTH,
    MAX_NAME_LENGTH,
)
from apps.accounts.enums import AvailabilityStatus
from apps.accounts.validators import validate_skill_list
from apps.common.constraints import positive_value_constraint
from apps.common.fields import PositiveMoneyField
from apps.common.models import TimeStampedModel


class Creator(TimeStampedModel):
    """Someone who posts gigs and hires suppliers.

    ``EmailField`` rather than the specification's plain "string": the intent is
    obviously an email address, and the format check turns ``"not-an-email"``
    into a clean 400 instead of a row that no mail system can ever reach.
    Recorded in DECISIONS.md as a deliberate strengthening of the spec.
    """

    name = models.CharField(max_length=MAX_NAME_LENGTH)
    email = models.EmailField(unique=True)
    channel_name = models.CharField(max_length=MAX_CHANNEL_NAME_LENGTH)

    class Meta:
        # Newest first is the conventional default for an API listing, and the
        # id tiebreak makes the order *total*: without it, rows created in the
        # same instant could come back in any order, which makes paginated
        # results non-deterministic and pagination tests flaky.
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.channel_name})"


class Supplier(TimeStampedModel):
    """Someone who applies to gigs and does the work."""

    name = models.CharField(max_length=MAX_NAME_LENGTH)
    email = models.EmailField(unique=True)

    # Stored as a JSON array of canonical tags. See the class docstring note in
    # DECISIONS.md: this is the simple choice, and it is the wrong choice the
    # moment "find every supplier who can animate" needs to use an index.
    skills = models.JSONField(default=list, blank=True, validators=[validate_skill_list])

    hourly_rate = PositiveMoneyField()

    availability_status = models.CharField(
        max_length=16,
        choices=AvailabilityStatus.choices,
        # The specification does not state a default. Defaulting to AVAILABLE is
        # the only sensible reading -- somebody registering as a supplier is
        # announcing they want work -- but it is an interpretation, so it is
        # recorded in DECISIONS.md rather than assumed silently.
        default=AvailabilityStatus.AVAILABLE,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # The validator on PositiveMoneyField produces the clean 400; this
            # constraint is what makes the invariant true even for writes that
            # never run validation.
            positive_value_constraint(
                field="hourly_rate",
                name="supplier_hourly_rate_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"

    @property
    def is_hireable(self) -> bool:
        """Whether this supplier may be given a new contract.

        Business rule 5 checks availability at accept-time. Expressing it as a
        property on the model keeps the *definition* of hireability in one place,
        so the accept service reads as a business rule rather than a string
        comparison, and a future change to the rule has exactly one edit site.

        Deliberately permissive about BUSY -- see AvailabilityStatus.
        """
        return self.availability_status != AvailabilityStatus.INACTIVE
