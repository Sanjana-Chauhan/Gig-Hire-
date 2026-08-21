"""Request and response shapes for the hiring workflow."""

from rest_framework import serializers

from apps.accounts.models import Supplier
from apps.hiring.models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    """Read representation of an application.

    Related objects as primary keys, for the same reason as GigSerializer: the
    ids are already columns on the row, so listing applications costs no extra
    queries.
    """

    class Meta:
        model = Application
        fields = [
            "id",
            "gig",
            "supplier",
            "proposed_rate",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApplyToGigSerializer(serializers.ModelSerializer):
    """Validates the body of ``POST /api/gigs/{id}/apply/``.

    This is a *command* payload rather than a representation of a resource, and
    it is used for validation only -- ``save()`` is never called on it. Creation
    goes through ``services.apply_to_gig``, because rules 1 and 2 need to see
    the gig's status and the supplier's other applications, which is more than a
    serializer should know about.

    Two details worth noting:

    ``supplier_id`` is declared explicitly because the specification names that
    field in the request body. DRF's own convention would call it ``supplier``;
    the spec wins, and ``source="supplier"`` maps it back so that
    ``validated_data`` contains a Supplier instance ready to hand to the service.
    Declaring it also gives a proper 400 for an unknown id instead of a 404 or a
    database error.

    ``proposed_rate`` is *not* declared. Letting DRF build it from the model
    means it inherits ``max_digits``, ``decimal_places`` and the positivity
    validator from PositiveMoneyField -- one definition of what a monetary
    amount is, rather than a second copy here that can drift. This is the same
    lesson as Step 3's email bug, applied in the other direction: DRF's
    inference from the model is a feature, and declaring a field throws it away.
    """

    supplier_id = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(),
        source="supplier",
    )

    class Meta:
        model = Application
        fields = ["supplier_id", "proposed_rate"]
