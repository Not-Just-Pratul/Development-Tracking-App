import os
from configparser import ConfigParser


def read_config():
    """Read configuration from config.ini in the same directory as this script"""
    config = ConfigParser()
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"config.ini not found at {config_path}\n"
            "Please copy config.ini.example to config.ini and update the settings."
        )
    
    config.read(config_path)
    return config


class Config:
    config = read_config()
    
    # Read from config.ini or environment variables
    SECRET_KEY = os.getenv('SECRET_KEY', config.get('FLASK', 'SECRET_KEY', fallback='dev-key'))
    
    # Build database URI from config.ini
    db_host = config.get('DATABASE', 'HOST', fallback='localhost')
    db_port = config.get('DATABASE', 'PORT', fallback='5432')
    db_name = config.get('DATABASE', 'DBNAME', fallback='development_tracking')
    db_user = config.get('DATABASE', 'USER', fallback='postgres')
    db_password = config.get('DATABASE', 'PASSWORD', fallback='1234')
    
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 
        f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', '0') == '1'
    
    # Performance optimization settings
    SQLALCHEMY_RECORD_QUERIES = False  # Disable query recording in production
    
    # Connection pool settings to prevent timeout errors
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 50,              # Maximum number of connections to keep open (increased)
        'max_overflow': 100,          # Maximum overflow connections beyond pool_size (increased)
        'pool_timeout': 60,           # Seconds to wait before giving up on getting a connection
        'pool_recycle': 600,          # Recycle connections after 10 minutes (more aggressive)
        'pool_pre_ping': True,        # Verify connections before using them
        'echo_pool': False,           # Set to True for debugging pool issues
        'execution_options': {
            'isolation_level': 'READ COMMITTED'  # Faster than default SERIALIZABLE
        },
        'connect_args': {
            'connect_timeout': 10,    # Connection timeout
            'options': '-c statement_timeout=30000 -c lock_timeout=30000'  # 30 second statement/lock timeout
        }
    }
    
    JWT_SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)
    JWT_TOKEN_LOCATION = ['headers']  # Only look for JWT in headers, not cookies
    JWT_CSRF_CHECK_FORM = False  # Disable CSRF protection for JWT
    JWT_COOKIE_CSRF_PROTECT = False  # Disable CSRF for cookies
    
    SCHEMA_VERSION = config.getint('SCHEMA', 'VERSION', fallback=1)
