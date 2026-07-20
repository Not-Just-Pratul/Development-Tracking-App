-- ============================================================================
-- Development Tracking Database Schema - Streamlined Single-File Setup
-- ============================================================================
-- Complete PostgreSQL schema for development tracking system
-- Version: 3.0 - Streamlined & Essential Only
-- Date: January 10, 2026
-- 
-- CRITICAL: SCHEMA CONSISTENCY
-- ------------------------------
-- This schema MUST match the SQLAlchemy models defined in models.py
-- Any changes to table columns must be reflected in models.py and vice versa.
--
-- To validate schema consistency after changes, run:
--     python validate_schema.py
--
-- REMOVED COLUMNS (as of Jan 2026):
-- ----------------------------------
-- - users.email (removed)
-- - users.phone (removed)  
-- - companies.email (removed)
-- - companies.phone (removed)
-- - locations.phone (removed)
--
-- If you add these back here, you MUST add them to models.py too!
-- 
-- INSTALLATION INSTRUCTIONS:
-- ============================================================================
-- This script is portable and works on any computer with PostgreSQL installed.
-- No hardcoded paths or computer-specific settings.
--
-- STEP 1: Create Database
-- -----------------------
-- Windows:
--   createdb -U postgres development_tracking
-- 
-- Linux/Mac:
--   createdb -U postgres development_tracking
--   OR
--   sudo -u postgres createdb development_tracking
--
-- STEP 2: Initialize Schema
-- -------------------------
-- Windows:
--   psql -U postgres -d development_tracking -f init.pgsql
--
-- Linux/Mac:
--   psql -U postgres -d development_tracking -f init.pgsql
--   OR
--   sudo -u postgres psql -d development_tracking -f init.pgsql
--
-- STEP 3: Verify Installation
-- ---------------------------
-- Connect to database:
--   psql -U postgres -d development_tracking
--
-- Check tables exist:
--   \dt
--
-- Should show: users, companies, locations, departments, designations, 
--              projects, phases, stages, steps, and more
--
-- Default Login Credentials:
-- -------------------------
--   Username: admin
--   Password: admin123
--   
--   IMPORTANT: Change this password after first login!
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- MIGRATION: Remove email and phone columns if they exist
-- ============================================================================
-- Drop indexes first
DROP INDEX IF EXISTS idx_users_email;

-- Drop columns from existing tables (for database upgrades)
ALTER TABLE IF EXISTS users DROP COLUMN IF EXISTS email;
ALTER TABLE IF EXISTS users DROP COLUMN IF EXISTS phone;
ALTER TABLE IF EXISTS companies DROP COLUMN IF EXISTS email;
ALTER TABLE IF EXISTS companies DROP COLUMN IF EXISTS phone;
ALTER TABLE IF EXISTS locations DROP COLUMN IF EXISTS phone;

-- Drop old columns from projects table if they exist
ALTER TABLE IF EXISTS projects DROP COLUMN IF EXISTS location;
ALTER TABLE IF EXISTS projects DROP COLUMN IF EXISTS department_name;
ALTER TABLE IF EXISTS projects DROP COLUMN IF EXISTS designation;

-- Update existing users to have created_date if null
UPDATE users SET created_date = CURRENT_TIMESTAMP WHERE created_date IS NULL;

-- ============================================================================
-- MASTER DATA TABLES
-- ============================================================================

-- Companies
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    company_code VARCHAR(20) UNIQUE NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- Locations
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    location_code VARCHAR(20) UNIQUE NOT NULL,
    location_name VARCHAR(200) NOT NULL,
    company_id INTEGER REFERENCES companies(id),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- Departments
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    department_code VARCHAR(20) UNIQUE NOT NULL,
    department_name VARCHAR(200) NOT NULL,
    parent_department_id INTEGER REFERENCES departments(id),
    location_id INTEGER REFERENCES locations(id),
    manager_user_id INTEGER,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- Designations
CREATE TABLE designations (
    id SERIAL PRIMARY KEY,
    designation_code VARCHAR(20) UNIQUE NOT NULL,
    designation_name VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER
);

-- ============================================================================
-- USER MANAGEMENT
-- ============================================================================

-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    is_super_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    department_id INTEGER REFERENCES departments(id),
    location_id INTEGER REFERENCES locations(id),
    employee_id VARCHAR(50),
    designation VARCHAR(100),
    date_of_joining DATE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    last_login TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    password_changed_date TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- APPLICATION MANAGEMENT
-- ============================================================================

-- Applications
CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    app_code VARCHAR(50) UNIQUE NOT NULL,
    app_name VARCHAR(200) NOT NULL,
    app_description TEXT,
    app_url VARCHAR(500),
    app_icon VARCHAR(255),
    app_category VARCHAR(100),
    requires_location BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    requires_authentication BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id)
);

-- User Application Access
CREATE TABLE user_applications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    can_access BOOLEAN DEFAULT TRUE,
    granted_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    last_accessed TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, application_id)
);

-- User Locations (Many-to-Many)
CREATE TABLE user_locations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    is_default BOOLEAN DEFAULT FALSE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, location_id)
);

-- User Companies (Many-to-Many)
CREATE TABLE user_companies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, company_id)
);

-- User Departments (Many-to-Many)
CREATE TABLE user_departments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, department_id)
);

-- User Permissions (for fine-grained access control)
CREATE TABLE user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_key VARCHAR(100) NOT NULL,
    granted BOOLEAN DEFAULT TRUE,
    granted_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(user_id, permission_key)
);

-- Available Permissions (permission definitions)
CREATE TABLE available_permissions (
    id SERIAL PRIMARY KEY,
    permission_key VARCHAR(100) UNIQUE NOT NULL,
    permission_name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Login History (audit trail for user logins)
CREATE TABLE login_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(80),
    login_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    failure_reason TEXT
);

-- ============================================================================
-- PROJECT TEMPLATES
-- ============================================================================

-- Project Templates
CREATE TABLE project_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    default_head_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    default_head_designation_id INTEGER REFERENCES designations(id) ON DELETE SET NULL,
    default_head_department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    default_location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    default_expected_duration_days INTEGER,
    default_customer_name VARCHAR(255),
    default_company_name VARCHAR(255),
    default_part_name VARCHAR(255),
    default_part_code VARCHAR(100),
    default_remarks TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

-- Template Phases
CREATE TABLE project_template_phases (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES project_templates(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    serial_number INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    default_responsible_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    default_responsible_department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    default_designation_id INTEGER REFERENCES designations(id) ON DELETE SET NULL,
    default_expected_duration_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Template Stages
CREATE TABLE project_template_stages (
    id SERIAL PRIMARY KEY,
    template_phase_id INTEGER NOT NULL REFERENCES project_template_phases(id) ON DELETE CASCADE,
    name VARCHAR(512) NOT NULL,
    serial_number INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    default_responsible_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    default_responsible_department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    default_designation_id INTEGER REFERENCES designations(id) ON DELETE SET NULL,
    default_expected_duration_days INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PROJECT TRACKING
-- ============================================================================

-- Projects
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    head_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    head_designation_id INTEGER REFERENCES designations(id) ON DELETE SET NULL,
    head_department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    department_id INTEGER REFERENCES departments(id),
    location_id INTEGER REFERENCES locations(id),
    customer_name VARCHAR(255),
    company_name VARCHAR(255),
    part_name VARCHAR(255),
    part_code VARCHAR(100),
    part_description TEXT,
    template_id INTEGER REFERENCES project_templates(id) ON DELETE SET NULL,
    auto_sync_with_template BOOLEAN DEFAULT TRUE NOT NULL,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_end_date DATE,
    actual_end_date DATE,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

-- Phases
CREATE TABLE phases (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    serial_number INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    responsible_user_id INTEGER REFERENCES users(id),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_end_date DATE,
    actual_end_date DATE,
    status VARCHAR(50) DEFAULT 'pending',
    attachment_filename VARCHAR(255),
    attachment_path VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Stages
CREATE TABLE stages (
    id SERIAL PRIMARY KEY,
    phase_id INTEGER NOT NULL REFERENCES phases(id) ON DELETE CASCADE,
    name VARCHAR(512) NOT NULL,
    serial_number INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    responsible_user_id INTEGER REFERENCES users(id),
    responsible_department_id INTEGER REFERENCES departments(id),
    responsible_designation_id INTEGER REFERENCES designations(id),
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expected_end_date DATE,
    actual_end_date DATE,
    status VARCHAR(50) DEFAULT 'pending',
    completed_by_id INTEGER REFERENCES users(id),
    attachment_filename VARCHAR(255),
    attachment_path VARCHAR(512),
    -- Enhanced scheduling fields
    duration_days INTEGER,
    max_duration_days INTEGER,
    depends_on_stage_id INTEGER REFERENCES stages(id) ON DELETE SET NULL,
    is_manual BOOLEAN DEFAULT FALSE,
    is_auto_complete BOOLEAN DEFAULT FALSE,
    can_start_without_previous_phase BOOLEAN DEFAULT FALSE,
    scheduling_type VARCHAR(50) DEFAULT 'sequential',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Steps
CREATE TABLE steps (
    id SERIAL PRIMARY KEY,
    stage_id INTEGER NOT NULL REFERENCES stages(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    expected_start_date DATE,
    expected_end_date DATE,
    actual_start_date DATE,
    actual_end_date DATE,
    responsible_user_id INTEGER REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'pending',
    attachment_filename VARCHAR(255),
    attachment_path VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- AUDIT & LOGGING
-- ============================================================================

-- Audit Logs
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(80),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INTEGER,
    details TEXT,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- System Settings
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string',
    is_system BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================================
-- INDEXES - Enhanced for Performance
-- ============================================================================

-- Users Table Indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_department ON users(department_id);
CREATE INDEX idx_users_location ON users(location_id);
CREATE INDEX idx_users_role ON users(role);

-- Projects Table Indexes
CREATE INDEX idx_projects_head_id ON projects(head_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_location ON projects(location_id);
CREATE INDEX idx_projects_template ON projects(template_id);
CREATE INDEX idx_projects_created_at ON projects(created_at);

-- Phases Table Indexes
CREATE INDEX idx_phases_project_id ON phases(project_id);
CREATE INDEX idx_phases_serial_number ON phases(project_id, serial_number);
CREATE INDEX idx_phases_responsible_user_id ON phases(responsible_user_id) WHERE responsible_user_id IS NOT NULL;

-- Stages Table Indexes (Critical for Performance)
CREATE INDEX idx_stages_phase_id ON stages(phase_id);
CREATE INDEX idx_stages_serial_number ON stages(phase_id, serial_number);
CREATE INDEX idx_stages_responsible_user_id ON stages(responsible_user_id) WHERE responsible_user_id IS NOT NULL;
CREATE INDEX idx_stages_expected_end_date ON stages(expected_end_date) WHERE expected_end_date IS NOT NULL;
CREATE INDEX idx_stages_actual_end_date ON stages(actual_end_date) WHERE actual_end_date IS NOT NULL;
CREATE INDEX idx_stages_completed_by_id ON stages(completed_by_id) WHERE completed_by_id IS NOT NULL;
CREATE INDEX idx_stages_department_id ON stages(responsible_department_id) WHERE responsible_department_id IS NOT NULL;
CREATE INDEX idx_stages_designation_id ON stages(responsible_designation_id) WHERE responsible_designation_id IS NOT NULL;

-- Enhanced scheduling indexes
CREATE INDEX idx_stages_depends_on_stage_id ON stages(depends_on_stage_id) WHERE depends_on_stage_id IS NOT NULL;
CREATE INDEX idx_stages_scheduling_type ON stages(scheduling_type);
CREATE INDEX idx_stages_is_manual ON stages(is_manual) WHERE is_manual = TRUE;
CREATE INDEX idx_stages_is_auto_complete ON stages(is_auto_complete) WHERE is_auto_complete = TRUE;
CREATE INDEX idx_stages_can_start_without_previous_phase ON stages(can_start_without_previous_phase) WHERE can_start_without_previous_phase = TRUE;

-- Composite indexes for common queries
CREATE INDEX idx_stages_overdue ON stages(expected_end_date, actual_end_date) 
    WHERE expected_end_date IS NOT NULL AND actual_end_date IS NULL;
CREATE INDEX idx_stages_unassigned ON stages(responsible_department_id, responsible_designation_id, actual_end_date)
    WHERE actual_end_date IS NULL;

-- Steps Table Indexes
CREATE INDEX idx_steps_stage_id ON steps(stage_id);
CREATE INDEX idx_steps_responsible_user_id ON steps(responsible_user_id) WHERE responsible_user_id IS NOT NULL;
CREATE INDEX idx_steps_expected_end_date ON steps(expected_end_date) WHERE expected_end_date IS NOT NULL;
CREATE INDEX idx_steps_status ON steps(status);
CREATE INDEX idx_steps_upcoming ON steps(expected_end_date, status) 
    WHERE expected_end_date IS NOT NULL AND status != 'completed';

-- Departments & Designations Indexes
CREATE INDEX idx_departments_is_active ON departments(is_active);
CREATE INDEX idx_departments_code ON departments(department_code);
CREATE INDEX idx_designations_is_active ON designations(is_active);
CREATE INDEX idx_designations_code ON designations(designation_code);

-- Locations & Companies Indexes
CREATE INDEX idx_locations_is_active ON locations(is_active);
CREATE INDEX idx_locations_code ON locations(location_code);
CREATE INDEX idx_companies_is_active ON companies(is_active);
CREATE INDEX idx_companies_code ON companies(company_code);

-- Project Templates Indexes
CREATE INDEX idx_project_templates_is_active ON project_templates(is_active);
CREATE INDEX idx_project_templates_created_at ON project_templates(created_at);
CREATE INDEX idx_template_phases_template_id ON project_template_phases(template_id);
CREATE INDEX idx_template_stages_phase_id ON project_template_stages(template_phase_id);

-- Audit & System Indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_date ON audit_logs(created_date);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_system_settings_key ON system_settings(setting_key);

-- Application & User Access Indexes
CREATE INDEX idx_applications_is_active ON applications(is_active);
CREATE INDEX idx_user_applications_user_id ON user_applications(user_id);
CREATE INDEX idx_user_locations_user_id ON user_locations(user_id);
CREATE INDEX idx_user_locations_location_id ON user_locations(location_id);
CREATE INDEX idx_user_companies_user_id ON user_companies(user_id);
CREATE INDEX idx_user_companies_company_id ON user_companies(company_id);
CREATE INDEX idx_user_departments_user_id ON user_departments(user_id);
CREATE INDEX idx_user_departments_department_id ON user_departments(department_id);
CREATE INDEX idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX idx_user_permissions_permission_key ON user_permissions(permission_key);
CREATE INDEX idx_available_permissions_key ON available_permissions(permission_key);
CREATE INDEX idx_login_history_user_id ON login_history(user_id);
CREATE INDEX idx_login_history_timestamp ON login_history(login_timestamp);

-- Analyze tables for query planner
ANALYZE companies;
ANALYZE locations;
ANALYZE departments;
ANALYZE designations;
ANALYZE users;
ANALYZE projects;
ANALYZE phases;
ANALYZE stages;
ANALYZE steps;

-- ============================================================================
-- COLUMN COMMENTS FOR ENHANCED SCHEDULING
-- ============================================================================

COMMENT ON COLUMN stages.duration_days IS 'Duration in days for this stage';
COMMENT ON COLUMN stages.max_duration_days IS 'Maximum allowed duration for manual stages';
COMMENT ON COLUMN stages.depends_on_stage_id IS 'ID of stage this stage depends on (custom dependency)';
COMMENT ON COLUMN stages.is_manual IS 'True if this is a manual stage with no automatic end date';
COMMENT ON COLUMN stages.is_auto_complete IS 'True if this stage auto-completes on project start';
COMMENT ON COLUMN stages.can_start_without_previous_phase IS 'True if this stage can start without previous phase completion';
COMMENT ON COLUMN stages.scheduling_type IS 'Type of scheduling: sequential, parallel, exception, manual, auto_complete, from_start, depends_on';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_phases_updated_at BEFORE UPDATE ON phases 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_stages_updated_at BEFORE UPDATE ON stages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_steps_updated_at BEFORE UPDATE ON steps 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_project_templates_updated_at BEFORE UPDATE ON project_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_project_template_phases_updated_at BEFORE UPDATE ON project_template_phases 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_project_template_stages_updated_at BEFORE UPDATE ON project_template_stages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Company
INSERT INTO companies (company_code, company_name, address, is_active)
VALUES ('MTPL', 'MTPL Software Suite', 'Head Office', TRUE)
ON CONFLICT (company_code) DO NOTHING;

-- Locations
INSERT INTO locations (location_code, location_name, company_id, city, state, country, is_active)
VALUES 
    ('PAL', 'Palwal', 1, 'Palwal', 'Haryana', 'India', TRUE)
ON CONFLICT (location_code) DO NOTHING;

-- Departments
INSERT INTO departments (department_code, department_name, location_id, description, is_active)
VALUES 
    ('COST', 'Costing Department', 1, 'Costing Department', TRUE),
    ('DIS', 'Dispatch', 1, 'Dispatch Department', TRUE),
    ('HR', 'Human Resources', 1, 'HR Department', TRUE),
    ('IT', 'Information Technology', 1, 'IT Department', TRUE),
    ('MNT', 'Machine Maintenance', 1, 'Machine Maintenance', TRUE),
    ('MR', 'Management Representative', 1, 'Management Representative', TRUE),
    ('MKT', 'Marketing', 1, 'Marketing Department', TRUE),
    ('MDI_MKT', 'MDI/Marketing', 1, 'MDI/Marketing', TRUE),
    ('NPD', 'New Product Development', 1, 'New Part Development', TRUE),
    ('PRD', 'Production', 1, 'Production Department', TRUE),
    ('PUR', 'Purchase', 1, 'Purchase Department', TRUE),
    ('QA', 'Quality Assurance', 1, 'Quality Assurance', TRUE),
    ('STR', 'Store', 1, 'Store Department', TRUE),
    ('TM', 'Tool Maintenance', 1, 'Tool Maintenance', TRUE),
    ('TOOL_ROOM', 'Tool Room', 1, 'Tool Room', TRUE)
ON CONFLICT (department_code) DO NOTHING;

-- Designations
INSERT INTO designations (designation_code, designation_name, is_active)
VALUES 
    ('BH', 'Business Head', TRUE),
    ('DSGN', 'Design', TRUE),
    ('DIR', 'Director', TRUE),
    ('Exec', 'Executive', TRUE),
    ('HOD', 'Head of Department', TRUE),
    ('I/C', 'In charge', TRUE),
    ('Insp.', 'Inspector', TRUE),
    ('MGR', 'Manager', TRUE),
    ('MD', 'Managing Director', TRUE),
    ('Optr.', 'Operator', TRUE),
    ('PH', 'Plant Head', TRUE),
    ('QA', 'Quality Assuarance', TRUE),
    ('SR. ENG', 'Senior Engineer', TRUE),
    ('Sup.', 'Supervisor', TRUE),
    ('TEC', 'Technician', TRUE)
ON CONFLICT (designation_code) DO NOTHING;

-- Admin User (password: admin123)
INSERT INTO users (username, full_name, password_hash, role, is_super_admin, is_active, department_id, location_id, designation, employee_id)
VALUES ('admin', 'System Administrator', 
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'admin', TRUE, TRUE, 1, 1, 'Administrator', 'EMP001')
ON CONFLICT (username) DO NOTHING;

-- Applications
INSERT INTO applications (app_code, app_name, app_description, app_url, app_icon, is_active, display_order, created_by)
VALUES 
    ('DEV_TRACKING', 'Development Tracking System', 'Track project development', '/projects', 'fas fa-tasks', TRUE, 1, 1),
    ('USER_MGMT', 'User Management', 'Manage users and permissions', '/admin/users', 'fas fa-users', TRUE, 2, 1),
    ('REPORTS', 'Reports & Analytics', 'Generate reports', '/reports', 'fas fa-chart-bar', TRUE, 3, 1)
ON CONFLICT (app_code) DO NOTHING;

-- Grant admin access to all applications
INSERT INTO user_applications (user_id, application_id, can_access, granted_by)
VALUES (1, 1, TRUE, 1), (1, 2, TRUE, 1), (1, 3, TRUE, 1);

-- Grant admin access to default location, company, and department
INSERT INTO user_locations (user_id, location_id) VALUES (1, 1);
INSERT INTO user_companies (user_id, company_id) VALUES (1, 1);
INSERT INTO user_departments (user_id, department_id) VALUES (1, 1);

-- System Settings
INSERT INTO system_settings (setting_key, setting_value, setting_type, is_system, description, updated_by) VALUES
('enable_audit_logs', 'true', 'boolean', TRUE, 'Enable system audit logging', 1),
('app_version', '1.0.0', 'string', TRUE, 'Application version', 1),
('schema_version', '1', 'integer', TRUE, 'Database schema version', 1);

-- ============================================================================
-- DEFAULT APQP TEMPLATE
-- ============================================================================

-- Clean up existing template data to prevent duplicates
DELETE FROM project_templates WHERE name = 'Default APQP Template';

-- APQP Template
INSERT INTO project_templates (name, description, default_expected_duration_days, default_location_id, is_active, created_by)
VALUES ('Default APQP Template', 'Standard 5-phase APQP process', 180, 1, TRUE, 1);

-- APQP Phases
INSERT INTO project_template_phases (template_id, name, serial_number, description) VALUES
(1, 'Phase-I (Plan & Define Program)', 1, 'Planning and definition'),
(1, 'Phase-II (Product Design & Development)', 2, 'Product design'),
(1, 'Phase-III (Process Design & Development)', 3, 'Process design'),
(1, 'Phase-IV (Product & Process Validation)', 4, 'Validation'),
(1, 'Phase-V (Feedback Assessment & Corrective Action)', 5, 'Feedback and corrective action');

-- Phase-I Stages (16 stages)
INSERT INTO project_template_stages (template_phase_id, name, serial_number) VALUES
(1, 'Receiving & Review of Enquiry along with Drawings/Reference sample, Indent, RFQ', 1),
(1, 'CFT Formation for conducting the activity', 2),
(1, 'Drawing Review', 3),
(1, 'Part Feasibility Assessment', 4),
(1, 'Technical Feasibility cum Risk Assessment Sheet', 5),
(1, 'Resorse Planning for development', 6),
(1, 'Quotation Submission to customer (business case to be add)', 7),
(1, 'Receipt of LOI/PO from Customer', 8),
(1, 'Customer specific requirement data', 9),
(1, 'Preparation Activity time plan.', 10),
(1, 'Prepare preliminary characteristics', 11),
(1, 'Prepare preliminary Process Flow Diagram (PFD)', 12),
(1, 'Bill of material (BOM) Preparation', 13),
(1, 'Spec Meting/ MOM with customer', 14),
(1, 'Update Past Defect History Sheet', 15),
(1, 'Review of 1st phase activity', 16);

-- Phase-II Stages (8 stages)
INSERT INTO project_template_stages (template_phase_id, name, serial_number) VALUES
(2, 'Resource requirement sheet(Man/Mchine/Method/Material) and Supplier development', 1),
(2, 'Tool/Insert/Gauge/Fixture/Panel checker development plan.', 2),
(2, 'Drawing issue or sharing Raw Material grade details with suppliers', 3),
(2, 'Preapre Primary Control plan', 4),
(2, 'Making proto samples', 5),
(2, 'Inspection of proto sample', 6),
(2, 'Submit to customer and feedback', 7),
(2, 'Review of 2nd phase activity', 8);

-- Phase-III Stages (13 stages)
INSERT INTO project_template_stages (template_phase_id, name, serial_number) VALUES
(3, 'Pre-Launch Process Flow Diagram', 1),
(3, 'Process Failure Mode & Effect Analysis (PFMEA).', 2),
(3, 'Tool & fixture Manufacturing status', 3),
(3, 'Pre-Launch Control Plan (if required)', 4),
(3, 'Operation Standard (IIS & PIS)', 5),
(3, 'Final Inspection Standard Preparation', 6),
(3, 'Packing Standard Signoff', 7),
(3, 'Sample Trial Run-Initial sample (T0,T1,……,TF)', 8),
(3, 'Sample Inspection Report Preparation & Sample Submission to Customers', 9),
(3, 'Pre-Launch Control Plan (Initial Control) if required.', 10),
(3, 'Product Development Problem History Updation', 11),
(3, 'Customer feed back', 12),
(3, 'Training to Operator / Supervisor for Product & Process', 13);

-- Phase-IV Stages (8 stages)
INSERT INTO project_template_stages (template_phase_id, name, serial_number) VALUES
(4, 'MSA Study', 1),
(4, 'Production trial run (Pilot Lot)', 2),
(4, 'Product & Process Audit', 3),
(4, 'Process Capability Study.', 4),
(4, 'Testing & Report Preparation', 5),
(4, 'Pilot Lot Inspection', 6),
(4, 'Updation of PFD/PFMEA/Control Plan/WI/Prelaunch)etc.', 7),
(4, 'Pilot Lot & PPAP Submission to Customer', 8);

-- Phase-V Stages (5 stages)
INSERT INTO project_template_stages (template_phase_id, name, serial_number) VALUES
(5, 'SOP at customer end (Monitor 3 consequitive lots end to end) & Formal information of lot status needs to be share with top management.', 1),
(5, 'Customer Approval', 2),
(5, 'Product development completion with sign off.', 3),
(5, 'Feed Back Analysis & Corrective Analysis', 4),
(5, 'Handover all the documents to concern department.', 5);

-- ============================================================================
-- EXECUTE DEPARTMENT ASSIGNMENT FOR TEMPLATE STAGES
-- ============================================================================

-- ============================================================================
-- ENHANCED SCHEDULING CONFIGURATION FOR TEMPLATE STAGES
-- ============================================================================

DO $$
DECLARE
    dept_npd INTEGER;
    dept_qa INTEGER;
    dept_costing INTEGER;
    dept_tool_room INTEGER;
    dept_prd INTEGER;
    dept_hr INTEGER;
    desig_manager INTEGER;
    desig_hod INTEGER;
    desig_design INTEGER;
BEGIN
    -- Get department IDs
    SELECT id INTO dept_npd FROM departments WHERE department_code = 'NPD';
    SELECT id INTO dept_qa FROM departments WHERE department_code = 'QA';
    SELECT id INTO dept_costing FROM departments WHERE department_code = 'COST';
    SELECT id INTO dept_tool_room FROM departments WHERE department_code = 'TOOL_ROOM';
    SELECT id INTO dept_prd FROM departments WHERE department_code = 'PRD';
    SELECT id INTO dept_hr FROM departments WHERE department_code = 'HR';
    
    -- Get designation IDs
    SELECT id INTO desig_manager FROM designations WHERE designation_code = 'MGR';
    SELECT id INTO desig_hod FROM designations WHERE designation_code = 'HOD';
    SELECT id INTO desig_design FROM designations WHERE designation_code = 'DSGN';

    -- ========================================================================
    -- PHASE 1: Enhanced scheduling configuration
    -- ========================================================================
    
    -- Stage 1: 1 day after start
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 1;

    -- Stage 2: duration 1 day from step 1
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 2;

    -- Stage 3: manual (max 2 weeks)
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 14
    WHERE template_phase_id = 1 AND serial_number = 3;

    -- Stage 4: duration 1 day from step 3
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 4;

    -- Stage 5: dur. 2 day from step 4
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 1 AND serial_number = 5;

    -- Stage 6: duration 1 day from step 5
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 6;

    -- Stage 7: 1 WEEK FROM START
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_costing,
        default_designation_id = desig_hod,
        default_expected_duration_days = 7
    WHERE template_phase_id = 1 AND serial_number = 7;

    -- Stage 8: NO DATE(EXCEPTION)(ANOTHER phases SHOULD START WITHOUT completing it)
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_costing,
        default_designation_id = desig_hod,
        default_expected_duration_days = NULL
    WHERE template_phase_id = 1 AND serial_number = 8;

    -- Stage 9: duration 1 day FROM STEP 6
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 9;

    -- Stage 10: duration 1 day from step 9 (Preparation Activity time plan - NO LONGER AUTO-COMPLETE)
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 10;

    -- Stage 11: duraction 1 day from step 9
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 11;

    -- Stage 12: dur 2 day from step 11
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 1 AND serial_number = 12;

    -- Stage 13: dur 1 day from step 12
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 13;

    -- Stage 14: dur 1 day from step 13
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 14;

    -- Stage 15: dur 1 day from step 14
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 15;

    -- Stage 16: dur 1 day from step 15
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 1 AND serial_number = 16;

    -- ========================================================================
    -- PHASE 2: Enhanced scheduling configuration
    -- ========================================================================
    
    -- Stage 17: dur 1 day from step 16
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 2 AND serial_number = 1;

    -- Stage 18: dur 4 day from step 17
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_tool_room,
        default_designation_id = desig_hod,
        default_expected_duration_days = 4
    WHERE template_phase_id = 2 AND serial_number = 2;

    -- Stage 19: dur 1 day from step 18
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_design,
        default_expected_duration_days = 1
    WHERE template_phase_id = 2 AND serial_number = 3;

    -- Stage 20: dur 2 day from step 19
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 2 AND serial_number = 4;

    -- Stage 21: Manual (max 2 weeks after step 20)
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 14
    WHERE template_phase_id = 2 AND serial_number = 5;

    -- Stage 22: dur 2 day from step 21
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 2 AND serial_number = 6;

    -- Stage 23: dur 1 day from step 22
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 2 AND serial_number = 7;

    -- Stage 24: dur 1 day from step 23
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 2 AND serial_number = 8;

    -- ========================================================================
    -- PHASE 3: Enhanced scheduling configuration
    -- ========================================================================
    
    -- Stage 25: dur 1 day from step 24
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 3 AND serial_number = 1;

    -- Stage 26: dur 2 days from step 25
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 3 AND serial_number = 2;

    -- Stage 27: As per tool dev, plan (60 days)
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_tool_room,
        default_designation_id = desig_hod,
        default_expected_duration_days = 60
    WHERE template_phase_id = 3 AND serial_number = 3;

    -- Continue with remaining Phase 3 stages (28-37)
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 1
    WHERE template_phase_id = 3 AND serial_number IN (4, 5, 6, 7, 9, 10);

    -- Stage 32: dur 7 day from step 31
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_prd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 7
    WHERE template_phase_id = 3 AND serial_number = 8;

    -- Stages 34-37: NPD responsibility
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 3 AND serial_number IN (11, 12, 13);

    -- ========================================================================
    -- PHASE 4: Enhanced scheduling configuration
    -- ========================================================================
    
    -- Phase 4 stages (38-45): QA and NPD mix
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_qa,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 4 AND serial_number IN (1, 3, 4, 5, 6, 7);

    -- Production trial run and PPAP submission
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_prd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 4
    WHERE template_phase_id = 4 AND serial_number IN (2, 8);

    -- ========================================================================
    -- PHASE 5: Enhanced scheduling configuration
    -- ========================================================================
    
    -- Stage 46: dur 15 days from step 45
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 15
    WHERE template_phase_id = 5 AND serial_number = 1;

    -- Remaining Phase 5 stages
    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 4
    WHERE template_phase_id = 5 AND serial_number = 2;

    UPDATE project_template_stages 
    SET default_responsible_department_id = dept_npd,
        default_designation_id = desig_hod,
        default_expected_duration_days = 2
    WHERE template_phase_id = 5 AND serial_number IN (3, 4, 5);

END $$;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres;