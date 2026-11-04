import os
import pytest
from django.conf import settings

def test_django_configured():
    assert settings.configured
    assert 'unisports.urls' in settings.ROOT_URLCONF

def test_apps_installed():
    expected_apps = ['core', 'accounts', 'universities', 'sports', 'tournaments', 'analytics']
    for app in expected_apps:
        assert app in settings.INSTALLED_APPS

def test_session_engine_cookie_based():
    assert settings.SESSION_ENGINE == 'django.contrib.sessions.backends.signed_cookies'
