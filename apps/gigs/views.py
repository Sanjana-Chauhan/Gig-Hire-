"""API endpoints for gigs."""

from rest_framework import viewsets

from apps.gigs.filters import GigFilterSet
from apps.gigs.models import Gig
from apps.gigs import transitions
from apps.gigs.serializers import GigSerializer, GigUpdateSerializer


class GigViewSet(viewsets.ModelViewSet):
    """Full CRUD for gigs, as the specification requires.

    Unlike the accounts viewsets, this one is a full ``ModelViewSet``: the
    specification explicitly lists POST, GET (list and detail), PATCH and
    DELETE, so every operation is asked for and nothing is published by
    accident.

    ``PUT`` comes along with ``ModelViewSet`` and is not in the specification.
    It is left in place because a partial-update-only resource that rejects
    ``PUT`` surprises clients, and because ``PUT`` on this serializer is
    equivalent to a full ``PATCH`` -- the read-only ``status`` cannot be set
    either way. Noted in DECISIONS.md.

    No ``select_related("creator")``. That is deliberate, not an oversight: the
    serializer represents the creator as a primary key, which DRF reads from the
    ``creator_id`` column already on the gig row. There is no related-table
    access to optimise, and a JOIN for data nothing reads is simply a slower
    query. If a nested creator representation is ever added, it must be added
    together with ``select_related`` -- nesting alone turns one query into N+1.

    The delete guard for business rule 7 (a gig with an active contract must not
    be deletable) is not here yet: contracts do not exist until Step 6. It lands
    in Step 8 alongside the status state machine and field immutability.
    """

    queryset = Gig.objects.all()
    serializer_class = GigSerializer
    filterset_class = GigFilterSet

    def get_serializer_class(self):
        """Use the update serializer for PATCH and PUT.

        Status is read-only on create (every gig starts open) and writable on
        update (rule 8 permits transitions). Selecting by action keeps each
        serializer's field set static and readable, rather than having one class
        whose behaviour depends on whether an instance is attached.
        """
        if self.action in {"update", "partial_update"}:
            return GigUpdateSerializer
        return GigSerializer

    def perform_destroy(self, instance: Gig) -> None:
        """Enforce business rule 7 before deleting.

        The guard lives here rather than in a serializer because DELETE has no
        serializer -- there is no payload to validate. Overriding
        ``perform_destroy`` is DRF's designated seam for exactly this: a rule
        that applies to the act of deleting rather than to any input.

        Contract.gig is PROTECT, so even without this check the database would
        refuse and the exception handler would turn it into a 409. This check
        exists so the client gets a specific, actionable message instead of a
        generic integrity error -- and so the ERROR log reserved for genuine
        validation gaps is not triggered by ordinary, expected refusals.
        """
        transitions.assert_gig_deletable(gig=instance)
        instance.delete()
