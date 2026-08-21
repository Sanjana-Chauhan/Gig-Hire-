from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Cross-cutting building blocks shared by the domain applications.

    Holds no models of its own beyond abstract bases: anything concrete here
    would mean a domain concept had been put in the wrong place.
    """

    name = "apps.common"
    label = "common"
    default_auto_field = "django.db.models.BigAutoField"
