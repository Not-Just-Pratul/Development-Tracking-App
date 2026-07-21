from flask import Flask, jsonify, session, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_compress import Compress
import logging
import os

from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
compress = Compress()

# Setup minimal logging for production
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Disable template caching for development
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching during development
    
    # Performance optimizations
    # app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # Cache static files for 1 year
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html', 'text/css', 'text/xml', 'text/plain',
        'application/javascript', 'application/json'
    ]
    app.config['COMPRESS_LEVEL'] = 6  # Compression level (1-9)
    app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress files larger than 500 bytes

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    jwt.init_app(app)
    CORS(app)
    compress.init_app(app)  # Enable response compression
    
    # Initialize unified authentication database manager
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, 'config.ini')
        from database import db_manager
        db_manager.initialize(config_path)
    except Exception as e:
        logger.error(f"Failed to initialize database manager: {e}")

    # Import models to ensure they're registered with SQLAlchemy
    import models
    
    from api import api as api_bp
    from auth import auth as auth_bp
    from ui import ui as ui_bp
    from ui_auth import ui_auth as ui_auth_bp
    from reports import reports as reports_bp
    from unified_db import get_all_users_with_details

    # Register request teardown to ensure connections are returned to pool
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Ensure database sessions are properly closed after each request"""
        try:
            if exception:
                db.session.rollback()
            db.session.remove()
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
    
    # Add error handlers to ensure proper connection cleanup
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Global exception handler to ensure database cleanup"""
        try:
            db.session.rollback()
        except Exception:
            pass
        
        from werkzeug.exceptions import NotFound, HTTPException
        from flask import request
        
        if isinstance(e, NotFound):
            if '.well-known' in request.path or 'devtools' in request.path.lower():
                return '', 404
            return jsonify({'error': 'Not found'}), 404
        
        if isinstance(e, HTTPException):
            return jsonify({'error': e.description}), e.code
        
        logger.error("Unhandled exception: %s", e, exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(ui_bp)
    app.register_blueprint(ui_auth_bp)
    app.register_blueprint(reports_bp)

    # -----------------------------
    # Root route - redirect to login
    # -----------------------------
    @app.route("/")
    def index():
        # If user is logged in, go to dashboard; otherwise login
        if 'user_id' in session:
            return redirect(url_for('ui.dashboard'))
        return redirect(url_for('ui_auth.login'))

    @app.context_processor
    def inject_user():
        """Inject user context into templates"""
        user_name = session.get('full_name') or session.get('user_name') or session.get('username') or 'Guest'
        user_id = session.get('user_id')
        
        class UserProxy:
            """Simple proxy for user data with dict and attribute access"""
            def __init__(self, data):
                self._data = data
                for key, value in data.items():
                    setattr(self, key, value)
            
            def __getitem__(self, key):
                return self._data.get(key)
            
            def get(self, key, default=None):
                return self._data.get(key, default)
        
        user_data = {
            'id': user_id,
            'name': user_name,
            'username': session.get('username'),
            'role': session.get('role'),
            'is_super_admin': session.get('is_super_admin', False),
        }
        
        return {
            'current_user': UserProxy(user_data),
            'session': session,
            'get_all_users_list': get_all_users_with_details
        }

    @jwt.unauthorized_loader
    def _unauthorized(reason):
        return jsonify({'message': 'Unauthorized', 'reason': reason}), 401

    @jwt.invalid_token_loader
    def _invalid(reason):
        return jsonify({'message': 'Invalid token', 'reason': reason}), 401

    @app.get('/health')
    def health():
        return {'status': 'ok'}, 200

    @app.route('/api/docs')
    def api_docs():
        return redirect('https://petstore.swagger.io/?url=http://localhost:5003/static/swagger.json')

    @app.route('/api/openapi.json')
    def openapi_spec():
        from flask import send_from_directory
        return send_from_directory('static', 'swagger.json')

    @app.route('/favicon.ico')
    def favicon():
        return redirect(url_for('static', filename='favicon.svg'))

    return app
