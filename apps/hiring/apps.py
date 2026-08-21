from django.apps import AppConfig


class HiringConfig(AppConfig):
    """The hiring workflow: applications, contracts and reviews.

    These three live in one app because they form a single process, not three
    independent concepts: an application becomes a contract, a contract earns
    reviews. They change together, and splitting them would mean three apps that
    only ever change for the same reasons.

    Dependency direction is deliberately one-way: hiring imports from gigs and
    accounts, never the reverse. That is why the gig-scoped endpoints
    (/api/gigs/{id}/apply/) are declared here rather than as actions on
    GigViewSet -- an action there would make gigs import hiring, and hiring
    already imports gigs for its foreign keys. Two apps that import each other
    cannot be reasoned about, tested, or removed separately.
    """

    name = "apps.hiring"
    label = "hiring"
    default_auto_field = "django.db.models.BigAutoField"
