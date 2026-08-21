"""Request and response shapes for creators and suppliers."""


from apps.accounts.models import Creator, Supplier
from apps.accounts.validators import normalize_skills
from apps.common.serializers import EmailNormalizingModelSerializer


class CreatorSerializer(EmailNormalizingModelSerializer):
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


class SupplierSerializer(EmailNormalizingModelSerializer):
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
