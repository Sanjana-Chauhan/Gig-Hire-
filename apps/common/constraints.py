"""Helpers for declaring database-level constraints consistently."""

from django.db import models


def positive_value_constraint(*, field: str, name: str) -> models.CheckConstraint:
    """A CheckConstraint asserting ``field > 0`` at the database level.

    This is the third layer of defence, beneath the serializer and the service.
    A validator only runs when something calls ``full_clean()``; the database
    constraint holds for every write, including ``objects.create()``,
    ``bulk_create()``, ``update()`` and raw SQL. It is the only check a buggy
    application cannot bypass.

    Constraint names are global to the database, so callers pass an explicit
    name rather than having one generated -- a generated name would collide the
    moment two apps had a field with the same name.
    """
    return models.CheckConstraint(
        condition=models.Q(**{f"{field}__gt": 0}),
        name=name,
    )
