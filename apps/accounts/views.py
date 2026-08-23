"""API endpoints for creators and suppliers."""

from rest_framework import mixins, viewsets

from apps.accounts.models import Creator, Supplier
from apps.accounts.serializers import CreatorSerializer, SupplierSerializer


class CreatorViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Create, retrieve, list and update creators.

    Update is included because a creator changing their display name, channel
    name or email address is ordinary account maintenance, not an exceptional
    operation -- and with no way to do it, a creator who rebrands or changes
    email would have to be recreated, orphaning nothing but starting their gig
    history from scratch. The specification lists no creator endpoints at all, so
    this is an addition rather than a deviation (table 3 in DECISIONS.md).

    Destroy is still deliberately absent. A creator's gigs are protected against
    deletion, so removing a creator would either fail at the database or, with a
    different setting, silently take their entire gig, contract and review
    history with it. The recognised way to retire an account is to stop using
    it, not to erase the record of what it did. Recorded as an open question in
    DECISIONS.md.

    The endpoints themselves are an addition to the specification, which lists no
    creator routes at all while requiring a creator FK on every gig. Without
    them the API cannot be used end to end. Listed in table 3 of DECISIONS.md.
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
    rule is unreachable and therefore untestable at the API layer. Listed in
    table 3 of DECISIONS.md.

    Destroy is again deliberately absent: a supplier with contracts and reviews
    is a reputation record, and the specification never asks for it to be
    removable.
    """

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
