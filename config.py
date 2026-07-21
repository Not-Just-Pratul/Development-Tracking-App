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
    
    # Detect serverless/cloud databases and adjust pool settings
    _db_url = SQLALCHEMY_DATABASE_URI or ''
    _is_serverless = False
    for _keyword in ['neon', 'supabase', 'railway', 'render', 'pooler']:
        if _keyword in _db_url:
            _is_serverless = True
            break
    
    if _is_serverless:
        pool_size = 5
        max_overflow = 10
        pool_recycle = 300
    else:
        pool_size = 20
        max_overflow = 40
        pool_recycle = 600
    
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': pool_size,
        'max_overflow': max_overflow,
        'pool_timeout': 30,
        'pool_recycle': pool_recycle,
        'pool_pre_ping': True,
        'echo_pool': False,
        'execution_options': {
            'isolation_level': 'READ COMMITTED'
        },
        'connect_args': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000 -c lock_timeout=30000'
        }
    }
    
    JWT_SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)
    JWT_TOKEN_LOCATION = ['headers']  # Only look for JWT in headers, not cookies
    JWT_CSRF_CHECK_FORM = False  # Disable CSRF protection for JWT
    JWT_COOKIE_CSRF_PROTECT = False  # Disable CSRF for cookies
    
    SCHEMA_VERSION = config.getint('SCHEMA', 'VERSION', fallback=1)
