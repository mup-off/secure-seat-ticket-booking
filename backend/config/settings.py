"""
SecureSeat settings.

Secrets and environment-specific values come from environment variables
(plan, Phase 3: Secrets). In development they can be put in backend/.env,
which is git-ignored. Production refuses to start with unsafe values.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent


def _load_env_file(path):
    """Minimal .env loader: KEY=VALUE lines; real environment variables win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / ".env")


def env(name, default=""):
    return os.environ.get(name, default)


def env_int(name, default):
    try:
        return int(env(name, str(default)))
    except ValueError:
        raise ImproperlyConfigured(f"{name} must be a whole number")


ENVIRONMENT = env("DJANGO_ENV", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
DEBUG = env("DEBUG", "0") == "1" and not IS_PRODUCTION

SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ImproperlyConfigured("SECRET_KEY must be set in production")
    # Random per-process key in development, so no default secret exists in the code.
    import secrets

    SECRET_KEY = secrets.token_urlsafe(50)
elif IS_PRODUCTION and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("SECRET_KEY must be at least 50 characters in production")

ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", "mock")
if IS_PRODUCTION and PAYMENT_PROVIDER == "mock":
    raise ImproperlyConfigured("The mock payment provider cannot be used in production")

HOLD_MINUTES = env_int("HOLD_MINUTES", 10)  # Phase 2: holds expire after 10 minutes
MAX_TICKETS_PER_ORDER = env_int("MAX_TICKETS_PER_ORDER", 10)
MAX_FAILED_LOGINS = env_int("MAX_FAILED_LOGINS", 5)
LOCKOUT_MINUTES = env_int("LOCKOUT_MINUTES", 15)
CURRENCY = "RWF"

INSTALLED_APPS = [
    # The Django admin is left out on purpose: one less login page to attack.
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "accounts",
    "audit",
    "events",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.ContentSecurityPolicyMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]

# PostgreSQL. Every query goes through the Django ORM, which uses parameters,
# so user input never becomes part of the SQL (plan, Phase 3: SQL injection).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "secureseat"),
        "USER": env("DB_USER", "secureseat"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": env("DB_SSLMODE", "require" if IS_PRODUCTION else "prefer")},
    }
}

AUTH_USER_MODEL = "accounts.User"

# Argon2 first (plan, Phase 3: Passwords). The others only let old hashes be read.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("email",)}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---- Sessions and CSRF (plan, Phase 3: Sessions) ----
# The React app talks to the API on the same site, using Django's session cookie.
# Tokens are never kept in localStorage, where an XSS bug could read them.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_AGE = 30 * 60  # 30-minute idle timeout...
SESSION_SAVE_EVERY_REQUEST = True  # ...restarted on each request
SESSION_COOKIE_NAME = "__Host-sessionid" if IS_PRODUCTION else "sessionid"

# The CSRF cookie must be readable by the React app so it can send it back in the
# X-CSRFToken header. It is not a secret on its own: an attacker's site can't read it.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_NAME = "__Host-csrftoken" if IS_PRODUCTION else "csrftoken"
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]

# ---- Security headers (plan, Phase 5) ----
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    CONTENT_SECURITY_POLICY += "; upgrade-insecure-requests"
if env("BEHIND_PROXY", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024  # no request in this app needs more than 20 KB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 50

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["core.authentication.StrictSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "core.exceptions.safe_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",  # per IP, plus account lockout in accounts/views.py
        "register": "10/hour",
        "checkout": "10/min",  # per user
        "webhook": "120/min",
        "unlock": "10/min",  # hidden-tier access code guesses, per IP
        "upload": "20/hour",  # cover image uploads, per user
    },
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

# Throttle counters. Local memory is fine for one process; use Redis or Memcached
# when running several processes so the limits are shared.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kigali"
USE_I18N = False
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# The built React app (frontend/dist) is served by Django in production, so the API
# and the pages share one origin and the same security headers.
FRONTEND_DIST = REPO_DIR / "frontend" / "dist"
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploaded cover images. Stored outside any folder the web server serves directly;
# they are sent through events.views.EventCoverView, which checks who may see them.
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640

# ---- Logging (plan, Phase 6) ----
# JSON lines; phone numbers masked and secrets redacted by core.logging.ScrubFilter.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"scrub": {"()": "core.logging.ScrubFilter"}},
    "formatters": {"json": {"()": "core.logging.JsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json", "filters": ["scrub"]}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
