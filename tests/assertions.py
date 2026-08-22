"""Assertion helpers.

Each one exists to make a failure message say what went wrong rather than
"assert 409 == 400". A test that fails should tell you the rule it was checking,
not just two numbers.
"""

from rest_framework import status


def assert_created(response):
    """The request created something."""
    assert response.status_code == status.HTTP_201_CREATED, (
        f"expected 201 Created, got {response.status_code}: {response.data}"
    )
    return response.data


def assert_ok(response):
    """The request succeeded and returned data."""
    assert response.status_code == status.HTTP_200_OK, (
        f"expected 200 OK, got {response.status_code}: {response.data}"
    )
    return response.data


def assert_field_error(response, field: str, code: str | None = None):
    """The request was refused because one field was wrong.

    Asserts on the machine-readable ``code`` rather than the message text where
    one is given. Message wording is free to be improved; a test that pins the
    prose fails the moment someone rewords it, and a suite that produces false
    failures is a suite people learn to ignore.
    """
    assert response.status_code == status.HTTP_400_BAD_REQUEST, (
        f"expected 400 Bad Request, got {response.status_code}: {response.data}"
    )
    assert field in response.data, (
        f"expected an error on the '{field}' field, got: {dict(response.data)}"
    )
    if code is not None:
        actual = [getattr(detail, "code", None) for detail in response.data[field]]
        assert code in actual, (
            f"expected error code '{code}' on '{field}', got {actual}: "
            f"{response.data[field]}"
        )
    return response.data


def assert_conflict(response, code: str):
    """The request was well-formed but clashed with the current situation.

    ``code`` is the stable identifier -- ``gig_not_open``, ``workload_cap_reached``
    -- so these assertions survive rewording of the human-readable message.
    """
    assert response.status_code == status.HTTP_409_CONFLICT, (
        f"expected 409 Conflict with code '{code}', "
        f"got {response.status_code}: {response.data}"
    )
    assert response.data.get("code") == code, (
        f"expected code '{code}', got '{response.data.get('code')}': "
        f"{response.data.get('detail')}"
    )
    return response.data


def assert_not_found(response):
    """The thing named in the address does not exist."""
    assert response.status_code == status.HTTP_404_NOT_FOUND, (
        f"expected 404 Not Found, got {response.status_code}: {response.data}"
    )


def assert_method_not_allowed(response):
    """That action is not available on that address."""
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED, (
        f"expected 405 Method Not Allowed, got {response.status_code}: "
        f"{response.data}"
    )


def assert_page(response, *, count: int, returned: int | None = None):
    """A paginated list came back with the expected totals.

    ``count`` is the total number of matching records, which is not the same as
    the number on this page -- conflating the two is a common and easily-missed
    mistake in pagination tests.
    """
    data = assert_ok(response)
    assert data["count"] == count, (
        f"expected {count} matching records in total, got {data['count']}"
    )
    if returned is not None:
        assert len(data["results"]) == returned, (
            f"expected {returned} records on this page, got {len(data['results'])}"
        )
    return data


def ids_in(response) -> list[int]:
    """The ids on this page of a paginated list, in the order returned."""
    return [item["id"] for item in response.data["results"]]
