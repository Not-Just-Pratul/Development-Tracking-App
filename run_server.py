"""Development Tracking System - Server Launcher

Simple script to run the Flask application directly.
Works from any directory - uses relative paths automatically.
"""
import os
import sys
import shutil
from configparser import ConfigParser

# Add the current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Change to script directory to ensure relative paths work
os.chdir(script_dir)

# Read configuration
config = ConfigParser()
config_path = os.path.join(script_dir, 'config.ini')

# Auto-create config.ini from example if missing
if not os.path.exists(config_path):
    example_path = os.path.join(script_dir, 'config.ini.example')
    if os.path.exists(example_path):
        shutil.copy(example_path, config_path)
        print(f"[INFO] Created config.ini from template")
    else:
        print("=" * 60)
        print("ERROR: config.ini not found and config.ini.example missing!")
        print("Please create config.ini with your database credentials.")
        print("=" * 60)
        sys.exit(1)

config.read(config_path)

# Get Flask configuration - support PORT env var for hosting platforms
flask_host = config.get('FLASK', 'HOST', fallback='0.0.0.0')
flask_port = int(os.getenv('PORT', config.getint('FLASK', 'PORT', fallback=5003)))
flask_debug = config.getboolean('FLASK', 'DEBUG', fallback=False) or os.getenv('DEBUG', '0') == '1'

if __name__ == '__main__':
    print("=" * 60)
    print("Development Tracking System - Starting...")
    print("=" * 60)
    
    # Quick schema validation check - skip in production/Docker
    skip_validation = os.getenv('SKIP_SCHEMA_VALIDATION', '0') == '1' or os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    
    if not skip_validation:
        print("\n[CHECK] Checking database schema consistency...")
        try:
            from validate_schema import main as validate_schema
            if not validate_schema():
                print("\n[WARN] WARNING: Schema validation failed!")
                print("    The app may encounter runtime errors.")
                print("    Run 'python validate_schema.py' for details.")
                print("    Continuing anyway...")
        except Exception as e:
            print(f"[WARN] Could not validate schema: {e}")
            print("   Continuing without validation...")
    else:
        print("\n[INFO] Skipping schema validation in production mode")
    
    print(f"\n[OK] Server configuration:")
    print(f"  - Host: {flask_host}")
    print(f"  - Port: {flask_port}")
    print(f"  - Debug: {flask_debug}")
    print(f"\nPress CTRL+C to quit")
    print("=" * 60)
    
    try:
        # Import and create the app using the factory function
        from __init__ import create_app
        app = create_app()
        print(f"[OK] Application created successfully")
        print(f"[OK] Starting server on {flask_host}:{flask_port}")
        app.run(host=flask_host, port=flask_port, debug=flask_debug, threaded=True)
    except Exception as e:
        print(f"\n[ERROR] Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)