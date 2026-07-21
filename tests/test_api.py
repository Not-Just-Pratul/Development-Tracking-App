"""Tests for project CRUD operations."""
import pytest
from models import User, Project, Phase, Stage, Step
from datetime import date


class TestProjects:
    def test_create_project(self, client, db_session, auth_headers):
        """Test creating a new project."""
        resp = client.post('/api/projects', headers=auth_headers, json={
            'name': 'Test Project',
            'head_id': 1
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Test Project'
        assert 'id' in data
        assert 'phases' in data
        assert len(data['phases']) == 5

    def test_get_projects(self, client, db_session, auth_headers):
        """Test listing projects."""
        # Create a project first
        client.post('/api/projects', headers=auth_headers, json={
            'name': 'Test Project',
            'head_id': 1
        })
        
        resp = client.get('/api/projects', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'projects' in data
        assert len(data['projects']) >= 1

    def test_get_project_detail(self, client, db_session, auth_headers):
        """Test getting project details."""
        # Create a project
        create_resp = client.post('/api/projects', headers=auth_headers, json={
            'name': 'Test Project Detail',
            'head_id': 1
        })
        project_id = create_resp.get_json()['id']
        
        # Get project detail
        resp = client.get(f'/api/projects/{project_id}', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['name'] == 'Test Project Detail'
        assert len(data['phases']) == 5

    def test_create_stage(self, client, db_session, auth_headers):
        """Test creating a stage in a project."""
        # Create project
        proj_resp = client.post('/api/projects', headers=auth_headers, json={
            'name': 'Stage Test Project',
            'head_id': 1
        })
        project_id = proj_resp.get_json()['id']
        
        # Create stage
        resp = client.post(f'/api/projects/{project_id}/stages', headers=auth_headers, json={
            'name': 'Test Stage',
            'responsible_user_id': 1
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Test Stage'

    def test_create_step(self, client, db_session, auth_headers):
        """Test creating a step in a stage."""
        # Create project and stage
        proj_resp = client.post('/api/projects', headers=auth_headers, json={
            'name': 'Step Test Project',
            'head_id': 1
        })
        project_id = proj_resp.get_json()['id']
        
        stage_resp = client.post(f'/api/projects/{project_id}/stages', headers=auth_headers, json={
            'name': 'Test Stage'
        })
        stage_id = stage_resp.get_json()['id']
        
        # Create step
        resp = client.post(f'/api/stages/{stage_id}/steps', headers=auth_headers, json={
            'name': 'Test Step'
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['name'] == 'Test Step'

    def test_update_step_expected_end_date(self, client, db_session, auth_headers):
        """Test updating step expected_end_date."""
        # Create project, stage, step
        proj_resp = client.post('/api/projects', headers=auth_headers, json={
            'name': 'Update Test Project',
            'head_id': 1
        })
        project_id = proj_resp.get_json()['id']
        
        stage_resp = client.post(f'/api/projects/{project_id}/stages', headers=auth_headers, json={
            'name': 'Test Stage'
        })
        stage_id = stage_resp.get_json()['id']
        
        step_resp = client.post(f'/api/stages/{stage_id}/steps', headers=auth_headers, json={
            'name': 'Test Step'
        })
        step_id = step_resp.get_json()['id']
        
        # Update step
        resp = client.patch(f'/api/steps/{step_id}', headers=auth_headers, json={
            'expected_end_date': '2026-12-31'
        })
        assert resp.status_code == 200
        assert resp.get_json()['expected_end_date'] == '2026-12-31'

    def test_delete_project(self, client, db_session, auth_headers):
        """Test deleting a project."""
        # Create project
        proj_resp = client.post('/api/projects', headers=auth_headers, json={
            'name': 'Delete Test Project',
            'head_id': 1
        })
        project_id = proj_resp.get_json()['id']
        
        # Delete project
        resp = client.delete(f'/api/projects/{project_id}', headers=auth_headers)
        assert resp.status_code == 200
