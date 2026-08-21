"""Abstract model bases shared across applications."""

from django.db import models


class TimeStampedModel(models.Model):
    """Adds automatic creation and modification timestamps.

    The specification only asks for ``created_at`` on Application, but every
    record in a hiring system benefits from knowing when it appeared and when
    it last changed: it is the difference between being able to reconstruct
    what happened and guessing. Defining it once as an abstract base keeps the
    two fields identical everywhere instead of re-declared per model.

    ``abstract = True`` means Django creates no table for this class; the
    columns are added to each concrete subclass instead.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
