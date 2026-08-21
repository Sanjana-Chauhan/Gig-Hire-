"""Reusable model fields."""

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.constants import (
    MONEY_DECIMAL_PLACES,
    MONEY_MAX_DIGITS,
    MONEY_SMALLEST_POSITIVE,
)


class PositiveMoneyField(models.DecimalField):
    """A monetary amount that must be strictly positive.

    Three fields in this domain share exactly these semantics -- a supplier's
    ``hourly_rate``, a gig's ``budget`` and an application's ``proposed_rate``
    are all "required, greater than zero, two decimal places". That is the rule
    of three: the third occurrence is the point at which extracting an
    abstraction stops being speculative.

    Why a field subclass rather than a helper returning kwargs: the field *is*
    the concept. ``budget = PositiveMoneyField()`` states the intent, whereas
    repeating ``DecimalField(max_digits=12, decimal_places=2, validators=[...])``
    three times invites the three copies to drift apart.

    Why ``default_validators`` rather than passing ``validators`` in ``__init__``:
    Django serialises constructor arguments into migrations, so a validator
    passed as a kwarg would be written into every migration that touches the
    field. ``default_validators`` is a class attribute, so it stays out of
    migrations while still being picked up by ``full_clean()`` and -- importantly
    -- by DRF, which copies model field validators onto the serializer field.
    That is what turns this into a 400 rather than a database error.

    Note that this is the *validation* layer only. Each model additionally
    declares a database CheckConstraint, because a validator can be bypassed by
    any code path that does not call ``full_clean()`` (``objects.create()``,
    ``bulk_create()``, a raw query). See apps/common/constraints.py.
    """

    default_validators = [MinValueValidator(MONEY_SMALLEST_POSITIVE)]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", MONEY_MAX_DIGITS)
        kwargs.setdefault("decimal_places", MONEY_DECIMAL_PLACES)
        super().__init__(*args, **kwargs)
