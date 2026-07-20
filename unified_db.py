"""
Unified Database Module
Provides database connection and utility functions
"""
from database import db_manager
from models import User, Company, Location, Department, Designation


def get_unified_db_connection():
    """Get database connection from the pool"""
    return db_manager.get_connection()


def get_all_users():
    """Get all users from the database"""
    try:
        users = User.query.all()
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        return []


def get_all_users_with_details():
    """Get all users with full details"""
    try:
        users = User.query.all()
        return users
    except Exception as e:
        print(f"Error getting users with details: {e}")
        return []


def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        return User.query.get(user_id)
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None


def get_all_active_locations():
    """Get all active locations"""
    try:
        locations = Location.query.filter_by(is_active=True).all()
        return locations
    except Exception as e:
        print(f"Error getting locations: {e}")
        return []


def get_all_active_companies():
    """Get all active companies"""
    try:
        companies = Company.query.filter_by(is_active=True).all()
        return companies
    except Exception as e:
        print(f"Error getting companies: {e}")
        return []


def get_all_active_departments():
    """Get all active departments"""
    try:
        departments = Department.query.filter_by(is_active=True).all()
        return departments
    except Exception as e:
        print(f"Error getting departments: {e}")
        return []


def get_all_active_designations():
    """Get all active designations"""
    try:
        designations = Designation.query.filter_by(is_active=True).all()
        return designations
    except Exception as e:
        print(f"Error getting designations: {e}")
        return []
