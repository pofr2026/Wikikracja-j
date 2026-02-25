import os
import sys
from os import path
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "t", "yes", "y", "on")


def env_int(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def env_list(name, default=None, sep=","):
    value = os.getenv(name)
    if value is None:
        return default if default is not None else []
    parts = [p.strip() for p in value.split(sep)]
    return [p for p in parts if p]

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = path.dirname(path.abspath(path.dirname(__file__)))
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
STATICFILES_DIRS = []
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
load_dotenv(os.path.join(BASE_DIR, '.env'))

DEBUG = env_bool("DEBUG", False)
SITE_PROTOCOL = "http" if DEBUG else "https"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-insecure-secret-key"
    else:
        raise RuntimeError("SECRET_KEY is required when DEBUG is False")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost", "http://127.0.0.1"],
)

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

# Reverse proxy configuration (required when behind Traefik/nginx)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Warsaw")
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pl")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db', 'db.sqlite3'),
    }
}

SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = (os.path.join(BASE_DIR, 'locale'),)
DATE_FORMAT = "Y-m-d"
INTERNAL_IPS = '127.0.0.1'
CRISPY_TEMPLATE_PACK = 'bootstrap4'  # TODO: template?
ASGI_APPLICATION = 'zzz.routing.application'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ROOT_URLCONF = 'zzz.urls'
FILEBROWSER_DIRECTORY = 'uploads/'

gettext_lazy = lambda s: s
LANGUAGES = (
    ('en', gettext_lazy('English')),
    ('pl', gettext_lazy('Polish')),
)

SESSION_EXPIRE_AT_BROWSER_CLOSE = env_bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", False)
SESSION_COOKIE_AGE = env_int("SESSION_COOKIE_AGE", 60 * 60 * 24 * 90)  # default 90 days
REMEMBER_ME_DAYS = env_int("REMEMBER_ME_DAYS", 90)
REMEMBER_ME_COOKIE_AGE = env_int("REMEMBER_ME_COOKIE_AGE", 60 * 60 * 24 * REMEMBER_ME_DAYS)

REDIS_HOST = os.getenv("REDIS_HOST", "redis://redis:6379/1")
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_HOST],
        },
    },
}

WYMAGANYCH_PODPISOW = env_int("WYMAGANYCH_PODPISOW", 2)
CZAS_NA_ZEBRANIE_PODPISOW = env_int("CZAS_NA_ZEBRANIE_PODPISOW", 365)
DYSKUSJA = env_int("DYSKUSJA", 3)
CZAS_TRWANIA_REFERENDUM = env_int("CZAS_TRWANIA_REFERENDUM", 3)

ARCHIVE_PUBLIC_CHAT_ROOM = env_int("ARCHIVE_PUBLIC_CHAT_ROOM", 9)
DELETE_PUBLIC_CHAT_ROOM = env_int("DELETE_PUBLIC_CHAT_ROOM", 360)

UPLOAD_IMAGE_MAX_SIZE_MB = env_int("UPLOAD_IMAGE_MAX_SIZE_MB", 5)
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 10485760)

ACCEPTANCE = env_int("ACCEPTANCE", 3)
DELETE_INACTIVE_USER_AFTER = env_int("DELETE_INACTIVE_USER_AFTER", 30)

GROUP_IS_PUBLIC = env_bool("GROUP_IS_PUBLIC", True)

X_FRAME_OPTIONS = 'SAMEORIGIN'
#X_FRAME_OPTIONS = 'ALLOW'
# TODO: Na produkcji jest:
X_FRAME_OPTIONS = 'DENY'
# Dlaczego?

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',  # filebrowser się nie otwiera jak to jest włączone
    # Na produkcji w nginx dodać:
    # add_header X-Frame-Options SAMEORIGIN;
    # albo w settings.py:
    # X_FRAME_OPTIONS = 'SAMEORIGIN'
    # X_FRAME_OPTIONS = 'ALLOW'
    # XS_SHARING_ALLOWED_METHODS = ['POST','GET','OPTIONS', 'PUT', 'DELETE']
    'allauth.account.middleware.AccountMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates'), os.path.join(BASE_DIR, 'templates', 'allauth')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'zzz.context_processors.footer',
            ],
            'debug': False
        },
    },
]

AUTHENTICATION_BACKENDS = [
    'obywatele.auth_backends.CaseInsensitiveEmailBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

INSTALLED_APPS = (
    'zzz.apps.SchedulerConfig',
    'daphne',
    'channels',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'allauth',
    'allauth.account',
    # 'allauth.socialaccount',
    'django.contrib.staticfiles',
    'django.contrib.admindocs',
    'django_extensions',
    'crispy_forms',
    'bootstrap4',
    'tinymce',
    'filebrowser',
    'django.contrib.admin',
    'django_tables2',
    'django_filters',
    'corsheaders',  # https://stackoverflow.com/questions/22355540/access-control-allow-origin-in-django-app
    'obywatele',
    'glosowania',
    'elibrary',
    'bookkeeping',
    'chat',
    'home',
    'pytz',
    'board',
    'events',
    'tasks',
    'crispy_bootstrap4',
    'captcha',
    'django_browser_reload',
    "django_watchfiles",
)


# Just for suppressing "Using selector: EpollSelector"
import logging
logging.getLogger('asyncio').setLevel(logging.INFO)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True
        },
        # 'django': {
        #     'handlers': ['console'],
        #     'level': 'INFO',
        #     'propagate': True
        # },
        # 'glosowania': {
        #     'handlers': ['console'],
        #     'level': 'INFO',
        #     'propagate': True
        # },
        # 'obywatele': {
        #     'handlers': ['console'],
        #     'level': 'INFO',
        #     'propagate': True
        # },
    },
}

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", SERVER_EMAIL)
EMAIL_SEND_DELAY_SECONDS = env_int("EMAIL_SEND_DELAY_SECONDS", 2)

if not DEBUG and EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    missing = []
    if not EMAIL_HOST:
        missing.append("EMAIL_HOST")
    if not EMAIL_HOST_USER:
        missing.append("EMAIL_HOST_USER")
    if not EMAIL_HOST_PASSWORD:
        missing.append("EMAIL_HOST_PASSWORD")
    if missing:
        raise RuntimeError(
            "SMTP email is enabled but required settings are missing: " + ", ".join(missing)
        )

#########################
# AllAuth Configuration #
#########################
ACCOUNT_FORMS = {
    'signup': 'obywatele.forms.CustomSignupForm',  # disable signup form if spam bots
}
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/board/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/obywatele/onboarding/'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = '/obywatele/onboarding/'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = '/obywatele/onboarding/'
ACCOUNT_PASSWORD_MIN_LENGTH = 8
# ACCOUNT_RATE_LIMITS = True  # doesn't work despite documentation
RATE_LIMITS = 5  # at least doesn't break signup
ACCOUNT_SESSION_REMEMBER = True  # Controls the life time of the session. Set to None to ask the user (“Remember me?”), False to not remember, and True to always remember.
ACCOUNT_SIGNUP_PASSWORD_VERIFICATION = False

# Captcha https://django-simple-captcha.readthedocs.io/en/latest/advanced.html
CAPTCHA_FONT_SIZE = 40
CAPTCHA_IMAGE_SIZE = (170,50)
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.random_char_challenge'
# CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'

#########################
# WhiteNoise Configuration
#########################
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_USE_FINDERS = DEBUG
WHITENOISE_MAX_AGE = 31536000