# What this file does:
# URL routes for sports analytics: graphical dashboard and stats JSON API endpoint.

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.analytics_dashboard, name='dashboard'),
    path('api/stats/', views.api_stats, name='api_stats'),
]
