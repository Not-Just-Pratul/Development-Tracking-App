"""
Database Schema Validation Script
===================================
This script validates that SQLAlchemy models match the PostgreSQL database schema.
Run this after any schema changes to prevent runtime errors.

Usage:
    python validate_schema.py
"""

import psycopg2
from config import Config
from models import (
    Company, Location, Department, Designation, User,
    Project, Phase, Stage, Step
)
import sys


def get_db_columns(cursor, table_name):
    """Get all columns from a PostgreSQL table"""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    return {row[0]: {'type': row[1], 'nullable': row[2], 'default': row[3]} 
            for row in cursor.fetchall()}


def get_model_columns(model):
    """Get all columns from a SQLAlchemy model"""
    columns = {}
    for col_name, col in model.__table__.columns.items():
        columns[col_name] = {
            'type': str(col.type),
            'nullable': col.nullable,
            'primary_key': col.primary_key,
            'foreign_keys': len(col.foreign_keys) > 0
        }
    return columns


def validate_model(cursor, model, table_name=None):
    """Validate a single model against the database"""
    if table_name is None:
        table_name = model.__tablename__
    
    print(f"\nValidating {model.__name__} (table: {table_name})...")
    
    db_columns = get_db_columns(cursor, table_name)
    model_columns = get_model_columns(model)
    
    errors = []
    warnings = []
    
    # Check for columns in model but not in database
    for col_name in model_columns:
        if col_name not in db_columns:
            errors.append(f"  ❌ Column '{col_name}' exists in model but NOT in database table")
    
    # Check for columns in database but not in model
    for col_name in db_columns:
        if col_name not in model_columns:
            warnings.append(f"  ⚠️  Column '{col_name}' exists in database but NOT in model")
    
    if errors:
        print("  ERRORS:")
        for error in errors:
            print(error)
    
    if warnings:
        print("  WARNINGS:")
        for warning in warnings:
            print(warning)
    
    if not errors and not warnings:
        print("  ✅ Schema matches perfectly!")
    
    return len(errors) == 0


def main():
    """Main validation function"""
    print("=" * 70)
    print("DATABASE SCHEMA VALIDATION")
    print("=" * 70)
    
    # Connect to database
    try:
        config = Config()
        conn = psycopg2.connect(config.SQLALCHEMY_DATABASE_URI)
        cursor = conn.cursor()
        print(f"✅ Connected to database: {config.SQLALCHEMY_DATABASE_URI.split('@')[1]}")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False
    
    # Validate all models
    models_to_validate = [
        (Company, 'companies'),
        (Location, 'locations'),
        (Department, 'departments'),
        (Designation, 'designations'),
        (User, 'users'),
        (Project, 'projects'),
        (Phase, 'phases'),
        (Stage, 'stages'),
        (Step, 'steps'),
    ]
    
    all_valid = True
    for model, table_name in models_to_validate:
        if not validate_model(cursor, model, table_name):
            all_valid = False
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    if all_valid:
        print("✅ ALL MODELS VALIDATED SUCCESSFULLY!")
        print("=" * 70)
        return True
    else:
        print("❌ VALIDATION FAILED - Please fix schema mismatches above")
        print("=" * 70)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
