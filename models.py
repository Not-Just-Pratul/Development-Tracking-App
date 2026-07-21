from __init__ import db
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.orm import relationship
from sqlalchemy import event


# APQP Process - Phases and Stages
PHASE_STAGE_STRUCTURE = [
    {
        'name': 'Phase-I (Plan & Define Program)',
        'stages': [
            'Receiving & Review of Enquiry along with Drawings/Reference sample, Indent, RFQ',
            'CFT Formation for conducting the activity',
            'Drawing Review',
            'Part Feasibility Assessment',
            'Technical Feasibility cum Risk Assessment Sheet',
            'Resorse Planning for development',
            'Quotation Submission to customer (business case to be add)',
            'Receipt of LOI/PO from Customer',
            'Customer specific requirement data',
            'Preparation Activity time plan',
            'Prepare preliminary characteristics',
            'Prepare preliminary Process Flow Diagram (PFD)',
            'Bill of material (BOM) Preparation',
            'Spec Meting/ MOM with customer',
            'Update Past Defect History Sheet',
            'Review of 1st phase activity',
        ]
    },
    {
        'name': 'Phase-II (Product Design & Development)',
        'stages': [
            'Resource requirement sheet (Man/Machine/Method/Material) and Supplier development',
            'Tool/Insert/Gauge/Fixture/Panel checker development plan',
            'Drawing issue or sharing Raw Material grade details with suppliers',
            'Prepare Primary Control plan',
            'Making proto samples',
            'Inspection of proto sample',
            'Submit to customer and feedback',
            'Review of 2nd phase activity',
        ]
    },
    {
        'name': 'Phase-III (Process Design & Development)',
        'stages': [
            'Pre-Launch Process Flow Diagram',
            'Process Failure Mode & Effect Analysis (PFMEA)',
            'Tool & fixture Manufacturing status',
            'Pre-Launch Control Plan (if required)',
            'Operation Standard (IIS & FIS)',
            'Final Inspection Standard Preparation',
            'Packing Standard Signoff',
            'Sample Trial Run-Initial sample (T0, T1, ....., TF)',
            'Sample Inspection Report Preparation & Sample Submission to Customers',
            'Pre-Launch Control Plan (Initial Control) if required',
            'Product Development Problem History Updation',
            'Customer feed back',
            'Training to Operator / Supervisor for Product & Process',
        ]
    },
    {
        'name': 'Phase-IV (Product & Process Validation)',
        'stages': [
            'MSA Study',
            'Production trial run (Pilot Lot)',
            'Product & Process Audit',
            'Process Capability Study',
            'Testing & Report Preparation',
            'Pilot Lot Inspection',
            'Updation of PFD/PFMEA / Control Plan/WI/Prelaunchsheet',
            'Pilot Lot & PPAP Submission to Customer',
        ]
    },
    {
        'name': 'Phase-V (Feedback Assessment & Corrective Action)',
        'stages': [
            'SOP at customer end (Monitor 3 consecutive lots and to end) & Formal information of lot status needs to be share with top management',
            'Customer Approval',
            'Product development completion with sign off',
            'Feed Back Analysis & Corrective Analysis',
            'Handover all product related concern document',
        ]
    },
]

# Enhanced scheduling configuration based on user requirements
ENHANCED_STAGE_SCHEDULING = {
    1: [  # Phase 1
        {'duration': 1, 'type': 'sequential', 'description': '1 day after start'},
        {'duration': 1, 'type': 'sequential', 'description': 'duration 1 day from step 1'},
        {'duration': 14, 'type': 'manual', 'max_duration': 14, 'description': 'manual (max 2 weeks)'},
        {'duration': 1, 'type': 'sequential', 'description': 'duration 1 day from step 3'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur. 2 day from step 4'},
        {'duration': 1, 'type': 'sequential', 'description': 'duration 1 day from step 5'},
        {'duration': 7, 'type': 'from_start', 'description': '1 WEEK FROM START'},
        {'duration': None, 'type': 'exception', 'can_start_without_previous_phase': True, 'description': 'NO DATE(EXCEPTION)(ANOTHER phases SHOULD START WITHOUT completing it)'},
        {'duration': 1, 'type': 'depends_on', 'depends_on_stage': 6, 'description': 'duration 1 day FROM STEP 6'},
        {'duration': 1, 'type': 'depends_on', 'depends_on_stage': 9, 'description': 'duration 1 day from step 9 (Preparation Activity time plan)'},
        {'duration': 1, 'type': 'depends_on', 'depends_on_stage': 9, 'description': 'duraction 1 day from step 9'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 11'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 12'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 13'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 14'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 15'},
    ],
    2: [  # Phase 2
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 16'},
        {'duration': 4, 'type': 'sequential', 'description': 'dur 4 day from step 17'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 18'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 19'},
        {'duration': 14, 'type': 'manual', 'max_duration': 14, 'description': 'Manual (max 2 weeks after step 20)'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 21'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 22'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 23'},
    ],
    3: [  # Phase 3
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 24'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 days from step 25'},
        {'duration': 60, 'type': 'manual', 'max_duration': 60, 'description': 'As per tool dev, plan (60 days)'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 27'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 28'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 29'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 30'},
        {'duration': 7, 'type': 'sequential', 'description': 'dur 7 day from step 31'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 32'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 33'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 34'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 35'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 36'},
    ],
    4: [  # Phase 4
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 37'},
        {'duration': 4, 'type': 'sequential', 'description': 'dur 4 day from step 38'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 39'},
        {'duration': 4, 'type': 'sequential', 'description': 'dur 4 day from step 40'},
        {'duration': 4, 'type': 'sequential', 'description': 'dur 4 day from step 41'},
        {'duration': 1, 'type': 'sequential', 'description': 'dur 1 day from step 42'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 43'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 day from step 44'},
    ],
    5: [  # Phase 5
        {'duration': 15, 'type': 'sequential', 'description': 'dur 15 days from step 45'},
        {'duration': 4, 'type': 'sequential', 'description': 'dur 4 days from step 46'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 days from step 47'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 days from step 48'},
        {'duration': 2, 'type': 'sequential', 'description': 'dur 2 days from step 49'},
    ]
}

# Default responsible departments for each stage (based on project requirements from image)
# Maps to department codes: NPD = New Part Development (Dev), QA = Quality Assurance (Quality),
# COST = Costing Department (Costing DEP), TOOL_ROOM = Tool Room, PRD = Production, HR = Human Resources
PHASE_STAGE_DEFAULT_DEPARTMENTS = {
    1: [
        'NPD',           # 1. Receiving & Review of Enquiry along with Drawings (Dev)
        'NPD',           # 2. CFT Formation for conducting the activity (Dev)
        'NPD',           # 3. Drawing Review (Dev)
        'NPD',           # 4. Part Feasibility Assessment (Dev)
        'NPD',           # 5. Technical Feasibility cum Risk Assessment Sheet (Dev)
        'NPD',           # 6. Resource Planning for development (Dev)
        'COST',       # 7. Quotation Submission to customer (Costing DEP)
        'COST',       # 8. Receipt of LOI/PO from Customer (Costing DEP)
        'NPD',           # 9. Customer specific requirement data (Dev)
        'NPD',           #10. Preparation Activity time plan (Dev)
        'QA',            #11. Prepare preliminary characteristics (Quality)
        'NPD',           #12. Prepare preliminary Process Flow Diagram (Dev)
        'NPD',           #13. Bill of material (BOM) Preparation (Dev)
        'NPD',           #14. Spec Meeting / MOM with customer (Dev)
        'QA',            #15. Update Past Defect History Sheet (quality)
        'NPD',           #16. Review of 1st phase activity (Dev)
    ],
    2: [
        'NPD',           #17. Resource requirement sheet (Man/Machine/Method/Material) and Supplier development (dev)
        'NPD',           #18. Tool/Insert/Gauge/Fixture/Panel checker development plan (dev)
        'NPD',           #19. Drawing issue or sharing Raw Material grade details with suppliers (dev)
        'QA',            #20. Prepare Primary Control plan (Quality)
        'NPD',           #21. Making proto samples (dev)
        'QA',            #22. Inspection of proto sample (Quality)
        'NPD',           #23. Submit to customer and feedback (dev)
        'NPD',           #24. Review of 2nd phase activity (dev)
    ],
    3: [
        'QA',            #25. Pre-Launch Process Flow Diagram (Quality)
        'QA',            #26. Process Failure Mode & Effect Analysis (PFMEA) (Quality)
        'NPD',           #27. Tool & fixture Manufacturing status (Dev/ TR)
        'QA',            #28. Pre-Launch Control Plan (if required) (Quality)
        'QA',            #29. Operation Standard (IIS & FIS) (Quality)
        'QA',            #30. Final Inspection Standard Preparation (Quality)
        'QA',            #31. Packing Standard Signoff (Dev/ QA/ Dis)
        'NPD',           #32. Sample Trial Run-Initial sample (T0, T1, ....., TF) (Dev/ QA)
        'NPD',           #33. Sample Inspection Report Preparation & Sample Submission to Customers (Dev/ QA)
        'QA',            #34. Pre-Launch Control Plan (Initial Control) if required (Quality)
        'QA',            #35. Product Development Problem History Updation (Quality)
        'NPD',           #36. Customer feed back (Dev)
        'NPD',           #37. Training to Operator / Supervisor for Product & Process (Dev/ QA/ HR/ Prod)
    ],
    4: [
        'QA',            #38. MSA Study (Quality)
        'NPD',           #39. Production trial run (Pilot Lot) (Dev)
        'QA',            #40. Product & Process Audit (Quality)
        'QA',            #41. Process Capability Study (Quality)
        'QA',            #42. Testing & Report Preparation (Quality)
        'QA',            #43. Pilot Lot Inspection (Quality)
        'QA',            #44. Updation of PFD/PFMEA / Control Plan/WI/Prelaunchsheet (Quality)
        'NPD',           #45. Pilot Lot & PPAP Submission to Customer (Dev/ QA)
    ],
    5: [
        'NPD',           #46. SOP at customer end (Monitor 3 consecutive lots and to end) (Dev/ QA)
        'NPD',           #47. Customer Approval (Dev)
        'NPD',           #48. Product development completion with sign off (Dev)
        'NPD',           #49. Feed Back Analysis & Corrective Analysis (Dev/ QA)
        'NPD',           #50. Handover all product related concern document (Dev)
    ],
}

# Default designations for each stage (based on project requirements)
PHASE_STAGE_DEFAULT_DESIGNATIONS = {
    1: [
        'Head of Department',    # 1. Receiving & Review
        'Head of Department',    # 2. CFT Formation
        'Head of Department',    # 3. Drawing Review
        'Head of Department',    # 4. Part Feasibility Assessment
        'Head of Department',    # 5. Technical Feasibility
        'Head of Department',    # 6. Resource Planning
        'Head of Department',    # 7. Quotation Submission
        'Head of Department',    # 8. Receipt of LOI/PO
        'Head of Department',    # 9. Customer specific requirement data
        'Head of Department',    #10. Preparation Activity time plan
        'Head of Department',    #11. Prepare preliminary characteristics
        'Head of Department',    #12. Prepare PFD
        'Head of Department',    #13. BOM Preparation
        'Head of Department',    #14. Spec Meeting / MOM
        'Head of Department',    #15. Update Past Defect History Sheet
        'Head of Department',    #16. Review of 1st phase activity
    ],
    2: [
        'Head of Department',    #17. Resource requirement
        'Head of Department',    #18. Tool/Insert/Gauge/Fixture development plan
        'Head of Department',    #19. Drawing issue or sharing Raw Material
        'Head of Department',    #20. Prepare Primary Control plan
        'Design',                #21. Making proto samples
        'Head of Department',    #22. Inspection of proto sample
        'Head of Department',    #23. Submit to customer and feedback
        'Head of Department',    #24. Review of 2nd phase activity
    ],
    3: [
        'Head of Department',    #25. Pre-Launch Process Flow Diagram
        'Head of Department',    #26. Process Failure Mode & Effect Analysis
        'Head of Department',    #27. Tool & fixture Manufacturing status
        'Head of Department',    #28. Pre-Launch Control Plan (if required)
        'Head of Department',    #29. Operation Standard (IIS & FIS)
        'Head of Department',    #30. Final Inspection Standard Preparation
        'Head of Department',    #31. Packing Standard Signoff
        'Head of Department',    #32. Sample Trial Run
        'Head of Department',    #33. Sample Inspection Report & Submission
        'Head of Department',    #34. Pre-Launch Control Plan (Initial Control)
        'Head of Department',    #35. Product Development Problem History Updation
        'Head of Department',    #36. Customer feed back
        'Head of Department',    #37. Training to Operator/Supervisor
    ],
    4: [
        'Head of Department',    #38. MSA Study
        'Head of Department',    #39. Production trial run (Pilot Lot)
        'Head of Department',    #40. Product & Process Audit
        'Head of Department',    #41. Process Capability Study
        'Head of Department',    #42. Testing & Report Preparation
        'Head of Department',    #43. Pilot Lot Inspection
        'Head of Department',    #44. Updation of PFD/PFMEA/Control Plan
        'Head of Department',    #45. Pilot Lot & PPAP Submission
    ],
    5: [
        'Head of Department',    #46. SOP at customer end
        'Head of Department',    #47. Customer Approval
        'Head of Department',    #48. Product development completion
        'Head of Department',    #49. Feed Back Analysis
        'Head of Department',    #50. Handover all documents
    ],
}

class TimestampMixin(db.Model):
    __abstract__ = True
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), 
                           onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class UserRole:
    ADMIN = 'admin'
    PROJECT_HEAD = 'project_head'
    STAGE_OWNER = 'stage_owner'
    TEAM_MEMBER = 'team_member'
    VIEWER = 'viewer'


class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    company_code = db.Column(db.String(20), unique=True, nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer)


class Location(db.Model):
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    location_code = db.Column(db.String(20), unique=True, nullable=False)
    location_name = db.Column(db.String(200), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer)
    
    company = relationship('Company', lazy='joined')


class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    department_code = db.Column(db.String(20), unique=True, nullable=False)
    department_name = db.Column(db.String(200), nullable=False)
    parent_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    manager_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer)
    
    location = relationship('Location', lazy='joined')
    manager = relationship('User', foreign_keys=[manager_user_id], lazy='joined')


class Designation(db.Model):
    __tablename__ = 'designations'
    
    id = db.Column(db.Integer, primary_key=True)
    designation_code = db.Column(db.String(20), unique=True, nullable=False)
    designation_name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    is_super_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    employee_id = db.Column(db.String(50))
    designation = db.Column(db.String(100))
    email = db.Column(db.String(120), nullable=True)
    date_of_joining = db.Column(db.Date)
    created_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.Integer)
    last_login = db.Column(db.DateTime(timezone=True))
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer)
    password_changed_date = db.Column(db.DateTime(timezone=True))
    
    department = relationship('Department', foreign_keys=[department_id], lazy='joined')
    location = relationship('Location', foreign_keys=[location_id], lazy='joined')

    def to_dict(self):
        """Convert user to dictionary (excludes password_hash)"""
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
        }


class ProjectTemplate(TimestampMixin):
    __tablename__ = 'project_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    default_head_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    default_head_designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    default_head_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    default_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    default_expected_duration_days = db.Column(db.Integer, nullable=True)
    default_customer_name = db.Column(db.String(255), nullable=True)
    default_company_name = db.Column(db.String(255), nullable=True)
    default_part_name = db.Column(db.String(255), nullable=True)
    default_part_code = db.Column(db.String(100), nullable=True)
    default_remarks = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    phases = relationship(
        'ProjectTemplatePhase', back_populates='template', cascade='all, delete-orphan', 
        lazy='selectin', order_by='ProjectTemplatePhase.serial_number'
    )

    def to_dict(self, include_children: bool = True):
        """Convert template to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
        }
        if include_children:
            data['phases'] = [p.to_dict(include_children=True) for p in self.phases]
        return data


class ProjectTemplatePhase(TimestampMixin):
    __tablename__ = 'project_template_phases'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('project_templates.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    serial_number = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, nullable=True)
    default_responsible_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    default_responsible_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    default_designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    default_expected_duration_days = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    template = relationship('ProjectTemplate', back_populates='phases')
    stages = relationship(
        'ProjectTemplateStage', back_populates='phase', cascade='all, delete-orphan',
        lazy='selectin', order_by='ProjectTemplateStage.serial_number'
    )

    def to_dict(self, include_children: bool = True):
        """Convert template phase to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'serial_number': self.serial_number,
            'description': self.description,
            'is_active': self.is_active,
        }
        if include_children:
            data['stages'] = [s.to_dict() for s in self.stages]
        return data


class ProjectTemplateStage(TimestampMixin):
    __tablename__ = 'project_template_stages'

    id = db.Column(db.Integer, primary_key=True)
    template_phase_id = db.Column(db.Integer, db.ForeignKey('project_template_phases.id'), nullable=False)
    name = db.Column(db.String(512), nullable=False)
    serial_number = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, nullable=True)
    default_responsible_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    default_responsible_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    default_designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    default_expected_duration_days = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    phase = relationship('ProjectTemplatePhase', back_populates='stages')

    def to_dict(self):
        """Convert template stage to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'serial_number': self.serial_number,
            'description': self.description,
            'default_expected_duration_days': self.default_expected_duration_days,
            'default_responsible_department_id': self.default_responsible_department_id,
            'default_designation_id': self.default_designation_id,
            'is_active': self.is_active,
        }


class Project(TimestampMixin):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    head_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    head_designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    head_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    template_id = db.Column(db.Integer, db.ForeignKey('project_templates.id'), nullable=True)
    auto_sync_with_template = db.Column(db.Boolean, default=True, nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_end_date = db.Column(db.Date, nullable=True)
    actual_end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default='active')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Project specific fields
    part_name = db.Column(db.String(255), nullable=True)
    part_code = db.Column(db.String(100), nullable=True)
    customer_name = db.Column(db.String(255), nullable=True)
    company_name = db.Column(db.String(255), nullable=True)
    part_description = db.Column(db.Text, nullable=True)

    head = relationship('User', foreign_keys=[head_id], lazy='joined')
    head_designation = relationship('Designation', foreign_keys=[head_designation_id], lazy='joined')
    head_department = relationship('Department', foreign_keys=[head_department_id], lazy='joined')
    department = relationship('Department', foreign_keys=[department_id], lazy='joined')
    location_rel = relationship('Location', lazy='joined')
    template = relationship('ProjectTemplate', foreign_keys=[template_id], lazy='joined')
    phases = relationship(
        'Phase', back_populates='project', cascade='all, delete-orphan', lazy='selectin', order_by='Phase.serial_number'
    )

    @property
    def progress_percent(self) -> float:
        """Calculate overall project progress"""
        if not self.phases:
            return 0.0
        return round(sum(p.progress_percent for p in self.phases) / len(self.phases), 2)

    def to_dict(self, include_children: bool = True):
        """Convert project to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'head_id': self.head_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expected_end_date': self.expected_end_date.isoformat() if self.expected_end_date else None,
            'progress_percent': self.progress_percent,
        }
        if include_children:
            data['phases'] = [p.to_dict(include_children=False) for p in self.phases]
        return data


@event.listens_for(Project, 'after_insert')
def create_default_phases_and_stages_after_project_insert(mapper, connection, target):  # type: ignore[no-redef]
    """Create phases and stages with enhanced scheduling logic"""
    phase_table = Phase.__table__  # type: ignore[attr-defined]
    stage_table = Stage.__table__  # type: ignore[attr-defined]
    step_table = Step.__table__  # type: ignore[attr-defined]
    template_table = ProjectTemplate.__table__  # type: ignore[attr-defined]
    template_phase_table = ProjectTemplatePhase.__table__  # type: ignore[attr-defined]
    template_stage_table = ProjectTemplateStage.__table__  # type: ignore[attr-defined]
    
    # Helper: resolve base date (project start date or today)
    project_start = target.start_date if getattr(target, 'start_date', None) else date.today()

    # Determine which template to use
    template_id = target.template_id
    
    # If no template_id specified, try to get the default/first active template
    if not template_id:
        default_template = connection.execute(
            template_table.select()
            .where(template_table.c.is_active == True)
            .order_by(template_table.c.id)
            .limit(1)
        ).first()
        if default_template:
            template_id = default_template.id
    
    # If we have a template, use it from the database
    if template_id:
        # Fetch template phases
        template_phases = connection.execute(
            template_phase_table.select()
            .where(template_phase_table.c.template_id == template_id)
            .where(template_phase_table.c.is_active == True)
            .order_by(template_phase_table.c.serial_number)
        ).fetchall()
        
        # Create phases and stages with enhanced scheduling
        stage_id_map = {}  # Map stage serial numbers to IDs for dependencies
        phase_start_date = project_start  # Track the start date for each phase
        
        for phase_idx, template_phase in enumerate(template_phases):
            # Insert phase
            phase_result = connection.execute(phase_table.insert().values(
                project_id=target.id,
                name=template_phase.name,
                serial_number=template_phase.serial_number,
                start_date=phase_start_date,
                description=template_phase.description,
                responsible_user_id=template_phase.default_responsible_user_id,
            ))
            phase_id = phase_result.inserted_primary_key[0]
            
            # Fetch template stages for this phase
            template_stages = connection.execute(
                template_stage_table.select()
                .where(template_stage_table.c.template_phase_id == template_phase.id)
                .where(template_stage_table.c.is_active == True)
                .order_by(template_stage_table.c.serial_number)
            ).fetchall()
            
            # Get enhanced scheduling config for this phase
            phase_num = template_phase.serial_number
            scheduling_config = ENHANCED_STAGE_SCHEDULING.get(phase_num, [])
            
            # Track the latest end date in this phase for the next phase
            latest_end_date = phase_start_date
            
            for stage_idx, template_stage in enumerate(template_stages):
                # Get scheduling configuration for this stage
                config = scheduling_config[stage_idx] if stage_idx < len(scheduling_config) else {}
                
                duration = config.get('duration')
                scheduling_type = config.get('type', 'sequential')
                max_duration = config.get('max_duration')
                depends_on_stage_num = config.get('depends_on_stage')
                
                # Calculate dates based on scheduling type
                start_date, expected_end_date = calculate_stage_dates(
                    phase_start_date, stage_idx, config, stage_id_map, phase_num
                )
                
                # Determine stage properties
                is_manual = (scheduling_type == 'manual' or duration is None)
                is_auto_complete = (duration == 0)
                can_start_without_previous_phase = config.get('can_start_without_previous_phase', False)
                depends_on_stage_id = None
                
                # Resolve dependency stage ID
                if depends_on_stage_num:
                    depends_on_stage_id = stage_id_map.get(depends_on_stage_num)
                
                # Insert stage with enhanced fields
                stage_result = connection.execute(stage_table.insert().values(
                    phase_id=phase_id,
                    name=template_stage.name,
                    serial_number=template_stage.serial_number,
                    start_date=start_date,
                    expected_end_date=expected_end_date,
                    description=template_stage.description,
                    responsible_department_id=template_stage.default_responsible_department_id,
                    responsible_designation_id=template_stage.default_designation_id,
                    responsible_user_id=template_stage.default_responsible_user_id,
                    duration_days=duration,
                    max_duration_days=max_duration,
                    depends_on_stage_id=depends_on_stage_id,
                    is_manual=is_manual,
                    is_auto_complete=is_auto_complete,
                    can_start_without_previous_phase=can_start_without_previous_phase,
                    scheduling_type=scheduling_type,
                ))
                stage_id = stage_result.inserted_primary_key[0]
                
                # Map stage serial number to ID for dependencies
                global_stage_num = sum(len(ENHANCED_STAGE_SCHEDULING.get(p, [])) for p in range(1, phase_num)) + stage_idx + 1
                stage_id_map[global_stage_num] = stage_id
                
                # Track the latest end date in this phase
                if expected_end_date and expected_end_date > latest_end_date:
                    latest_end_date = expected_end_date
                
                # Auto-complete stages that should be completed on project start
                if is_auto_complete:
                    connection.execute(stage_table.update()
                        .where(stage_table.c.id == stage_id)
                        .values(actual_end_date=phase_start_date, status='completed'))
                
                # Create 2 default steps for each stage
                for step_num in range(1, 3):
                    connection.execute(step_table.insert().values(
                        stage_id=stage_id,
                        name=f'Step {step_num}',
                        description='',
                        status='pending',
                    ))
            
            # Update the phase's expected_end_date based on the latest stage end date
            if latest_end_date > phase_start_date:
                connection.execute(phase_table.update()
                    .where(phase_table.c.id == phase_id)
                    .values(expected_end_date=latest_end_date))
            
            # Set the start date for the next phase (day after this phase ends)
            phase_start_date = latest_end_date + timedelta(days=1) if latest_end_date else phase_start_date


def calculate_stage_dates(project_start: date, stage_idx: int, config: dict, stage_id_map: dict, phase_num: int) -> tuple[date, date]:
    """Calculate start and end dates for a stage based on its configuration"""
    duration = config.get('duration')
    scheduling_type = config.get('type', 'sequential')
    depends_on_stage_num = config.get('depends_on_stage')
    
    # Calculate start date
    if scheduling_type == 'auto_complete':
        start_date = project_start
        end_date = project_start
    elif scheduling_type == 'from_start':
        # Calculate from project start (e.g., "1 WEEK FROM START")
        start_date = project_start
        end_date = project_start + timedelta(days=duration) if duration else None
    elif scheduling_type == 'depends_on' and depends_on_stage_num:
        # This will be resolved later when the dependency stage is created
        start_date = project_start + timedelta(days=stage_idx)  # Temporary
        end_date = start_date + timedelta(days=duration) if duration else None
    elif scheduling_type == 'exception':
        # Exception stages have no automatic dates
        start_date = project_start
        end_date = None
    elif scheduling_type == 'manual':
        # Manual stages start immediately but have no end date
        start_date = project_start + timedelta(days=stage_idx)
        end_date = None
    else:  # sequential (default)
        # Sequential stages start after previous stage
        start_date = project_start + timedelta(days=stage_idx)
        end_date = start_date + timedelta(days=duration) if duration else None
    
    return start_date, end_date


class Phase(TimestampMixin):
    __tablename__ = 'phases'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    serial_number = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, nullable=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_end_date = db.Column(db.Date, nullable=True)
    actual_end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default='pending')
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_path = db.Column(db.String(512), nullable=True)

    project = relationship('Project', back_populates='phases', lazy='select')
    responsible = relationship('User', foreign_keys=[responsible_user_id], lazy='joined')
    stages = relationship(
        'Stage', back_populates='phase', cascade='all, delete-orphan', lazy='selectin', order_by='Stage.serial_number'
    )

    @property
    def progress_percent(self) -> float:
        """Calculate phase progress"""
        if not self.stages:
            return 0.0
        return round(sum(s.progress_percent for s in self.stages) / len(self.stages), 2)

    def to_dict(self, include_children: bool = True):
        """Convert phase to dictionary"""
        data = {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'serial_number': self.serial_number,
            'responsible_user_id': self.responsible_user_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expected_end_date': self.expected_end_date.isoformat() if self.expected_end_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'progress_percent': self.progress_percent,
        }
        if include_children:
            data['stages'] = [s.to_dict() for s in self.stages]
        return data


class Stage(TimestampMixin):
    __tablename__ = 'stages'

    id = db.Column(db.Integer, primary_key=True)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=False)
    name = db.Column(db.String(512), nullable=False)
    serial_number = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text, nullable=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    responsible_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    responsible_designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_end_date = db.Column(db.Date, nullable=True)
    actual_end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), default='pending')
    completed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_path = db.Column(db.String(512), nullable=True)
    
    # Enhanced scheduling fields
    duration_days = db.Column(db.Integer, nullable=True)  # Duration in days
    max_duration_days = db.Column(db.Integer, nullable=True)  # Max duration for manual stages
    depends_on_stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=True)  # Custom dependency
    is_manual = db.Column(db.Boolean, default=False)  # Manual stage flag
    is_auto_complete = db.Column(db.Boolean, default=False)  # Auto-complete on project start
    can_start_without_previous_phase = db.Column(db.Boolean, default=False)  # Exception rule
    scheduling_type = db.Column(db.String(50), default='sequential')  # sequential, parallel, exception

    phase = relationship('Phase', back_populates='stages', lazy='select')
    responsible = relationship('User', foreign_keys=[responsible_user_id], lazy='joined')
    responsible_department = relationship('Department', foreign_keys=[responsible_department_id], lazy='joined')
    responsible_designation = relationship('Designation', foreign_keys=[responsible_designation_id], lazy='joined')
    completed_by = relationship('User', foreign_keys=[completed_by_id], lazy='joined')
    depends_on_stage = relationship('Stage', remote_side=[id], lazy='joined')
    steps = relationship(
        'Step', back_populates='stage', cascade='all, delete-orphan', lazy='selectin'
    )

    @property
    def project(self):
        """Access project through phase"""
        return self.phase.project if self.phase else None
    
    @property
    def project_id(self):
        """Access project_id through phase"""
        return self.phase.project_id if self.phase else None

    @property
    def progress_percent(self) -> float:
        """Stage is complete if actual_end_date is set"""
        return 100.0 if self.actual_end_date else 0.0
    
    def can_be_started(self) -> bool:
        """Check if this stage can be started based on dependencies and rules"""
        # Auto-complete stages can always be started
        if self.is_auto_complete:
            return True
            
        # Exception stages can start without previous phase completion
        if self.can_start_without_previous_phase:
            return True
        
        # Check previous phase completion FIRST (so first phase is never locked)
        if not self.phase:
            return True
        
        # If this is the first phase (serial_number == 1), it can always be started
        if self.phase.serial_number == 1:
            return True
        
        # Get the previous phase
        previous_phase = Phase.query.filter(
            Phase.project_id == self.phase.project_id,
            Phase.serial_number == self.phase.serial_number - 1
        ).first()
        
        # If there's no previous phase, it can be started
        if not previous_phase:
            return True
        
        # Check if all stages in the previous phase are completed
        if not all(stage.actual_end_date is not None for stage in previous_phase.stages):
            return False
        
        # Check custom dependency (only if previous phase is complete)
        if self.depends_on_stage_id:
            dependency_stage = Stage.query.get(self.depends_on_stage_id)
            if dependency_stage and not dependency_stage.actual_end_date:
                return False
        
        return True
    
    def can_be_completed(self) -> bool:
        """Check if this stage can be completed"""
        # Check if max duration exceeded for manual stages
        if self.is_manual and self.max_duration_days and self.start_date:
            max_end_date = self.start_date + timedelta(days=self.max_duration_days)
            if date.today() > max_end_date:
                return False  # Exceeded maximum duration
        
        return True
    
    def calculate_expected_dates(self, project_start_date: date) -> tuple[date, date]:
        """Calculate start and end dates based on dependencies and rules"""
        # Auto-complete stages complete immediately
        if self.is_auto_complete:
            return project_start_date, project_start_date
        
        # Calculate start date
        start_date = project_start_date
        
        # If depends on specific stage
        if self.depends_on_stage_id:
            dependency_stage = Stage.query.get(self.depends_on_stage_id)
            if dependency_stage and dependency_stage.expected_end_date:
                start_date = dependency_stage.expected_end_date + timedelta(days=1)
        
        # If depends on previous stage in same phase (sequential)
        elif self.scheduling_type == 'sequential' and self.serial_number > 1:
            previous_stage = Stage.query.filter(
                Stage.phase_id == self.phase_id,
                Stage.serial_number == self.serial_number - 1
            ).first()
            if previous_stage and previous_stage.expected_end_date:
                start_date = previous_stage.expected_end_date + timedelta(days=1)
        
        # Calculate end date
        if self.duration_days is not None:
            if self.duration_days == 0:
                # Auto-complete
                end_date = start_date
            else:
                end_date = start_date + timedelta(days=self.duration_days)
        else:
            # Manual stage - no automatic end date
            end_date = None
        
        return start_date, end_date

    def to_dict(self, include_children: bool = True):
        """Convert stage to dictionary"""
        data = {
            'id': self.id,
            'phase_id': self.phase_id,
            'name': self.name,
            'serial_number': self.serial_number,
            'responsible_user_id': self.responsible_user_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expected_end_date': self.expected_end_date.isoformat() if self.expected_end_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'progress_percent': self.progress_percent,
            'duration_days': self.duration_days,
            'is_manual': self.is_manual,
            'is_auto_complete': self.is_auto_complete,
            'can_start_without_previous_phase': self.can_start_without_previous_phase,
        }
        if include_children:
            data['steps'] = [s.to_dict() for s in self.steps]
        return data


class Step(TimestampMixin):
    __tablename__ = 'steps'

    id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('stages.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    expected_start_date = db.Column(db.Date, nullable=True)
    expected_end_date = db.Column(db.Date, nullable=True)
    actual_start_date = db.Column(db.Date, nullable=True)
    actual_end_date = db.Column(db.Date, nullable=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(50), default='pending')
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_path = db.Column(db.String(512), nullable=True)

    stage = relationship('Stage', back_populates='steps', lazy='joined')
    responsible = relationship('User', foreign_keys=[responsible_user_id], lazy='joined')

    def to_dict(self):
        """Convert step to dictionary"""
        return {
            'id': self.id,
            'stage_id': self.stage_id,
            'name': self.name,
            'description': self.description,
            'expected_start_date': self.expected_start_date.isoformat() if self.expected_start_date else None,
            'expected_end_date': self.expected_end_date.isoformat() if self.expected_end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'responsible_user_id': self.responsible_user_id,
            'status': self.status,
        }


# Event hooks to manage dates
@event.listens_for(Step.status, 'set')
def set_completion_date_on_complete(target, value, oldvalue, initiator):  # type: ignore[no-redef]
    if value == 'completed' and target.actual_end_date is None:
        target.actual_end_date = date.today()
    elif oldvalue == 'completed' and value != 'completed':
        target.actual_end_date = None


@event.listens_for(Stage.steps, 'append')
def ensure_stage_dates_on_new_step(stage, step, initiator):  # type: ignore[no-redef]
    if stage.start_date is None:
        stage.start_date = date.today()


@event.listens_for(Stage.steps, 'remove')
@event.listens_for(Step.status, 'set')
def update_stage_actual_end_date(*args, **kwargs):  # type: ignore[no-redef]
    target = args[0]
    stage = None
    if isinstance(target, Stage):
        stage = target
    elif isinstance(target, Step):
        stage = target.stage
    if not stage:
        return
    if stage.steps and all(s.status == 'completed' for s in stage.steps):
        if stage.actual_end_date is None:
            stage.actual_end_date = date.today()
    else:
        stage.actual_end_date = None


@event.listens_for(Phase.stages, 'append')
def ensure_phase_dates_on_new_stage(phase, stage, initiator):  # type: ignore[no-redef]
    if phase.start_date is None:
        phase.start_date = date.today()


@event.listens_for(Phase.stages, 'remove')
def update_phase_actual_end_date_on_stage_remove(phase, stage, initiator):  # type: ignore[no-redef]
    if phase.stages and all(s.actual_end_date is not None for s in phase.stages):
        if phase.actual_end_date is None:
            phase.actual_end_date = date.today()
    else:
        phase.actual_end_date = None