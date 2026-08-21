"""Shared pagination for list endpoints."""

from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.settings import api_settings


class DefaultPagination(PageNumberPagination):
    """Page-number pagination with a client-adjustable, server-capped size.

    Page-number paging is the right fit here: the collections are small, and
    the specification asks for a page number boundary to be testable, which
    needs stable, addressable pages.

    ``page_size`` and ``max_page_size`` are exposed as properties rather than
    plain class attributes. DRF evaluates its own class attributes once at
    import time, which would freeze the values and make them impossible to
    change from configuration afterwards. Reading them on each request means:

    * ``API_PAGE_SIZE`` / ``API_MAX_PAGE_SIZE`` genuinely control behaviour, and
    * a test can shrink the page size to three records to exercise pagination
      boundaries, instead of having to create twenty-one rows to cross one.

    The cap matters for a real deployment: without ``max_page_size`` a client
    could ask for ``?page_size=1000000`` and turn a list endpoint into a
    denial-of-service vector.
    """

    page_query_param = "page"
    page_size_query_param = "page_size"

    @property
    def page_size(self) -> int:
        return api_settings.PAGE_SIZE

    @property
    def max_page_size(self) -> int:
        return getattr(settings, "API_MAX_PAGE_SIZE", 100)
