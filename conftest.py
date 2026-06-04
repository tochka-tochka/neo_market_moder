import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django import db

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def test_user(db):
    return User.objects.create_user(username="jwt_user", password="password123")

@pytest.fixture
def jwt_client(api_client, test_user):
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.defaults
    return api_client

@pytest.fixture(autouse=True)
def mock_service_key(monkeypatch):
    monkeypatch.setenv('MODER_SERVICE_KEY', 'test_key_123')
    monkeypatch.setenv('B2B_SERVICE_KEY', 'test_key_123')

@pytest.fixture
def service_client(client):
    client.defaults['HTTP_X_SERVICE_KEY'] = 'test_key_123'
    return client