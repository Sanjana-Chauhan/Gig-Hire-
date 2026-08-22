"""Admin registrations for the hiring workflow."""

from django.contrib import admin

from apps.hiring.models import Application, Contract, Review


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["id", "gig", "supplier", "proposed_rate", "status", "created_at"]
    list_filter = ["status"]
    autocomplete_fields = ["supplier"]


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["id", "gig", "supplier", "agreed_rate", "status", "created_at"]
    list_filter = ["status"]
    autocomplete_fields = ["supplier"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["id", "contract", "reviewer_type", "rating", "created_at"]
    list_filter = ["reviewer_type", "rating"]
