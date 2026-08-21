"""The Gig: a unit of work a creator wants done."""

from django.db import models

from apps.gigs.constants import MAX_CATEGORY_LENGTH, MAX_TITLE_LENGTH
from apps.gigs.enums import GigStatus
from apps.common.constraints import positive_value_constraint
from apps.common.fields import PositiveMoneyField
from apps.common.models import TimeStampedModel


class Gig(TimeStampedModel):
    """Work posted by a creator, which suppliers may apply to."""

    creator = models.ForeignKey(
        "accounts.Creator",
        on_delete=models.PROTECT,
        related_name="gigs",
        # PROTECT, not CASCADE. Deleting a creator would otherwise silently
        # delete their entire gig history -- and, once contracts exist, the
        # financial and reputation record attached to it. Refusing the delete is
        # recoverable; a cascade is not. No endpoint exposes creator deletion,
        # so this guards the admin and any future management command.
    )

    title = models.CharField(max_length=MAX_TITLE_LENGTH)
    description = models.TextField()
    budget = PositiveMoneyField()

    # Indexed because the specification requires filtering on it. An index on a
    # column that is always filtered is the cheapest performance decision
    # available; an index on a column nobody filters is pure write overhead.
    category = models.CharField(max_length=MAX_CATEGORY_LENGTH, db_index=True)

    status = models.CharField(
        max_length=16,
        choices=GigStatus.choices,
        default=GigStatus.OPEN,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            positive_value_constraint(field="budget", name="gig_budget_positive"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_open(self) -> bool:
        """Whether this gig currently accepts applications.

        Named as a business question rather than a status comparison, so callers
        read as rules. Business rule 1 (only open gigs accept applications) and
        the accept guard (ambiguity A10) both ask exactly this, and both should
        change together if the definition ever widens.
        """
        return self.status == GigStatus.OPEN

    @property
    def has_active_contract(self) -> bool:
        """Whether this gig is currently under contract.

        Reads through the reverse relation using hiring's own queryset
        vocabulary, so the gigs app never imports hiring and the dependency
        graph stays acyclic. See ContractQuerySet.active().

        This is the question behind business rule 7 (a gig with an active
        contract cannot be deleted) and behind rule 8's transition
        preconditions -- a gig must not be completed or cancelled out from under
        a live agreement.
        """
        return self.contracts.active().exists()

    @property
    def has_contract_history(self) -> bool:
        """Whether any contract has ever existed for this gig.

        Distinct from has_active_contract, and the distinction is the whole of
        ambiguity A5. Rule 7 only forbids deleting a gig with an *active*
        contract -- read literally, a gig whose contract has been completed is
        deletable, which would cascade away that contract and its reviews.
        Since Contract.gig is PROTECT, that cascade cannot actually happen; this
        property is what turns the database's refusal into a clean 409 with a
        useful message.
        """
        return self.contracts.exists()
