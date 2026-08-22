"""Aggregates every application's API routes under the ``/api/`` prefix.

Kept separate from ``config.urls`` so that project-level concerns (admin, static
files) stay distinct from the public API surface.

Note on routers: each app defines its own ``DefaultRouter``, but they are merged
into a single router here rather than each being ``include()``-ed separately.
A DefaultRouter generates an API-root view listing its own registrations, so
including two routers at the same prefix produces two competing ``/api/`` views
-- Django resolves the first and the second app's endpoints become undiscoverable
from the root. Merging the registries gives one root that lists everything.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.urls import router as accounts_router
from apps.gigs.urls import router as gigs_router

router = DefaultRouter()

# Combine the per-app registries into one router so a single API root lists
# every collection endpoint.
for app_router in (accounts_router, gigs_router):
    router.registry.extend(app_router.registry)

urlpatterns = [
    path("", include(router.urls)),
    # Action and nested endpoints are explicit paths rather than viewset
    # registrations, so they do not appear in the router's root listing. See
    # apps/hiring/urls.py for why they live in the hiring app.
    path("", include("apps.hiring.urls")),
]
