from flask import Blueprint, request, jsonify, abort, make_response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, create_refresh_token
from datetime import timedelta
import traceback
import logging

from __init__ import db
from models import User, UserRole
from unified_db import get_unified_db_connection
from secure_auth import SecurityManager

auth = Blueprint('auth', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)


@auth.post('/register')
def register():
    """Register new user (team_member role only for security)"""
    payload = request.get_json(force=True) or {}
    required = ['username', 'name', 'password']
    if not all(k in payload and payload[k] for k in required):
        abort(400, description='username, name, password are required')

    if User.query.filter_by(username=payload['username']).first():
        abort(409, description='username already exists')

    # Security: Only allow team_member role for public registration
    user = User(
        username=payload['username'],
        full_name=payload['name'],
        role=UserRole.TEAM_MEMBER,
        password_hash=SecurityManager.hash_password(payload['password'])
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({'id': user.id, 'username': user.username, 'role': user.role}), 201


@auth.post('/login')
def login():
    """Login endpoint supporting both local and unified authentication"""
    payload = request.get_json(force=True) or {}
    username = payload.get('username')
    password = payload.get('password')
    
    if not username or not password:
        return make_response(jsonify({'error': 'username and password are required'}), 400)
    
    try:
        # Try unified authentication first
        with get_unified_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, full_name, role, is_super_admin, is_active FROM users WHERE username = %s",
                (username,)
            )
            row = cursor.fetchone()
            
            if not row:
                return make_response(jsonify({'error': 'User not found'}), 404)
                
            user_id, db_username, password_hash, full_name, unified_role, is_super_admin, is_active = row
                
            # Verify password
            if not SecurityManager.verify_password(password, password_hash):
                try:
                    SecurityManager.record_audit_log(user_id=user_id, action='LOGIN_FAILED', 
                                                    details='Invalid password', success=False, username=username)
                except Exception as e:
                    logger.warning(f"Failed to record audit log: {e}")
                return make_response(jsonify({'error': 'Invalid credentials'}), 401)
                
            # Check if user is active
            if not is_active:
                try:
                    SecurityManager.record_audit_log(user_id=user_id, action='LOGIN_FAILED', 
                                                    details='Account is inactive', success=False, username=username)
                except Exception as e:
                    logger.warning(f"Failed to record audit log: {e}")
                return make_response(jsonify({'error': 'Account is inactive'}), 403)
                
            # Map unified role to local role
            if is_super_admin or unified_role == 'admin':
                local_role = UserRole.PROJECT_HEAD
            else:
                local_user = User.query.filter_by(username=username).first()
                local_role = local_user.role if local_user else UserRole.TEAM_MEMBER
            
            # Create JWT tokens
            additional_claims = {
                'role': local_role,
                'user_id': user_id,
                'username': username,
                'full_name': full_name,
                'is_super_admin': is_super_admin,
                'auth_source': 'unified'
            }
            
            access_token = create_access_token(identity=str(user_id), additional_claims=additional_claims,
                                              expires_delta=timedelta(hours=8))
            refresh_token = create_refresh_token(identity=str(user_id), additional_claims=additional_claims,
                                                expires_delta=timedelta(days=30))
            
            # Record successful login
            try:
                SecurityManager.record_audit_log(user_id=user_id, action='LOGIN_SUCCESS', 
                                                details=f'Unified auth login - Role: {local_role}', 
                                                success=True, username=username)
            except Exception:
                pass
            
            # Create session for browser requests so UI pages work
            session.clear()
            session['user_id'] = user_id
            session['username'] = username
            session['full_name'] = full_name
            session['role'] = local_role
            session['unified_role'] = local_role
            session['is_super_admin'] = is_super_admin
            session['user_name'] = full_name
            session['jwt_token'] = access_token
            session.modified = True
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': user_id,
                    'username': username,
                    'name': full_name,
                    'role': local_role,
                    'is_super_admin': is_super_admin
                }
            }), 200
    
    except Exception as e:
        traceback.print_exc()
        # Fall through to local authentication
    
    # Fallback to local authentication
    user = User.query.filter_by(username=username).first()
    if not user or not SecurityManager.verify_password(password, user.password_hash):
        if user:
            try:
                SecurityManager.record_audit_log(user_id=user.id, action='LOGIN_FAILED', 
                                                details='Invalid password (local auth)', success=False, username=username)
            except Exception:
                pass
        return make_response(jsonify({'error': 'Invalid credentials'}), 401)
    
    additional_claims = {
        'role': user.role,
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'is_super_admin': False,
        'auth_source': 'local'
    }
    
    access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims,
                                      expires_delta=timedelta(hours=8))
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=additional_claims,
                                        expires_delta=timedelta(days=30))
    
    # Record successful login
    try:
        SecurityManager.record_audit_log(user_id=user.id, action='LOGIN_SUCCESS', 
                                        details=f'Local auth login - Role: {user.role}', 
                                        success=True, username=user.username)
    except Exception:
        pass
    
    # Create session for browser requests so UI pages work
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['full_name'] = user.full_name
    session['role'] = user.role
    session['unified_role'] = user.role
    session['is_super_admin'] = False
    session['user_name'] = user.full_name
    session['jwt_token'] = access_token
    session.modified = True
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'role': user.role,
            'is_super_admin': False
        }
    }), 200


@auth.patch('/users/<int:user_id>/role')
@jwt_required()
def update_user_role(user_id):
    """Update user role - only accessible by PROJECT_HEAD users"""
    claims = get_jwt()
    if claims.get('role') != UserRole.PROJECT_HEAD:
        abort(403, description='Only project heads can assign roles')
    
    payload = request.get_json(force=True) or {}
    new_role = payload.get('role')
    
    if not new_role:
        abort(400, description='role is required')
    
    if new_role not in [UserRole.PROJECT_HEAD, UserRole.STAGE_OWNER, UserRole.TEAM_MEMBER, UserRole.VIEWER]:
        abort(400, description='invalid role')
    
    user = User.query.get_or_404(user_id)
    old_role = user.role
    user.role = new_role
    db.session.commit()
    
    return jsonify({
        'id': user.id,
        'username': user.username,
        'name': user.full_name,
        'role': user.role,
        'message': f'Role updated from {old_role} to {new_role}'
    })


@auth.post('/refresh')
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token"""
    claims = get_jwt()
    identity = claims.get('sub')
    
    # Recreate claims from refresh token
    additional_claims = {
        'role': claims.get('role'),
        'user_id': claims.get('user_id'),
        'username': claims.get('username'),
        'full_name': claims.get('full_name'),
        'is_super_admin': claims.get('is_super_admin', False),
        'auth_source': claims.get('auth_source', 'local')
    }
    
    access_token = create_access_token(
        identity=identity,
        additional_claims=additional_claims,
        expires_delta=timedelta(hours=8)
    )
    
    return jsonify({'access_token': access_token}), 200


@auth.get('/verify')
@jwt_required()
def verify_token():
    """Verify if the current token is valid and return user info"""
    claims = get_jwt()
    return jsonify({
        'valid': True,
        'user': {
            'id': claims.get('user_id'),
            'username': claims.get('username'),
            'name': claims.get('full_name'),
            'role': claims.get('role'),
            'is_super_admin': claims.get('is_super_admin', False)
        }
    }), 200


@auth.get('/users')
@jwt_required()
def list_users():
    """List all users - only accessible by PROJECT_HEAD and STAGE_OWNER"""
    claims = get_jwt()
    user_role = claims.get('role')
    is_super_admin = claims.get('is_super_admin', False)
    
    if not is_super_admin and user_role not in [UserRole.PROJECT_HEAD, UserRole.STAGE_OWNER]:
        abort(403, description='Access denied')
    
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])
