# What this file does:
# URL routes for user authentication, coach registration, admin panel management, coach approval workflows, and coach portal features.

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_coach, name='register_coach'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/approvals/', views.admin_approvals, name='admin_approvals'),
    path('admin-panel/approvals/<str:fixture_id>/approve/', views.admin_approve_fixture, name='approve_fixture'),
    path('admin-panel/approvals/<str:fixture_id>/reject/', views.admin_reject_fixture, name='reject_fixture'),
    path('admin-panel/coach-approvals/', views.admin_coach_approvals, name='admin_coach_approvals'),
    path('admin-panel/coach-approvals/<str:user_id>/approve/', views.admin_approve_coach, name='approve_coach'),
    path('admin-panel/coach-approvals/<str:user_id>/reject/', views.admin_reject_coach, name='reject_coach'),
    path('admin-panel/tournament-approvals/', views.admin_tournament_approvals, name='admin_tournament_approvals'),
    path('admin-panel/tournament-approvals/<str:tournament_id>/approve/', views.admin_approve_tournament, name='admin_approve_tournament'),
    path('admin-panel/tournament-approvals/<str:tournament_id>/reject/', views.admin_reject_tournament, name='admin_reject_tournament'),
    path('admin-panel/tournament/<str:tournament_id>/finalize/', views.admin_finalize_tournament, name='finalize_tournament'),
    path('admin-panel/university/create/', views.admin_create_university, name='create_university'),
    path('admin-panel/sport/create/', views.admin_create_sport, name='create_sport'),

    # University Coach Portal & Submission
    path('university-portal/', views.university_portal, name='university_portal'),
    path('university-portal/submit-score/', views.submit_score, name='submit_score'),
]
