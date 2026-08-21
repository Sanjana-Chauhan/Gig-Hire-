"""Enumerations for the hiring workflow."""

from django.db import models


class ApplicationStatus(models.TextChoices):
    """The lifecycle of a supplier's application to a gig.

    Business rule 6 declares ``ACCEPTED`` and ``REJECTED`` terminal. The
    specification is silent on ``WITHDRAWN`` (ambiguity A12), but the same
    reasoning applies: a withdrawn application is a completed decision, and
    withdrawing twice is not a meaningful operation.

    So all three non-pending states are terminal, which means the model never
    needs a list of terminal states -- it only needs to know whether an
    application is still ``PENDING``. Framing it that way is not cosmetic: a
    hardcoded set of terminal states is something a future contributor can
    forget to update when adding a state, whereas "anything that is not pending
    is finished" stays correct by construction.
    """

    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
