#!/usr/bin/env python3
"""
Development Tracking System - Setup Script
Automates initial setup on a new computer
"""
import os
import sys
import shutil
from configparser import ConfigParser


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_step(number, text):
    """Print formatted step"""
    print(f"\n[{number}] {text}")


def check_python_version():
    """Ensure Python version is 3.7+"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required.")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def setup_config_file():
    """Create config.ini from template if it doesn't exist"""
    if os.path.exists('config.ini'):
        print("✅ config.ini already exists")
        return True
    
    if not os.path.exists('config.ini.example'):
        print("❌ Error: config.ini.example not found")
        return False
    
    shutil.copy('config.ini.example', 'config.ini')
    print("✅ Created config.ini from template")
    print("   ⚠️  IMPORTANT: Edit config.ini and update:")
    print("      - DATABASE PASSWORD")
    print("      - SECRET_KEY (change to a random string)")
    return True


def check_postgresql():
    """Check if PostgreSQL is accessible"""
    import subprocess
    
    try:
        # Try to run psql --version
        result = subprocess.run(['psql', '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ PostgreSQL found: {version}")
            return True
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"⚠️  Error checking PostgreSQL: {e}")
    
    print("❌ PostgreSQL not found in PATH")
    print("   Please install PostgreSQL and ensure it's in your system PATH")
    return False


def create_directories():
    """Create necessary directories"""
    directories = [
        'uploads',
        'uploads/stage_attachments',
        'uploads/step_attachments'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ Created upload directories")


def check_requirements():
    """Check if requirements.txt exists"""
    if not os.path.exists('requirements.txt'):
        print("❌ Error: requirements.txt not found")
        return False
    
    print("✅ requirements.txt found")
    return True


def install_packages():
    """Install Python packages"""
    import subprocess
    
    response = input("\n   Install Python packages now? (y/N): ").strip().lower()
    if response != 'y':
        print("⏭️  Skipping package installation")
        print("   Run manually: pip install -r requirements.txt")
        return
    
    print("\n   Installing packages (this may take a few minutes)...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                      check=True)
        print("✅ Packages installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing packages: {e}")
        print("   Run manually: pip install -r requirements.txt")


def show_database_setup():
    """Show database setup instructions"""
    print_step("DATABASE SETUP", "Create and initialize the database")
    print("\n   Run these commands in your terminal:\n")
    print("   1. Create database:")
    print("      createdb -U postgres development_tracking")
    print()
    print("   2. Initialize schema:")
    print("      psql -U postgres -d development_tracking -f init.pgsql")
    print()
    print("   Note: You'll need your PostgreSQL password")


def show_next_steps():
    """Show what to do next"""
    print_header("SETUP COMPLETE!")
    print("\n📋 Next Steps:\n")
    print("1. Edit config.ini:")
    print("   - Set your PostgreSQL password")
    print("   - Change SECRET_KEY to a random string")
    print()
    print("2. Create the database:")
    print("   createdb -U postgres development_tracking")
    print()
    print("3. Initialize database schema:")
    print("   psql -U postgres -d development_tracking -f init.pgsql")
    print()
    print("4. Start the server:")
    print("   python run_server.py")
    print()
    print("5. Open browser:")
    print("   http://localhost:5003")
    print()
    print("6. Login:")
    print("   Username: admin")
    print("   Password: admin123")
    print()
    print("⚠️  IMPORTANT: Change admin password after first login!")
    print()


def main():
    """Main setup function"""
    print_header("Development Tracking System - Setup Wizard")
    
    print_step(1, "Checking Python version...")
    check_python_version()
    
    print_step(2, "Checking PostgreSQL...")
    pg_found = check_postgresql()
    if not pg_found:
        print("\n⚠️  Warning: PostgreSQL not detected")
        print("   Install PostgreSQL before proceeding with database setup")
    
    print_step(3, "Creating configuration file...")
    if not setup_config_file():
        print("❌ Setup failed: Could not create config.ini")
        sys.exit(1)
    
    print_step(4, "Creating directories...")
    create_directories()
    
    print_step(5, "Checking requirements...")
    if not check_requirements():
        print("❌ Setup failed: requirements.txt not found")
        sys.exit(1)
    
    print_step(6, "Installing Python packages...")
    install_packages()
    
    show_next_steps()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
