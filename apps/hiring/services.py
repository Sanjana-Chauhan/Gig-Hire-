"""Business operations for the hiring workflow.

Every function here is one named business operation. They take and return domain
objects, raise domain exceptions, and know nothing about HTTP -- so the same rule
is enforced whether it is reached from the API, a management command, a
background job or a test.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Supplier
from apps.common.exceptions import ConflictError
from apps.gigs.enums import GigStatus
from apps.gigs.models import Gig
from apps.hiring.constants import MAX_ACTIVE_CONTRACTS_PER_SUPPLIER
from apps.hiring.enums import ApplicationStatus, ContractStatus
from apps.hiring.models import Application, Contract


def apply_to_gig(*, gig: Gig, supplier: Supplier, proposed_rate) -> Application:
    """Submit an application from ``supplier`` to ``gig``.

    Enforces business rule 1 (the gig must be open) and business rule 2 (no
    second *pending* application from the same supplier, but reapplying after
    withdrawal or rejection is allowed).

    Note what is deliberately *not* checked here: the supplier's
    ``availability_status``. Business rule 5 states that availability is
    evaluated at accept-time, not apply-time -- an ``inactive`` supplier may
    still apply, and a supplier who was ``available`` when applying can be
    blocked later. Adding the obvious-looking check here would break rule 5 in
    the direction nobody tests: it would silently prevent a case the rule
    explicitly permits.

    Keyword-only arguments throughout: ``apply_to_gig(gig, supplier, rate)`` has
    two interchangeable-looking positional objects, and transposing them is the
    kind of bug that type checkers catch and reviewers do not.
    """
    if not gig.is_open:
        # 409 rather than 400: the request is perfectly well-formed and would
        # have succeeded while the gig was open. The problem is timing.
        raise ConflictError(
            f"Applications are only accepted while a gig is open; "
            f"this gig is {gig.status}.",
            code="gig_not_open",
        )

    if _has_pending_application(gig=gig, supplier=supplier):
        raise ConflictError(
            "This supplier already has a pending application for this gig.",
            code="duplicate_pending_application",
        )

    # The check above exists to produce a good error message; the constraint
    # below is what makes the rule true. Two concurrent requests can both pass
    # the check -- there is a window between reading and writing -- and only the
    # database can settle it.
    #
    # The inner atomic() is load-bearing, not decoration: an IntegrityError
    # poisons the surrounding transaction, so catching one without a savepoint
    # to roll back to leaves the connection unusable for any further query.
    # atomic() creates that savepoint.
    try:
        with transaction.atomic():
            return Application.objects.create(
                gig=gig,
                supplier=supplier,
                proposed_rate=proposed_rate,
                status=ApplicationStatus.PENDING,
            )
    except IntegrityError as exc:
        raise ConflictError(
            "This supplier already has a pending application for this gig.",
            code="duplicate_pending_application",
        ) from exc


def _has_pending_application(*, gig: Gig, supplier: Supplier) -> bool:
    """Whether this supplier currently has a live bid on this gig."""
    return Application.objects.filter(
        gig=gig,
        supplier=supplier,
        status=ApplicationStatus.PENDING,
    ).exists()


def accept_application(*, application: Application) -> Contract:
    """Accept an application, creating a contract (business rule 3).

    Everything below happens in one transaction, or none of it does:

    1. a ``Contract`` is created with the application's proposed rate,
    2. the application becomes ``accepted``,
    3. every *other* pending application on that gig becomes ``rejected``,
    4. the gig moves to ``in_progress``.

    Guards, in order: the application must still be pending (rule 6), the gig
    must still be open (ambiguity A10), the supplier must not be ``inactive``
    (rule 5), and the supplier must be under the workload cap (rule 4).

    Structure worth noting: **every guard runs before every write.** The
    transaction already guarantees all-or-nothing, so this ordering is not what
    makes the operation atomic -- but it makes the atomicity *legible*. A reader
    can see that no row is touched until every rule has passed, without having
    to trust the rollback. Interleaving checks and writes would be equally
    correct and much harder to verify by eye.
    """
    with transaction.atomic():
        # Re-read inside the transaction rather than trusting the instance the
        # caller handed us. That object was loaded before the transaction began,
        # so its status may already be stale -- another request may have
        # accepted or withdrawn it in the meantime. Validating a stale copy and
        # writing based on it is the classic lost-update bug.
        #
        # select_for_update() asks the database to lock these rows until the
        # transaction ends. See the note on SQLite in _assert_under_workload_cap.
        application = (
            Application.objects.select_for_update()
            .select_related("gig", "supplier")
            .get(pk=application.pk)
        )
        gig = application.gig

        _assert_application_is_pending(application)
        _assert_gig_accepts_hiring(gig)
        _assert_supplier_is_hireable(application.supplier)
        _assert_under_workload_cap(supplier=application.supplier)

        contract = Contract.objects.create(
            gig=gig,
            supplier=application.supplier,
            # Rule 3: the agreed rate is the rate that was proposed. Copied, not
            # referenced -- see the note on Contract.agreed_rate.
            agreed_rate=application.proposed_rate,
            status=ContractStatus.ACTIVE,
        )

        application.status = ApplicationStatus.ACCEPTED
        application.save(update_fields=["status", "updated_at"])

        _reject_competing_applications(gig=gig, accepted=application)

        gig.status = GigStatus.IN_PROGRESS
        gig.save(update_fields=["status", "updated_at"])

    return contract


def _reject_competing_applications(*, gig: Gig, accepted: Application) -> int:
    """Reject every other pending application on ``gig``. Returns the count.

    A single UPDATE rather than a loop of ``save()`` calls. With fifty
    applicants a loop is fifty queries and fifty round trips, all while holding
    locks inside a transaction -- the difference is not stylistic.

    The cost of ``.update()``, stated plainly: it bypasses ``save()``, model
    signals and ``full_clean()``. That is acceptable here because the only
    change is a status field being set to a known-valid enum member. It would
    not be acceptable for anything with side effects, and ``updated_at`` has to
    be set by hand precisely because of it -- ``auto_now`` is implemented in
    ``Model.save()``, so a queryset UPDATE silently leaves the timestamp stale.
    That is a genuinely easy bug to ship.

    Scope is limited to *this* gig. The accepted supplier's pending applications
    on other gigs are untouched: rule 3 says "every other pending application
    for that gig", and a supplier may legitimately still be in the running
    elsewhere (ambiguity A2).
    """
    return (
        Application.objects.filter(gig=gig, status=ApplicationStatus.PENDING)
        .exclude(pk=accepted.pk)
        .update(status=ApplicationStatus.REJECTED, updated_at=timezone.now())
    )


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
# Each rule is one named function. That is not ceremony: it means the rule has a
# name that matches how the business talks about it, the accept flow reads as a
# list of rules rather than a wall of conditionals, and reject/withdraw (Step 7)
# reuse the same guards instead of restating them slightly differently.


def _assert_application_is_pending(application: Application) -> None:
    """Business rule 6: accepted, rejected and withdrawn are terminal."""
    if not application.is_pending:
        raise ConflictError(
            f"This application is {application.status} and can no longer be "
            f"modified.",
            code="application_not_pending",
        )


def _assert_gig_accepts_hiring(gig: Gig) -> None:
    """Ambiguity A10: accepting requires an open gig.

    The specification guards *applying* to a non-open gig (rule 1) but says
    nothing about *accepting* on one. Without this, accepting an application on a
    cancelled gig would resurrect it into ``in_progress``, and a second accept
    on an already-in-progress gig would create a second contract.
    """
    if not gig.is_open:
        raise ConflictError(
            f"Applications can only be accepted while a gig is open; "
            f"this gig is {gig.status}.",
            code="gig_not_open",
        )


def _assert_supplier_is_hireable(supplier: Supplier) -> None:
    """Business rule 5: availability is checked at accept-time.

    Deliberately permissive about ``busy``: the rule names only ``inactive``.
    A busy supplier can be hired. That reads like a product error and is flagged
    as such (ambiguity A3), but it is what the specification says, and quietly
    "fixing" it here would make the implementation disagree with the document
    it is being measured against.
    """
    if not supplier.is_hireable:
        raise ConflictError(
            "This supplier is inactive and cannot be given new work.",
            code="supplier_not_hireable",
        )


def _assert_under_workload_cap(*, supplier: Supplier) -> None:
    """Business rule 4: at most MAX_ACTIVE_CONTRACTS_PER_SUPPLIER active contracts.

    Counting rows and then inserting has an inherent race: two concurrent
    accepts can both read 3 and both insert, leaving the supplier with 4. The
    read must therefore be protected by a lock held until the transaction ends.

    **The honest limitation.** ``select_for_update()`` in ``accept_application``
    is correct on PostgreSQL and MySQL, and is a documented **no-op on SQLite**
    -- Django acquires no row lock at all. On this project's database the cap is
    protected only by SQLite serialising writes database-wide, which is a
    side effect of its locking model rather than a guarantee we asked for.

    This rule also cannot be expressed as a database constraint: "at most three
    rows matching a condition" is not something CHECK or UNIQUE can say. That is
    precisely why rule 4 is the highest-risk rule in the specification -- it is
    the only one with no database-level backstop, so a bug in this function
    corrupts data with nothing to catch it.

    Current learning implementation -> production implementation:
    ``SQLite + a select_for_update() that no-ops`` ->
    ``PostgreSQL row locks, or a denormalised active_contract_count column with
    a CHECK constraint, or SERIALIZABLE isolation with retry``.
    """
    active_contracts = Contract.objects.filter(
        supplier=supplier,
        status=ContractStatus.ACTIVE,
    ).count()

    if active_contracts >= MAX_ACTIVE_CONTRACTS_PER_SUPPLIER:
        raise ConflictError(
            f"This supplier already holds {active_contracts} active contracts, "
            f"the maximum is {MAX_ACTIVE_CONTRACTS_PER_SUPPLIER}.",
            code="workload_cap_reached",
        )
