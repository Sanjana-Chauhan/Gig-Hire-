"""The gig lifecycle: which status transitions are legal, and when.

Business rule 8 says that once a gig leaves ``open``, only status transitions are
allowed -- and gives two examples out of roughly twelve possible transitions.
The rest is interpretation I7 in DECISIONS.md, resolved here as an explicit table
rather than left to whatever the code happens to permit.

Why a table instead of scattered ``if`` statements: the set of legal moves is the
single most important thing to be able to *read* about a state machine. A table
can be reviewed by someone who does not read Python, compared against the spec
line by line, and turned directly into a parameterised test over every
from/to pair -- including the illegal ones, which is where the bugs are.
"""

from apps.common.exceptions import ConflictError
from apps.gigs.enums import GigStatus

# Fields frozen once a gig leaves `open` (business rule 8).
#
# Only these two are named by the rule. `title` and `description` therefore stay
# editable on an in-progress gig -- a literal reading, and arguably a sensible
# one (fixing a typo in a brief harms nobody), but it is an interpretation and
# is recorded as A7 in DECISIONS.md.
IMMUTABLE_FIELDS_ONCE_NOT_OPEN = frozenset({"budget", "category"})

# The transition table. Absent pairs are illegal.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    # open -> in_progress is deliberately absent: that transition belongs to
    # accepting an application, which also creates the Contract. Allowing it by
    # PATCH would produce an in-progress gig with no contract.
    # open -> completed is absent: nothing was ever contracted, so there is no
    # work to have completed.
    GigStatus.OPEN: frozenset({GigStatus.CANCELLED}),
    # Both of these are additionally gated on there being no active contract --
    # see assert_transition_allowed. A gig must not be closed or abandoned out
    # from under a live agreement.
    GigStatus.IN_PROGRESS: frozenset({GigStatus.COMPLETED, GigStatus.CANCELLED}),
    # Terminal. A completed gig cannot reopen; a cancelled one cannot either --
    # its applications were already resolved, and reopening would strand them.
    # A creator who changes their mind posts a new gig, which keeps history
    # honest.
    GigStatus.COMPLETED: frozenset(),
    GigStatus.CANCELLED: frozenset(),
}


def assert_transition_allowed(*, gig, target_status: str) -> None:
    """Raise unless ``gig`` may move to ``target_status``.

    Two levels of check, deliberately separate:

    1. Is the transition in the table at all? A structural question about the
       lifecycle.
    2. Are its preconditions satisfied? A question about this gig's contracts.

    Keeping them apart means the error message tells the caller *which* kind of
    problem they have -- "you cannot go from completed to open" is a different
    conversation from "finish the contract first".
    """
    current = gig.status

    if target_status == current:
        # A no-op PATCH is not an error. Nothing changes, nothing is claimed to
        # have changed, and rejecting it would make idempotent clients fail for
        # no reason.
        return

    if target_status not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise ConflictError(
            f"A gig cannot move from {current} to {target_status}.",
            code="invalid_status_transition",
        )

    if target_status in {GigStatus.COMPLETED, GigStatus.CANCELLED}:
        if gig.has_active_contract:
            raise ConflictError(
                f"This gig has an active contract; complete it before marking "
                f"the gig {target_status}.",
                code="gig_has_active_contract",
            )


def assert_fields_mutable(*, gig, incoming_fields) -> None:
    """Raise if a frozen field is being changed on a gig that has left ``open``.

    409 rather than 400: while the gig was open these fields were perfectly
    editable, so the request is not malformed -- it is late. That distinction is
    what tells a client whether to fix their payload or accept that the world
    moved on.
    """
    if gig.status == GigStatus.OPEN:
        return

    frozen = IMMUTABLE_FIELDS_ONCE_NOT_OPEN & set(incoming_fields)
    if frozen:
        raise ConflictError(
            f"{', '.join(sorted(frozen))} cannot be changed once a gig leaves "
            f"the open state; this gig is {gig.status}.",
            code="gig_fields_immutable",
        )


def assert_gig_deletable(*, gig) -> None:
    """Raise unless ``gig`` may be deleted (business rule 7).

    Two distinct refusals, and the second is a documented deviation:

    * An **active** contract blocks deletion. This is rule 7 verbatim.
    * **Any** contract blocks deletion. Rule 7 mentions only active contracts,
      so a gig whose contract has been completed reads as deletable -- but that
      would destroy the contract and its reviews, which is the financial and
      reputation record of work actually done. Rule 7's own words say deletion
      "must not cascade-delete the contract or its reviews", and Contract.gig is
      PROTECT precisely so it cannot. This check turns the database's refusal
      into a clean 409 with an explanation instead of a generic integrity error.

    Recorded as deviation S1 in DECISIONS.md, with the recommendation that gigs
    be soft-deleted rather than removed. Applications are unaffected -- they
    cascade, because a bid carries no money and no reputation (interpretation
    I14).
    """
    if gig.has_active_contract:
        raise ConflictError(
            "This gig has an active contract and cannot be deleted.",
            code="gig_has_active_contract",
        )

    if gig.has_contract_history:
        raise ConflictError(
            "This gig has contract history and cannot be deleted; deleting it "
            "would destroy the contract and any reviews attached to it.",
            code="gig_has_contract_history",
        )
