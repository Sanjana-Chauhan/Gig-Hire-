"""Business operations for the hiring workflow.

Every function here is one named business operation. They take and return domain
objects, raise domain exceptions, and know nothing about HTTP -- so the same rule
is enforced whether it is reached from the API, a management command, a
background job or a test.
"""

from django.db import IntegrityError, transaction

from apps.accounts.models import Supplier
from apps.common.exceptions import ConflictError
from apps.gigs.models import Gig
from apps.hiring.enums import ApplicationStatus
from apps.hiring.models import Application


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
