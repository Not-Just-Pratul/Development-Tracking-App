"""Tests for authentication and authorization."""
import pytest


class TestAuth:
    def test_login_success(self, client, db_session):
        """Test successful login returns JWT token."""
        resp = client.post('/auth/login', json={
            'username': 'admin',
            'password': 'admin123'
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data
        assert data['user']['username'] == 'admin'

    def test_login_invalid_password(self, client, db_session):
        """Test login with wrong password fails."""
        resp = client.post('/auth/login', json={
            'username': 'admin',
            'password': 'wrongpassword'
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client, db_session):
        """Test login with missing fields fails."""
        resp = client.post('/auth/login', json={})
        assert resp.status_code == 400

    def test_protected_route_without_token(self, client, db_session):
        """Test accessing protected route without token returns 401."""
        resp = client.get('/api/projects')
        assert resp.status_code == 401

    def test_protected_route_with_token(self, client, db_session, auth_headers):
        """Test accessing protected route with valid token succeeds."""
        resp = client.get('/api/projects', headers=auth_headers)
        assert resp.status_code == 200
