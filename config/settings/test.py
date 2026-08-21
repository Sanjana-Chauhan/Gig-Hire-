"""Settings used by the automated test suite.

Two goals: make the suite fast, and make it behave like a deployed service
rather than a debug server, so that error responses under test are the same
ones a client would really receive.
"""

from .base import *  # noqa: F401,F403
from .base import DATABASES, REST_FRAMEWORK

# DEBUG=False matters for correctness, not just speed: with DEBUG on, Django
# and DRF surface extra detail and swallow some failure modes differently.
# Tests should assert against production-shaped responses.
DEBUG = False

ALLOWED_HOSTS = ["testserver", "localhost"]

# Django already runs SQLite tests in memory, but stating it makes the intent
# explicit and keeps a developer's on-disk db.sqlite3 untouched by the suite.
DATABASES = {
    **DATABASES,
    "default": {**DATABASES["default"], "TEST": {"NAME": None}},
}

# Hashing is irrelevant to these tests; the fast hasher removes needless work.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# JSON only. The browsable renderer would otherwise change response bodies
# depending on the Accept header a test happens to send.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
