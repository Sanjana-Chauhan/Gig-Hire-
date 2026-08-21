"""Aggregates every application's API routes under the ``/api/`` prefix.

Kept separate from ``config.urls`` so that project-level concerns (admin,
static files) stay distinct from the public API surface.
"""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.gigs.urls")),
    path("", include("apps.hiring.urls")),
]
