"""Enumerations for the accounts domain."""

from django.db import models


class AvailabilityStatus(models.TextChoices):
    """Whether a supplier is open to being hired.

    ``TextChoices`` rather than bare strings gives three things at once: the
    valid set is declared in one place, Django validates against it, and
    ``AvailabilityStatus.INACTIVE`` can be referenced from code and tests
    instead of the string ``"inactive"`` -- so a typo is an AttributeError at
    import time rather than a silently unmatched filter at runtime.

    A note on the domain, because it is counter-intuitive: business rule 5
    blocks acceptance only for ``INACTIVE``. A ``BUSY`` supplier can still be
    hired. That is what the specification says, and it is flagged in
    DECISIONS.md as a probable product error rather than quietly "fixed" here.
    """

    AVAILABLE = "available", "Available"
    BUSY = "busy", "Busy"
    INACTIVE = "inactive", "Inactive"
