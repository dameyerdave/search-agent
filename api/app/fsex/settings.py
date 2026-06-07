from datetime import timedelta
from pathlib import Path

import environ
import sqlparse
import structlog
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env()
SECRET_KEY = env.str(
    "DJANGO_SECRET_KEY",
    default="dd8d1abef5651a7d7c12-3f6db86b9-da531b6b55b-114d4fdf0bf5d3de876b",
)
DEBUG = env.bool("DJANGO_DEBUG", default=False)
LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", default="INFO")
LOG_SQL = env.bool("DJANGO_LOG_SQL", default=False)
SEARXNG_BASE_URL = env.str("SEARXNG_BASE_URL", default="http://searxng:8080")
SEARXNG_TIMEOUT_S = env.float("SEARXNG_TIMEOUT_S", default=30.0)
CRAWL4AI_ENABLED = env.bool("CRAWL4AI_ENABLED", default=True)
CRAWL4AI_HEADLESS = env.bool("CRAWL4AI_HEADLESS", default=True)
CRAWL4AI_MAX_PAGES_PER_RUN = env.int("CRAWL4AI_MAX_PAGES_PER_RUN", default=25)
CRAWL4AI_PRUNE_THRESHOLD = env.float("CRAWL4AI_PRUNE_THRESHOLD", default=0.4)
CRAWL4AI_WORD_COUNT_THRESHOLD = env.int("CRAWL4AI_WORD_COUNT_THRESHOLD", default=20)
CLOUDFLARE_ACCESS_TEAM_DOMAIN = env.str(
    "CLOUDFLARE_ACCESS_TEAM_DOMAIN",
    default="",
).strip().rstrip("/")
CLOUDFLARE_ACCESS_APP_DOMAIN = env.str(
    "CLOUDFLARE_ACCESS_APP_DOMAIN",
    default="",
).strip()
CLOUDFLARE_ACCESS_AUDIENCE = env.str(
    "CLOUDFLARE_ACCESS_AUDIENCE",
    default="",
).strip()
CLOUDFLARE_ACCESS_REDIRECT_URL = env.str(
    "CLOUDFLARE_ACCESS_REDIRECT_URL",
    default="",
).strip()
CLOUDFLARE_ACCESS_JWKS_CACHE_TTL_S = env.int(
    "CLOUDFLARE_ACCESS_JWKS_CACHE_TTL_S",
    default=300,
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
    "django_extensions",
    "guardian",
    "corsheaders",
    "rest_framework",
    "django_structlog",
    "core",
]

if DEBUG:
    INSTALLED_APPS += [
        "drf_spectacular",
        "drf_spectacular_sidecar",
    ]

INSTALLED_APPS += [
    "django_celery_beat",
    "django_celery_results",
]

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)

ANONYMOUS_USER_ID = -1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fsex.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "fsex.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env.str("POSTGRES_HOST"),
        "PORT": env.str("POSTGRES_PORT"),
        "NAME": env.str("POSTGRES_DB"),
        "USER": env.str("POSTGRES_USER"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
    },
}
REDIS_HOST = env.str("REDIS_HOST", default="redis")
REDIS_PORT = env.str("REDIS_PORT", default="6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = "django-db"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-topic-searches": {
        "task": "core.tasks.dispatch_due_topic_searches",
        "schedule": timedelta(minutes=1),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-US"
TIME_ZONE = "Europe/Zurich"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = "/vol/web/static"

MEDIA_URL = "/media/"
MEDIA_ROOT = "/vol/web/media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DISABLE_BROWSABLE_API = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "core.authentication.CloudflareAccessAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Use drf-spectacular for schema generation in DEBUG
if DEBUG:
    REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] = "drf_spectacular.openapi.AutoSchema"
    SPECTACULAR_SETTINGS = {
        "TITLE": "Search Agent API",
        "DESCRIPTION": (
            "Configurable SearxNG topic monitoring with Crawl4AI content extraction."
        ),
        "VERSION": "v1",
        "SERVERS": [
            {"url": "http://localhost:8077/api/v1/"},
        ],
        "SCHEMA_PATH_PREFIX": "/api/v1/",
    }

if DISABLE_BROWSABLE_API:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
        "rest_framework.renderers.JSONRenderer",
    ]

FIXTURE_DIRS = []

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_HEADERS = default_headers + (
    "cache-control",
    "pragma",
    "expires",
    "X-CSRFTOKEN",
)
CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken"]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")
CSRF_USE_SESSIONS = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SAMESITE = env.str("DJANGO_SESSION_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_AGE = 1209600  # (1209600) default: 2 weeks in seconds
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True

STRUCTLOG_RENDERER = (
    structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer()
)


class _PrettySQLFormatter:
    def format(self, record):
        try:
            return sqlparse.format(
                record.getMessage(),
                reindent=True,
                keyword_case="upper",
            )
        except Exception:
            return record.getMessage()


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structlog": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": STRUCTLOG_RENDERER,
            "foreign_pre_chain": [
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_logger_name,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
            ],
        },
        "pretty_sql": {
            "()": "fsex.settings._PrettySQLFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structlog",
        },
        "sql_console": {
            "class": "logging.StreamHandler",
            "formatter": "pretty_sql",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console"],
    },
    "loggers": {
        "django.server": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


def _drop_common_polling_logs(logger, method_name, event_dict):
    if not DEBUG:
        return event_dict

    event = event_dict.get("event")
    if event not in {"request_started", "request_finished"}:
        return event_dict

    request = event_dict.get("request")
    if isinstance(request, str) and "/api/v1/schema/" in request:
        if event == "request_started":
            raise structlog.DropEvent
        if event == "request_finished" and int(event_dict.get("code", 0)) < 400:
            raise structlog.DropEvent

    if isinstance(request, str) and "/api/v1/health/" in request:
        if event == "request_started":
            raise structlog.DropEvent
        if event == "request_finished" and int(event_dict.get("code", 0)) < 400:
            raise structlog.DropEvent

    return event_dict


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.add_logger_name,
        _drop_common_polling_logs,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
if LOG_SQL:
    LOGGING["loggers"]["django.db.backends"] = {
        "level": "DEBUG",
        "handlers": ["sql_console"],
        "propagate": False,
    }
