"""
Settings shared by every environment.

Environment-specific modules (``dev``, ``test``) import from here and override
only what genuinely differs. Values that change between machines, deployments
or environments are read from the environment rather than hardcoded, so the
same code can run locally, in CI and in production without edits.
"""

from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# base.py lives at <repo>/config/settings/base.py, so the repository root is
# three parents up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env()

# A local .env file is optional and never committed. It exists so developers
# can override settings without exporting shell variables by hand.
env.read_env(BASE_DIR / ".env")

# The default below is a placeholder, not a secret: it is only ever used when
# DJANGO_SECRET_KEY is unset, which must never be the case in production.
# ``dev`` and ``test`` tolerate it; a production settings module should not.
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-placeholder-override-me")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
# Grouped by origin so it stays obvious what we own and what we depend on.
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
]

LOCAL_APPS = [
    "apps.common",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# DATABASE_URL is the 12-factor convention and lets a deployment point at
# PostgreSQL without touching code. When it is absent we fall back to SQLite,
# which the assignment explicitly permits.
DATABASE_URL = env("DATABASE_URL", default="")

if DATABASE_URL:
    DATABASES = {"default": env.db_url_config(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / env("SQLITE_NAME", default="db.sqlite3"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", default="en-us")
TIME_ZONE = env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / env("DJANGO_STATIC_ROOT", default="staticfiles")

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
# Upper bound on a client-supplied ?page_size=. Read by
# apps.common.pagination.DefaultPagination; kept as a plain Django setting
# because DRF has no equivalent of its own.
API_MAX_PAGE_SIZE = env.int("API_MAX_PAGE_SIZE", default=100)

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE", default=20),
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    # One handler renders every rule violation and keeps database errors from
    # reaching clients raw. See apps.common.exceptions.
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# A single console handler is enough here. The point of configuring it at all
# is that unexpected server errors are visible rather than swallowed.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
}
