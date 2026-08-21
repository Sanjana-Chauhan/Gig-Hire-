"""Reusable serializer fields and base classes."""

from django.db import models
from rest_framework import serializers


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


class EmailNormalizingModelSerializer(serializers.ModelSerializer):
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
    }
