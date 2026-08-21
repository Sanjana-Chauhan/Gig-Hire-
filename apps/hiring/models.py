"""Models for the hiring workflow."""

from django.db import models

from apps.common.constraints import positive_value_constraint
from apps.common.fields import PositiveMoneyField
from apps.common.models import TimeStampedModel
from apps.hiring.enums import ApplicationStatus, ContractStatus


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


class ContractQuerySet(models.QuerySet):
    """Query vocabulary for contracts.

    ``active()`` exists so that other apps can ask "is this gig under contract?"
    without importing anything from hiring. Django builds a reverse-relation
    manager from the related model's default manager class, so ``ContractStatus``
    knowledge stays entirely inside this app while remaining usable as:

        gig.contracts.active().exists()

    That matters for dependency direction. The gig lifecycle rules (rule 7's
    delete guard, rule 8's transition preconditions) live in the gigs app and
    need to know about contracts -- but hiring already imports gigs, so gigs
    importing hiring would create a cycle. Exposing the concept as queryset
    vocabulary lets gigs ask the question in hiring's own words while the
    dependency graph stays one-way.
    """

    def active(self) -> "ContractQuerySet":
        return self.filter(status=ContractStatus.ACTIVE)

    def for_supplier(self, supplier) -> "ContractQuerySet":
        return self.filter(supplier=supplier)

    def for_creator(self, creator) -> "ContractQuerySet":
        return self.filter(gig__creator=creator)


class Contract(TimeStampedModel):
    """A binding agreement created when a creator accepts an application.

    Created only by ``services.accept_application`` -- there is no endpoint that
    creates one directly. That is what makes business rule 3's invariants hold:
    a contract exists if and only if an application was accepted, in the same
    transaction that moved the gig to ``in_progress``.
    """

    gig = models.ForeignKey(
        "gigs.Gig",
        on_delete=models.PROTECT,
        related_name="contracts",
        # PROTECT, and this one is required rather than merely prudent.
        # Business rule 7 says deleting a gig "must not cascade-delete the
        # contract or its reviews". CASCADE would do exactly that, and the loss
        # would be a financial and reputation record -- unrecoverable. The
        # database refusing is the guarantee; the API's 409 (Step 8) is the
        # good error message on top of it.
    )
    supplier = models.ForeignKey(
        "accounts.Supplier",
        on_delete=models.PROTECT,
        related_name="contracts",
    )

    # Copied from the accepted application rather than referenced through it.
    # A rate that shifts after the fact is not an agreement, and the supplier's
    # later rate changes must not retroactively alter what was agreed. This is
    # the standard reason financial records denormalise: the value at the moment
    # of agreement is itself the fact being recorded.
    agreed_rate = PositiveMoneyField()

    status = models.CharField(
        max_length=16,
        choices=ContractStatus.choices,
        default=ContractStatus.ACTIVE,
    )

    objects = ContractQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            positive_value_constraint(
                field="agreed_rate",
                name="contract_agreed_rate_positive",
            ),
            # At most one *active* contract per gig. Nothing in the workflow
            # should produce a second -- accepting requires an open gig, and the
            # first accept closes that door -- so this constraint is a statement
            # that the workflow is correct, and it will fail loudly if a future
            # change breaks it. Same partial-index pattern as Application's
            # pending constraint, for the same reason: "at most one live X".
            models.UniqueConstraint(
                fields=["gig"],
                condition=models.Q(status=ContractStatus.ACTIVE),
                name="unique_active_contract_per_gig",
            ),
        ]
        indexes = [
            # Business rule 4 counts a supplier's active contracts on every
            # accept. This is the index that count uses.
            models.Index(
                fields=["supplier", "status"],
                name="contract_supplier_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"contract {self.pk}: supplier {self.supplier_id} on gig {self.gig_id}"

    @property
    def is_active(self) -> bool:
        """Whether this contract counts towards a supplier's workload cap."""
        return self.status == ContractStatus.ACTIVE
