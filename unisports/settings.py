# What this file does:
# Configuration file for the UniSports Django application.
# Sets up installed apps, MongoEngine MongoDB Atlas connection, signed cookie sessions, templates, and static directories.

from pathlib import Path

import os
import sys
from dotenv import load_dotenv
import mongoengine

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-x($xc(jhfg3&690pab70evedwcw&vvaeb0wz^hl31)e60g@y0u')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*'] if DEBUG else [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,.vercel.app').split(',') if h.strip()]

# CSRF Trusted Origins for HTTPS deployment (Vercel & custom domains)
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', 'https://*.vercel.app,http://127.0.0.1,http://localhost').split(',')
    if origin.strip()
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # UniSports Apps
    'core',
    'accounts',
    'universities',
    'sports',
    'tournaments',
    'analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    INSTALLED_APPS.append('django_browser_reload')
    MIDDLEWARE.append('django_browser_reload.middleware.BrowserReloadMiddleware')

ROOT_URLCONF = 'unisports.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'unisports.wsgi.application'

# Database - MongoDB via MongoEngine (No SQL DB required)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy',
    }
}

# MongoEngine Connection Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/unisports_db')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'unisports_db')
USE_MONGOMOCK = os.getenv('USE_MONGOMOCK', 'False').lower() in ('1', 'true')

# Detect build-time / asset collection tasks so static build never hangs or fails on DB
is_static_build_task = any(cmd in sys.argv for cmd in ['collectstatic', 'findstatic'])

if USE_MONGOMOCK or is_static_build_task:
    import mongomock
    mongoengine.disconnect(alias='default')
    mongoengine.connect(
        db=MONGO_DB_NAME,
        mongo_client_class=mongomock.MongoClient,
        alias='default',
        uuidRepresentation='standard'
    )
    if is_static_build_task:
        print("[UniSports DB] Static build task detected: isolated using in-memory mock to avoid DB block.")
    else:
        print("[UniSports DB] USE_MONGOMOCK is set: running with in-memory mongomock.")
else:
    # Check if existing connection is already healthy to prevent drop on Django autoreload
    already_connected = False
    try:
        from mongoengine.connection import get_connection
        existing_conn = get_connection('default')
        if existing_conn and not getattr(existing_conn, 'is_mongomock', False):
            existing_conn.admin.command('ping')
            already_connected = True
            print("[UniSports DB] Existing live MongoDB connection active & healthy.")
    except Exception:
        already_connected = False

    if not already_connected:
        import time
        max_retries = 3
        connected = False
        last_err = None

        for attempt in range(1, max_retries + 1):
            try:
                mongoengine.disconnect(alias='default')
                client = mongoengine.connect(
                    db=MONGO_DB_NAME,
                    host=MONGO_URI,
                    alias='default',
                    uuidRepresentation='standard',
                    serverSelectionTimeoutMS=15000,
                    connectTimeoutMS=15000,
                    retryWrites=True
                )
                client.admin.command('ping')
                connected = True
                print(f"[UniSports DB] Connected LIVE to MongoDB Atlas! (Attempt {attempt})")
                break
            except Exception as e:
                last_err = e
                print(f"[UniSports DB] Atlas connection attempt {attempt}/{max_retries} failed: {e}")
                time.sleep(1)

        if not connected:
            print("=" * 70)
            print("[UniSports DB ERROR] FATAL: Could not connect to MongoDB Atlas.")
            print(f"Details: {last_err}")
            print("Ensure 0.0.0.0/0 is whitelisted in MongoDB Atlas Network Access.")
            print("=" * 70)
            if os.getenv('ALLOW_MOCK_FALLBACK', 'False').lower() in ('1', 'true'):
                import mongomock
                mongoengine.disconnect(alias='default')
                mongoengine.connect(db=MONGO_DB_NAME, mongo_client_class=mongomock.MongoClient, alias='default', uuidRepresentation='standard')
                print("[UniSports DB WARNING] Operating with empty in-memory mongomock fallback.")
            else:
                if last_err:
                    raise last_err
                raise ConnectionError("Could not connect to MongoDB Atlas.")

    # Run automatic database integrity check & schema migration on boot
    try:
        from unisports.db_integrity import ensure_db_schema_integrity
        ensure_db_schema_integrity()
    except Exception as e:
        print(f"[UniSports DB] Note on schema integrity check: {e}")


# Database-less Session Engine (using cryptographically signed cookies)
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_NAME = 'unisports_session'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 86400 * 7

CSRF_COOKIE_NAME = 'unisports_csrftoken'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG

# Security Headers & Defenses
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
