"""Routes for the hiring workflow.

Declared as explicit paths rather than router actions on GigViewSet. The routes
are gig-scoped, but the behaviour belongs to hiring, and an @action on
GigViewSet would make the gigs app import hiring while hiring already imports
gigs -- a circular dependency between applications.

These patterns cannot collide with the gig router: DefaultRouter matches
``gigs/<pk>/`` with nothing after it, so ``gigs/1/apply/`` never reaches it.
"""

from django.urls import path

from apps.hiring.views import (
    AcceptApplicationView,
    ApplyToGigView,
    GigApplicationListView,
)

urlpatterns = [
    path("gigs/<int:gig_id>/apply/", ApplyToGigView.as_view(), name="gig-apply"),
    path(
        "gigs/<int:gig_id>/applications/",
        GigApplicationListView.as_view(),
        name="gig-applications",
    ),
    path(
        "applications/<int:application_id>/accept/",
        AcceptApplicationView.as_view(),
        name="application-accept",
    ),
]
