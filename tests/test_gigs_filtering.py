"""Filtering and paging the gig list.

Covers cases GF-01 to GF-38 in TEST_CASES.md.

The distinction this module is built around: a filter value that is *invalid* and
a filter value that simply *matches nothing* are different answers. Collapsing
them into one empty list hides the caller's mistake, and that is a bug class
which survives for years.
"""

import pytest

from tests import endpoints
from tests.assertions import assert_field_error, assert_not_found, assert_page, ids_in
from tests.factories import GigFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def six_gigs(creator):
    """Six gigs spanning three categories and two statuses."""
    return {
        "g1": GigFactory(creator=creator, category="editing", status="open"),
        "g2": GigFactory(creator=creator, category="editing", status="open"),
        "g3": GigFactory(creator=creator, category="design", status="open"),
        "g4": GigFactory(creator=creator, category="editing", status="cancelled"),
        "g5": GigFactory(creator=creator, category="design", status="cancelled"),
        "g6": GigFactory(creator=creator, category="writing", status="open"),
    }


@pytest.mark.case("GF-01")
def test_listing_gigs_with_no_filter_returns_all_of_them(api, six_gigs):
    assert_page(api.get(endpoints.GIGS), count=6, returned=6)


@pytest.mark.case("GF-02,GF-03,GF-04")
@pytest.mark.parametrize(
    "status, expected",
    [("open", 4), ("cancelled", 2), ("in_progress", 0), ("completed", 0)],
)
def test_gigs_can_be_filtered_by_status(api, six_gigs, status, expected):
    assert_page(api.get(f"{endpoints.GIGS}?status={status}"), count=expected)


@pytest.mark.case("GF-05,GF-06,GF-07,GF-08")
@pytest.mark.parametrize(
    "category, expected",
    [("editing", 3), ("design", 2), ("writing", 1), ("photography", 0)],
)
def test_gigs_can_be_filtered_by_category(api, six_gigs, category, expected):
    assert_page(api.get(f"{endpoints.GIGS}?category={category}"), count=expected)


@pytest.mark.case("GF-09,GF-10")
@pytest.mark.parametrize(
    "value", ["EDITING", "Editing", "  editing  "], ids=["upper", "mixed", "padded"]
)
def test_a_category_filter_ignores_capitals_and_spaces(api, six_gigs, value):
    """Categories are stored tidied, so the filter value is tidied too.

    Without this, a gig posted as "Editing" would not be found by
    ``?category=Editing`` -- the filter would appear to work while silently
    returning nothing, which is worse than an error.
    """
    assert_page(api.get(f"{endpoints.GIGS}?category={value}"), count=3)


@pytest.mark.case("GF-11,GF-12,GF-13,GF-14")
@pytest.mark.parametrize(
    "status, category, expected",
    [
        pytest.param("open", "editing", 2, id="both-match"),
        pytest.param("cancelled", "design", 1, id="one-match"),
        pytest.param("cancelled", "writing", 0, id="no-overlap"),
        pytest.param("completed", "editing", 0, id="impossible-combination"),
    ],
)
def test_both_filters_must_be_satisfied_together(
    api, six_gigs, status, category, expected
):
    response = api.get(f"{endpoints.GIGS}?status={status}&category={category}")

    assert_page(response, count=expected)


@pytest.mark.case("GF-15,GF-16")
@pytest.mark.parametrize(
    "query", ["?status=nonsense", "?status=nonsense&category=editing"]
)
def test_an_invalid_status_filter_is_refused_rather_than_matching_nothing(
    api, six_gigs, query
):
    """The caller has made a mistake and needs to hear about it.

    "photography" is a valid category that happens to match nothing -- answer
    zero. "nonsense" is not a status at all -- answer that the request is wrong.
    Returning an empty list for both would make the two indistinguishable.
    """
    assert_field_error(api.get(f"{endpoints.GIGS}{query}"), "status")


@pytest.mark.case("GF-17,GF-18,GF-19")
@pytest.mark.parametrize(
    "query",
    ["?status=", "?category=", "?colour=red"],
    ids=["empty-status", "empty-category", "unknown-filter"],
)
def test_an_empty_or_unknown_filter_is_treated_as_no_filter(api, six_gigs, query):
    assert_page(api.get(f"{endpoints.GIGS}{query}"), count=6)


@pytest.mark.case("GF-20,GF-21,GF-22,GF-23")
def test_paging_walks_through_every_gig_exactly_once(api, six_gigs):
    """Three pages of two, with no gig appearing twice or being skipped.

    Ordering is newest first with the id as a tiebreak, so the order is total --
    two gigs created in the same instant cannot swap between requests, which is
    what would make a paging test flaky.
    """
    seen = []
    for page in [1, 2, 3]:
        body = assert_page(
            api.get(f"{endpoints.GIGS}?page_size=2&page={page}"), count=6, returned=2
        )
        seen.extend(item["id"] for item in body["results"])

    assert len(set(seen)) == 6


@pytest.mark.case("GF-21")
def test_the_total_count_is_the_whole_collection_not_the_page(api, six_gigs):
    """A common and easily-missed mistake: count is not len(results)."""
    body = assert_page(api.get(f"{endpoints.GIGS}?page_size=2"), count=6, returned=2)

    assert body["next"] is not None
    assert body["previous"] is None


@pytest.mark.case("GF-24,GF-25,GF-26,GF-27,GF-28")
@pytest.mark.parametrize(
    "query",
    [
        pytest.param("?page_size=2&page=4", id="beyond-the-last-page"),
        pytest.param("?page=2", id="beyond-the-last-with-default-size"),
        pytest.param("?page=0", id="page-zero"),
        pytest.param("?page=-1", id="negative-page"),
        pytest.param("?page=abc", id="page-not-a-number"),
    ],
)
def test_a_page_that_does_not_exist_reports_not_found(api, six_gigs, query):
    """404 for all five, including the malformed ones.

    ``?page=abc`` is arguably a malformed request, and 400 would be more
    accurate. This is the framework's standard behaviour, and overriding a
    convention to win an argument about a status code is not worth surprising
    every client that already knows it. Asserted deliberately, so the behaviour
    is documented rather than discovered by accident later.
    """
    assert_not_found(api.get(f"{endpoints.GIGS}{query}"))


@pytest.mark.case("GF-29,GF-30,GF-31,GF-32")
@pytest.mark.parametrize(
    "page_size",
    [
        pytest.param("100", id="the-maximum"),
        pytest.param("99999", id="above-the-maximum-is-capped"),
        pytest.param("0", id="zero-falls-back-to-the-default"),
        pytest.param("abc", id="not-a-number-falls-back-to-the-default"),
    ],
)
def test_an_out_of_range_page_size_is_handled_without_an_error(api, six_gigs, page_size):
    """A cap, not a refusal.

    ``?page_size=99999`` is capped rather than rejected, because an unbounded
    client-controlled limit is how a list endpoint becomes a way to overload the
    service.
    """
    assert_page(api.get(f"{endpoints.GIGS}?page_size={page_size}"), count=6, returned=6)


@pytest.mark.case("GF-33")
def test_an_empty_collection_pages_cleanly(api):
    body = assert_page(api.get(endpoints.GIGS), count=0, returned=0)

    assert body["next"] is None
    assert body["previous"] is None


@pytest.mark.case("GF-34,GF-35,GF-36,GF-37")
def test_a_filter_and_paging_work_together(api, six_gigs):
    """The count reflects the filter, not the whole collection."""
    first = api.get(f"{endpoints.GIGS}?status=open&page_size=2")
    second = api.get(f"{endpoints.GIGS}?status=open&page_size=2&page=2")

    assert_page(first, count=4, returned=2)
    assert_page(second, count=4, returned=2)
    assert not set(ids_in(first)) & set(ids_in(second))
    assert_not_found(api.get(f"{endpoints.GIGS}?status=open&page_size=2&page=3"))


@pytest.mark.case("GF-38")
def test_asking_for_the_same_page_twice_gives_the_same_answer(api, six_gigs):
    first = ids_in(api.get(f"{endpoints.GIGS}?page_size=3"))
    second = ids_in(api.get(f"{endpoints.GIGS}?page_size=3"))

    assert first == second
