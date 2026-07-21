from flask import Blueprint, request, jsonify, abort, make_response, session, Response
from flask_jwt_extended import jwt_required, get_jwt
from authz import role_required
from __init__ import db
from models import Project, Phase, Stage, Step, UserRole, User
from datetime import date, timedelta, datetime, timezone
from sqlalchemy import and_, case, or_
from secure_auth import SecurityManager
from email_notifications import is_email_enabled, send_stage_assignment_email
import logging

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')


@api.post('/projects')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def create_project():
    payload = request.get_json(force=True) or {}
    data = payload  # Use payload directly without schema validation

    project = Project(  # type: ignore[call-arg]
        name=data.get('name'),
        head_id=data.get('head_id'),
        template_id=data.get('template_id'),  # Accept template_id
        auto_sync_with_template=data.get('auto_sync_with_template', True),  # Default to True
        expected_end_date=data.get('expected_end_date'),
        location_id=data.get('location_id'),
        part_name=data.get('part_name'),
        part_code=data.get('part_code'),
        customer_name=data.get('customer_name'),
        company_name=data.get('company_name'),
        part_description=data.get('part_description'),
    )
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@jwt_required()
@api.get('/projects/<int:project_id>')
def get_project(project_id: int):
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    return jsonify(project.to_dict())


@api.post('/stages/<int:stage_id>/steps')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.STAGE_OWNER, UserRole.PROJECT_HEAD)
def create_step(stage_id: int):
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    payload = request.get_json(force=True) or {}
    data = payload  # Use payload directly without schema validation

    # Automatically start the step when created
    step = Step(  # type: ignore[call-arg]
        stage=stage,
        name=data.get('name'),
        description=data.get('description'),
        expected_start_date=date.today(),  # Automatically set to today
        expected_end_date=data.get('expected_end_date'),
        responsible_user_id=data.get('responsible_user_id'),
        status='in_progress',  # Automatically start the step
    )
    db.session.add(step)
    db.session.commit()
    return jsonify(step.to_dict()), 201


@api.patch('/steps/<int:step_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.STAGE_OWNER, UserRole.TEAM_MEMBER, UserRole.PROJECT_HEAD)
def update_step(step_id: int):
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    
    payload = request.get_json(force=True) or {}
    data = payload  # Use payload directly without schema validation

    if 'name' in data:
        step.name = data['name']
    if 'description' in data:
        step.description = data['description']
    if 'expected_start_date' in data:
        step.expected_start_date = data['expected_start_date']
    if 'expected_end_date' in data:
        step.expected_end_date = data['expected_end_date']
    if 'actual_start_date' in data:
        step.actual_start_date = data['actual_start_date']
    if 'actual_end_date' in data:
        step.actual_end_date = data['actual_end_date']
    if 'responsible_user_id' in data:
        step.responsible_user_id = data['responsible_user_id']
    if 'status' in data:
        step.status = data['status']

    db.session.commit()
    return jsonify(step.to_dict())


@api.patch('/projects/<int:project_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def update_project(project_id: int):
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    payload = request.get_json(force=True) or {}
    # Allow partial updates
    name = payload.get('name')
    if name:
        project.name = name
    if 'head_id' in payload:
        project.head_id = payload.get('head_id')
    if 'expected_end_date' in payload:
        val = payload.get('expected_end_date')
        try:
            project.expected_end_date = date.fromisoformat(val) if val else None
        except ValueError:
            abort(400, description='invalid expected_end_date format, use YYYY-MM-DD')
    if 'auto_sync_with_template' in payload:
        project.auto_sync_with_template = bool(payload.get('auto_sync_with_template'))
    db.session.commit()
    return jsonify(project.to_dict())


@api.delete('/projects/<int:project_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_project(project_id: int):
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'}), 200


@api.delete('/steps/<int:step_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.STAGE_OWNER, UserRole.PROJECT_HEAD)
def delete_step(step_id: int):
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    db.session.delete(step)
    db.session.commit()
    return '', 204


@jwt_required()
@api.get('/stages/<int:stage_id>')
def get_stage(stage_id: int):
    """Get a specific stage with its steps"""
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    return jsonify(stage.to_dict())


@api.patch('/stages/<int:stage_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD, UserRole.STAGE_OWNER)
def update_stage(stage_id: int):
    """Update stage details"""
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    # Get current user from JWT
    claims = get_jwt() or {}
    user_id = claims.get('user_id')
    user_role = claims.get('role')
    is_super_admin = claims.get('is_super_admin', False)
    unified_role = claims.get('unified_role', '').lower()
    
    # Additional authorization check for stage completion
    payload = request.get_json(force=True) or {}
    data = payload  # Use payload directly without schema validation

    # Check if trying to complete the stage
    is_completing = 'actual_end_date' in data and data['actual_end_date'] is not None
    
    if is_completing:
        # Check if user has permission to complete this stage
        can_complete = False
        
        # Super admin can complete anything
        if is_super_admin:
            can_complete = True
        # Admin role can complete anything
        elif 'admin' in unified_role:
            can_complete = True
        # Project head or admin role can complete anything
        elif user_role in [UserRole.PROJECT_HEAD, UserRole.ADMIN, 'project_head', 'admin']:
            can_complete = True
        # Project head of this specific project can complete
        elif stage.phase.project.head_id == user_id:
            can_complete = True
        # Responsible person for this stage can complete
        elif stage.responsible_user_id == user_id:
            can_complete = True
        
        if not can_complete:
            return make_response(jsonify({
                'error': 'You do not have permission to mark this stage as complete. Only the project head, stage responsible person, or administrators can complete stages.'
            }), 403)
        
        # Validate that previous phase is completed
        # Only check previous phase completion if this is NOT the first phase
        if stage.phase.serial_number > 1 and not stage.can_be_started():
            return make_response(jsonify({
                'error': 'Cannot complete this stage. The previous phase must be completed first.',
                'phase': stage.phase.name,
                'serial_number': stage.phase.serial_number
            }), 400)
        
        # Validate that previous stages in same phase are completed
        if not stage.can_be_completed():
            return make_response(jsonify({
                'error': 'Cannot complete this stage. All previous stages in this phase must be completed first.',
                'phase': stage.phase.name,
                'stage': stage.name
            }), 400)

    # Update fields if provided
    if 'name' in data:
        stage.name = data['name']
    if 'responsible_user_id' in data:
        stage.responsible_user_id = data['responsible_user_id']
    if 'expected_end_date' in data:
        stage.expected_end_date = data['expected_end_date']
    if 'actual_end_date' in data:
        stage.actual_end_date = data['actual_end_date']

    db.session.commit()
    return jsonify(stage.to_dict())


@api.delete('/stages/<int:stage_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_stage(stage_id: int):
    """Delete a stage and all its steps"""
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    # Check if this is the last stage in the project
    project = stage.project
    if len(project.stages) <= 1:
        abort(400, description="Cannot delete the last stage in a project")
    
    db.session.delete(stage)
    db.session.commit()
    return '', 204


@jwt_required()
@api.get('/projects')
def list_projects():
    """List all projects with optional filtering and pagination"""
    # Query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    head_id = request.args.get('head_id', type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status')  # 'active', 'completed', 'overdue'
    include_children = request.args.get('include_children', 'false').lower() == 'true'
    
    # Build query
    query = Project.query
    
    # Filter by project head
    if head_id:
        query = query.filter_by(head_id=head_id)
    
    # Search by name
    if search:
        query = query.filter(Project.name.ilike(f'%{search}%'))
    
    # Get all projects for status filtering (needs computed property)
    all_projects = query.order_by(Project.id.desc()).all()
    
    # Filter by status
    if status == 'active':
        all_projects = [p for p in all_projects if p.progress_percent < 100.0]
    elif status == 'completed':
        all_projects = [p for p in all_projects if p.progress_percent >= 100.0]
    elif status == 'overdue':
        today = date.today()
        all_projects = [p for p in all_projects if p.expected_end_date and p.expected_end_date < today and p.progress_percent < 100.0]
    
    # Manual pagination
    total = len(all_projects)
    start = (page - 1) * per_page
    end = start + per_page
    projects = all_projects[start:end]
    
    return jsonify({
        'projects': [p.to_dict(include_children=include_children) for p in projects],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })


# ==================== USER MANAGEMENT ENDPOINTS ====================

@api.get('/apqp/users')
@jwt_required()
def list_users():
    """List all users with optional filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    role = request.args.get('role')
    search = request.args.get('search', '').strip()
    
    query = User.query
    
    # Filter by role
    if role and role in [UserRole.PROJECT_HEAD, UserRole.STAGE_OWNER, UserRole.TEAM_MEMBER, UserRole.VIEWER]:
        query = query.filter_by(role=role)
    
    # Search by username or name
    if search:
        query = query.filter(
            or_(
                User.username.ilike(f'%{search}%'),
                User.full_name.ilike(f'%{search}%')
            )
        )
    
    # Paginate
    paginated = query.order_by(User.full_name).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'users': [user.to_dict() for user in paginated.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': paginated.total,
            'pages': paginated.pages
        }
    })


@api.get('/users/<int:user_id>')
@jwt_required()
def get_user(user_id: int):
    """Get a specific user by ID"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404, description="User not found")
    return jsonify(user.to_dict())


@api.post('/users')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def create_user():
    """Create a new user"""
    try:
        payload = request.get_json(force=True) or {}
    except Exception as e:
        return make_response(jsonify({'error': 'Invalid JSON payload'}), 400)
    
    # Validate required fields
    username = payload.get('username', '').strip()
    name = payload.get('name', '').strip()
    password = payload.get('password', '').strip()
    role = payload.get('role', UserRole.TEAM_MEMBER)
    
    if not username:
        return make_response(jsonify({'error': 'username is required'}), 400)
    if not name:
        return make_response(jsonify({'error': 'name is required'}), 400)
    if not password:
        return make_response(jsonify({'error': 'password is required'}), 400)
    
    # Validate role
    if role not in [UserRole.ADMIN, UserRole.PROJECT_HEAD, UserRole.STAGE_OWNER, UserRole.TEAM_MEMBER, UserRole.VIEWER]:
        return make_response(jsonify({'error': 'Invalid role'}), 400)
    
    # Check if username already exists
    existing = User.query.filter_by(username=username).first()
    if existing:
        return make_response(jsonify({'error': 'Username already exists'}), 409)
    
    # Create user
    user = User(  # type: ignore[call-arg]
        username=username,
        full_name=name,
        role=role,
        password_hash=SecurityManager.hash_password(password)
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify(user.to_dict()), 201


@api.patch('/users/<int:user_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def update_user(user_id: int):
    """Update a user's information"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404, description="User not found")
    
    try:
        payload = request.get_json(force=True) or {}
    except Exception as e:
        return make_response(jsonify({'error': 'Invalid JSON payload'}), 400)
    
    # Update fields if provided
    if 'name' in payload:
        name = payload['name'].strip()
        if not name:
            return make_response(jsonify({'error': 'name cannot be empty'}), 400)
        user.full_name = name
    
    if 'role' in payload:
        role = payload['role']
        if role not in [UserRole.ADMIN, UserRole.PROJECT_HEAD, UserRole.STAGE_OWNER, UserRole.TEAM_MEMBER, UserRole.VIEWER]:
            return make_response(jsonify({'error': 'Invalid role'}), 400)
        user.role = role
    
    if 'password' in payload:
        password = payload['password'].strip()
        if not password:
            return make_response(jsonify({'error': 'password cannot be empty'}), 400)
        user.password_hash = SecurityManager.hash_password(password)
    
    # Username cannot be changed for security reasons
    
    db.session.commit()
    return jsonify(user.to_dict())


@api.delete('/users/<int:user_id>')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_user(user_id: int):
    """Delete a user (soft delete - sets inactive flag if implemented)"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404, description="User not found")
    
    # Check if user has active projects or stages
    user_projects = Project.query.filter_by(head_id=user_id).all()
    if user_projects:
        return make_response(jsonify({
            'error': 'Cannot delete user with active projects. Reassign projects first.',
            'projects': [p.id for p in user_projects]
        }), 409)
    
    # Check if user is responsible for stages
    responsible_stages = Stage.query.filter_by(responsible_user_id=user_id).all()
    if responsible_stages:
        return make_response(jsonify({
            'error': 'Cannot delete user responsible for stages. Reassign stages first.',
            'stages': [s.id for s in responsible_stages]
        }), 409)
    
    db.session.delete(user)
    db.session.commit()
    return '', 204


@api.get('/users/<int:user_id>/projects')
@jwt_required()
def get_user_projects(user_id: int):
    """Get all projects where user is the project head"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404, description="User not found")
    
    projects = Project.query.filter_by(head_id=user_id).order_by(Project.id.desc()).all()
    return jsonify({
        'user_id': user_id,
        'user_name': user.full_name,
        'projects': [p.to_dict(include_children=False) for p in projects]
    })


@api.get('/users/<int:user_id>/stages')
@jwt_required()
def get_user_stages(user_id: int):
    """Get all stages where user is responsible"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404, description="User not found")
    
    stages = Stage.query.filter_by(responsible_user_id=user_id).order_by(Stage.project_id, Stage.id).all()
    return jsonify({
        'user_id': user_id,
        'user_name': user.full_name,
        'stages': [s.to_dict(include_children=False) for s in stages]
    })


@api.get('/users/<int:user_id>/workload')
@jwt_required()
def get_user_workload(user_id: int):
    """Get user's workload summary including projects and stages"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404, description="User not found")
    
    # Projects as head
    projects = Project.query.filter_by(head_id=user_id).all()
    active_projects = [p for p in projects if p.progress_percent < 100.0]
    
    # Stages as responsible user
    stages = Stage.query.filter_by(responsible_user_id=user_id).all()
    active_stages = [s for s in stages if not s.actual_end_date]
    overdue_stages = [s for s in stages if s.expected_end_date and s.expected_end_date < date.today() and not s.actual_end_date]
    
    # Steps in user's stages
    total_steps = sum(len(s.steps) for s in stages)
    completed_steps = sum(len([step for step in s.steps if step.status == 'completed']) for s in stages)
    overdue_steps = sum(len([step for step in s.steps if step.expected_end_date and step.expected_end_date < date.today() and step.status != 'completed']) for s in stages)
    
    return jsonify({
        'user': user.to_dict(),
        'workload': {
            'projects': {
                'total': len(projects),
                'active': len(active_projects),
                'completion_rate': round(sum(p.progress_percent for p in projects) / len(projects), 2) if projects else 0
            },
            'stages': {
                'total': len(stages),
                'active': len(active_stages),
                'overdue': len(overdue_stages),
                'completion_rate': round(sum(s.progress_percent for s in stages) / len(stages), 2) if stages else 0
            },
            'steps': {
                'total': total_steps,
                'completed': completed_steps,
                'overdue': overdue_steps,
                'completion_rate': round((completed_steps / total_steps * 100), 2) if total_steps > 0 else 0
            }
        }
    })


# ==================== STAGES ENDPOINTS ====================

@api.post('/projects/<int:project_id>/stages')
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def create_stage(project_id: int):
    """Create a new stage in a project"""
    project = db.session.get(Project, project_id)
    if not project:
        abort(404, description="Project not found")
    
    try:
        payload = request.get_json(force=True) or {}
    except Exception as e:
        return make_response(jsonify({'error': 'Invalid JSON payload'}), 400)
    
    # Validate required fields
    name = payload.get('name', '').strip()
    if not name:
        return make_response(jsonify({'error': 'name is required'}), 400)
    
    responsible_user_id = payload.get('responsible_user_id')
    if responsible_user_id:
        user = db.session.get(User, responsible_user_id)
        if not user:
            return make_response(jsonify({'error': 'Invalid responsible_user_id'}), 400)
    
    # Parse expected end date
    expected_end_date = None
    if payload.get('expected_end_date'):
        try:
            expected_end_date = date.fromisoformat(payload['expected_end_date'])
        except ValueError:
            return make_response(jsonify({'error': 'Invalid expected_end_date format, use YYYY-MM-DD'}), 400)
    
    # Create stage - automatically started with today's date (ignoring any user-provided start_date)
    stage = Stage(  # type: ignore[call-arg]
        project_id=project_id,
        name=name,
        responsible_user_id=responsible_user_id,
        start_date=date.today(),  # Automatically start the stage immediately
        expected_end_date=expected_end_date
    )
    
    db.session.add(stage)
    db.session.commit()
    
    if is_email_enabled() and responsible_user_id:
        responsible_user = User.query.get(responsible_user_id)
        if responsible_user and responsible_user.email:
            send_stage_assignment_email(
                responsible_user.email,
                responsible_user.full_name,
                stage.name,
                project.name,
                expected_end_date,
            )
    
    return jsonify(stage.to_dict()), 201


# ==================== ADDITIONAL PROJECT ENDPOINTS ====================

@jwt_required()
@api.get('/projects/summary')
def projects_summary():
    """Get a quick summary of all projects"""
    projects = Project.query.all()
    
    total_projects = len(projects)
    active_projects = len([p for p in projects if p.progress_percent < 100.0])
    completed_projects = len([p for p in projects if p.progress_percent >= 100.0])
    
    today = date.today()
    overdue_projects = len([p for p in projects if p.expected_end_date and p.expected_end_date < today and p.progress_percent < 100.0])
    
    avg_progress = sum(p.progress_percent for p in projects) / total_projects if total_projects > 0 else 0
    
    return jsonify({
        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,
        'overdue_projects': overdue_projects,
        'avg_progress': round(avg_progress, 2)
    })


@jwt_required()
@api.get('/projects/by-user/<int:user_id>')
def get_projects_by_user(user_id: int):
    """Get all projects related to a user (as head or stage responsible)"""
    user = db.session.get(User, user_id)
    if not user:
        abort(404, description="User not found")
    
    # Projects as head
    head_projects = Project.query.filter_by(head_id=user_id).all()
    
    # Projects where user is responsible for at least one stage
    stage_project_ids = db.session.query(Stage.project_id).filter_by(responsible_user_id=user_id).distinct().all()
    stage_projects = Project.query.filter(Project.id.in_([pid[0] for pid in stage_project_ids])).all()
    
    # Combine and deduplicate
    all_project_ids = set([p.id for p in head_projects] + [p.id for p in stage_projects])
    all_projects = Project.query.filter(Project.id.in_(all_project_ids)).order_by(Project.id.desc()).all()
    
    return jsonify({
        'user_id': user_id,
        'user_name': user.full_name,
        'projects': [p.to_dict(include_children=False) for p in all_projects],
        'as_head': [p.id for p in head_projects],
        'as_stage_responsible': [p.id for p in stage_projects]
    })


# Dashboard endpoints (read-only)
@jwt_required()
@api.get('/dashboard/summary')
def dashboard_summary():
    projects = Project.query.all()
    active_projects = [p for p in projects if p.progress_percent < 100.0]

    overdue_stages_q = Stage.query.filter(
        Stage.expected_end_date.isnot(None),
        Stage.expected_end_date < date.today(),
        Stage.actual_end_date.is_(None),
    )
    overdue_stages_count = overdue_stages_q.count()

    days = int(request.args.get('days', 7))
    window_end = date.today() + timedelta(days=days)
    upcoming_steps_count = Step.query.filter(
        Step.expected_end_date.isnot(None),
        Step.expected_end_date >= date.today(),
        Step.expected_end_date <= window_end,
        Step.status != 'completed',
    ).count()

    overdue_steps_count = Step.query.filter(
        Step.expected_end_date.isnot(None),
        Step.expected_end_date < date.today(),
        Step.status != 'completed',
    ).count()

    top_projects = sorted(projects, key=lambda x: x.progress_percent, reverse=True)[:5]

    return jsonify({
        'totals': {
            'projects': len(projects),
            'active_projects': len(active_projects),
            'overdue_stages': overdue_stages_count,
            'upcoming_steps': upcoming_steps_count,
            'overdue_steps': overdue_steps_count,
        },
        'top_projects': [
            {'id': p.id, 'name': p.name, 'progress_percent': p.progress_percent}
            for p in top_projects
        ],
    })


@jwt_required()
@api.get('/dashboard/overdue_stages')
def dashboard_overdue_stages():
    q = Stage.query.filter(
        Stage.expected_end_date.isnot(None),
        Stage.expected_end_date < date.today(),
        Stage.actual_end_date.is_(None),
    ).order_by(Stage.expected_end_date.asc())
    stages = q.all()
    return jsonify([s.to_dict(include_children=False) for s in stages])


@jwt_required()
@api.get('/dashboard/upcoming_steps')
def dashboard_upcoming_steps():
    days = int(request.args.get('days', 7))
    window_end = date.today() + timedelta(days=days)
    steps = Step.query.filter(
        Step.expected_end_date.isnot(None),
        Step.expected_end_date >= date.today(),
        Step.expected_end_date <= window_end,
        Step.status != 'completed',
    ).order_by(Step.expected_end_date.asc()).all()
    return jsonify([s.to_dict() for s in steps])


@jwt_required()
@api.get('/dashboard/overdue_steps')
def dashboard_overdue_steps():
    steps = Step.query.filter(
        Step.expected_end_date.isnot(None),
        Step.expected_end_date < date.today(),
        Step.status != 'completed',
    ).order_by(Step.expected_end_date.asc()).all()
    return jsonify([s.to_dict() for s in steps])


# Enhanced Analytics Endpoints
@jwt_required()
@api.get('/dashboard/analytics/trends')
def dashboard_trends():
    """Get trend analysis for project completion and performance metrics."""
    from sqlalchemy import func
    
    # Get last 30 days of data points
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    # Daily completion trends
    completed_steps_trend = db.session.query(
        func.date(Step.actual_end_date).label('date'),
        func.count(Step.id).label('completed_steps')
    ).filter(
        Step.actual_end_date.isnot(None),
        Step.actual_end_date >= start_date,
        Step.actual_end_date <= end_date
    ).group_by(func.date(Step.actual_end_date)).all()
    
    # Weekly stage completion rates
    stage_completion_trend = db.session.query(
        func.extract('week', Stage.actual_end_date).label('week'),
        func.count(Stage.id).label('completed_stages')
    ).filter(
        Stage.actual_end_date.isnot(None),
        Stage.actual_end_date >= start_date
    ).group_by(func.extract('week', Stage.actual_end_date)).all()
    
    # Project progress velocity (average daily progress)
    projects = Project.query.all()
    project_velocities = []
    for project in projects:
        if project.created_at and project.progress_percent > 0:
            days_active = (datetime.now(timezone.utc) - project.created_at).days or 1
            velocity = project.progress_percent / days_active
            project_velocities.append({
                'project_id': project.id,
                'project_name': project.name,
                'velocity': round(velocity, 2),
                'current_progress': project.progress_percent
            })
    
    # Sort by velocity (fastest projects first)
    project_velocities.sort(key=lambda x: x['velocity'], reverse=True)  # type: ignore[arg-type]
    
    return jsonify({
        'daily_completions': [
            {'date': str(item.date), 'completed_steps': item.completed_steps}
            for item in completed_steps_trend
        ],
        'weekly_stage_completions': [
            {'week': int(item.week), 'completed_stages': item.completed_stages}
            for item in stage_completion_trend
        ],
        'project_velocities': project_velocities[:10],  # Top 10 fastest projects
        'period': {
            'start_date': str(start_date),
            'end_date': str(end_date),
            'days': 30
        }
    })


@jwt_required()
@api.get('/dashboard/analytics/user-performance')
def dashboard_user_performance():
    """Get user performance metrics and productivity analysis."""
    from sqlalchemy import func
    
    # Get today's date as a proper date object for the query
    today = date.today()
    
    # Get responsible users and their stage performance
    # Note: We'll calculate avg_progress after querying since progress_percent is a computed property
    user_stage_stats = db.session.query(
        Stage.responsible_user_id,
        func.count(Stage.id).label('total_stages'),
        func.count(case((Stage.actual_end_date.isnot(None), 1))).label('completed_stages'),
        func.count(case((and_(Stage.expected_end_date.isnot(None), 
                              Stage.expected_end_date < today, 
                              Stage.actual_end_date.is_(None)), 1))).label('overdue_stages')
    ).filter(
        Stage.responsible_user_id.isnot(None)
    ).group_by(Stage.responsible_user_id).all()
    
    # Get user information and compile performance data
    user_performance = []
    for stats in user_stage_stats:
        user = User.query.get(stats.responsible_user_id)
        if user:
            # Get all stages for this user to calculate average progress
            user_stages = Stage.query.filter_by(responsible_user_id=stats.responsible_user_id).all()
            avg_progress = sum(stage.progress_percent for stage in user_stages) / len(user_stages) if user_stages else 0
            
            completion_rate = (stats.completed_stages / stats.total_stages * 100) if stats.total_stages > 0 else 0
            user_performance.append({
                'user_id': user.id,
                'user_name': user.full_name,
                'username': user.username,
                'role': user.role,
                'total_stages': stats.total_stages,
                'completed_stages': stats.completed_stages,
                'completion_rate': round(completion_rate, 2),
                'avg_progress': round(float(avg_progress), 2),
                'overdue_stages': stats.overdue_stages,
                'performance_score': round((completion_rate * 0.7) + (float(avg_progress) * 0.3), 2)
            })
    
    # Sort by performance score
    user_performance.sort(key=lambda x: x['performance_score'], reverse=True)
    
    # Overall user activity stats
    total_users = User.query.count()
    active_users = len([u for u in user_performance if u['total_stages'] > 0])
    
    return jsonify({
        'user_performance': user_performance,
        'summary': {
            'total_users': total_users,
            'active_users': active_users,
            'avg_completion_rate': round(sum(u['completion_rate'] for u in user_performance) / len(user_performance), 2) if user_performance else 0,
            'top_performer': user_performance[0] if user_performance else None
        }
    })


@jwt_required()
@api.get('/dashboard/analytics/project-health')
def dashboard_project_health():
    """Get comprehensive project health metrics and risk analysis."""
    from sqlalchemy import func
    
    projects = Project.query.all()
    project_health = []
    
    for project in projects:
        # Calculate various health metrics
        total_stages = len(project.stages)
        completed_stages = len([s for s in project.stages if s.actual_end_date])
        overdue_stages = len([s for s in project.stages if s.expected_end_date and s.expected_end_date < date.today() and not s.actual_end_date])
        
        total_steps = sum(len(s.steps) for s in project.stages)
        completed_steps = sum(len([step for step in s.steps if step.status == 'completed']) for s in project.stages)
        overdue_steps = sum(len([step for step in s.steps if step.expected_end_date and step.expected_end_date < date.today() and step.status != 'completed']) for s in project.stages)
        
        # Risk assessment
        risk_factors = []
        risk_score = 0
        
        if overdue_stages > 0:
            risk_factors.append(f"{overdue_stages} overdue stages")
            risk_score += overdue_stages * 10
            
        if overdue_steps > 0:
            risk_factors.append(f"{overdue_steps} overdue steps")
            risk_score += overdue_steps * 5
            
        if project.progress_percent < 25 and project.expected_end_date and (project.expected_end_date - date.today()).days < 30:
            risk_factors.append("Low progress with approaching deadline")
            risk_score += 20
            
        if total_stages > 0 and completed_stages / total_stages < 0.3 and project.created_at and (datetime.now(timezone.utc) - project.created_at).days > 60:
            risk_factors.append("Slow stage completion rate")
            risk_score += 15
        
        # Health status determination
        if risk_score == 0:
            health_status = "excellent"
        elif risk_score <= 15:
            health_status = "good"
        elif risk_score <= 35:
            health_status = "warning"
        else:
            health_status = "critical"
        
        project_health.append({
            'project_id': project.id,
            'project_name': project.name,
            'progress_percent': project.progress_percent,
            'health_status': health_status,
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'metrics': {
                'total_stages': total_stages,
                'completed_stages': completed_stages,
                'overdue_stages': overdue_stages,
                'total_steps': total_steps,
                'completed_steps': completed_steps,
                'overdue_steps': overdue_steps,
                'stage_completion_rate': round((completed_stages / total_stages * 100) if total_stages > 0 else 0, 2),
                'step_completion_rate': round((completed_steps / total_steps * 100) if total_steps > 0 else 0, 2)
            },
            'expected_end_date': project.expected_end_date.strftime('%Y-%m-%d') if project.expected_end_date else None,
            'days_until_deadline': (project.expected_end_date - date.today()).days if project.expected_end_date else None
        })
    
    # Sort by risk score (highest risk first)
    project_health.sort(key=lambda x: x['risk_score'], reverse=True)
    
    # Summary statistics
    health_summary = {
        'excellent': len([p for p in project_health if p['health_status'] == 'excellent']),
        'good': len([p for p in project_health if p['health_status'] == 'good']),
        'warning': len([p for p in project_health if p['health_status'] == 'warning']),
        'critical': len([p for p in project_health if p['health_status'] == 'critical'])
    }
    
    return jsonify({
        'project_health': project_health,
        'summary': health_summary,
        'high_risk_projects': [p for p in project_health if p['health_status'] in ['critical', 'warning']][:5]
    })



# Audit Logs Endpoints
@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
@api.get('/audit-logs')
def get_audit_logs():
    """Get audit logs with pagination and filtering from unified database"""
    try:
        from unified_db import get_unified_db_connection
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()
        action_filter = request.args.get('action', '').strip()
        user_filter = request.args.get('user', '').strip()
        resource_type_filter = request.args.get('resource_type', '').strip()
        success_filter = request.args.get('success', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Build WHERE clause based on filters
            where_clauses = []
            params = []
            
            if search:
                where_clauses.append("""
                    (al.username ILIKE %s OR al.action ILIKE %s OR 
                     al.details ILIKE %s OR al.ip_address ILIKE %s)
                """)
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param, search_param])
            
            if action_filter:
                where_clauses.append("al.action = %s")
                params.append(action_filter)
            
            if user_filter:
                where_clauses.append("al.username ILIKE %s")
                params.append(f'%{user_filter}%')
            
            if resource_type_filter:
                where_clauses.append("al.resource_type = %s")
                params.append(resource_type_filter)
            
            if success_filter:
                where_clauses.append("al.success = %s")
                params.append(success_filter.lower() == 'true')
            
            if date_from:
                where_clauses.append("DATE(al.created_date) >= %s")
                params.append(date_from)
            
            if date_to:
                where_clauses.append("DATE(al.created_date) <= %s")
                params.append(date_to)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Get total count
            count_query = f"""
                SELECT COUNT(*) 
                FROM audit_logs al
                WHERE {where_sql}
            """
            cur.execute(count_query, params)
            total_count = cur.fetchone()[0]
            
            # Get paginated logs with user and location details
            logs_query = f"""
                SELECT 
                    al.id,
                    al.user_id,
                    al.username,
                    al.action,
                    al.resource_type,
                    al.resource_id,
                    al.details,
                    al.ip_address,
                    al.user_agent,
                    al.success,
                    al.created_date,
                    l.location_name,
                    l.location_code,
                    u.full_name,
                    u.role
                FROM audit_logs al
                LEFT JOIN locations l ON al.location_id = l.id
                LEFT JOIN users u ON al.user_id = u.id
                WHERE {where_sql}
                ORDER BY al.created_date DESC
                LIMIT %s OFFSET %s
            """
            
            cur.execute(logs_query, params + [per_page, offset])
            logs = []
            
            for row in cur.fetchall():
                logs.append({
                    'id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'action': row[3],
                    'resource_type': row[4],
                    'resource_id': row[5],
                    'details': row[6],
                    'ip_address': row[7],
                    'user_agent': row[8],
                    'success': row[9],
                    'created_date': row[10].isoformat() if row[10] else None,
                    'location_name': row[11],
                    'location_code': row[12],
                    'full_name': row[13],
                    'user_role': row[14]
                })
            
            # Get unique action types for filter dropdown
            cur.execute("""
                SELECT DISTINCT action 
                FROM audit_logs 
                ORDER BY action
            """)
            action_types = [row[0] for row in cur.fetchall()]
            
            # Get unique resource types for filter dropdown
            cur.execute("""
                SELECT DISTINCT resource_type 
                FROM audit_logs 
                WHERE resource_type IS NOT NULL
                ORDER BY resource_type
            """)
            resource_types = [row[0] for row in cur.fetchall()]
            
            total_pages = (total_count + per_page - 1) // per_page
            
            return jsonify({
                'logs': logs,
                'total': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page,
                'action_types': action_types,
                'resource_types': resource_types
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
@api.get('/audit-logs/stats')
def get_audit_logs_stats():
    """Get audit logs statistics from unified database"""
    try:
        from unified_db import get_unified_db_connection
        from datetime import date
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Get total logs count
            cur.execute("SELECT COUNT(*) FROM audit_logs")
            total_logs = cur.fetchone()[0]
            
            # Get today's logs count
            cur.execute("""
                SELECT COUNT(*) 
                FROM audit_logs 
                WHERE DATE(created_date) = %s
            """, (date.today(),))
            logs_today = cur.fetchone()[0]
            
            # Get today's failed logs count
            cur.execute("""
                SELECT COUNT(*) 
                FROM audit_logs 
                WHERE DATE(created_date) = %s AND success = FALSE
            """, (date.today(),))
            failed_today = cur.fetchone()[0]
            
            return jsonify({
                'total_logs': total_logs,
                'logs_today': logs_today,
                'failed_today': failed_today
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
@api.get('/audit-logs/export')
def export_audit_logs():
    """Export audit logs to CSV"""
    try:
        from unified_db import get_unified_db_connection
        import csv
        from io import StringIO
        
        # Get filters
        search = request.args.get('search', '').strip()
        action_filter = request.args.get('action', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Build WHERE clause
            where_clauses = []
            params = []
            
            if search:
                where_clauses.append("(username ILIKE %s OR action ILIKE %s OR details ILIKE %s)")
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            if action_filter:
                where_clauses.append("action = %s")
                params.append(action_filter)
            
            if date_from:
                where_clauses.append("DATE(created_date) >= %s")
                params.append(date_from)
            
            if date_to:
                where_clauses.append("DATE(created_date) <= %s")
                params.append(date_to)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # Get logs
            query = f"""
                SELECT 
                    al.username,
                    al.action,
                    al.resource_type,
                    al.details,
                    al.ip_address,
                    al.success,
                    al.created_date,
                    l.location_name
                FROM audit_logs al
                LEFT JOIN locations l ON al.location_id = l.id
                WHERE {where_sql}
                ORDER BY al.created_date DESC
                LIMIT 10000
            """
            
            cur.execute(query, params)
            
            # Create CSV
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['Username', 'Action', 'Resource Type', 'Details', 'IP Address', 'Success', 'Date', 'Location'])
            
            # Write data
            for row in cur.fetchall():
                writer.writerow([
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    'Yes' if row[5] else 'No',
                    row[6].strftime('%Y-%m-%d %H:%M:%S') if row[6] else '',
                    row[7]
                ])
            
            output.seek(0)
            
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=audit_logs.csv'}
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.delete('/audit-logs/cleanup')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def cleanup_audit_logs():
    """Delete audit logs older than specified days"""
    try:
        from unified_db import get_unified_db_connection
        from datetime import datetime, timedelta
        
        # Get days parameter
        days = request.args.get('days', type=int)
        
        if not days or days < 1:
            return jsonify({'error': 'Invalid days parameter. Must be a positive integer.'}), 400
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Delete old logs
            cur.execute("""
                DELETE FROM audit_logs
                WHERE created_date < %s
            """, (cutoff_date,))
            
            deleted_count = cur.rowcount
            conn.commit()
            
            # Log the cleanup action
            from secure_auth import SecurityManager
            SecurityManager.record_audit_log(
                user_id=session.get('user_id'),
                action='CLEANUP_AUDIT_LOGS',
                details=f'Deleted {deleted_count} audit logs older than {days} days',
                success=True,
                username=session.get('username'),
                location_id=session.get('location_id')
            )
            
            return jsonify({
                'message': f'Successfully deleted {deleted_count} audit log(s)',
                'deleted_count': deleted_count,
                'cutoff_date': cutoff_date.isoformat()
            }), 200
            
    except Exception as e:
        logger.error(f"Error cleaning up audit logs: {e}")
        return jsonify({'error': str(e)}), 500


# Settings API Endpoints - Users, Locations, Companies, Departments, Applications
@jwt_required()
@api.get('/users')
def get_users():
    """Get all users from unified database with locations, companies, departments"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Get all users
            cur.execute("""
                SELECT id, username, full_name, role,
                       is_active, is_super_admin, created_date, last_login, designation
                FROM users
                ORDER BY username
            """)
            
            users_dict = {}
            for row in cur.fetchall():
                user_id = row[0]
                users_dict[user_id] = {
                    'id': user_id,
                    'username': row[1],
                    'full_name': row[2],
                    'role': row[3],
                    'is_active': row[4],
                    'is_super_admin': row[5],
                    'created_date': row[6].isoformat() if row[6] else None,
                    'last_login': row[7].isoformat() if row[7] else None,
                    'designation': row[8],
                    'locations': [],
                    'companies': [],
                    'departments': [],
                    'applications': [],
                    'location_count': 0
                }
            
            # Get locations for all users
            user_ids = list(users_dict.keys())
            if user_ids:
                placeholders = ','.join(['%s'] * len(user_ids))
                cur.execute(f"""
                    SELECT ul.user_id, l.id, l.location_code, l.location_name
                    FROM user_locations ul
                    JOIN locations l ON ul.location_id = l.id AND l.is_active = TRUE
                    WHERE ul.user_id IN ({placeholders})
                    ORDER BY l.location_name
                """, user_ids)
                
                for row in cur.fetchall():
                    user_id = row[0]
                    if user_id in users_dict:
                        users_dict[user_id]['locations'].append({
                            'id': row[1],
                            'code': row[2],
                            'name': row[3]
                        })
                        users_dict[user_id]['location_count'] = len(users_dict[user_id]['locations'])
                
                # Get companies for all users
                cur.execute(f"""
                    SELECT uc.user_id, c.id, c.company_code, c.company_name
                    FROM user_companies uc
                    JOIN companies c ON uc.company_id = c.id AND c.is_active = TRUE
                    WHERE uc.user_id IN ({placeholders})
                    ORDER BY c.company_name
                """, user_ids)
                
                for row in cur.fetchall():
                    user_id = row[0]
                    if user_id in users_dict:
                        users_dict[user_id]['companies'].append({
                            'id': row[1],
                            'code': row[2],
                            'name': row[3]
                        })
                
                # Get departments for all users
                cur.execute(f"""
                    SELECT ud.user_id, d.id, d.department_code, d.department_name
                    FROM user_departments ud
                    JOIN departments d ON ud.department_id = d.id AND d.is_active = TRUE
                    WHERE ud.user_id IN ({placeholders})
                    ORDER BY d.department_name
                """, user_ids)
                
                for row in cur.fetchall():
                    user_id = row[0]
                    if user_id in users_dict:
                        users_dict[user_id]['departments'].append({
                            'id': row[1],
                            'code': row[2],
                            'name': row[3]
                        })
                
                # Get applications for all users
                cur.execute(f"""
                    SELECT ua.user_id, a.id, a.app_name, ua.can_access
                    FROM user_applications ua
                    JOIN applications a ON ua.application_id = a.id
                    WHERE ua.user_id IN ({placeholders})
                    ORDER BY a.app_name
                """, user_ids)
                
                for row in cur.fetchall():
                    user_id = row[0]
                    if user_id in users_dict:
                        users_dict[user_id]['applications'].append({
                            'id': row[1],
                            'name': row[2],
                            'can_access': row[3]
                        })
            
            users = list(users_dict.values())
            return jsonify({'users': users, 'total': len(users)})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
@api.get('/settings/users/<int:user_id>')
def get_settings_user(user_id):
    """Get single user details for settings"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Get user basic info
            cur.execute("""
                SELECT id, username, full_name, role, is_active, is_super_admin
                FROM users WHERE id = %s
            """, (user_id,))
            
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'User not found'}), 404
            
            user = {
                'id': row[0],
                'username': row[1],
                'full_name': row[2],
                'role': row[3],
                'is_active': row[4],
                'is_super_admin': row[5],
                'locations': [],
                'companies': [],
                'departments': [],
                'applications': []
            }
            
            # Get user locations
            cur.execute("""
                SELECT l.id, l.location_code, l.location_name
                FROM user_locations ul
                JOIN locations l ON ul.location_id = l.id
                WHERE ul.user_id = %s
            """, (user_id,))
            user['locations'] = [{'id': r[0], 'code': r[1], 'name': r[2]} for r in cur.fetchall()]
            
            # Get user companies
            cur.execute("""
                SELECT c.id, c.company_code, c.company_name
                FROM user_companies uc
                JOIN companies c ON uc.company_id = c.id
                WHERE uc.user_id = %s
            """, (user_id,))
            user['companies'] = [{'id': r[0], 'code': r[1], 'name': r[2]} for r in cur.fetchall()]
            
            # Get user departments
            cur.execute("""
                SELECT d.id, d.department_code, d.department_name
                FROM user_departments ud
                JOIN departments d ON ud.department_id = d.id
                WHERE ud.user_id = %s
            """, (user_id,))
            user['departments'] = [{'id': r[0], 'code': r[1], 'name': r[2]} for r in cur.fetchall()]
            
            # Get user applications
            cur.execute("""
                SELECT a.id, a.app_name
                FROM user_applications ua
                JOIN applications a ON ua.application_id = a.id
                WHERE ua.user_id = %s AND ua.can_access = TRUE
            """, (user_id,))
            user['applications'] = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
            
            return jsonify({'user': user})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.post('/settings/users')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def create_settings_user():
    """Create new user"""
    try:
        from unified_db import get_unified_db_connection
        import traceback
        import pg8000.exceptions
        
        data = request.get_json()
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        full_name = data.get('full_name', '').strip()
        role = data.get('role', 'user').strip()
        locations = data.get('locations', [])
        companies = data.get('companies', [])
        departments = data.get('departments', [])
        applications = data.get('applications', [])
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        if not locations or len(locations) == 0:
            return jsonify({'error': 'At least one location is required'}), 400
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if username exists
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return jsonify({'error': 'Username already exists'}), 400
            
            # Create user
            password_hash = SecurityManager.hash_password(password)
            claims = get_jwt()
            created_by = claims.get('user_id')
            
            try:
                cur.execute("""
                    INSERT INTO users (username, password_hash, full_name, role, is_active, created_by)
                    VALUES (%s, %s, %s, %s, TRUE, %s)
                    RETURNING id
                """, (username, password_hash, full_name, role, created_by))
                
                user_id = cur.fetchone()[0]
            except pg8000.exceptions.DatabaseError as db_err:
                # Handle unique constraint violations
                error_msg = str(db_err)
                if '23505' in error_msg or 'unique constraint' in error_msg.lower():
                    if 'username' in error_msg.lower():
                        return jsonify({'error': 'Username already exists'}), 400
                    else:
                        return jsonify({'error': 'Duplicate entry found'}), 400
                # Re-raise other database errors
                raise
            
            # Add locations
            for loc_id in locations:
                cur.execute("""
                    INSERT INTO user_locations (user_id, location_id)
                    VALUES (%s, %s)
                """, (user_id, loc_id))
            
            # Add companies
            for comp_id in companies:
                cur.execute("""
                    INSERT INTO user_companies (user_id, company_id)
                    VALUES (%s, %s)
                """, (user_id, comp_id))
            
            # Add departments
            for dept_id in departments:
                cur.execute("""
                    INSERT INTO user_departments (user_id, department_id)
                    VALUES (%s, %s)
                """, (user_id, dept_id))
            
            # Add applications
            for app_id in applications:
                cur.execute("""
                    INSERT INTO user_applications (user_id, application_id, can_access)
                    VALUES (%s, %s, TRUE)
                """, (user_id, app_id))
            
            conn.commit()
            
            return jsonify({
                'message': 'User created successfully',
                'user_id': user_id
            }), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR: Failed to create user: {str(e)}")
        print(f"ERROR: Traceback: {error_trace}")
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500


@api.put('/settings/users/<int:user_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def update_settings_user(user_id):
    """Update user"""
    try:
        from unified_db import get_unified_db_connection
        import pg8000.exceptions
        
        data = request.get_json()
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT id, is_super_admin FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            if not result:
                return jsonify({'error': 'User not found'}), 404
            
            is_super_admin = result[1]
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            if 'full_name' in data:
                update_fields.append('full_name = %s')
                params.append(data['full_name'].strip())
            
            if 'role' in data:
                update_fields.append('role = %s')
                params.append(data['role'].strip())
            
            if 'is_active' in data and not is_super_admin:
                update_fields.append('is_active = %s')
                params.append(data['is_active'])
            
            if 'password' in data and data['password'].strip():
                update_fields.append('password_hash = %s')
                params.append(SecurityManager.hash_password(data['password'].strip()))
            
            if update_fields:
                claims = get_jwt()
                updated_by = claims.get('user_id')
                update_fields.append('updated_by = %s')
                params.append(updated_by)
                params.append(user_id)
                
                try:
                    cur.execute(f"""
                        UPDATE users SET {', '.join(update_fields)}
                        WHERE id = %s
                    """, params)
                except pg8000.exceptions.DatabaseError as db_err:
                    # Handle unique constraint violations
                    error_msg = str(db_err)
                    if '23505' in error_msg or 'unique constraint' in error_msg.lower():
                        if 'username' in error_msg.lower():
                            return jsonify({'error': 'Username already exists'}), 400
                        else:
                            return jsonify({'error': 'Duplicate entry found'}), 400
                    # Re-raise other database errors
                    raise
            
            # Update locations
            if 'locations' in data:
                if not data['locations']:
                    return jsonify({'error': 'At least one location is required'}), 400
                
                cur.execute("DELETE FROM user_locations WHERE user_id = %s", (user_id,))
                for loc_id in data['locations']:
                    cur.execute("""
                        INSERT INTO user_locations (user_id, location_id)
                        VALUES (%s, %s)
                    """, (user_id, loc_id))
            
            # Update companies
            if 'companies' in data:
                cur.execute("DELETE FROM user_companies WHERE user_id = %s", (user_id,))
                for comp_id in data['companies']:
                    cur.execute("""
                        INSERT INTO user_companies (user_id, company_id)
                        VALUES (%s, %s)
                    """, (user_id, comp_id))
            
            # Update departments
            if 'departments' in data:
                cur.execute("DELETE FROM user_departments WHERE user_id = %s", (user_id,))
                for dept_id in data['departments']:
                    cur.execute("""
                        INSERT INTO user_departments (user_id, department_id)
                        VALUES (%s, %s)
                    """, (user_id, dept_id))
            
            # Update applications
            if 'applications' in data:
                cur.execute("DELETE FROM user_applications WHERE user_id = %s", (user_id,))
                for app_id in data['applications']:
                    cur.execute("""
                        INSERT INTO user_applications (user_id, application_id, can_access)
                        VALUES (%s, %s, TRUE)
                    """, (user_id, app_id))
            
            conn.commit()
            
            return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.delete('/settings/users/<int:user_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_settings_user(user_id):
    """Delete user"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if user exists and is super admin
            cur.execute("SELECT is_super_admin FROM users WHERE id = %s", (user_id,))
            result = cur.fetchone()
            
            if not result:
                return jsonify({'error': 'User not found'}), 404
            
            if result[0]:  # is_super_admin
                return jsonify({'error': 'Cannot delete super admin user'}), 400

            # Check if the user is a project head
            cur.execute("SELECT COUNT(*) FROM projects WHERE head_id = %s", (user_id,))
            project_count = cur.fetchone()[0]
            if project_count > 0:
                return jsonify({'error': f'Cannot delete user who is head of {project_count} project(s). Please reassign them first.'}), 400
            
            # Delete user (cascading deletes will handle related records)
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            
            return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@api.get('/locations')
def get_locations():
    """Get all locations from unified database"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, location_code, location_name, address, city, state, country,
                       is_active, created_date
                FROM locations
                WHERE is_active = TRUE
                ORDER BY location_name
            """)
            
            locations = []
            for row in cur.fetchall():
                locations.append({
                    'id': row[0],
                    'code': row[1],
                    'name': row[2],
                    'address': row[3],
                    'city': row[4],
                    'state': row[5],
                    'country': row[6],
                    'is_active': row[7],
                    'created_at': row[8].isoformat() if row[8] else None
                })
            
            return jsonify({'locations': locations, 'total': len(locations)})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.post('/locations')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def create_location():
    """Create new location"""
    try:
        from unified_db import get_unified_db_connection
        
        data = request.get_json()
        code = data.get('code', '').strip().upper()
        name = data.get('name', '').strip()
        
        if not code or not name:
            return jsonify({'error': 'Location code and name are required'}), 400
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if code already exists
            cur.execute("SELECT id FROM locations WHERE location_code = %s", (code,))
            if cur.fetchone():
                return jsonify({'error': 'Location code already exists'}), 400
            
            # Create location
            claims = get_jwt()
            user_id = claims.get('user_id')
            cur.execute("""
                INSERT INTO locations (location_code, location_name, is_active, created_by)
                VALUES (%s, %s, TRUE, %s)
                RETURNING id
            """, (code, name, user_id))
            
            result = cur.fetchone()
            conn.commit()
            
            return jsonify({
                'message': 'Location created successfully',
                'location_id': result[0]
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.put('/locations/<int:location_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def update_location(location_id):
    """Update location"""
    try:
        from unified_db import get_unified_db_connection
        
        data = request.get_json()
        code = data.get('code', '').strip().upper()
        name = data.get('name', '').strip()
        
        if not code or not name:
            return jsonify({'error': 'Location code and name are required'}), 400
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if location exists
            cur.execute("SELECT id FROM locations WHERE id = %s", (location_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Location not found'}), 404
            
            # Check if new code conflicts with another location
            cur.execute(
                "SELECT id FROM locations WHERE location_code = %s AND id != %s",
                (code, location_id)
            )
            if cur.fetchone():
                return jsonify({'error': 'Location code already exists'}), 400
            
            # Update location
            claims = get_jwt()
            user_id = claims.get('user_id')
            cur.execute("""
                UPDATE locations 
                SET location_code = %s, location_name = %s, updated_by = %s
                WHERE id = %s
            """, (code, name, user_id, location_id))
            
            conn.commit()
            
            return jsonify({'message': 'Location updated successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.delete('/locations/<int:location_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_location(location_id):
    """Delete location and cascade delete empty departments"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if this is the last location
            cur.execute("SELECT COUNT(*) FROM locations WHERE is_active = TRUE")
            total_locations = cur.fetchone()[0]
            
            if total_locations <= 1:
                return jsonify({
                    'error': 'Cannot delete the last location. At least one location must exist.'
                }), 400
            
            # Check if location is set as primary location for any users
            # If yes, set their location_id to NULL (unassign them)
            cur.execute("""
                SELECT COUNT(*) FROM users WHERE location_id = %s
            """, (location_id,))
            
            users_count = cur.fetchone()[0]
            
            if users_count > 0:
                # Unassign users from this location
                cur.execute("""
                    UPDATE users SET location_id = NULL WHERE location_id = %s
                """, (location_id,))
                print(f"Unassigned {users_count} user(s) from location {location_id}")
            
            # Delete user_locations junction table entries (these will be cascade deleted anyway)
            cur.execute("""
                DELETE FROM user_locations WHERE location_id = %s
            """, (location_id,))
            
            # Check if location has departments with users assigned directly
            cur.execute("""
                SELECT d.id, d.department_name, COUNT(u.id) as user_count
                FROM departments d
                LEFT JOIN users u ON d.id = u.department_id AND u.is_active = TRUE
                WHERE d.location_id = %s
                GROUP BY d.id, d.department_name
                HAVING COUNT(u.id) > 0
            """, (location_id,))
            
            depts_with_users = cur.fetchall()
            
            if depts_with_users:
                dept_names = [dept[1] for dept in depts_with_users]
                total_users = sum(dept[2] for dept in depts_with_users)
                conn.rollback()
                return jsonify({
                    'error': f'Cannot delete location. {len(depts_with_users)} department(s) have {total_users} user(s): {", ".join(dept_names)}. Please reassign users first.'
                }), 400
            
            # Delete empty departments at this location
            cur.execute("DELETE FROM departments WHERE location_id = %s", (location_id,))
            
            # Delete location
            cur.execute("DELETE FROM locations WHERE id = %s", (location_id,))
            conn.commit()
            
            return jsonify({'message': 'Location deleted successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@api.get('/companies')
def get_companies():
    """Get all companies from unified database"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, company_code, company_name, created_date
                FROM companies
                WHERE is_active = TRUE
                ORDER BY company_name
            """)
            
            companies = []
            for row in cur.fetchall():
                companies.append({
                    'id': row[0],
                    'company_code': row[1],
                    'company_name': row[2],
                    'code': row[1],
                    'created_date': row[3].isoformat() if row[3] else None
                })
            
            return jsonify({'companies': companies, 'total': len(companies)})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.post('/companies')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def create_company():
    """Create new company"""
    try:
        from unified_db import get_unified_db_connection
        
        data = request.get_json()
        company_code = data.get('company_code', '').strip().upper()
        company_name = data.get('company_name', '').strip()
        
        if not company_code or not company_name:
            return jsonify({'error': 'Company code and name are required'}), 400
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if company code already exists
            cur.execute(
                "SELECT id FROM companies WHERE company_code = %s",
                (company_code,)
            )
            if cur.fetchone():
                return jsonify({'error': 'Company code already exists'}), 400
            
            # Insert new company
            claims = get_jwt()
            user_id = claims.get('user_id')
            cur.execute("""
                INSERT INTO companies (company_code, company_name, is_active, created_by)
                VALUES (%s, %s, TRUE, %s)
                RETURNING id
            """, (company_code, company_name, user_id))
            
            result = cur.fetchone()
            conn.commit()
            
            return jsonify({
                'message': 'Company created successfully',
                'company_id': result[0]
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.put('/companies/<int:company_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def update_company(company_id):
    """Update company"""
    try:
        from unified_db import get_unified_db_connection
        
        data = request.get_json()
        company_code = data.get('company_code', '').strip().upper()
        company_name = data.get('company_name', '').strip()
        
        if not company_code or not company_name:
            return jsonify({'error': 'Company code and name are required'}), 400
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if company exists
            cur.execute("SELECT id FROM companies WHERE id = %s", (company_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Company not found'}), 404
            
            # Check if new code conflicts with another company
            cur.execute(
                "SELECT id FROM companies WHERE company_code = %s AND id != %s",
                (company_code, company_id)
            )
            if cur.fetchone():
                return jsonify({'error': 'Company code already exists'}), 400
            
            # Update company
            claims = get_jwt()
            user_id = claims.get('user_id')
            cur.execute("""
                UPDATE companies 
                SET company_code = %s, company_name = %s, updated_by = %s
                WHERE id = %s
            """, (company_code, company_name, user_id, company_id))
            
            conn.commit()
            
            return jsonify({'message': 'Company updated successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.delete('/companies/<int:company_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_company(company_id):
    """Delete company"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Get company details before deleting
            cur.execute(
                "SELECT company_code, company_name FROM companies WHERE id = %s",
                (company_id,)
            )
            result = cur.fetchone()
            if not result:
                return jsonify({'error': 'Company not found'}), 404
            
            # Check if this is the last company
            cur.execute("SELECT COUNT(*) FROM companies WHERE is_active = TRUE")
            total_companies = cur.fetchone()[0]
            
            if total_companies <= 1:
                return jsonify({
                    'error': 'Cannot delete the last company. At least one company must exist.'
                }), 400
            
            # Check if company has locations
            cur.execute(
                "SELECT COUNT(*) FROM locations WHERE company_id = %s",
                (company_id,)
            )
            location_count = cur.fetchone()[0]
            
            if location_count > 0:
                return jsonify({
                    'error': f'Cannot delete company with {location_count} location(s). Please reassign or delete locations first.'
                }), 400
            
            # Check if company has users
            cur.execute(
                "SELECT COUNT(*) FROM user_companies WHERE company_id = %s",
                (company_id,)
            )
            user_count = cur.fetchone()[0]
            
            if user_count > 0:
                return jsonify({
                    'error': f'Cannot delete company with {user_count} user(s). Please reassign users first.'
                }), 400
            
            # Delete company
            cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))
            conn.commit()
            
            return jsonify({'message': 'Company deleted successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@api.get('/departments')
def get_departments():
    """Get all departments from unified database with user counts"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT d.id, d.department_code, d.department_name,
                       d.is_active, d.created_date, 
                       COUNT(DISTINCT ud.user_id) as user_count
                FROM departments d
                LEFT JOIN user_departments ud ON d.id = ud.department_id
                LEFT JOIN users u ON ud.user_id = u.id AND u.is_active = TRUE
                WHERE d.is_active = TRUE
                GROUP BY d.id, d.department_code, d.department_name,
                         d.is_active, d.created_date
                ORDER BY d.department_name
            """)
            
            departments = []
            for row in cur.fetchall():
                departments.append({
                    'id': row[0],
                    'department_code': row[1],
                    'department_name': row[2],
                    'is_active': row[3],
                    'created_date': row[4].isoformat() if row[4] else None,
                    'user_count': row[5]
                })
            
            return jsonify({'departments': departments, 'total': len(departments)})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.post('/departments')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def create_department():
    """Create new department"""
    try:
        from unified_db import get_unified_db_connection
        
        data = request.get_json()
        department_code = data.get('department_code', '').strip().upper()
        department_name = data.get('department_name', '').strip()
        description = data.get('description', '').strip()
        
        if not department_code or not department_name:
            return jsonify({'error': 'Department code and name are required'}), 400
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if department code already exists
            cur.execute(
                "SELECT id FROM departments WHERE department_code = %s",
                (department_code,)
            )
            if cur.fetchone():
                return jsonify({'error': 'Department code already exists'}), 400
            
            # Insert new department
            claims = get_jwt()
            user_id = claims.get('user_id')
            cur.execute("""
                INSERT INTO departments (department_code, department_name, description, is_active, created_by)
                VALUES (%s, %s, %s, TRUE, %s)
                RETURNING id
            """, (department_code, department_name, description, user_id))
            
            result = cur.fetchone()
            conn.commit()
            
            return jsonify({
                'message': 'Department created successfully',
                'department_id': result[0]
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.put('/departments/<int:department_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def update_department(department_id):
    """Update department"""
    try:
        from unified_db import get_unified_db_connection
        
        data = request.get_json()
        department_code = data.get('department_code', '').strip().upper()
        department_name = data.get('department_name', '').strip()
        description = data.get('description', '').strip()
        
        if not department_code or not department_name:
            return jsonify({'error': 'Department code and name are required'}), 400
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if department exists
            cur.execute("SELECT id FROM departments WHERE id = %s", (department_id,))
            if not cur.fetchone():
                return jsonify({'error': 'Department not found'}), 404
            
            # Check if new code conflicts with another department
            cur.execute(
                "SELECT id FROM departments WHERE department_code = %s AND id != %s",
                (department_code, department_id)
            )
            if cur.fetchone():
                return jsonify({'error': 'Department code already exists'}), 400
            
            # Update department
            claims = get_jwt()
            user_id = claims.get('user_id')
            cur.execute("""
                UPDATE departments 
                SET department_code = %s, department_name = %s, description = %s, updated_by = %s
                WHERE id = %s
            """, (department_code, department_name, description, user_id, department_id))
            
            conn.commit()
            
            return jsonify({'message': 'Department updated successfully'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.delete('/departments/<int:department_id>')
@role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_department(department_id):
    """Delete department"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if department exists
            cur.execute(
                "SELECT department_name FROM departments WHERE id = %s",
                (department_id,)
            )
            result = cur.fetchone()
            if not result:
                return jsonify({'error': 'Department not found'}), 404
            
            # Check if department is set as primary department for any users
            # If yes, set their department_id to NULL (unassign them)
            cur.execute("""
                SELECT COUNT(*) FROM users WHERE department_id = %s
            """, (department_id,))
            
            users_count = cur.fetchone()[0]
            
            if users_count > 0:
                # Unassign users from this department
                cur.execute("""
                    UPDATE users SET department_id = NULL WHERE department_id = %s
                """, (department_id,))
                print(f"Unassigned {users_count} user(s) from department {department_id}")
            
            # Check if department has child departments
            cur.execute("""
                SELECT COUNT(*) FROM departments WHERE parent_department_id = %s
            """, (department_id,))
            
            child_dept_count = cur.fetchone()[0]
            if child_dept_count > 0:
                return jsonify({
                    'error': f'Cannot delete department with {child_dept_count} sub-department(s). Please reassign or delete sub-departments first.'
                }), 400
            
            # Check if department is assigned to any projects
            cur.execute("""
                SELECT COUNT(*) FROM projects WHERE department_id = %s
            """, (department_id,))
            
            project_count = cur.fetchone()[0]
            if project_count > 0:
                return jsonify({
                    'error': f'Cannot delete department with {project_count} project(s). Please reassign projects first.'
                }), 400
            
            # Delete department
            try:
                cur.execute("DELETE FROM departments WHERE id = %s", (department_id,))
                conn.commit()
                return jsonify({'message': 'Department deleted successfully'})
            except Exception as delete_error:
                conn.rollback()
                error_msg = str(delete_error)
                # Check if it's a foreign key constraint error
                if 'foreign key constraint' in error_msg.lower() or '23503' in error_msg:
                    return jsonify({
                        'error': 'Cannot delete department. It is still referenced by users or other records. Please reassign all users first.'
                    }), 400
                raise
            
    except Exception as e:
        error_msg = str(e)
        if 'foreign key constraint' in error_msg.lower() or '23503' in error_msg:
            return jsonify({
                'error': 'Cannot delete department. It is still referenced by users or other records. Please reassign all users first.'
            }), 400
        return jsonify({'error': error_msg}), 500


@jwt_required()
@api.get('/applications')
def get_applications():
    """Get all applications from unified database"""
    try:
        from unified_db import get_unified_db_connection
        from datetime import datetime
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id, a.app_name, a.app_description, a.app_icon, a.app_url,
                       a.is_active, a.created_date, a.display_order,
                       MAX(ua.last_accessed) as last_accessed
                FROM applications a
                LEFT JOIN user_applications ua ON a.id = ua.application_id
                GROUP BY a.id, a.app_name, a.app_description, a.app_icon, a.app_url,
                         a.is_active, a.created_date, a.display_order
                ORDER BY a.display_order, a.app_name
            """)
            
            applications = []
            for row in cur.fetchall():
                applications.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'icon': row[3] or 'fas fa-cube',
                    'route': row[4],
                    'is_active': row[5],
                    'created_date': row[6].isoformat() if row[6] else None,
                    'sort_order': row[7],
                    'last_accessed': row[8].isoformat() if row[8] else None
                })
            
            return jsonify({'applications': applications, 'total': len(applications)})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@api.get('/applications/<int:app_id>/size')
def get_application_size(app_id):
    """Get application size"""
    # Mock data for now
    return jsonify({
        'total_size': 'N/A',
        'folder_size': 'N/A',
        'database_size': 'N/A'
    })


@api.put('/applications/<int:app_id>/toggle')
def toggle_application(app_id):
    """Toggle application active status"""
    return jsonify({'message': 'Application status updated'})


# ==================== DESIGNATION MANAGEMENT ENDPOINTS ====================

@jwt_required()
@api.get('/designations')
def get_designations():
    """Get all designations"""
    try:
        from models import Designation
        
        designations = Designation.query.filter_by(is_active=True).order_by(Designation.designation_name).all()
        
        return jsonify({
            'designations': [{
                'id': d.id,
                'designation_code': d.designation_code,
                'designation_name': d.designation_name,
                'is_active': d.is_active,
                'created_date': d.created_date.isoformat() if d.created_date else None
            } for d in designations],
            'total': len(designations)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.post('/designations')
@role_required(UserRole.ADMIN)
def create_designation():
    """Create new designation"""
    try:
        from models import Designation
        
        payload = request.get_json(force=True) or {}
        code = payload.get('code', '').strip().upper()
        name = payload.get('name', '').strip()
        
        # Validate inputs
        if not code or not name:
            return jsonify({'error': 'Designation code and name are required'}), 400
        
        # Check if code already exists
        existing = Designation.query.filter_by(designation_code=code).first()
        if existing:
            return jsonify({'error': 'Designation code already exists'}), 400
        
        # Create designation
        claims = get_jwt()
        user_id = claims.get('user_id')
        
        designation = Designation(
            designation_code=code,
            designation_name=name,
            is_active=True,
            created_by=user_id
        )
        
        db.session.add(designation)
        db.session.commit()
        
        return jsonify({
            'message': 'Designation created successfully',
            'designation': {
                'id': designation.id,
                'code': designation.designation_code,
                'name': designation.designation_name
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api.put('/designations/<int:designation_id>')
@role_required(UserRole.ADMIN)
def update_designation(designation_id):
    """Update designation"""
    try:
        from models import Designation
        
        designation = db.session.get(Designation, designation_id)
        if not designation:
            return jsonify({'error': 'Designation not found'}), 404
        
        payload = request.get_json(force=True) or {}
        code = payload.get('code', '').strip().upper()
        name = payload.get('name', '').strip()
        
        # Validate inputs
        if not code or not name:
            return jsonify({'error': 'Designation code and name are required'}), 400
        
        # Check if new code conflicts with another designation
        existing = Designation.query.filter(
            Designation.designation_code == code,
            Designation.id != designation_id
        ).first()
        if existing:
            return jsonify({'error': 'Designation code already exists'}), 400
        
        # Update designation
        claims = get_jwt()
        user_id = claims.get('user_id')
        
        designation.designation_code = code
        designation.designation_name = name
        designation.updated_by = user_id
        
        db.session.commit()
        
        return jsonify({'message': 'Designation updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api.delete('/designations/<int:designation_id>')
@role_required(UserRole.ADMIN)
def delete_designation(designation_id):
    """Delete designation"""
    try:
        from models import Designation, User
        
        designation = db.session.get(Designation, designation_id)
        if not designation:
            return jsonify({'error': 'Designation not found'}), 404
        
        # Check if any users have this designation and get their names
        users = User.query.filter_by(designation=designation.designation_name).limit(5).all()
        
        if users:
            user_names = [f"{u.full_name} ({u.username})" if u.full_name else u.username for u in users]
            total_user_count = User.query.filter_by(designation=designation.designation_name).count()
            
            user_list = ", ".join(user_names[:3])
            if total_user_count > 3:
                user_list += f" and {total_user_count - 3} more"
            
            return jsonify({
                'error': f'Cannot delete designation with {total_user_count} user(s): {user_list}. Please reassign users first.'
            }), 400
        
        db.session.delete(designation)
        db.session.commit()
        
        return jsonify({'message': 'Designation deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ==================== DEPARTMENTS AND DESIGNATIONS ====================

@jwt_required()
@api.get('/hardcoded/departments')
def get_hardcoded_departments():
    """Get departments list from database (for backward compatibility)"""
    try:
        from unified_db import get_unified_db_connection
        
        with get_unified_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, department_code, department_name
                FROM departments
                WHERE is_active = TRUE
                ORDER BY department_name
            """)
            
            departments = []
            for row in cur.fetchall():
                departments.append({
                    'id': row[0],
                    'code': row[1],
                    'name': row[2]
                })
            
            return jsonify({'departments': departments})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@jwt_required()
@api.get('/hardcoded/designations')
def get_hardcoded_designations():
    """Get designations list from database"""
    from models import Designation
    designations = Designation.query.filter_by(is_active=True).all()
    return jsonify({'designations': [
        {'code': d.designation_code, 'name': d.designation_name, 'id': d.id}
        for d in designations
    ]})


@jwt_required()
@api.get('/templates')
def get_templates():
    """Get all available project templates"""
    from models import ProjectTemplate
    
    templates = ProjectTemplate.query.filter_by(is_active=True).order_by(ProjectTemplate.id).all()
    
    return jsonify({
        'templates': [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
            }
            for t in templates
        ]
    })


@jwt_required()
@api.get('/template-structure')
def get_template_structure():
    """Get the template phase and stage structure from the database"""
    from models import ProjectTemplate, Department, Designation, User
    
    # Get the first active template (default template)
    template = ProjectTemplate.query.filter_by(is_active=True).order_by(ProjectTemplate.id).first()
    
    if not template:
        return jsonify({'structure': [], 'template_id': None, 'template_name': None})
    
    # Build structure from database template
    structure = []
    for phase in template.phases:
        if not phase.is_active:
            continue
            
        stages = []
        for stage in phase.stages:
            if not stage.is_active:
                continue
            
            # Get department code
            department_code = None
            if stage.default_responsible_department_id:
                dept = Department.query.get(stage.default_responsible_department_id)
                department_code = dept.department_code if dept else None
            
            # Get designation code (for frontend consistency)
            designation_code = None
            if stage.default_designation_id:
                desig = Designation.query.get(stage.default_designation_id)
                designation_code = desig.designation_code if desig else None
            
            # Get responsible user info
            responsible_user_id = stage.default_responsible_user_id
            responsible_user_name = None
            if responsible_user_id:
                user = User.query.get(responsible_user_id)
                responsible_user_name = user.full_name if user else None
            
            stage_info = {
                'name': stage.name,
                'department': department_code,
                'designation': designation_code,
                'responsible_user_id': responsible_user_id,
                'responsible_user_name': responsible_user_name,
                'default_responsible_user_id': responsible_user_id,  # For backward compatibility
                'default_responsible_department_id': stage.default_responsible_department_id,  # For frontend
                'duration': stage.default_expected_duration_days
            }
            stages.append(stage_info)
        
        structure.append({
            'name': phase.name,
            'stages': stages
        })
    
    return jsonify({
        'structure': structure,
        'template_id': template.id,
        'template_name': template.name
    })


@api.put('/template-structure')
@jwt_required()
@role_required(UserRole.ADMIN)
def update_template_structure():
    """Update the template phase and stage structure in the database"""
    from models import ProjectTemplate, ProjectTemplatePhase, ProjectTemplateStage, Department, Designation
    
    # Debug logging
    logger.info("=== UPDATE TEMPLATE STRUCTURE REQUEST ===")
    logger.info(f"Headers: {dict(request.headers)}")
    try:
        claims = get_jwt()
        logger.info(f"JWT Claims: {claims}")
        logger.info(f"User: {claims.get('username')}, Role: {claims.get('role')}")
    except Exception as e:
        logger.error(f"Failed to get JWT claims: {e}")
    
    data = request.get_json()
    structure = data.get('structure', [])
    
    if not structure:
        return jsonify({'error': 'Structure is required'}), 400
    
    logger.info(f"Received structure with {len(structure)} phases")
    
    # Validate structure
    for phase in structure:
        if 'name' not in phase or 'stages' not in phase:
            return jsonify({'error': 'Invalid phase structure'}), 400
        for stage in phase['stages']:
            if 'name' not in stage:
                return jsonify({'error': 'Invalid stage structure'}), 400
    
    try:
        # Get or create the default template
        template = ProjectTemplate.query.filter_by(is_active=True).order_by(ProjectTemplate.id).first()
        
        if not template:
            # Create a new default template
            template = ProjectTemplate(
                name='Default APQP Template',
                description='Default APQP process template',
                is_active=True
            )
            db.session.add(template)
            db.session.flush()  # Get the template ID
        
        # Get department and designation lookups
        departments = {dept.department_code: dept.id for dept in Department.query.filter_by(is_active=True).all()}
        designations_by_code = {desig.designation_code: desig.id for desig in Designation.query.filter_by(is_active=True).all()}
        designations_by_name = {desig.designation_name: desig.id for desig in Designation.query.filter_by(is_active=True).all()}
        
        logger.info(f"Available departments: {list(departments.keys())}")
        logger.info(f"Available designation codes: {list(designations_by_code.keys())}")
        
        # Delete existing phases and stages (cascade will handle stages)
        ProjectTemplatePhase.query.filter_by(template_id=template.id).delete()
        
        # Create new phases and stages
        for phase_idx, phase_data in enumerate(structure, start=1):
            logger.info(f"Creating phase {phase_idx}: {phase_data['name']}")
            phase = ProjectTemplatePhase(
                template_id=template.id,
                name=phase_data['name'],
                serial_number=phase_idx,
                is_active=True
            )
            db.session.add(phase)
            db.session.flush()  # Get the phase ID
            
            # Create stages for this phase
            for stage_idx, stage_data in enumerate(phase_data['stages'], start=1):
                # Resolve department ID
                department_id = None
                if 'department' in stage_data and stage_data['department']:
                    department_id = departments.get(stage_data['department'])
                    if department_id:
                        logger.info(f"  Stage {stage_idx}: Mapped department '{stage_data['department']}' to ID {department_id}")
                    else:
                        logger.warning(f"  Stage {stage_idx}: Department '{stage_data['department']}' not found")
                
                # Resolve designation ID - try code first, then name for backward compatibility
                designation_id = None
                if 'designation' in stage_data and stage_data['designation']:
                    # Try to resolve by code first
                    designation_id = designations_by_code.get(stage_data['designation'])
                    if not designation_id:
                        # Fall back to name lookup
                        designation_id = designations_by_name.get(stage_data['designation'])
                    
                    if designation_id:
                        logger.info(f"  Stage {stage_idx}: Mapped designation '{stage_data['designation']}' to ID {designation_id}")
                    else:
                        logger.warning(f"  Stage {stage_idx}: Designation '{stage_data['designation']}' not found")
                
                # Get responsible user ID directly from stage_data
                responsible_user_id = stage_data.get('responsible_user_id')
                
                stage = ProjectTemplateStage(
                    template_phase_id=phase.id,
                    name=stage_data['name'],
                    serial_number=stage_idx,
                    default_expected_duration_days=stage_data.get('duration'),
                    default_responsible_department_id=department_id,
                    default_designation_id=designation_id,
                    default_responsible_user_id=responsible_user_id,
                    is_active=True
                )
                db.session.add(stage)
        
        db.session.commit()
        
        # Sync department changes to projects with auto_sync enabled
        sync_departments_to_projects(template.id)
        
        return jsonify({
            'message': 'Template structure updated successfully',
            'template_id': template.id
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def sync_departments_to_projects(template_id):
    """Sync department assignments from template to all projects with auto_sync enabled"""
    try:
        # Get all projects that use this template and have auto_sync enabled
        projects = Project.query.filter_by(
            template_id=template_id,
            auto_sync_with_template=True
        ).all()
        
        if not projects:
            logger.info(f"No projects found with auto_sync enabled for template {template_id}")
            return
        
        logger.info(f"Syncing departments to {len(projects)} projects with auto_sync enabled")
        
        # Get the template stages
        template = db.session.get(ProjectTemplate, template_id)
        if not template:
            return
        
        for project in projects:
            # Match stages by phase serial_number and stage serial_number
            for phase in project.phases:
                # Find matching template phase
                template_phase = next(
                    (tp for tp in template.phases if tp.serial_number == phase.serial_number),
                    None
                )
                if not template_phase:
                    continue
                
                for stage in phase.stages:
                    # Find matching template stage
                    template_stage = next(
                        (ts for ts in template_phase.stages if ts.serial_number == stage.serial_number),
                        None
                    )
                    if template_stage:
                        # Update department from template (only if not already completed)
                        if not stage.actual_end_date:
                            old_dept_id = stage.responsible_department_id
                            stage.responsible_department_id = template_stage.default_responsible_department_id
                            if old_dept_id != stage.responsible_department_id:
                                logger.info(f"Updated stage '{stage.name}' in project {project.id} - department changed from {old_dept_id} to {stage.responsible_department_id}")
        
        db.session.commit()
        logger.info(f"Department sync completed for template {template_id}")
        
    except Exception as e:
        logger.error(f"Error syncing departments to projects: {e}")
        db.session.rollback()


@api.post('/refresh-token')
def refresh_jwt_token():
    """Refresh JWT token if user is still logged in via session"""
    try:
        # Check if user is logged in via session
        if 'user_id' not in session or 'username' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        from flask_jwt_extended import create_access_token
        from datetime import timedelta
        
        # Create new JWT token with extended expiration
        jwt_claims = {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role'),
            'unified_role': session.get('unified_role') or session.get('role'),
            'is_super_admin': session.get('is_super_admin', False)
        }
        
        access_token = create_access_token(
            identity=session.get('username'),
            additional_claims=jwt_claims,
            expires_delta=timedelta(hours=24)
        )
        
        # Update session with new token
        session['jwt_token'] = access_token
        session.modified = True
        
        logger.info(f"JWT token refreshed for user {session.get('username')}")
        
        return jsonify({
            'token': access_token,
            'message': 'Token refreshed successfully'
        })
    
    except Exception as e:
        logger.error(f"Error refreshing JWT token: {e}")
        return jsonify({'error': 'Failed to refresh token'}), 500

