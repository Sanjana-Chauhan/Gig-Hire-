"""Root URL configuration.

Application routes are mounted under a single versioned-ish ``/api/`` prefix
declared once here. Each app owns its own urls module, so adding a resource
never means editing unrelated routing.
"""

from django.contrib import admin
from django.urls import include, path

API_PREFIX = "api/"

urlpatterns = [
    path("admin/", admin.site.urls),
    path(API_PREFIX, include("config.api_urls")),
]
