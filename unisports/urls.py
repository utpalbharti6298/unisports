# What this file does:
# Root URL router for the UniSports platform.
# Routes incoming web requests to the core, accounts, universities, sports, tournaments, and analytics apps.

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Top-level URL patterns linking each functional app
urlpatterns = [
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('universities/', include('universities.urls')),
    path('sports/', include('sports.urls')),
    path('tournaments/', include('tournaments.urls')),
    path('analytics/', include('analytics.urls')),
]

if settings.DEBUG:
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
