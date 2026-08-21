"""Local development settings.

Optimised for feedback speed and introspection, not for safety. Never deploy
with this module.
"""

from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

# Convenient locally; a real deployment must pin this to known hostnames.
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])

# The browsable API is a genuine help when probing endpoints by hand, which is
# part of the exploratory testing story. It is a development affordance only.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
