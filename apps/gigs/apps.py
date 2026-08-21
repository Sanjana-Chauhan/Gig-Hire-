from django.apps import AppConfig


class GigsConfig(AppConfig):
    """Work postings: what a creator wants done, for how much."""

    name = "apps.gigs"
    label = "gigs"
    default_auto_field = "django.db.models.BigAutoField"
