from pathlib import Path

from .app_settings import APP_SETTINGS

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = APP_SETTINGS.DJANGO_SECRET_KEY
DEBUG = APP_SETTINGS.DJANGO_DEBUG
ALLOWED_HOSTS = APP_SETTINGS.ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = APP_SETTINGS.CSRF_TRUSTED_ORIGINS

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_celery_beat",
    "scheduler",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "scheduler.context_processors.auth_status",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"
ASGI_APPLICATION = "app.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db.sqlite3",
        "OPTIONS": {"timeout": 30},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

REDIS_URL = APP_SETTINGS.REDIS_URL
CELERY_BROKER_URL = APP_SETTINGS.REDIS_URL
CELERY_RESULT_BACKEND = APP_SETTINGS.REDIS_URL
CELERY_TASK_TRACK_STARTED = APP_SETTINGS.CELERY_TASK_TRACK_STARTED
CELERY_TIMEZONE = APP_SETTINGS.CELERY_TIMEZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CLAUDE_BIN = APP_SETTINGS.CLAUDE_BIN
RUN_LOG_DIR = BASE_DIR / "data" / "runs"

(BASE_DIR / "data").mkdir(exist_ok=True)
RUN_LOG_DIR.mkdir(exist_ok=True, parents=True)
