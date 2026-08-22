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


class ContractStatus(models.TextChoices):
    """The lifecycle of a contract.

    ``TERMINATED`` is declared because business rule 4 counts "non-completed,
    non-terminated" contracts, so the rule itself refers to the state. No
    endpoint in the specification can produce it, however -- there is no
    terminate action. It is therefore currently unreachable through the API,
    recorded as gap G4 in DECISIONS.md, and deliberately *not* given an invented
    endpoint: implementing a feature the specification never asked for is a
    worse failure than reporting the gap.
    """

    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    TERMINATED = "terminated", "Terminated"


class ReviewerType(models.TextChoices):
    """Which direction a review runs.

    A hiring transaction has two sides and both get to speak, so the reviewer
    type is not "who wrote it" but "which relationship is being rated". That is
    what makes business rule 9's uniqueness meaningful: one review per direction
    per contract, so a creator cannot pile on but the supplier's own review is
    unaffected.
    """

    CREATOR_ON_SUPPLIER = "creator_on_supplier", "Creator on supplier"
    SUPPLIER_ON_CREATOR = "supplier_on_creator", "Supplier on creator"
