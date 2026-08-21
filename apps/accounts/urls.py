"""Routes for the accounts app.

A router is used rather than hand-written paths so that the URL shape is derived
from the viewset. Hand-written paths drift: someone adds an action to the viewset
and forgets the URL, or renames a route and breaks a client. With a router there
is exactly one declaration.
"""

from rest_framework.routers import DefaultRouter

from apps.accounts.views import CreatorViewSet, SupplierViewSet

router = DefaultRouter()
router.register("creators", CreatorViewSet, basename="creator")
router.register("suppliers", SupplierViewSet, basename="supplier")

urlpatterns = router.urls
