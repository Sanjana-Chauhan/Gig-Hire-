from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """The two participants in the marketplace: creators and suppliers.

    Grouped into one app because they are the same concept from two sides -- a
    party with an identity and contact details -- and they are always reasoned
    about together. Splitting them would create two apps that only ever change
    for the same reasons.
    """

    name = "apps.accounts"
    label = "accounts"
    default_auto_field = "django.db.models.BigAutoField"
