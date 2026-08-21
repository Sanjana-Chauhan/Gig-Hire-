"""API endpoints for gigs."""

from rest_framework import viewsets

from apps.gigs.filters import GigFilterSet
from apps.gigs.models import Gig
from apps.gigs.serializers import GigSerializer


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
