"""Pytest configuration and shared fixtures for Development Tracking System tests."""
import pytest
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from __init__ import create_app, db as _db
from models import User, Project, Phase, Stage, Step
from config import Config


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    return app


@pytest.fixture(scope='function')
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for tests."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.session.remove()
        # Disable FK checks to avoid circular dependency drop issues
        try:
            with _db.engine.connect() as conn:
                conn.execute(_db.text('SET session_replication_role = replica;'))
                _db.drop_all()
                conn.execute(_db.text('SET session_replication_role = DEFAULT;'))
        except Exception:
            pass


@pytest.fixture(scope='function')
def auth_headers(client, db_session):
    """Create authenticated user and return JWT headers."""
    # Ensure admin user exists
    user = User.query.filter_by(username='admin').first()
    if not user:
        user = User(
            username='admin',
            full_name='System Administrator',
            password_hash='240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
            role='admin',
            is_super_admin=True,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
    
    resp = client.post('/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    assert resp.status_code == 200
    token = resp.get_json()['access_token']
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
