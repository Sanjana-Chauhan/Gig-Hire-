"""Request and response shapes for gigs."""

from rest_framework import serializers

from apps.common.text import canonicalize_tag
from apps.gigs import transitions
from apps.gigs.models import Gig


class GigSerializer(serializers.ModelSerializer):
    """Full representation of a gig.

    ``creator`` is represented as a primary key rather than a nested object.
    That matches the specification (``FK -> Creator``) and it avoids an N+1
    query: DRF's PrimaryKeyRelatedField reads ``gig.creator_id``, a column
    already present on the gig row, so serialising a page of gigs never touches
    the creator table. A nested representation would issue one query per row and
    would need ``select_related`` to compensate.

    ``status`` is read-only. Every gig is created ``open``; the lifecycle is
    driven by domain actions (accepting an application, or an explicit
    transition), never by a client asserting a state directly. Allowing it here
    would permit an ``in_progress`` gig with no contract, which is a state the
    rest of the rules assume cannot exist.

    Note the consequence, recorded in DECISIONS.md: DRF ignores read-only fields
    silently, so ``POST {"status": "completed"}`` returns 201 with status
    ``open`` rather than a 400. That is conventional REST behaviour, and it is
    covered by an explicit test so it is documented rather than accidental.
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
        read_only_fields = ["id", "status", "created_at", "updated_at"]

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
