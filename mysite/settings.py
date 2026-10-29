"""
Django settings for mysite project.
ExploreAnywhere - Multi-city, hobby-based place recommender.

Deployment configuration is read from the environment so that no secret has to
live in the repository. Every variable has a working development default, so a
fresh clone still runs with `python manage.py runserver` unchanged.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_flag(name, default=False):
    """Read a boolean environment variable ('1', 'true', 'yes', 'on')."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name, default=()):
    """Read a comma separated environment variable into a clean list."""
    raw = os.environ.get(name)
    if raw is None:
        return [item.strip() for item in default]
    return [item.strip() for item in raw.split(",") if item.strip()]


# The value below is the development fallback only. Set DJANGO_SECRET_KEY in
# the environment before deploying; never commit a production key.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-zsnno#^l!whuzs%55j6*366px#r09+borh$1^2mj*_ovz47!o_",
)

DEBUG = _env_flag("DJANGO_DEBUG", default=True)

# Hosts allowed to serve this site. The development default accepts any host
# so the project can be opened from a phone on the local network; production
# should set DJANGO_ALLOWED_HOSTS to the real domain names.
LOCAL_DEV_HOSTS = ("192.168.80.1", "10.172.248.90")
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", default=("*",))
if DEBUG:
    for host in LOCAL_DEV_HOSTS:
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)

# MapTiler access token used by the interactive Leaflet maps. The default is
# the public development token that the project already shipped with; override
# it with MAPTILER_API_KEY for a deployment.
MAPTILER_API_KEY = os.environ.get(
    "MAPTILER_API_KEY",
    "2G4T5asnBPm0kLPHVQsl",
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # ExploreAnywhere Apps
    'apps.users',
    'apps.cities',
    'apps.core',
    'apps.places',
    'apps.itineraries',
    'apps.visits.apps.VisitsConfig',  # ExploreAnywhere phase3f visits-and-rewards v1
    'apps.info',
]

AUTH_USER_MODEL = 'users.User'

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",

    "apps.cities.middleware.KabankalanOnlyMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.explore_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'


_DB_ENGINE = os.environ.get("DJANGO_DB_ENGINE", "django.db.backends.mysql")


def _database_options(engine):
    """Connection options for the configured database engine.

    Only MySQL understands ``charset`` and ``init_command``. Handing them to
    the SQLite backend raises
    ``TypeError: 'charset' is an invalid keyword argument for Connection()``,
    so the SQLite fallback used for local testing stays option-free.
    """
    if engine.endswith("mysql"):
        return {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    return {}


DATABASES = {
    "default": {
        "ENGINE": _DB_ENGINE,
        "NAME": os.environ.get("DJANGO_DB_NAME", "exploreanywhere"),
        "USER": os.environ.get("DJANGO_DB_USER", "root"),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", ""),
        "HOST": os.environ.get("DJANGO_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DJANGO_DB_PORT", "3306"),
        "OPTIONS": _database_options(_DB_ENGINE),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ExploreAnywhere Authentication Redirects
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/cities/select/"
LOGOUT_REDIRECT_URL = "/"
