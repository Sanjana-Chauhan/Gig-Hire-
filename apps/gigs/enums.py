"""Enumerations for the gigs domain."""

from django.db import models


class GigStatus(models.TextChoices):
    """The lifecycle of a gig.

    ``OPEN`` is the only state a gig can be created in: it is reached by posting
    a gig, and every other state is reached by an explicit domain action.
    ``IN_PROGRESS`` in particular is reachable *only* by accepting an application
    (business rule 3), because that transition also creates the Contract. If a
    client could set it directly there would be in-progress gigs with no
    contract, and every rule that reasons about in-progress gigs -- including
    rule 7's delete guard -- would be quietly bypassable.

    The full transition table lives in ``apps/gigs/transitions.py``, where the
    specification's silence on which of the sixteen transitions are legal is
    resolved (interpretation I7 in DECISIONS.md).
    """

    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
