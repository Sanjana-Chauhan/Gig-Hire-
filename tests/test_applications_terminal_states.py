"""Once a bid is finished, nothing more can be done to it.

Covers cases AW-01 to AW-31 in TEST_CASES.md, and business rule 6.

The whole module is built around one sweep: four starting states multiplied by
three actions is twelve combinations, of which nine must be refused. Enumerating
the cross product rather than a hand-picked list means the table cannot have a
hole -- and the cell people forget is "withdraw an already-accepted bid", which
the specification calls out precisely because implementations get it wrong.
"""

import itertools

import pytest

from tests import endpoints
from tests.assertions import (
    assert_conflict,
    assert_not_found,
    assert_ok,
    assert_page,
)
from tests.factories import ApplicationFactory, GigFactory

pytestmark = [pytest.mark.django_db, pytest.mark.rule("BR-06")]

STARTING_STATES = ["pending", "accepted", "rejected", "withdrawn"]
ACTIONS = ["accept", "reject", "withdraw"]

#: What each action does to a bid that is still pending.
SUCCESSFUL_OUTCOME = {"accept": 201, "reject": 200, "withdraw": 200}


@pytest.mark.case("AW-01,AW-02")
@pytest.mark.parametrize(
    "action, resulting_status",
    [("reject", "rejected"), ("withdraw", "withdrawn")],
)
def test_a_pending_bid_can_be_rejected_or_withdrawn(
    api, application, action, resulting_status
):
    body = assert_ok(api.post(endpoints.APPLICATION_ACTIONS[action](application.id)))

    assert body["status"] == resulting_status


@pytest.mark.case("AW-01 to AW-12")
@pytest.mark.parametrize(
    "start, action", list(itertools.product(STARTING_STATES, ACTIONS))
)
def test_every_combination_of_starting_state_and_action(
    api, creator, supplier, start, action
):
    """All twelve cells. Nine refusals, three successes.

    Bids in a finished state are built with the factory: reaching "accepted"
    through the API would also move the gig and create an agreement, which would
    make this test about the workflow rather than about the terminal-state rule.
    What the workflow does is covered in test_hiring_accept.py.
    """
    gig = GigFactory(creator=creator)
    application = ApplicationFactory(gig=gig, supplier=supplier, status=start)

    response = api.post(endpoints.APPLICATION_ACTIONS[action](application.id))

    if start == "pending":
        assert response.status_code == SUCCESSFUL_OUTCOME[action]
    else:
        assert_conflict(response, "application_not_pending")
        application.refresh_from_db()
        assert application.status == start


@pytest.mark.case("AW-13,AW-14,AW-15,AW-16")
@pytest.mark.parametrize(
    "first, second", list(itertools.product(["reject", "withdraw"], repeat=2))
)
def test_a_second_action_on_a_finished_bid_is_refused_not_silently_accepted(
    api, application, first, second
):
    """Never report success for something that did not happen.

    Returning 200 would be tempting -- the bid is already in a finished state, so
    "nothing to do" could look like success. But if the bid had been *accepted*,
    a 200 on "reject" would tell the creator they had cancelled a hire that is
    in fact still live. The caller's understanding of the world would silently
    stop matching reality.
    """
    assert_ok(api.post(endpoints.APPLICATION_ACTIONS[first](application.id)))

    response = api.post(endpoints.APPLICATION_ACTIONS[second](application.id))

    assert_conflict(response, "application_not_pending")


@pytest.mark.case("AW-17,AW-18,AW-19,AW-20,AW-21")
@pytest.mark.parametrize("action", ["reject", "withdraw"])
def test_finishing_one_bid_leaves_everything_else_alone(
    api, gig_with_three_bids, action
):
    """Rule 3's cascade belongs to *accepting* only.

    Implementing rejection by reusing the cascade helper would silently reject
    every bid on the gig -- a plausible mistake that looks like code reuse.
    """
    gig, bids = gig_with_three_bids

    assert_ok(api.post(endpoints.APPLICATION_ACTIONS[action](bids[0]["id"])))

    listing = assert_page(api.get(endpoints.applications_for(gig.id)), count=3)
    statuses = {item["id"]: item["status"] for item in listing["results"]}
    assert statuses[bids[1]["id"]] == "pending"
    assert statuses[bids[2]["id"]] == "pending"

    gig.refresh_from_db()
    assert gig.status == "open"

    contracts = assert_ok(api.get(f"{endpoints.CONTRACTS}?creator_id={gig.creator_id}"))
    assert contracts["count"] == 0


@pytest.mark.case("AW-22,AW-23,AW-24,AW-25")
@pytest.mark.parametrize("gig_status", ["in_progress", "completed", "cancelled"])
@pytest.mark.parametrize("action", ["reject", "withdraw"])
def test_closing_out_a_bid_never_depends_on_the_gig_status(
    api, creator, supplier, gig_status, action
):
    """Tidying up is always allowed.

    A bid that could not be closed because its gig had moved on would sit
    pending for ever, showing in listings as a live offer for work that no
    longer exists.
    """
    gig = GigFactory(creator=creator, status=gig_status)
    application = ApplicationFactory(gig=gig, supplier=supplier)

    assert_ok(api.post(endpoints.APPLICATION_ACTIONS[action](application.id)))


@pytest.mark.case("AW-26,AW-27,AW-28")
@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("application_id", [999999, "abc"], ids=["unknown", "not-a-number"])
def test_acting_on_a_bid_that_does_not_exist_reports_not_found(
    api, action, application_id
):
    assert_not_found(api.post(endpoints.APPLICATION_ACTIONS[action](application_id)))


@pytest.mark.case("AW-29,AW-30")
@pytest.mark.parametrize("body", [None, {"reason": "changed my mind"}], ids=["empty", "extra-values"])
def test_these_actions_need_no_request_body(api, application, body):
    """The address identifies everything needed; extra values are ignored."""
    response = api.post(endpoints.withdraw(application.id), body, format="json")

    assert_ok(response)


@pytest.mark.case("AW-31")
@pytest.mark.parametrize("action", ACTIONS)
def test_these_actions_are_available_only_by_posting(api, application, action):
    url = endpoints.APPLICATION_ACTIONS[action](application.id)

    assert api.get(url).status_code == 405
