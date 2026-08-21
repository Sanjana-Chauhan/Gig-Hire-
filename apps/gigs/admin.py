"""Admin registrations for gigs, to support manual exploratory testing."""

from django.contrib import admin

from apps.gigs.models import Gig


@admin.register(Gig)
class GigAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "creator", "category", "budget", "status"]
    list_filter = ["status", "category"]
    search_fields = ["title", "description"]
    autocomplete_fields = ["creator"]
