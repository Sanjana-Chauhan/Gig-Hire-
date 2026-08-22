"""Reusable serializer fields and the project's base model serializer."""

from django.db import models
from rest_framework import serializers

from apps.common.constants import (
    MONEY_DECIMAL_PLACES,
    MONEY_MAX_DIGITS,
    MONEY_SMALLEST_POSITIVE,
)
from apps.common.fields import PositiveMoneyField


class NormalizedEmailField(serializers.EmailField):
    """An email field that lowercases and trims before anything else sees it.

    Why normalise at all
    --------------------
    The specification says email is unique but is silent on case. Left as-is,
    ``Bob@example.com`` and ``bob@example.com`` are two distinct accounts for the
    same person -- and in a hiring platform that means split reputation, split
    contract history, and a supplier who cannot find their own gigs. The domain
    part of an email address is case-insensitive by definition, and in practice
    every mainstream provider treats the local part that way too.

    Why a custom field instead of ``validate_email()`` on the serializer
    -------------------------------------------------------------------
    This is about DRF's validation *order*, which is easy to get wrong:

        1. ``Field.to_internal_value()``       <- conversion
        2. ``Field.validators``                <- includes UniqueValidator
        3. ``Serializer.validate_<field>()``   <- runs LAST

    Normalising in ``validate_email()`` would run *after* the uniqueness check.
    A POST of ``BOB@example.com`` when ``bob@example.com`` already exists would
    therefore pass the uniqueness validator on the raw value, get lowercased
    afterwards, and only fail at the database -- surfacing as a 409 integrity
    error instead of a clean 400 with a field-level message.

    Normalising in ``to_internal_value()`` happens at step 1, so the uniqueness
    validator sees the value that will actually be stored, and the client gets
    ``{"email": ["This field must be unique."]}`` with a 400.

    Kept in ``common`` rather than duplicated across Creator and Supplier: there
    are only two usages today, which normally argues for waiting. It lives here
    anyway because this is a *correctness* fix with non-obvious reasoning, and
    duplicating a subtle correctness fix is materially worse than duplicating
    boilerplate -- the copies drift, and the second copy never gets the comment.
    """

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        return value.strip().lower()


def _largest_allowed_amount() -> str:
    """The biggest value a money field can hold, formatted for a person to read.

    Derived from the precision constants rather than written out, so the message
    cannot drift away from the rule it describes.
    """
    whole_digits = MONEY_MAX_DIGITS - MONEY_DECIMAL_PLACES
    largest_whole = 10**whole_digits - 1
    largest_fraction = "9" * MONEY_DECIMAL_PLACES
    return f"{largest_whole:,}.{largest_fraction}"


class MoneyField(serializers.DecimalField):
    """A money field whose error messages describe money, not arithmetic.

    The framework's defaults are technically accurate and unhelpful: "Ensure
    that there are no more than 12 digits in total" tells a caller about the
    storage format rather than about the amount they sent. Someone who mistyped
    a rate needs to know what the limit *is* and what a correct value looks like.

    The messages are declared as ``default_error_messages`` -- a class attribute
    -- rather than updated inside ``__init__``. That is not a style preference:
    DRF's DecimalField builds its own MinValueValidator during ``__init__`` and
    bakes the *current* text of ``error_messages["min_value"]`` into it. Editing
    the dictionary after calling ``super().__init__()`` is therefore too late,
    and the old wording survives. Field collects ``default_error_messages`` from
    every class in the hierarchy before any of that happens, so a subclass
    declared this way wins.

    Applied everywhere automatically through BaseModelSerializer's field
    mapping, so no serializer has to remember to ask for it.
    """

    default_error_messages = {
        "invalid": "Enter this amount as a number, for example 45.50.",
        "min_value": (
            f"This amount must be greater than zero. The smallest allowed "
            f"value is {MONEY_SMALLEST_POSITIVE}."
        ),
        "max_decimal_places": (
            f"Amounts may have at most {MONEY_DECIMAL_PLACES} decimal places, "
            f"for example 45.50."
        ),
        "max_digits": (
            f"This amount is too large. The largest allowed value is "
            f"{_largest_allowed_amount()}."
        ),
        "max_whole_digits": (
            f"This amount is too large. The largest allowed value is "
            f"{_largest_allowed_amount()}."
        ),
    }


class BaseModelSerializer(serializers.ModelSerializer):
    """A ModelSerializer that renders every model EmailField as a normalised one.

    Why this exists rather than declaring ``email = NormalizedEmailField()`` on
    each serializer -- a trap worth remembering:

    DRF adds a ``UniqueValidator`` automatically only to fields it *builds
    itself* from the model. The moment a field is declared explicitly on the
    serializer, DRF uses the declaration verbatim and every validator inferred
    from the model -- uniqueness included -- is silently dropped. Declaring
    ``email = NormalizedEmailField()`` therefore removes the uniqueness check,
    and a duplicate email falls through to the database as an IntegrityError,
    surfacing as a 409 instead of the 400 that business rule 10 requires.

    Overriding ``serializer_field_mapping`` instead means DRF still builds the
    field, so it still attaches ``UniqueValidator``, ``max_length`` and
    ``required`` from the model -- it just builds it as our subclass. The
    normalisation and the uniqueness check compose, and no subclass can forget
    either one.

    The cost, stated honestly: this is implicit. A reader of CreatorSerializer
    sees no mention of email handling and has to look at the base class. The
    alternative -- an explicit declaration in every serializer -- is more visible
    at the point of use, but it has to be got right every time, and getting it
    wrong fails silently. A footgun removed structurally beats a footgun
    documented.
    """

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.EmailField: NormalizedEmailField,
        PositiveMoneyField: MoneyField,
    }
