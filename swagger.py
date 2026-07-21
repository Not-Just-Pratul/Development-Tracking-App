"""
Swagger/OpenAPI documentation for Development Tracking System.
Access at /api/docs when running the application.
"""
from flask import Flask
from flask_swagger_swagger_ui import get_swaggerui_blueprint
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
import json


def create_swagger_blueprint(app: Flask) -> Flask:
    """Initialize Swagger UI and OpenAPI spec for the app."""
    
    # Create OpenAPI spec
    spec = APISpec(
        title="Development Tracking System API",
        version="1.0.0",
        openapi_version="3.0.2",
        info={
            "description": "REST API for APQP project management with role-based access control",
            "contact": {"name": "Support", "email": "support@example.com"},
        },
        servers=[
            {"url": "http://localhost:5003", "description": "Development server"}
        ],
        plugins=[MarshmallowPlugin()],
    )
    
    # Store spec in app config
    app.config['API_SPEC'] = spec
    
    # Swagger UI blueprint
    swagger_ui_bp = get_swaggerui_blueprint(
        base_url='/api/docs',
        api_url='/api/openapi.json',
        config={
            'app_name': "Development Tracking System API",
            'docExpansion': 'list',
            'defaultModelsExpandDepth': 2,
            'defaultModelExpandDepth': 2,
        }
    )
    
    app.register_blueprint(swagger_ui_bp)
    
    @app.route('/api/openapi.json')
    def openapi_spec():
        """Serve OpenAPI specification as JSON."""
        return json.dumps(spec.to_dict())
    
    return app
