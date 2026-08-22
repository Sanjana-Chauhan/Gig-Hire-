"""Request and response shapes for creators and suppliers."""


from rest_framework import serializers

from apps.accounts.enums import AvailabilityStatus
from apps.accounts.models import Creator, Supplier
from apps.accounts.validators import normalize_skills
from apps.common.constants import MAX_ACTIVE_CONTRACTS_PER_SUPPLIER
from apps.common.serializers import BaseModelSerializer


class CreatorSerializer(BaseModelSerializer):
    """Full representation of a creator, used for both input and output.

    One serializer for both directions is right while the two shapes are
    identical apart from read-only fields. The moment they diverge -- a write
    field the response must not echo, say -- this should split into
    CreatorWriteSerializer / CreatorReadSerializer rather than grow conditionals.
    """

    class Meta:
        model = Creator
        fields = ["id", "name", "email", "channel_name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplierSerializer(BaseModelSerializer):
    """Full representation of a supplier."""

    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "email",
            "skills",
            "hourly_rate",
            "availability_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_availability_status(self, value: str) -> str:
        """``busy`` is set by the service, not by the client.

        Our interpretation, taken from how marketplaces normally work: a
        supplier is busy exactly when they are carrying as much work as the
        platform allows -- three live agreements. That makes it a *derived*
        value, recomputed whenever the supplier is hired or finishes a job, so
        letting a client set it would only create a value the next hire
        overwrites.

        A supplier therefore chooses between two states:

        * ``available`` -- open to work
        * ``inactive``  -- not taking work, and never overwritten by the service

        Recorded as B-3 and D-2 in DECISIONS.md, together with the reason this
        reading resolves rule 5 rather than contradicting it.
        """
        if value == AvailabilityStatus.BUSY:
            raise serializers.ValidationError(
                f'"{AvailabilityStatus.BUSY}" is set automatically when a '
                f"supplier reaches the maximum of "
                f"{MAX_ACTIVE_CONTRACTS_PER_SUPPLIER} live agreements, and "
                f"cleared when one finishes. Send "
                f'"{AvailabilityStatus.AVAILABLE}" to take work or '
                f'"{AvailabilityStatus.INACTIVE}" to stop.'
            )
        return value

    def validate_skills(self, value: list[str]) -> list[str]:
        """Canonicalise the skills list.

        The model-level ``validate_skill_list`` has already rejected anything
        structurally wrong (not a list, non-string entries, over-long tags),
        because DRF copies model field validators onto the serializer field and
        runs them before this hook. So by the time we get here the value is known
        to be a well-formed list of strings and this only has to canonicalise it.

        Enforcement in the model, canonicalisation at the boundary -- the same
        split as NormalizedEmailField, for the same reason.
        """
        return normalize_skills(value)
