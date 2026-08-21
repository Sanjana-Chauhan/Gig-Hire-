"""Routes for the gigs app."""

from rest_framework.routers import DefaultRouter

from apps.gigs.views import GigViewSet

router = DefaultRouter()
router.register("gigs", GigViewSet, basename="gig")

urlpatterns = router.urls
