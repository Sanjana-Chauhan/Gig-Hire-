"""API endpoints for creators and suppliers."""

from rest_framework import mixins, viewsets

from apps.accounts.models import Creator, Supplier
from apps.accounts.serializers import CreatorSerializer, SupplierSerializer


class CreatorViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Create, retrieve and list creators.

    Composed from explicit mixins rather than subclassing ``ModelViewSet``. That
    is a least-privilege decision: ``ModelViewSet`` would also expose update and
    destroy, and ``DELETE /api/creators/{id}/`` would cascade away every gig that
    creator ever posted -- along with its contracts and reviews. Nothing in the
    specification asks for it, so the safest thing to expose is nothing.

    The endpoints themselves are an addition to the specification, which lists no
    creator routes at all while requiring a creator FK on every gig. Without
    them the API cannot be used end to end. Recorded as gap G1 in DECISIONS.md.
    """

    queryset = Creator.objects.all()
    serializer_class = CreatorSerializer


class SupplierViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Register, retrieve, list and update suppliers.

    ``UpdateModelMixin`` is present for a specific reason beyond completeness:
    business rule 5 requires a supplier to become ``inactive`` *between* applying
    and being accepted. With no way to change availability over the API, that
    rule is unreachable and therefore untestable at the API layer. Recorded as
    gap G2 in DECISIONS.md.

    Destroy is again deliberately absent: a supplier with contracts and reviews
    is a reputation record, and the specification never asks for it to be
    removable.
    """

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
