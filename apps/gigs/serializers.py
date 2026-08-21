"""Request and response shapes for gigs."""

from rest_framework import serializers

from apps.common.text import canonicalize_tag
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
