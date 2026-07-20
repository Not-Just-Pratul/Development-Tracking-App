import pg8000.dbapi
import configparser
import os
import logging
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from queue import Queue, Empty
from typing import Optional, Dict, Any, List, Tuple, Union

# Production-grade database constants
DEFAULT_QUERY_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAYS = [0.5, 1.0, 1.5]  # seconds between retries

# Custom exceptions for better error handling
class DatabaseTimeoutError(Exception):
    """Raised when a database operation times out."""
    pass

class DatabaseConnectionError(Exception):
    """Raised when unable to establish or maintain database connection."""
    pass

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

def validate_config(config: configparser.ConfigParser) -> None:
    """Validate that all required configuration keys are present and valid."""
    required_keys = [
        ('DATABASE', 'HOST'),
        ('DATABASE', 'PORT'), 
        ('DATABASE', 'DBNAME'),
        ('DATABASE', 'USER'),
        ('DATABASE', 'PASSWORD'),
        ('FLASK', 'SECRET_KEY')
    ]
    
    missing_keys = []
    for section, key in required_keys:
        try:
            value = config.get(section, key)
            if not value or (key == 'SECRET_KEY' and len(value) < 20):
                missing_keys.append(f"{section}.{key}")
        except (configparser.NoSectionError, configparser.NoOptionError):
            missing_keys.append(f"{section}.{key}")
    
    if missing_keys:
        raise ValueError(f"Missing or invalid configuration keys: {missing_keys}")

class SimpleConnectionPool:
    """Enhanced connection pool for pg8000 with improved error handling and performance."""
    
    def __init__(self, minconn, maxconn, **kwargs):
        self.minconn = max(3, minconn)  # Minimum 3 connections
        self.maxconn = max(self.minconn, maxconn)
        self.kwargs = kwargs
        self._pool = Queue(maxsize=self.maxconn)
        self._lock = threading.RLock()
        self._created_connections = 0
        self._active_connections = 0
        
        # Pre-create minimum connections
        try:
            for _ in range(self.minconn):
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn)
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")

    def _create_connection(self):
        """Create a new database connection with enhanced error handling."""
        try:
            conn = pg8000.dbapi.connect(**self.kwargs)
            # Set connection properties for better performance
            cursor = conn.cursor()
            try:
                cursor.execute("SET statement_timeout = '30s'")
                cursor.execute("SET timezone = 'UTC'")
                cursor.execute("SET lock_timeout = '30s'")
                conn.commit()
            finally:
                cursor.close()
            
            with self._lock:
                self._created_connections += 1
            return conn
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            return None
    
    def _validate_connection(self, conn):
        """Validate that a connection is still usable."""
        try:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT 1")
                return True
            finally:
                cursor.close()
        except Exception:
            return False
    
    def getconn(self):
        """Get a connection from the pool with enhanced reliability."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Try to get existing connection
                try:
                    conn = self._pool.get_nowait()
                    # Validate connection before returning
                    if self._validate_connection(conn):
                        with self._lock:
                            self._active_connections += 1
                        return conn
                    else:
                        # Connection is bad, try to close it
                        try:
                            conn.close()
                        except:
                            pass
                        with self._lock:
                            self._created_connections -= 1
                        continue
                except Empty:
                    pass
                
                # Create new connection if under limit
                with self._lock:
                    if self._created_connections < self.maxconn:
                        conn = self._create_connection()
                        if conn:
                            self._active_connections += 1
                            return conn
                        else:
                            if attempt == max_retries - 1:
                                raise Exception("Failed to create database connection after multiple attempts")
                            time.sleep(0.1 * (attempt + 1))  # Reduced from 0.5
                            continue
                    else:
                        # Wait for a connection to be returned - increased timeout
                        try:
                            conn = self._pool.get(timeout=30.0)  # Increased from 5 to 30 seconds
                            if self._validate_connection(conn):
                                with self._lock:
                                    self._active_connections += 1
                                return conn
                            else:
                                try:
                                    conn.close()
                                except:
                                    pass
                                with self._lock:
                                    self._created_connections -= 1
                                continue
                        except Empty:
                            if attempt == max_retries - 1:
                                # Log pool statistics before raising error
                                logger.error(f"Connection pool exhausted: {self._created_connections}/{self.maxconn} connections, {self._active_connections} active")
                                raise Exception("Timeout waiting for database connection")
                            time.sleep(0.1 * (attempt + 1))  # Reduced from 0.5
                            continue
            except Exception as e:
                logger.error(f"Error getting connection (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))
        
        raise Exception("Failed to get database connection after all retries")
    
    def putconn(self, conn):
        """Return a connection to the pool."""
        try:
            with self._lock:
                self._active_connections = max(0, self._active_connections - 1)
            
            if self._validate_connection(conn):
                try:
                    # Use put with timeout instead of put_nowait to handle full pool better
                    self._pool.put(conn, block=True, timeout=1.0)
                except:
                    # Pool is full or timeout, close the connection
                    try:
                        conn.close()
                        with self._lock:
                            self._created_connections -= 1
                    except:
                        pass
            else:
                # Connection is bad, close it
                try:
                    conn.close()
                    with self._lock:
                        self._created_connections -= 1
                except:
                    pass
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
    
    def closeall(self):
        """Close all connections in the pool."""
        logger.info("Closing all database connections...")
        closed_count = 0
        while True:
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.close()
                    closed_count += 1
                except:
                    pass
            except Empty:
                break
        
        with self._lock:
            self._created_connections = 0
            self._active_connections = 0
        
        logger.info(f"Closed {closed_count} database connections")

class DatabaseManager:
    """Singleton database manager for development tracking application."""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def initialize(self, config_path='config.ini'):
        """Initialize database connection pool."""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            try:
                # Load configuration
                config = configparser.ConfigParser()
                config.read(config_path)
                
                # Validate configuration
                validate_config(config)
                
                # Create connection pool with optimized settings
                self.pool = SimpleConnectionPool(
                    minconn=10,
                    maxconn=150,
                    host=config.get('DATABASE', 'HOST'),
                    port=int(config.get('DATABASE', 'PORT')),
                    database=config.get('DATABASE', 'DBNAME'),
                    user=config.get('DATABASE', 'USER'),
                    password=config.get('DATABASE', 'PASSWORD')
                )
                
                self._initialized = True
                logger.info("Database manager initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize database manager: {e}")
                raise
    
    def get_connection(self):
        """Get a database connection from the pool."""
        if not self._initialized:
            raise Exception("Database manager not initialized")
        return self.pool.getconn()
    
    def return_connection(self, conn):
        """Return a database connection to the pool."""
        if not self._initialized:
            return
        try:
            self.pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
            try:
                conn.close()
            except:
                pass
    
    def get_pool_stats(self):
        """Get connection pool statistics for monitoring."""
        if not self._initialized:
            return {'status': 'not_initialized'}
        
        return {
            'created': self.pool._created_connections,
            'active': self.pool._active_connections,
            'max': self.pool.maxconn,
            'available': self.pool._created_connections - self.pool._active_connections
        }
    
    def close_all(self):
        """Close all database connections."""
        if self._initialized:
            try:
                self.pool.closeall()
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")
            finally:
                self._initialized = False

# Global database manager instance
db_manager = DatabaseManager()

@contextmanager
def get_db_connection_context():
    """Context manager for database connections."""
    conn = db_manager.get_connection()
    try:
        yield conn
    finally:
        db_manager.return_connection(conn)

def execute_query(query: str, params: Optional[tuple] = None, fetch: bool = False, commit: bool = True, timeout: int = DEFAULT_QUERY_TIMEOUT):
    """
    Execute a database query with automatic connection management, timeout protection, and retry logic.
    
    Args:
        query: SQL query string
        params: Query parameters tuple
        fetch: Whether to fetch and return results
        commit: Whether to commit the transaction
        timeout: Query timeout in seconds (default: 30s)
        
    Returns:
        Query results if fetch=True, otherwise row count
        
    Raises:
        DatabaseTimeoutError: If query exceeds timeout
        DatabaseConnectionError: If connection cannot be established
        Exception: For other database errors
    """
    last_error = None
    
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            with get_db_connection_context() as conn:
                cursor = conn.cursor()
                try:
                    # Set statement timeout for this query
                    if timeout:
                        cursor.execute(f"SET LOCAL statement_timeout = '{timeout}s'")
                    
                    # Execute the main query
                    start_time = time.time()
                    cursor.execute(query, params or ())
                    execution_time = time.time() - start_time
                    
                    # Log slow queries
                    if execution_time > 1.0:
                        logger.warning(f"Slow query detected ({execution_time:.2f}s): {query[:200]}")
                    
                    if commit and not fetch:
                        conn.commit()
                    
                    if fetch:
                        result = cursor.fetchall()
                        return result
                    
                    return cursor.rowcount
                    
                except pg8000.dbapi.DatabaseError as e:
                    conn.rollback()
                    error_msg = str(e).lower()
                    
                    # Check for timeout-related errors
                    if 'timeout' in error_msg or 'canceling statement' in error_msg:
                        logger.error(f"Query timeout after {timeout}s: {query[:200]}")
                        raise DatabaseTimeoutError(f"Query execution exceeded {timeout}s timeout")
                    
                    # Connection errors that should trigger retry
                    if attempt < MAX_RETRY_ATTEMPTS - 1 and any(err in error_msg for err in ['connection', 'network', 'server closed']):
                        delay = RETRY_DELAYS[attempt]
                        logger.warning(f"Database connection error (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}), retrying in {delay}s: {e}")
                        time.sleep(delay)
                        last_error = e
                        continue
                    
                    # Non-retryable errors
                    logger.error(f"Database error: {e}")
                    logger.error(f"Query: {query}")
                    logger.error(f"Params: {params}")
                    raise
                    
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Unexpected database error: {e}")
                    logger.error(f"Query: {query}")
                    logger.error(f"Params: {params}")
                    raise
                    
                finally:
                    cursor.close()
                    
        except (pg8000.dbapi.InterfaceError, pg8000.dbapi.OperationalError) as e:
            # Connection-level errors - retry
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Connection error (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}), retrying in {delay}s: {e}")
                time.sleep(delay)
                last_error = e
                continue
            else:
                logger.error(f"Failed to execute query after {MAX_RETRY_ATTEMPTS} attempts")
                raise DatabaseConnectionError(f"Could not establish database connection: {e}")
        
        # If we get here without continuing, the query succeeded
        break
    
    # If we exhausted all retries
    if last_error:
        raise DatabaseConnectionError(f"Failed after {MAX_RETRY_ATTEMPTS} attempts: {last_error}")

def get_schema_version():
    """Get the current schema version from the database."""
    try:
        result = execute_query(
            "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1",
            fetch=True
        )
        if result and isinstance(result, list) and len(result) > 0:
            return result[0][0]
        return 0
    except Exception as e:
        logger.error(f"Error getting schema version: {e}")
        return 0

def get_system_setting(key: str, default=None):
    """Get a system setting value."""
    try:
        result = execute_query(
            "SELECT setting_value, setting_type FROM system_settings WHERE setting_key = %s",
            (key,),
            fetch=True
        )
        if result and isinstance(result, list) and len(result) > 0:
            value, setting_type = result[0]
            
            # Convert value based on type
            if setting_type == 'boolean':
                return value.lower() == 'true'
            elif setting_type == 'integer':
                return int(value)
            else:
                return value
        
        return default
    except Exception as e:
        logger.error(f"Error getting system setting {key}: {e}")
        return default

def set_system_setting(key: str, value: Any, user_id: Optional[int] = None):
    """Set a system setting value."""
    try:
        # Check if setting exists
        exists = execute_query(
            "SELECT id, is_system FROM system_settings WHERE setting_key = %s",
            (key,),
            fetch=True
        )
        
        if exists and isinstance(exists, list) and len(exists) > 0 and exists[0][1]:  # is_system = True
            raise Exception(f"Cannot modify system setting: {key}")
        
        if exists:
            # Update existing setting
            execute_query(
                "UPDATE system_settings SET setting_value = %s, updated_by = %s WHERE setting_key = %s",
                (str(value), user_id, key),
                commit=True
            )
        else:
            # Insert new setting
            execute_query(
                """INSERT INTO system_settings (setting_key, setting_value, setting_type, updated_by) 
                   VALUES (%s, %s, 'string', %s)""",
                (key, str(value), user_id),
                commit=True
            )
        
        return True
    except Exception as e:
        logger.error(f"Error setting system setting {key}: {e}")
        raise
