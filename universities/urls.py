# What this file does:
# URL routes for universities: directory roster and individual university detail profiles.

from django.urls import path
from . import views

app_name = 'universities'

urlpatterns = [
    path('', views.university_list, name='list'),
    path('<str:uni_id>/', views.university_detail, name='detail'),
]
