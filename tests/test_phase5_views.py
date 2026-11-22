import pytest
from django.test import Client
from tournaments.models import Tournament

@pytest.fixture
def client():
    return Client()

def test_home_page_status(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"UniSports" in response.content

def test_universities_list_status(client):
    response = client.get('/universities/')
    assert response.status_code == 200
    assert b"Universities" in response.content or b"Participating Universities" in response.content

def test_tournaments_list_status(client):
    response = client.get('/tournaments/')
    assert response.status_code == 200
    assert b"Tournaments" in response.content or b"Tournaments Calendar" in response.content

def test_sports_list_status(client):
    response = client.get('/sports/')
    assert response.status_code == 200
    assert b"Sports &amp; Competitions" in response.content or b"Sports" in response.content

def test_rankings_status(client):
    response = client.get('/rankings/?year=2025&sport=All')
    assert response.status_code == 200
    assert b"Rankings" in response.content or b"Overall University Rankings" in response.content

def test_compare_status(client):
    response = client.get('/compare/')
    assert response.status_code == 200
    assert b"Compare" in response.content or b"Head-to-Head" in response.content

def test_admin_panel_requires_login(client):
    response = client.get('/accounts/admin-panel/')
    # Must redirect to login when unauthenticated
    assert response.status_code == 302
    assert '/accounts/login/' in response.url

def test_tournament_pdf_export(client):
    t = Tournament.objects.first()
    if t:
        response = client.get(f'/tournaments/{t.id}/pdf/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
