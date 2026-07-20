from functools import wraps
from flask import jsonify, session, redirect, url_for, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from __init__ import db


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Try JWT authentication first
            jwt_valid = False
            try:
                verify_jwt_in_request(optional=True)
                claims = get_jwt()
                
                if claims:  # JWT is present and valid
                    jwt_valid = True
                    # Check for super admin or admin role
                    if claims.get('is_super_admin'):
                        return fn(*args, **kwargs)
                    
                    unified_role = claims.get('unified_role', '').lower()
                    if 'admin' in unified_role:
                        return fn(*args, **kwargs)
                    
                    role = claims.get('role')
                    if allowed_roles and role not in allowed_roles:
                        return jsonify({'message': 'forbidden'}), 403
                    return fn(*args, **kwargs)
            except Exception as e:
                # JWT verification failed, will try session auth
                pass
            
            # Fall back to session-based authentication if JWT not valid
            if not jwt_valid:
                # Check for super admin or admin role in session
                if session.get('is_super_admin'):
                    return fn(*args, **kwargs)
                
                unified_role = session.get('unified_role', '').lower()
                if 'admin' in unified_role:
                    return fn(*args, **kwargs)
                
                role = session.get('role')
                if not role:
                    return jsonify({'message': 'unauthorized - please login'}), 401
                
                if allowed_roles and role not in allowed_roles:
                    return jsonify({'message': 'forbidden'}), 403
                return fn(*args, **kwargs)
        return wrapper
    return decorator


def super_admin_required(fn):
    """
    Decorator to restrict access to super administrators only.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt() or {}
        
        if not claims.get('is_super_admin'):
            return jsonify({'message': 'Super admin access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper


def ui_role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Super admins bypass all role checks
            if session.get('is_super_admin'):
                return fn(*args, **kwargs)
            
            # Check if user has admin role from unified database
            user_unified_role = session.get('unified_role', '').lower()
            if 'admin' in user_unified_role:
                return fn(*args, **kwargs)
            
            role = session.get('role')
            if not role:
                return redirect(url_for('ui_auth.login'))
            if allowed_roles and role not in allowed_roles:
                return redirect(url_for('ui.dashboard'))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def stage_access_required(access_type='view'):
    """
    Decorator to check stage access permissions.
    
    Args:
        access_type: 'view' for read access, 'edit' for write access
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Get stage_id from URL parameters
            stage_id = kwargs.get('stage_id')
            if not stage_id:
                abort(400, "Stage ID required")
            
            # Get current user
            user_id = session.get('user_id')
            user_role = session.get('role')
            
            if not user_id:
                return redirect(url_for('ui_auth.login'))
            
            # Get stage with responsible user
            from models import Stage
            stage = db.session.get(Stage, stage_id)
            if not stage:
                abort(404, "Stage not found")
            
            # Check permissions
            can_access = check_stage_access(user_id, user_role, stage, access_type)
            
            if not can_access:
                if access_type == 'edit':
                    abort(403, "You don't have permission to edit this stage")
                else:
                    abort(403, "You don't have permission to view this stage")
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def api_stage_access_required(access_type='view'):
    """
    API version of stage access control using JWT.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            
            # Get stage_id from URL parameters
            stage_id = kwargs.get('stage_id')
            if not stage_id:
                return jsonify({'message': 'Stage ID required'}), 400
            
            # Get current user from JWT
            claims = get_jwt() or {}
            user_id = claims.get('user_id')
            user_role = claims.get('role')
            
            if not user_id:
                return jsonify({'message': 'User ID required in token'}), 400
            
            # Get stage with responsible user
            from models import Stage
            stage = db.session.get(Stage, stage_id)
            if not stage:
                return jsonify({'message': 'Stage not found'}), 404
            
            # Check permissions
            can_access = check_stage_access(user_id, user_role, stage, access_type)
            
            if not can_access:
                if access_type == 'edit':
                    return jsonify({'message': 'You don\'t have permission to edit this stage'}), 403
                else:
                    return jsonify({'message': 'You don\'t have permission to view this stage'}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def check_stage_access(user_id, user_role, stage, access_type):
    """
    Check if a user has access to a stage.
    
    Args:
        user_id: Current user ID
        user_role: Current user role  
        stage: Stage model instance
        access_type: 'view' or 'edit'
    
    Returns:
        bool: True if user has access, False otherwise
    """
    from models import UserRole
    from flask import session
    
    # ONLY Project head and Stage responsible person can edit
    # Removed admin access as per requirement
    
    # For view access: all authenticated users can view
    if access_type == 'view':
        return True  # All users can view all stages
    
    # For edit access: ONLY project head and stage responsible person
    if access_type == 'edit':
        # Project head of this project can edit any stage in their project
        if stage.phase.project.head_id == user_id:
            return True
        
        # Stage responsible person (stage head) can edit their stage
        if stage.responsible_user_id == user_id:
            return True
    
    return False


def can_user_edit_stage(user_id, user_role, stage):
    """
    Helper function to check if user can edit a stage (for use in templates).
    """
    return check_stage_access(user_id, user_role, stage, 'edit')
