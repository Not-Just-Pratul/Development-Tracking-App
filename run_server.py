"""Development Tracking System - Server Launcher

Simple script to run the Flask application directly.
Works from any directory - uses relative paths automatically.
"""
import os
import sys
from configparser import ConfigParser

# Add the current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Change to script directory to ensure relative paths work
os.chdir(script_dir)

# Read configuration
config = ConfigParser()
config_path = os.path.join(script_dir, 'config.ini')

if not os.path.exists(config_path):
    print("=" * 60)
    print("ERROR: config.ini not found!")
    print("=" * 60)
    print()
    print("Please create config.ini from the template:")
    print()
    print("  Windows:   copy config.ini.example config.ini")
    print("  Linux/Mac: cp config.ini.example config.ini")
    print()
    print("Then edit config.ini with your database credentials.")
    print("=" * 60)
    sys.exit(1)

config.read(config_path)

# Get Flask configuration
flask_host = config.get('FLASK', 'HOST', fallback='127.0.0.1')
flask_port = config.getint('FLASK', 'PORT', fallback=5003)
flask_debug = config.getboolean('FLASK', 'DEBUG', fallback=False)

if __name__ == '__main__':
    print("=" * 60)
    print("Development Tracking System - Starting...")
    print("=" * 60)
    
    # Quick schema validation check
    print("\n🔍 Checking database schema consistency...")
    try:
        from validate_schema import main as validate_schema
        if not validate_schema():
            print("\n⚠️  WARNING: Schema validation failed!")
            print("    The app may encounter runtime errors.")
            print("    Run 'python validate_schema.py' for details.")
            response = input("\n    Continue anyway? (y/N): ")
            if response.lower() != 'y':
                print("Startup cancelled.")
                sys.exit(1)
    except Exception as e:
        print(f"⚠️  Could not validate schema: {e}")
        print("   Continuing without validation...")
    
    print(f"\n✅ Server configuration:")
    print(f"  - Local:   http://127.0.0.1:{flask_port}")
    print(f"  - Network: http://localhost:{flask_port}")
    print(f"\nPress CTRL+C to quit")
    print("=" * 60)
    
    try:
        # Import and create the app using the factory function
        from __init__ import create_app
        app = create_app()
        app.run(host=flask_host, port=flask_port, debug=flask_debug)
    except Exception as e:
        print(f"\nError starting server: {e}")
        import traceback
        traceback.print_exc()