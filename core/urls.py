# What this file does:
# URL patterns for core platform pages: index, rankings, and head-to-head compare.

from django.urls import path
from . import views

app_name = 'core'

# Core application route definitions
urlpatterns = [
    path('', views.index, name='index'),
    path('rankings/', views.rankings, name='rankings'),
    path('compare/', views.compare, name='compare'),
]
