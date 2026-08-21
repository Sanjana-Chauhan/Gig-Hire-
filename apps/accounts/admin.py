"""Admin registrations.

Not required by the specification, and worth the twenty lines: the test plan
includes a manual exploratory testing charter, and the admin is the fastest way
to set up an awkward state by hand -- flipping a supplier to ``inactive`` mid
workflow, or eyeballing what a cascade actually did to sibling rows.
"""

from django.contrib import admin

from apps.accounts.models import Creator, Supplier


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "channel_name", "created_at"]
    search_fields = ["name", "email", "channel_name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "hourly_rate", "availability_status"]
    list_filter = ["availability_status"]
    search_fields = ["name", "email"]
