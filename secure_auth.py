from functools import wraps
from flask import session, request, jsonify, redirect, url_for, flash
import hashlib
import time
import logging
from datetime import datetime, timedelta
from database import execute_query, get_system_setting, get_db_connection_context

logger = logging.getLogger(__name__)

class SecurityManager:
    """Handles security-related operations."""
    
    @staticmethod
    def hash_password(password):
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify password against hash."""
        return SecurityManager.hash_password(password) == password_hash
    
    @staticmethod
    def record_audit_log(user_id, action, resource_type=None, resource_id=None, details=None, success=True, username=None, location_id=None):
        """Record an audit log entry to the unified database."""
        try:
            # Import unified_db here to avoid circular import
            from unified_db import get_unified_db_connection
            
            # Check if audit logging is enabled (default to True if setting doesn't exist)
            audit_enabled = get_system_setting('enable_audit_logs', True)
            
            if not audit_enabled:
                logger.warning("Audit logging is disabled in system settings")
                return
            
            # Use provided username or fall back to session (for JWT, username must be passed)
            log_username = username or session.get('username')
            # Use provided location_id or fall back to session
            log_location_id = location_id if location_id is not None else session.get('location_id')
            
            logger.info(f"Recording audit log: user_id={user_id}, username={log_username}, action={action}, success={success}")
            
            # Write audit log to unified database (mtpl_unified_launcher)
            with get_unified_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO audit_logs 
                       (user_id, username, action, resource_type, resource_id, details, 
                        ip_address, user_agent, location_id, success)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user_id, log_username, action, resource_type, resource_id, 
                     details, request.remote_addr, request.headers.get('User-Agent'), 
                     log_location_id, success)
                )
                conn.commit()
            
            logger.info(f"Successfully recorded audit log for action: {action}")
        except Exception as e:
            logger.error(f"Failed to record audit log: {e}")
            logger.exception(e)  # Log full stack trace
    
    @staticmethod
    def log_action(user_id, action, resource_type=None, resource_id=None, details=None, success=True, username=None, location_id=None):
        """Alias for record_audit_log for backward compatibility."""
        SecurityManager.record_audit_log(user_id, action, resource_type, resource_id, details, success, username, location_id)

    @staticmethod
    def has_role(user_id, role):
        """Check if a user has a specific role."""
        try:
            with get_db_connection_context() as conn:
                cur = conn.cursor()
                cur.execute("SELECT role, is_super_admin FROM users WHERE id = %s", (user_id,))
                result = cur.fetchone()
                if result:
                    user_role, is_super_admin = result
                    if is_super_admin:
                        return True
                    return user_role == role
                return False
        except Exception as e:
            logger.error(f"Error checking role for user {user_id}: {e}")
            return False
def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        if 'user_id' not in session:
            # Check if this is an API request
            if (request.is_json or 
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.path.startswith('/api/')):
                return jsonify({'error': 'Unauthorized: Please log in.'}), 401
            flash('Please log in to access this page', 'error')
            logger.warning(f"Redirecting to login - no user_id in session")
            return redirect(url_for('ui_auth.login'))
        
        # Session exists - user is authenticated via unified auth
        # No need to check local database as we use unified authentication
        # Update last activity time
        session['last_activity'] = time.time()
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_key):
    """Decorator to require specific permission for routes."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('ui_auth.login'))
            
            # Super admins have all permissions
            if session.get('is_super_admin'):
                return f(*args, **kwargs)
            
            # Check if user has the specific permission
            try:
                with get_db_connection_context() as conn:
                    cur = conn.cursor()
                    
                    cur.execute("""
                        SELECT granted FROM user_permissions 
                        WHERE user_id = %s AND permission_key = %s AND granted = TRUE
                    """, (user_id, permission_key))
                    
                    permission = cur.fetchone()
                    if not permission:
                        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'error': f'Permission denied: {permission_key}'}), 403
                        flash(f'You do not have permission to access this resource: {permission_key}', 'error')
                        return redirect(url_for('ui.root'))
                    
                    return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Permission check error for {permission_key}: {e}")
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Permission check failed'}), 500
                flash('System error occurred. Please try again.', 'error')
                return redirect(url_for('ui.root'))
        
        return decorated_function
    return decorator

def has_user_permission(user_id, permission_key):
    """Check if user has specific permission (utility function)"""
    try:
        # Super admins have all permissions
        with get_db_connection_context() as conn:
            cur = conn.cursor()
            
            # Check if user is super admin
            cur.execute("SELECT is_super_admin FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            if result and result[0]:
                return True
            
            # Check specific permission
            cur.execute("""
                SELECT granted FROM user_permissions 
                WHERE user_id = %s AND permission_key = %s AND granted = TRUE
            """, (user_id, permission_key))
            
            return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Permission check error for user {user_id}, permission {permission_key}: {e}")
        return False

def get_user_permissions(user_id):
    """Get all permissions for a user"""
    try:
        with get_db_connection_context() as conn:
            cur = conn.cursor()
            
            # Check if user is super admin
            cur.execute("SELECT is_super_admin FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            
            # Super admins get all permissions
            if result and result[0]:
                cur.execute("""
                    SELECT permission_key, permission_name, category
                    FROM available_permissions
                    WHERE is_active = TRUE
                    ORDER BY category, permission_name
                """)
                permissions = cur.fetchall()
                return [{'key': perm[0], 'name': perm[1], 'category': perm[2]} for perm in permissions]
            
            # Regular users get their assigned permissions
            cur.execute("""
                SELECT ap.permission_key, ap.permission_name, ap.category
                FROM user_permissions up
                JOIN available_permissions ap ON up.permission_key = ap.permission_key
                WHERE up.user_id = %s AND up.granted = TRUE AND ap.is_active = TRUE
                ORDER BY ap.category, ap.permission_name
            """, (user_id,))
            
            permissions = cur.fetchall()
            return [{'key': perm[0], 'name': perm[1], 'category': perm[2]} for perm in permissions]
    except Exception as e:
        logger.error(f"Error fetching permissions for user {user_id}: {e}")
        return []

def get_user_locations(user_id):
    """Get all locations for a user"""
    try:
        with get_db_connection_context() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT l.id, l.location_name, l.location_code, ul.is_default
                FROM user_locations ul
                JOIN locations l ON ul.location_id = l.id
                WHERE ul.user_id = %s AND l.is_active = TRUE
                ORDER BY ul.is_default DESC, l.location_name
            """, (user_id,))
            
            locations = cur.fetchall()
            return [{'id': loc[0], 'name': loc[1], 'code': loc[2], 'is_default': loc[3]} for loc in locations]
    except Exception as e:
        logger.error(f"Error fetching locations for user {user_id}: {e}")
        return []

def get_user_companies(user_id):
    """Get all companies for a user"""
    try:
        with get_db_connection_context() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT c.id, c.company_name, c.company_code
                FROM user_companies uc
                JOIN companies c ON uc.company_id = c.id
                WHERE uc.user_id = %s AND c.is_active = TRUE
                ORDER BY c.company_name
            """, (user_id,))
            
            companies = cur.fetchall()
            return [{'id': comp[0], 'name': comp[1], 'code': comp[2]} for comp in companies]
    except Exception as e:
        logger.error(f"Error fetching companies for user {user_id}: {e}")
        return []

def get_user_departments(user_id):
    """Get all departments for a user"""
    try:
        with get_db_connection_context() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT d.id, d.department_name
                FROM user_departments ud
                JOIN departments d ON ud.department_id = d.id
                WHERE ud.user_id = %s AND d.is_active = TRUE
                ORDER BY d.department_name
            """, (user_id,))
            
            departments = cur.fetchall()
            return [{'id': dept[0], 'name': dept[1]} for dept in departments]
    except Exception as e:
        logger.error(f"Error fetching departments for user {user_id}: {e}")
        return []

def get_user_applications(user_id):
    """Get all applications for a user"""
    try:
        # Check if user has special admin flag (is_super_admin)
        # Note: This is different from role='admin'. is_super_admin is a special flag
        # that gives unrestricted access to all applications
        result = execute_query(
            "SELECT is_super_admin, role FROM users WHERE id = %s",
            (user_id,),
            fetch=True
        )
        
        with get_db_connection_context() as conn:
            cur = conn.cursor()
            
            # Only is_super_admin flag (NOT role='admin') gets all applications automatically
            # This allows admin users to have restricted application access if needed
            if result and isinstance(result, list) and len(result) > 0 and result[0][0]:
                cur.execute("""
                    SELECT id, app_name, app_code, app_url, app_icon, app_category, 
                           app_description, requires_location
                    FROM applications
                    WHERE is_active = TRUE
                    ORDER BY display_order, app_name
                """)
            elif has_user_permission(user_id, 'access_all_apps'):
                cur.execute("""
                    SELECT id, app_name, app_code, app_url, app_icon, app_category, 
                           app_description, requires_location
                    FROM applications
                    WHERE is_active = TRUE
                    ORDER BY display_order, app_name
                """)
            else:
                # Regular users and admin users (without is_super_admin flag) 
                # get their assigned applications from user_applications table
                cur.execute("""
                    SELECT a.id, a.app_name, a.app_code, a.app_url, a.app_icon, a.app_category,
                           a.app_description, a.requires_location
                    FROM user_applications ua
                    JOIN applications a ON ua.application_id = a.id
                    WHERE ua.user_id = %s AND ua.can_access = TRUE AND a.is_active = TRUE
                    ORDER BY a.display_order, a.app_name
                """, (user_id,))
            
            applications = cur.fetchall()
            return [{
                'id': app[0],
                'name': app[1],
                'code': app[2],
                'url': app[3],
                'icon': app[4],
                'category': app[5],
                'description': app[6],
                'requires_location': app[7]
            } for app in applications]
    except Exception as e:
        logger.error(f"Error fetching applications for user {user_id}: {e}")
        return []

def admin_required(f):
    """Decorator to require admin role (includes super_admin for backward compatibility)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_role = session.get('role')
        is_super_admin = session.get('is_super_admin', False)
        
        # Allow both 'admin' role and is_super_admin flag (for backward compatibility)
        if user_role != 'admin' and not is_super_admin:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required. Only administrators can access this page.', 'error')
            return redirect(url_for('ui.root'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require admin role (super_admin is now same as admin)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_role = session.get('role')
        is_super_admin = session.get('is_super_admin', False)
        
        # Allow both 'admin' role and is_super_admin flag (for backward compatibility)
        if user_role != 'admin' and not is_super_admin:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required. Only administrators can access this page.', 'error')
            return redirect(url_for('ui.root'))
        return f(*args, **kwargs)
    return decorated_function
