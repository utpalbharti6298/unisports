# What this file does:
# URL routes for athletic sports disciplines: disciplines catalog and individual sport details.

from django.urls import path
from . import views

app_name = 'sports'

urlpatterns = [
    path('', views.sport_list, name='list'),
    path('<str:sport_id>/', views.sport_detail, name='detail'),
]
