"""Query-parameter filtering for gig listings."""

import django_filters

from apps.common.text import canonicalize_tag
from apps.gigs.enums import GigStatus
from apps.gigs.models import Gig


class GigFilterSet(django_filters.FilterSet):
    """Filters the gig list by category and status, as the specification requires.

    Why a FilterSet rather than reading ``request.query_params`` in
    ``get_queryset``:

    * ``status`` is declared as a ChoiceFilter, so ``?status=nonsense`` returns a
      400 naming the valid choices. Hand-rolled filtering would filter on an
      impossible value and return an empty list with a 200 -- indistinguishable
      from "no matches", which is the kind of bug that survives for years.
    * The filters are declarative, so adding one later is one line rather than
      another branch in an ever-growing ``get_queryset``.
    """

    status = django_filters.ChoiceFilter(
        choices=GigStatus.choices,
        help_text="Exact match on gig status.",
    )
    category = django_filters.CharFilter(
        method="filter_category",
        help_text="Exact match on category, case-insensitive.",
    )

    class Meta:
        model = Gig
        fields = ["status", "category"]

    def filter_category(self, queryset, name, value):
        """Match the stored canonical form of the category.

        Categories are canonicalised on write, so the query value must be
        canonicalised too. Without this, a gig posted as ``Editing`` (stored
        ``editing``) would not be found by ``?category=Editing`` -- the filter
        would appear to work while returning nothing, which is worse than an
        error because nothing signals that it went wrong.
        """
        return queryset.filter(**{name: canonicalize_tag(value)})
