"""
Base settings to build other settings files upon.
"""
from pathlib import Path
import os
import environ
from datetime import timedelta
import sys

# 1. Path Configuration
# BASE_DIR is "audit_ease/"
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# 2. Add APPS_DIR to Python path
# This allows you to import 'users' instead of 'apps.users'
# sys.path.append(str(APPS_DIR)) 

# Sentry Configuration
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    traces_sample_rate=1.0,
    send_default_pii=True,
    environment=os.environ.get("DJANGO_ENV", "production")
) 

# 2. Environment Configuration
env = environ.Env()
# Always try to read .env file if it exists
env.read_env(str(BASE_DIR / ".env"))

# 3. General Config
DEBUG = env.bool("DJANGO_DEBUG", False)
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True

# 4. Databases
# Default to SQLite for safety, override with DATABASE_URL in .env
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# 5. URLs
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# 6. Applications
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_celery_results",  # Stores celery tasks in DB if needed
    # "django_extensions",    # Optional: useful for shell_plus
    "drf_spectacular",
    "auditlog",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.github",
]

LOCAL_APPS = [
    "apps.users",
    "apps.organizations",
    "apps.billing",
    "apps.integrations",
    # "apps.integrations.apps.IntegrationsConfig",
    "apps.audits",
    "apps.reports",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# 7. Authentication
AUTH_USER_MODEL = "users.User"  # Points to apps/users/models.py

# 8. Middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # Must be near top
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom Middleware
    "middleware.org_context.OrgContextMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
    "middleware.audit_logging.AuditLogMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# 9. Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
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

# 10. Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# 11. Static & Media Files
STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "staticfiles")
STATICFILES_DIRS = [str(BASE_DIR / "static")]

MEDIA_URL = "/media/"
MEDIA_ROOT = str(BASE_DIR / "media")

# 12. Celery Configuration
if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# 12.5 Cache Configuration (For Rate Limiting)
# Uses local memory cache for development; can be switched to Redis in production
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "audit-ease-cache",
        "OPTIONS": {
            "MAX_ENTRIES": 10000
        }
    }
}
# Use Redis if configured in environment (Production)
if env.str("REDIS_URL", default=None):
    CACHES["default"] = {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }

# 13. REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",

    # Global Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',   # Strict: Block bots/scrapers
        'user': '1000/hour', # Standard: Approx 16 requests/minute
    }
}

# 14. JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# 14.5 AllAuth Configuration
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
]

SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'SCOPE': [
            'read:user',
            'user:email',
            'read:org', # Needed to verify organization membership
        ],
    }
}

# Add AllAuth apps to INSTALLED_APPS (Appending to existing list)
# (Added to THIRD_PARTY_APPS above)

# 15. Logging (Basic Setup)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# 16. App Specific Settings & Environment Validation
# Encryption key for Integration tokens (Fernet)
FERNET_KEY = env("FERNET_KEY", default=env("ENCRYPTION_KEY", default=None))

# Use 'env' to read the variable (it now contains data from .env)
# We check for either name since your .env has both
ENCRYPTION_KEY = FERNET_KEY

# 16.1 Rate Limiting Configuration
# AUDIT_RATE_LIMIT: Controls the rate limit for audit creation (e.g., "5/h" = 5 per hour)
AUDIT_RATE_LIMIT = env("AUDIT_RATE_LIMIT", default="5/h")

# 16.2 Stripe Configuration
# For development, these can be test keys. In production, they are required.
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="pk_test_placeholder")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="sk_test_placeholder")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="whsec_placeholder")

# Frontend URL for Stripe redirect (success/cancel URLs)
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# CRITICAL: Validate that the key exists on production startup
if not FERNET_KEY:
    # Only raise error if we are NOT in debug mode (optional safety)
    # or just always raise it because your app needs it to run.
    raise ValueError(
        "🔴 CRITICAL: ENCRYPTION_KEY (or FERNET_KEY) is missing from .env or environment variables!\n"
        "Run: ./production_env_setup.sh to generate required credentials"
    )

# 16.5 CRITICAL: Environment Variable Validation
# Ensure all critical secrets are configured for production

from django.core.exceptions import ImproperlyConfigured

def validate_required_settings():
    """
    Validate that all required production settings are configured.
    Raises ImproperlyConfigured if any critical setting is missing.
    """
    missing_settings = []
    
    # Check FERNET_KEY (Encryption)
    if not FERNET_KEY or FERNET_KEY == "":
        missing_settings.append("FERNET_KEY (or ENCRYPTION_KEY)")
    
    # Check DJANGO_SECRET_KEY
    secret_key = env("DJANGO_SECRET_KEY", default=None)
    if not secret_key:
        missing_settings.append("DJANGO_SECRET_KEY")
    
    # Check DATABASE_URL
    database_url = env("DATABASE_URL", default=None)
    if not database_url and not DEBUG:
        # Only enforce DATABASE_URL in production (not DEBUG mode)
        missing_settings.append("DATABASE_URL")
    
    # If using production cache or sessions, require proper backend
    if not DEBUG and DATABASES.get("default", {}).get("ENGINE") == "django.db.backends.sqlite3":
        import warnings
        warnings.warn(
            "⚠️  WARNING: Using SQLite in production is not recommended. "
            "Configure DATABASE_URL to use PostgreSQL or another production database.",
            UserWarning
        )
    
    if missing_settings:
        error_message = (
            "🔴 CRITICAL: The following required settings are missing:\n\n"
            + "\n".join(f"  - {setting}" for setting in missing_settings)
            + "\n\nFix: Run './production_env_setup.sh' to configure your environment.\n"
            "Or ensure these variables are set in your .env file or environment."
        )
        raise ImproperlyConfigured(error_message)

# Run validation on startup
if not DEBUG:
    # Strict validation for production
    validate_required_settings()
else:
    # Permissive validation for development
    try:
        validate_required_settings()
    except ImproperlyConfigured:
        import warnings
        warnings.warn(
            "⚠️  Some production settings are missing, but DEBUG mode is enabled. "
            "This is fine for development.",
            UserWarning
        )

# 17. Set DJANGO_SECRET_KEY (or use default for development)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-key-change-in-production")

# 18. CORS & Security Settings for Production
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://localhost:8000"]
)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"]
)

# Security middleware settings (enforce in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_SECURITY_POLICY = {
        "default-src": ("'self'",),
        "script-src": ("'self'", "'unsafe-inline'"),
        "style-src": ("'self'", "'unsafe-inline'"),
    }


# Celery Configuration Options
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'







SPECTACULAR_SETTINGS = {
    "TITLE": "AuditEase API",
    "DESCRIPTION": "Programmatic access for integrating AuditEase into your workflow.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,

    "SECURITY": [{"BearerAuth": []}],
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}
ENABLE_AWS_BETA = False
