"""Models for the hiring workflow."""

from django.db import models

from apps.common.constraints import positive_value_constraint
from apps.common.fields import PositiveMoneyField
from apps.common.models import TimeStampedModel
from apps.hiring.enums import ApplicationStatus


class Application(TimeStampedModel):
    """A supplier's bid for a gig."""

    gig = models.ForeignKey(
        "gigs.Gig",
        on_delete=models.CASCADE,
        related_name="applications",
        # CASCADE here, unlike everywhere else in this project. An application
        # has no meaning independent of its gig -- it is a bid for that specific
        # piece of work, carries no money and no reputation. Contracts and
        # reviews are the opposite and will use PROTECT.
        #
        # PROTECT here would also make DELETE /api/gigs/{id}/ nearly unusable:
        # any gig that had ever received an application would be undeletable,
        # which contradicts the specification exposing the endpoint at all.
        # Recorded as A23 in DECISIONS.md.
    )
    supplier = models.ForeignKey(
        "accounts.Supplier",
        on_delete=models.PROTECT,
        related_name="applications",
        # PROTECT: a supplier's application history is a record of their
        # activity, and no endpoint exposes supplier deletion anyway.
    )

    proposed_rate = PositiveMoneyField()

    status = models.CharField(
        max_length=16,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            positive_value_constraint(
                field="proposed_rate",
                name="application_proposed_rate_positive",
            ),
            # Business rule 2, resolved as a *partial* unique index.
            #
            # Rule 2 allows reapplying after withdrawal or rejection; rule 6
            # makes those states terminal. The only way both hold is for a
            # reapplication to be a new row, leaving the terminal one untouched
            # as history. A plain unique(gig, supplier) would therefore break
            # rule 2 permanently, and no constraint at all would allow two
            # simultaneous pending bids.
            #
            # Conditioning uniqueness on status='pending' expresses exactly the
            # rule: at most one live bid per supplier per gig, unlimited
            # history. Supported by SQLite (3.8+) and PostgreSQL alike.
            models.UniqueConstraint(
                fields=["gig", "supplier"],
                condition=models.Q(status=ApplicationStatus.PENDING),
                name="unique_pending_application_per_gig_and_supplier",
            ),
        ]
        indexes = [
            # Serves both hot queries: rule 2's "does a pending bid exist for
            # this supplier on this gig" and rule 3's cascade, which selects
            # every pending application for one gig. A lone index on `status`
            # would be near-useless -- four values across every row is too low
            # a cardinality for the planner to bother with.
            models.Index(fields=["gig", "status"], name="application_gig_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.supplier_id} -> gig {self.gig_id} ({self.status})"

    @property
    def is_pending(self) -> bool:
        """Whether this application can still be acted on.

        The single question the workflow needs to ask. Accept, reject and
        withdraw all require a pending application (rules 3 and 6), so they all
        guard on this one property rather than each maintaining its own idea of
        which states are terminal.
        """
        return self.status == ApplicationStatus.PENDING
