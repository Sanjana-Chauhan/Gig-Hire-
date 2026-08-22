"""Query-parameter filtering for the hiring workflow."""

import django_filters

from apps.hiring.models import Contract


class ContractFilterSet(django_filters.FilterSet):
    """Filters contracts by supplier or creator, as the specification requires.

    Parameter names follow the spec (``supplier_id``, ``creator_id``) rather than
    django-filter's default of naming them after the model field.

    ``creator_id`` traverses a relation: a contract has no creator column, it has
    a gig which has a creator. ``gig__creator_id`` expresses that as a join
    rather than requiring a denormalised column.

    With **neither** parameter the endpoint returns every contract, paginated
    (ambiguity A14). That is the conventional REST reading, and it is worth
    stating plainly what it means in the absence of authentication (gap G3):
    every rate every supplier ever agreed to is readable by anyone. Faithful to
    the spec, and not something to ship -- see DECISIONS.md.

    NumberFilter, not ModelChoiceFilter: a non-numeric ``?supplier_id=abc`` is a
    malformed request and returns 400, while a numeric id that matches nothing
    returns an empty page with 200. Those are genuinely different answers --
    "your request is wrong" versus "this supplier has no contracts" -- and
    collapsing them is the bug class from Step 4.
    """

    supplier_id = django_filters.NumberFilter(
        field_name="supplier_id",
        help_text="Only contracts held by this supplier.",
    )
    creator_id = django_filters.NumberFilter(
        field_name="gig__creator_id",
        help_text="Only contracts on gigs posted by this creator.",
    )

    class Meta:
        model = Contract
        fields = ["supplier_id", "creator_id"]
