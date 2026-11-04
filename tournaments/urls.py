# What this file does:
# URL routes for tournaments: list calendar, create new championship, tournament standings detail, and PDF export.

from django.urls import path
from . import views

app_name = 'tournaments'

urlpatterns = [
    path('', views.tournament_list, name='list'),
    path('create/', views.tournament_create, name='create'),
    path('<str:tournament_id>/', views.tournament_detail, name='detail'),
    path('<str:tournament_id>/edit/', views.tournament_edit, name='edit'),
    path('<str:tournament_id>/pdf/', views.export_tournament_pdf, name='export_pdf'),
]
