from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import logging
from flask_jwt_extended import create_access_token
from datetime import timedelta
from unified_db import get_unified_db_connection
from secure_auth import SecurityManager

logger = logging.getLogger(__name__)

ui_auth = Blueprint('ui_auth', __name__, url_prefix='/ui')


@ui_auth.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication handler using unified authentication."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        audit_username = username or request.form.get('username', 'unknown')
        
        logger.info(f"=== LOGIN ATTEMPT ===")
        logger.info(f"Username: {username}")
        logger.info(f"Password length: {len(password)}")
        logger.info(f"Form data: {dict(request.form)}")
        
        def record_login_event(user_id, action, details, success):
            """Best-effort audit logging for UI logins."""
            try:
                SecurityManager.record_audit_log(
                    user_id=user_id,
                    action=action,
                    details=details,
                    success=success,
                    username=audit_username
                )
            except Exception as log_error:
                logger.error(f"Audit logging failed for {action}: {log_error}")
        
        try:
            # Get user from unified database
            with get_unified_db_connection() as conn:
                logger.info("Database connection established")
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, username, password_hash, full_name, role, is_super_admin, is_active
                    FROM users WHERE username = %s
                """, (username,))
                
                user = cur.fetchone()
                logger.info(f"User query result: {user is not None}")
                
                if not user:
                    logger.warning(f"Login failed: User not found - {username}")
                    record_login_event(None, 'LOGIN_FAILED', 'User not found during UI login', False)
                    flash('Invalid username or password', 'error')
                    return render_template('login.html')
                
                user_id, username, password_hash, full_name, role, is_super_admin, is_active = user
                logger.info(f"User found: ID={user_id}, Active={is_active}")
                
                # Check if user is active
                if not is_active:
                    logger.warning(f"Login failed: Account disabled - {username}")
                    record_login_event(user_id, 'LOGIN_FAILED', 'Account disabled', False)
                    flash('Your account has been disabled. Please contact an administrator.', 'error')
                    return render_template('login.html')
                
                # Verify password
                password_match = SecurityManager.verify_password(password, password_hash)
                logger.info(f"Password verification: {password_match}")
                if not password_match:
                    logger.warning(f"Login failed: Invalid password - {username}")
                    record_login_event(user_id, 'LOGIN_FAILED', 'Invalid password', False)
                    flash('Invalid username or password', 'error')
                    return render_template('login.html')
                
                # Update last login
                cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
                conn.commit()
                
                # Create JWT token for API calls
                jwt_claims = {
                    'user_id': user_id,
                    'username': username,
                    'role': role,
                    'unified_role': role,
                    'is_super_admin': is_super_admin
                }
                access_token = create_access_token(
                    identity=username,
                    additional_claims=jwt_claims,
                    expires_delta=timedelta(hours=24)
                )
                
                # Create session
                session.clear()
                session['user_id'] = user_id
                session['username'] = username
                session['full_name'] = full_name
                session['role'] = role
                session['unified_role'] = role  # Store unified role for authz checks
                session['is_super_admin'] = is_super_admin
                session['user_name'] = full_name  # For backward compatibility
                session['jwt_token'] = access_token  # Store JWT token for API calls
                
                if request.form.get('remember_me') == '1':
                    session.permanent = True
                else:
                    session.permanent = False
                
                # Force session save
                session.modified = True
                
                logger.info(f"Session created for user {username} (ID: {user_id})")
                
                # Log successful login
                logger.info(f"Login successful: {username}")
                record_login_event(user_id, 'LOGIN_SUCCESS', f'UI login successful - Role: {role}', True)
                
                return redirect(url_for('ui.dashboard'))
                
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            flash(f'An error occurred during login: {str(e)}', 'error')
            return render_template('login.html')
    
    return render_template('login.html')


@ui_auth.post('/logout')
def logout():
    """Logout handler."""
    username = session.get('username', 'unknown')
    user_id = session.get('user_id')
    logger.info(f"Logout: {username}")
    
    try:
        SecurityManager.record_audit_log(
            user_id=user_id,
            action='LOGOUT',
            details='User initiated logout via UI',
            success=True,
            username=username,
            location_id=session.get('location_id')
        )
    except Exception as log_error:
        logger.error(f"Audit logging failed for LOGOUT: {log_error}")
    
    session.clear()
    return redirect(url_for('ui_auth.login'))
