"""Domain exceptions and the single DRF exception handler that renders them.

Why this module exists
----------------------
The specification repeatedly demands that a rule violation produce "a clean
400/409, not a 500", and that database integrity errors never reach the client
raw. There are two ways to achieve that:

1. Wrap every view body in try/except and build a Response by hand.
2. Let the service layer raise exceptions that describe *what rule was
   broken*, and translate them to HTTP in exactly one place.

We do the second. The service layer should not know or care that it is being
called over HTTP: it raises ``ConflictError("this application is already
accepted")`` and the handler below decides that means 409. That keeps the rules
reusable from a management command, a background job or a unit test, and it
means the HTTP mapping cannot drift between endpoints.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """A business rule was violated.

    Subclasses carry their own HTTP status, so callers never pass status codes
    around by hand. ``code`` is a stable, machine-readable identifier: tests
    and API clients should assert on it rather than on the English message,
    which is free to be reworded without breaking anything.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request could not be completed."
    default_code = "domain_error"

    def __init__(self, detail: str | None = None, code: str | None = None) -> None:
        self.detail = detail or self.default_detail
        self.code = code or self.default_code
        super().__init__(self.detail)


class InvalidRequest(DomainError):
    """The request is well-formed but semantically unacceptable (400)."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The request is not valid."
    default_code = "invalid_request"


class ConflictError(DomainError):
    """The request conflicts with the current state of the resource (409).

    Used for state-machine violations: withdrawing an already-accepted
    application, deleting a gig that is under contract, reviewing twice.
    409 rather than 400 because the request would have been perfectly valid at
    some other point in the resource's life. The problem is *when* it was made,
    not *what* it said.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state."
    default_code = "conflict"


def api_exception_handler(exc, context):
    """Project-wide DRF exception handler.

    Registered as ``REST_FRAMEWORK["EXCEPTION_HANDLER"]``. It runs for every
    exception raised inside a DRF view, and converts three categories that DRF
    would otherwise turn into a 500:

    * ``DomainError`` -- our own rule violations, mapped to their own status.
    * ``DjangoValidationError`` -- raised by ``Model.full_clean()`` and by
      model field validators. DRF only understands its own ValidationError, so
      without this a model-level check would surface as a 500.
    * ``IntegrityError`` -- a database constraint fired. This is the safety net
      beneath the validation layers: it should be unreachable, so we log it at
      ERROR (never silently swallowed) and still answer with a 409 rather than
      leaking a raw database message to the client.

    Anything else keeps DRF's standard behaviour.
    """
    if isinstance(exc, DomainError):
        return Response(
            {"detail": exc.detail, "code": exc.code},
            status=exc.status_code,
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            {"detail": _flatten_django_validation_error(exc), "code": "invalid"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        # Reaching here means a validation layer has a gap: the database caught
        # something the API should have. Loud in the logs, clean on the wire.
        view = context.get("view") if context else None
        logger.error(
            "Database integrity error surfaced to the API layer in %s: %s",
            type(view).__name__ if view else "unknown view",
            exc,
            exc_info=True,
        )
        return Response(
            {
                "detail": "The request conflicts with existing data.",
                "code": "integrity_error",
            },
            status=status.HTTP_409_CONFLICT,
        )

    return drf_exception_handler(exc, context)


def _flatten_django_validation_error(exc: DjangoValidationError):
    """Turn a Django ValidationError into a JSON-serialisable payload.

    Django's version carries either ``message_dict`` (field-keyed) or a flat
    ``messages`` list. Both shapes are preserved rather than collapsed into a
    string, so a client can still tell which field was at fault.
    """
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages
