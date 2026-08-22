"""Every address the API exposes, in one place.

No test builds a URL by hand. Two reasons:

* A path that changes changes here once, rather than in eighty tests.
* ``apply_to(gig_id)`` reads as intent where ``f"/api/gigs/{gig_id}/apply/"``
  reads as plumbing. A test should describe behaviour, not string formatting.

Written as literal paths rather than Django's ``reverse()`` on purpose. These are
the addresses the specification promises to callers, so writing them out means a
renamed route breaks a test -- which is exactly what should happen, because it
would break every client too. ``reverse()`` would silently follow the rename and
hide the fact that a published contract had changed.
"""

CREATORS = "/api/creators/"
SUPPLIERS = "/api/suppliers/"
GIGS = "/api/gigs/"
CONTRACTS = "/api/contracts/"


def creator(creator_id) -> str:
    return f"{CREATORS}{creator_id}/"


def supplier(supplier_id) -> str:
    return f"{SUPPLIERS}{supplier_id}/"


def gig(gig_id) -> str:
    return f"{GIGS}{gig_id}/"


def apply_to(gig_id) -> str:
    return f"{GIGS}{gig_id}/apply/"


def applications_for(gig_id) -> str:
    return f"{GIGS}{gig_id}/applications/"


def accept(application_id) -> str:
    return f"/api/applications/{application_id}/accept/"


def reject(application_id) -> str:
    return f"/api/applications/{application_id}/reject/"


def withdraw(application_id) -> str:
    return f"/api/applications/{application_id}/withdraw/"


def complete(contract_id) -> str:
    return f"{CONTRACTS}{contract_id}/complete/"


def reviews_for(contract_id) -> str:
    return f"{CONTRACTS}{contract_id}/reviews/"


#: Maps an action name to its URL builder, for tests that sweep every action
#: against every starting state.
APPLICATION_ACTIONS = {
    "accept": accept,
    "reject": reject,
    "withdraw": withdraw,
}
