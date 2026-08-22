"""Request and response shapes for gigs."""

from rest_framework import serializers

from apps.common.serializers import BaseModelSerializer

from apps.common.text import canonicalize_tag
from apps.gigs import transitions
from apps.gigs.enums import GigStatus
from apps.gigs.models import Gig


class GigSerializer(BaseModelSerializer):
    """Full representation of a gig.

    ``creator`` is represented as a primary key rather than a nested object.
    That matches the specification (``FK -> Creator``) and it avoids an N+1
    query: DRF's PrimaryKeyRelatedField reads ``gig.creator_id``, a column
    already present on the gig row, so serialising a page of gigs never touches
    the creator table. A nested representation would issue one query per row and
    would need ``select_related`` to compensate.

    ``status`` may be supplied when creating, but only as ``open`` -- see
    ``validate_status``. Every gig therefore begins open, and the lifecycle is
    driven by domain actions (accepting an application, or an explicit
    transition) rather than by a client asserting a state directly. Allowing
    any value here would permit an ``in_progress`` gig with no contract, which
    is a state the rest of the rules assume cannot exist.
    """

    class Meta:
        model = Gig
        fields = [
            "id",
            "creator",
            "title",
            "description",
            "budget",
            "category",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_status(self, value: str) -> str:
        """Only ``open`` may be supplied when creating a gig.

        ``status`` used to be read-only here, which protected the workflow but
        had a dishonest side effect: DRF drops read-only fields *silently*, so
        ``POST {"status": "completed"}`` returned 201 with a gig that was
        actually open. The caller was told their request succeeded when the most
        important part of it had been discarded.

        Accepting the field and refusing every value except ``open`` keeps the
        protection and adds the missing error. The invariant is unchanged:
        ``in_progress`` is still reachable only by accepting an application, and
        ``completed``/``cancelled`` only by an explicit transition on an existing
        gig.

        GigUpdateSerializer overrides this, because on update any status may be
        *sent* -- whether the move is legal is decided by the transition table.
        """
        if value != GigStatus.OPEN:
            raise serializers.ValidationError(
                f'A gig can only be created with status "{GigStatus.OPEN}". '
                f'"{value}" is reached through the hiring workflow or an '
                f"explicit status change on an existing gig."
            )
        return value

    def validate_category(self, value: str) -> str:
        """Canonicalise the category so filtering is reliable.

        Category is free text, so without this ``Editing``, ``editing`` and
        `` editing `` are three distinct categories, and a filter for any one of
        them silently misses the other two. The same canonicalisation is applied
        to the query parameter in GigFilterSet -- both sides must agree, which is
        why the function is shared rather than inlined.
        """
        return canonicalize_tag(value)


class GigUpdateSerializer(GigSerializer):
    """Serializer for PATCH/PUT, where ``status`` becomes writable.

    A separate class rather than conditional logic inside GigSerializer, because
    the two contexts genuinely have different rules: on create, ``status`` is not
    a client's business at all (every gig starts open); on update, a status
    transition is the *main* thing rule 8 allows. Expressing that as two
    serializers means each one is readable on its own, instead of one serializer
    whose field set depends on whether ``self.instance`` happens to be set.

    Business rules are enforced in ``validate()`` by delegating to
    apps.gigs.transitions. The rules live there, not here, so they can be tested
    without constructing a serializer and reused by anything else that moves a
    gig through its lifecycle.
    """

    class Meta(GigSerializer.Meta):
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_status(self, value: str) -> str:
        """Any valid status may be *sent* on update.

        Deliberately neutralises the parent's create-only restriction. Whether a
        particular move is permitted is not a question about the value in
        isolation -- it depends on the gig's current status and its contracts --
        so it is answered by the transition table in ``validate()`` below, which
        can give a far more useful message than "that is not open".
        """
        return value

    def validate(self, attrs: dict) -> dict:
        gig = self.instance

        # Rule 8: budget and category freeze once the gig leaves `open`.
        # Checked against the keys the client actually sent -- not against every
        # field on the serializer -- so a PATCH that merely echoes the current
        # budget is treated the same as one that changes it. That is deliberate:
        # "you may not send this field now" is a simpler contract to reason about
        # than "you may send it if the value happens to match".
        transitions.assert_fields_mutable(gig=gig, incoming_fields=attrs.keys())

        if "status" in attrs:
            transitions.assert_transition_allowed(gig=gig, target_status=attrs["status"])

        return attrs
