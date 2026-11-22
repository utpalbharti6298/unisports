import pytest
import json
from django.test import Client

@pytest.fixture
def client():
    return Client()

def test_analytics_dashboard_status(client):
    response = client.get('/analytics/')
    assert response.status_code == 200
    assert b"Analytics" in response.content or b"Sports Analytics &amp; Visualization" in response.content or b"Sports Analytics" in response.content

def test_analytics_api_stats_payload(client):
    response = client.get('/analytics/api/stats/')
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'

    data = json.loads(response.content)
    assert data['status'] == 'success'
    assert 'rankings' in data
    assert 'medals' in data
    assert 'sports' in data
    assert 'win_rates' in data
    assert isinstance(data['rankings']['points'], list)
    assert isinstance(data['medals']['data'], list)
