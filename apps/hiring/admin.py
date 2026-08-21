"""Admin registrations for the hiring workflow."""

from django.contrib import admin

from apps.hiring.models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["id", "gig", "supplier", "proposed_rate", "status", "created_at"]
    list_filter = ["status"]
    autocomplete_fields = ["supplier"]
