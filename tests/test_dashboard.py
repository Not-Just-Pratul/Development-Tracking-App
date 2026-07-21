"""Tests for dashboard and analytics endpoints."""
import pytest


class TestDashboard:
    def test_dashboard_summary(self, client, db_session, auth_headers):
        """Test dashboard summary endpoint."""
        resp = client.get('/api/dashboard/summary', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'totals' in data or 'total_projects' in data
        if 'totals' in data:
            assert 'projects' in data['totals']
        else:
            assert 'total_projects' in data

    def test_dashboard_overdue_stages(self, client, db_session, auth_headers):
        """Test overdue stages endpoint."""
        resp = client.get('/api/dashboard/overdue_stages', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list) or 'overdue_stages' in data

    def test_dashboard_user_performance(self, client, db_session, auth_headers):
        """Test user performance analytics."""
        resp = client.get('/api/dashboard/analytics/user-performance', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'user_performance' in data
        assert 'summary' in data

    def test_dashboard_project_health(self, client, db_session, auth_headers):
        """Test project health analytics."""
        resp = client.get('/api/dashboard/analytics/project-health', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'project_health' in data
