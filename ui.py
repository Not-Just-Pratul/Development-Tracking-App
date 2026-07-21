from flask import Blueprint, render_template, request, redirect, url_for, abort, flash, session
from datetime import date, timedelta
from __init__ import db
from authz import ui_role_required, stage_access_required, can_user_edit_stage
from models import Project, Stage, Step, User, UserRole, Phase, Department, Location, Designation
from secure_auth import login_required
from unified_db import (
    get_all_users,
    get_all_users_with_details,
    get_user_by_id,
    get_all_active_locations,
    get_all_active_companies,
)
import logging

logger = logging.getLogger(__name__)

ui = Blueprint('ui', __name__, url_prefix='/ui')


@ui.get('/')
@login_required
def root():
    return redirect(url_for('ui.dashboard'))


@ui.get('/dashboard')
@login_required
def dashboard():
    # Optimize: Use selectinload to eagerly load relationships in single queries
    from sqlalchemy.orm import selectinload, joinedload
    
    projects = Project.query.options(
        selectinload(Project.phases).selectinload(Phase.stages)
    ).all()
    active_projects = [p for p in projects if p.progress_percent < 100.0]

    # Optimize: Eager load related user data for overdue stages
    overdue_stages = Stage.query.options(
        joinedload(Stage.phase).joinedload(Phase.project),
        joinedload(Stage.responsible),
        joinedload(Stage.responsible_department)
    ).filter(
        Stage.expected_end_date.isnot(None),
        Stage.expected_end_date < date.today(),
        Stage.actual_end_date.is_(None),
    ).order_by(Stage.expected_end_date.asc()).limit(50).all()

    days = int(request.args.get('days', 7))
    window_end = date.today() + timedelta(days=days)
    # Optimize: Eager load relationships and limit results
    upcoming_steps = Step.query.options(
        joinedload(Step.stage).joinedload(Stage.phase).joinedload(Phase.project),
        joinedload(Step.responsible)
    ).filter(
        Step.expected_end_date.isnot(None),
        Step.expected_end_date >= date.today(),
        Step.expected_end_date <= window_end,
        Step.status != 'completed',
    ).order_by(Step.expected_end_date.asc()).limit(100).all()

    # Fetch advanced analytics data directly from database
    from sqlalchemy import func, case, and_
    from datetime import datetime, timezone
    
    analytics_data = {
        'trends': None,
        'user_performance': None,
        'project_health': None
    }
    
    try:
        # Trends data - Track Stage completions with flexible date ranges
        date_range = request.args.get('range', 'all')  # all, 7, 30, 90
        
        query = db.session.query(
            func.date(Stage.actual_end_date).label('date'),
            func.count(Stage.id).label('completed_stages')
        ).filter(
            Stage.actual_end_date.isnot(None)
        )
        
        # Apply date filter if specified
        if date_range != 'all':
            try:
                days = int(date_range)
                start_date = date.today() - timedelta(days=days)
                query = query.filter(Stage.actual_end_date >= start_date)
            except ValueError:
                pass  # Invalid range, show all
        
        completed_stages_trend = query.group_by(func.date(Stage.actual_end_date)).order_by(func.date(Stage.actual_end_date)).all()
        
        analytics_data['trends'] = {
            'daily_completions': [
                {'date': str(item.date), 'completed_steps': item.completed_stages}
                for item in completed_stages_trend
            ]
        }
        
        # User performance data
        today = date.today()
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
        
        # Optimize: Fetch all users at once instead of in loop
        user_ids = [stats.responsible_user_id for stats in user_stage_stats]
        users_dict = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
        
        # Calculate average progress in Python (progress_percent is a property, not a column)
        stages_by_user = {}
        if user_ids:
            stages = Stage.query.filter(Stage.responsible_user_id.in_(user_ids)).all()
            for stage in stages:
                if stage.responsible_user_id not in stages_by_user:
                    stages_by_user[stage.responsible_user_id] = []
                stages_by_user[stage.responsible_user_id].append(stage)
        
        avg_progress_dict = {
            user_id: sum(s.progress_percent for s in user_stages) / len(user_stages) if user_stages else 0
            for user_id, user_stages in stages_by_user.items()
        }
        
        user_performance = []
        for stats in user_stage_stats:
            user = users_dict.get(stats.responsible_user_id)
            if user:
                avg_progress = avg_progress_dict.get(stats.responsible_user_id, 0)
                completion_rate = (stats.completed_stages / stats.total_stages * 100) if stats.total_stages > 0 else 0
                
                # Get user role
                user_role = user.role if hasattr(user, 'role') and user.role else 'User'
                
                user_performance.append({
                    'user_id': user.id,
                    'user_name': user.full_name,
                    'username': user.username,
                    'role': user_role,
                    'total_stages': stats.total_stages,
                    'completed_stages': stats.completed_stages,
                    'overdue_stages': stats.overdue_stages,
                    'completion_rate': round(completion_rate, 2),
                    'performance_score': round((completion_rate * 0.7) + (avg_progress * 0.3), 2)
                })
        
        user_performance.sort(key=lambda x: x['performance_score'], reverse=True)
        
        analytics_data['user_performance'] = {
            'user_performance': user_performance,
            'summary': {
                'top_performer': user_performance[0] if user_performance else None
            }
        }
        
        # Project health data
        project_health = []
        for project in projects:
            # Count all stages across all phases
            all_stages = []
            for phase in project.phases:
                all_stages.extend(phase.stages)
            
            total_stages = len(all_stages)
            completed_stages = len([s for s in all_stages if s.actual_end_date])
            overdue_stages_count = len([s for s in all_stages if s.expected_end_date and s.expected_end_date < date.today() and not s.actual_end_date])
            
            # Risk assessment
            risk_factors = []
            risk_score = 0
            
            if overdue_stages_count > 0:
                risk_factors.append(f"{overdue_stages_count} overdue stage{'s' if overdue_stages_count > 1 else ''}")
                risk_score += overdue_stages_count * 10
            
            # Determine health status based on risk factors
            if len(risk_factors) == 0:
                # No issues = healthy (regardless of progress)
                health_status = 'healthy'
            elif risk_score < 20:
                health_status = 'warning'
            else:
                health_status = 'critical'
            
            project_health.append({
                'project_id': project.id,
                'project_name': project.name,
                'progress_percent': round(project.progress_percent, 1),
                'health_status': health_status,
                'risk_score': risk_score,
                'risk_factors': risk_factors,
                'total_stages': total_stages,
                'completed_stages': completed_stages,
                'overdue_stages': overdue_stages_count
            })
        
        # Sort by risk score (highest risk first)
        project_health.sort(key=lambda x: x['risk_score'], reverse=True)
        
        analytics_data['project_health'] = {
            'project_health': project_health
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Error loading analytics data: {e}", "warning")

    return render_template('dashboard.html',
                           projects=projects,
                           active_projects=active_projects,
                           overdue_stages=overdue_stages,
                           upcoming_steps=upcoming_steps,
                           days=days,
                           analytics=analytics_data)


@ui.get('/projects')
@login_required
def projects_list():
    # Get filter parameters
    company_filter = request.args.get('company', '').strip()
    department_filter = request.args.get('department', '').strip()
    location_filter = request.args.get('location', '').strip()
    head_filter = request.args.get('head', '').strip()
    status_filter = request.args.get('status', '').strip()
    customer_filter = request.args.get('customer', '').strip()
    search_filter = request.args.get('search', '').strip()
    
    # Optimize: Eager load phases for progress calculation
    from sqlalchemy.orm import selectinload, joinedload
    
    # Build query with filters
    query = Project.query.options(
        selectinload(Project.phases),
        joinedload(Project.head),
        joinedload(Project.department),
        joinedload(Project.location_rel)
    )
    
    # Apply filters
    if company_filter:
        query = query.filter(Project.company_name.ilike(f'%{company_filter}%'))
    
    if department_filter:
        query = query.join(Department, Project.department_id == Department.id, isouter=True)\
                    .filter(Department.department_name.ilike(f'%{department_filter}%'))
    
    if location_filter:
        query = query.join(Location, Project.location_id == Location.id, isouter=True)\
                    .filter(Location.location_name.ilike(f'%{location_filter}%'))
    
    if head_filter:
        query = query.join(User, Project.head_id == User.id, isouter=True)\
                    .filter(User.full_name.ilike(f'%{head_filter}%'))
    
    if customer_filter:
        query = query.filter(Project.customer_name.ilike(f'%{customer_filter}%'))
    
    if search_filter:
        search_term = f'%{search_filter}%'
        query = query.filter(
            db.or_(
                Project.name.ilike(search_term),
                Project.part_name.ilike(search_term),
                Project.part_description.ilike(search_term),
                Project.description.ilike(search_term)
            )
        )
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    # Apply status filter after loading (since it's calculated)
    if status_filter:
        if status_filter == 'completed':
            projects = [p for p in projects if p.progress_percent == 100]
        elif status_filter == 'active':
            projects = [p for p in projects if 0 < p.progress_percent < 100]
        elif status_filter == 'pending':
            projects = [p for p in projects if p.progress_percent == 0]
    
    # Get filter options for dropdowns
    all_companies = db.session.query(Project.company_name).filter(Project.company_name.isnot(None)).distinct().all()
    all_departments = Department.query.filter_by(is_active=True).all()
    all_locations = Location.query.filter_by(is_active=True).all()
    all_heads = db.session.query(User).join(Project, User.id == Project.head_id).distinct().all()
    all_customers = db.session.query(Project.customer_name).filter(Project.customer_name.isnot(None)).distinct().all()
    
    # Optimize: Calculate issues in database using subqueries
    from sqlalchemy import func, and_, or_
    today = date.today()
    
    # Get overdue counts per project
    overdue_subquery = db.session.query(
        Phase.project_id,
        func.count(Stage.id).label('overdue_count')
    ).join(Stage, Phase.id == Stage.phase_id).filter(
        and_(
            Stage.expected_end_date.isnot(None),
            Stage.expected_end_date < today,
            Stage.actual_end_date.is_(None)
        )
    ).group_by(Phase.project_id).subquery()
    
    # Get unassigned counts per project
    unassigned_subquery = db.session.query(
        Phase.project_id,
        func.count(Stage.id).label('unassigned_count')
    ).join(Stage, Phase.id == Stage.phase_id).filter(
        and_(
            Stage.actual_end_date.is_(None),
            Stage.responsible_department_id.is_(None),
            Stage.responsible_designation_id.is_(None)
        )
    ).group_by(Phase.project_id).subquery()
    
    # Build issues dictionary
    project_issues = {}
    for project in projects:
        project_issues[project.id] = {
            'overdue': 0,
            'unassigned': 0,
            'total': 0
        }
    
    # Populate with actual counts
    overdue_results = db.session.query(
        overdue_subquery.c.project_id,
        overdue_subquery.c.overdue_count
    ).all()
    
    for project_id, count in overdue_results:
        if project_id in project_issues:
            project_issues[project_id]['overdue'] = count
            project_issues[project_id]['total'] += count
    
    unassigned_results = db.session.query(
        unassigned_subquery.c.project_id,
        unassigned_subquery.c.unassigned_count
    ).all()
    
    for project_id, count in unassigned_results:
        if project_id in project_issues:
            project_issues[project_id]['unassigned'] = count
            project_issues[project_id]['total'] += count
    
    # Prepare filter data
    filter_data = {
        'companies': [c[0] for c in all_companies if c[0]],
        'departments': [{'id': d.id, 'name': d.department_name} for d in all_departments],
        'locations': [{'id': l.id, 'name': l.location_name} for l in all_locations],
        'heads': [{'id': h.id, 'name': h.full_name} for h in all_heads],
        'customers': [c[0] for c in all_customers if c[0]],
        'current_filters': {
            'company': company_filter,
            'department': department_filter,
            'location': location_filter,
            'head': head_filter,
            'status': status_filter,
            'customer': customer_filter,
            'search': search_filter
        }
    }
    
    return render_template('projects.html', 
                         projects=projects, 
                         project_issues=project_issues,
                         filter_data=filter_data)


@ui.route('/projects/new', methods=['GET', 'POST'])
@ui_role_required(UserRole.PROJECT_HEAD)
def create_project():
    if request.method == 'POST':
        name = request.form.get('name')
        head_id = request.form.get('head_id') or None
        
        # Required fields validation
        required_fields = {
            'customer_name': 'Customer Name',
            'company_name': 'Company Name',
            'part_name': 'Part Name',
            'part_code': 'Part Code',
            'part_description': 'Part Description',
            'name': 'Project name'
        }
        
        missing = [label for field, label in required_fields.items() if not request.form.get(field)]
        if missing:
            flash('Please fill all required fields: ' + ', '.join(missing), 'error')
            return redirect(url_for('ui.create_project'))

        # expected_end_date will be auto-calculated from last stage completion date
        end_date = None

        # Validate user from unified database
        if head_id and not get_user_by_id(int(head_id)):
            flash('Selected project head is not a valid user.', 'error')
            return redirect(url_for('ui.create_project'))
        
        # Look up location_id by name if provided
        location_id = None
        location_name = request.form.get('location')
        if location_name and location_name.strip():
            location = Location.query.filter_by(location_name=location_name, is_active=True).first()
            if location:
                location_id = location.id
        
        # Look up department_id by name if provided (head department)
        head_department_id = None
        department_name = request.form.get('department_name')
        if department_name and department_name.strip():
            department = Department.query.filter_by(department_name=department_name, is_active=True).first()
            if department:
                head_department_id = department.id
        
        # Look up designation_id by name if provided (head designation)
        head_designation_id = None
        designation_name = request.form.get('designation')
        if designation_name and designation_name.strip():
            designation = Designation.query.filter_by(designation_name=designation_name, is_active=True).first()
            if designation:
                head_designation_id = designation.id

        # Create project from form values
        proj = Project(
            name=name,
            head_id=int(head_id) if head_id else None,
            head_designation_id=head_designation_id,
            head_department_id=head_department_id,
            expected_end_date=end_date,
            location_id=location_id,
            department_id=head_department_id,  # Use head_department_id as the project department
            part_name=request.form.get('part_name'),
            part_code=request.form.get('part_code'),
            customer_name=request.form.get('customer_name'),
            company_name=request.form.get('company_name'),
            part_description=request.form.get('part_description'),
        )
        db.session.add(proj)
        db.session.flush()  # Get the project ID without committing
        
        # Process stage assignments (department, designation, responsible person, completion date)
        # The form will have fields like: stage_department_0_0, stage_designation_0_0, stage_responsible_0_0, stage_completion_date_0_0
        # Format: stage_{field}_{phaseIdx}_{stageIdx} or stage_completion_date_{phaseIdx}_{stageIdx}
        stage_assignments = {}
        for key in request.form.keys():
            if key.startswith('stage_'):
                parts = key.split('_')
                
                # Handle stage_completion_date_X_Y (5 parts)
                if len(parts) == 5 and parts[1] == 'completion' and parts[2] == 'date':
                    field_type = 'completion_date'
                    phase_idx = parts[3]
                    stage_idx = parts[4]
                # Handle stage_department_X_Y, stage_designation_X_Y, stage_responsible_X_Y (4 parts)
                elif len(parts) == 4:
                    field_type = parts[1]  # department, designation, or responsible
                    phase_idx = parts[2]
                    stage_idx = parts[3]
                else:
                    continue
                
                stage_key = f"{phase_idx}_{stage_idx}"
                
                if stage_key not in stage_assignments:
                    stage_assignments[stage_key] = {}
                
                value = request.form.get(key)
                if value:  # Only process if a value was provided
                    stage_assignments[stage_key][field_type] = value
        
        # After the project is created, the event listener creates phases and stages
        # We need to commit first to trigger the event, then update the stages
        db.session.commit()
        
        # Reload the project with phases and stages
        proj = db.session.get(Project, proj.id)
        
        # Now update stage assignments if any were provided
        if stage_assignments:
            for stage_key, assignments in stage_assignments.items():
                # Parse the key to get phase and stage indices
                parts = stage_key.split('_')
                if len(parts) == 2:
                    phase_idx = int(parts[0])
                    stage_idx = int(parts[1])
                    
                    # Find the corresponding stage
                    if phase_idx < len(proj.phases):
                        phase = proj.phases[phase_idx]
                        if stage_idx < len(phase.stages):
                            stage = phase.stages[stage_idx]
                            
                            # Department is set from template and cannot be changed
                            # responsible_department_id comes from template_stage.default_responsible_department_id
                            
                            # Update designation if provided
                            if 'designation' in assignments:
                                # If responsible person is also provided, use that
                                if 'responsible' in assignments:
                                    stage.responsible_user_id = int(assignments['responsible'])
                                else:
                                    # Find a user with this designation
                                    user_with_designation = User.query.filter_by(
                                        designation=assignments['designation'], 
                                        is_active=True
                                    ).first()
                                    
                                    if user_with_designation:
                                        stage.responsible_user_id = user_with_designation.id
                            
                            # Update responsible person if provided (overrides designation-based assignment)
                            if 'responsible' in assignments:
                                stage.responsible_user_id = int(assignments['responsible'])
                            
                            # Update completion date if provided
                            if 'completion_date' in assignments:
                                try:
                                    completion_date = date.fromisoformat(assignments['completion_date'])
                                    stage.expected_end_date = completion_date
                                except ValueError:
                                    pass  # Skip invalid dates
        
        # Auto-calculate project expected_end_date from last stage
        # Always calculate this regardless of whether stage assignments were provided
        # Get all stages across all phases and find the latest expected_end_date
        all_stages = []
        for phase in proj.phases:
            all_stages.extend(phase.stages)
        
        # Filter stages with expected_end_date and find the maximum
        stage_dates = [s.expected_end_date for s in all_stages if s.expected_end_date]
        if stage_dates:
            proj.expected_end_date = max(stage_dates)
            logger.info(f"Auto-calculated project expected_end_date: {proj.expected_end_date}")
        
        db.session.commit()
        
        flash('Project created successfully with APQP structure and stage assignments!', 'success')
        return redirect(url_for('ui.project_detail', project_id=proj.id))
    # Fetch users from unified database
    users_data = get_all_users()
    users = []
    for u in users_data:
        user_dict = {
            'id': u.id, 
            'name': u.full_name, 
            'username': u.username,
            'designation': None,
            'department': None
        }
        # Get designation name if user has one
        if u.designation:
            user_dict['designation'] = u.designation
        # Get department name if user has one
        if u.department_id and u.department:
            user_dict['department'] = u.department.department_name
        users.append(user_dict)
        
    # Fetch locations and companies for dropdowns
    locations_data = get_all_active_locations()
    companies_data = get_all_active_companies()
    locations = [{'id': l.id, 'code': l.location_code, 'name': l.location_name} for l in locations_data]
    companies = [{'id': c.id, 'code': c.company_code, 'name': c.company_name} for c in companies_data]
    # Fetch departments and designations from database
    departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    designations = Designation.query.filter_by(is_active=True).order_by(Designation.designation_name).all()
    
    departments_list = [{'code': d.department_code, 'name': d.department_name} for d in departments]
    designations_list = [{'code': d.designation_code, 'name': d.designation_name} for d in designations]
    
    return render_template('create_project.html', users=users, locations=locations, companies=companies, 
                         departments=departments_list, designations=designations_list)


@ui.post('/projects/<int:project_id>/delete')
@login_required
def delete_project(project_id: int):
    project = db.session.get(Project, project_id)
    if not project:
        abort(404)
    
    # Only admin can delete projects
    if not session.get('is_super_admin') and session.get('unified_role', '').lower() != 'admin':
        flash('Only administrators can delete projects.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=project_id))
    
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully.', 'success')
    return redirect(url_for('ui.projects_list'))


@ui.post('/projects/<int:project_id>/toggle-auto-sync')
@ui_role_required(UserRole.ADMIN)
def toggle_project_auto_sync(project_id: int):
    """Toggle auto-sync with template for a project - Admin only"""
    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    if not project.template_id:
        return jsonify({'error': 'Project is not linked to a template'}), 400
    
    # Toggle the auto_sync_with_template field
    project.auto_sync_with_template = not project.auto_sync_with_template
    db.session.commit()
    
    return jsonify({
        'success': True,
        'auto_sync_with_template': project.auto_sync_with_template,
        'message': f"Auto-sync {'enabled' if project.auto_sync_with_template else 'disabled'} successfully"
    })


@ui.get('/projects/<int:project_id>')
@login_required
def project_detail(project_id: int):
    # Optimize: Eager load all related data in minimal queries
    from sqlalchemy.orm import selectinload, joinedload
    from flask import make_response
    
    project = db.session.query(Project).options(
        selectinload(Project.phases).selectinload(Phase.stages).joinedload(Stage.responsible),
        selectinload(Project.phases).selectinload(Phase.stages).joinedload(Stage.responsible_department),
        selectinload(Project.phases).selectinload(Phase.stages).joinedload(Stage.responsible_designation),
        selectinload(Project.phases).selectinload(Phase.stages).joinedload(Stage.completed_by),
        joinedload(Project.head),
        joinedload(Project.location_rel)
    ).filter(Project.id == project_id).first()
    
    if not project:
        abort(404)
    
    # Fetch designations from Designation table
    from models import Designation
    designations = Designation.query.filter_by(is_active=True).order_by(Designation.designation_name).all()
    designations_list = [{'code': d.designation_code, 'name': d.designation_name} for d in designations]
    
    # Fetch users from unified database
    users_data = get_all_users()
    users = [{'id': u.id, 'name': u.full_name, 'username': u.username, 'role': u.role, 'full_name': u.full_name, 'designation': u.designation} for u in users_data]
    
    # Create a lookup dictionary for user names by ID
    users_by_id = {u.id: u.full_name for u in users_data}  # id -> full_name
    
    # Add helper function to template context
    from flask import session
    user_id = session.get('user_id')
    user_role = session.get('role')
    is_super_admin = session.get('is_super_admin', False)
    
    def can_edit_stage(stage):
        result = can_user_edit_stage(user_id, user_role, stage) if user_id else False
        return result
    
    def can_complete_stage(stage):
        """Check if user can complete this stage"""
        if not user_id:
            return False
        
        # Super admin can complete anything
        if is_super_admin:
            return True
        
        # Admin role can complete anything
        if session.get('unified_role', '').lower() == 'admin':
            return True
        
        # Project head or admin role can complete anything
        if user_role in ['project_head', 'admin']:
            return True
        
        # Project head of this specific project can complete
        if stage.phase.project.head_id == user_id:
            return True
        
        # Responsible person for this stage can complete
        if stage.responsible_user_id == user_id:
            return True
        
        return False
    
    def get_user_name(user_id_param):
        """Get user name from unified database"""
        if not user_id_param:
            return None
        return users_by_id.get(user_id_param, 'Unknown User')
    
    def get_all_users_list():
        """Get all users for dropdowns"""
        return users
    
    # Don't override current_user - it comes from the context processor
    # Just pass the helper function and additional data
    html = render_template('project_detail.html', 
                         project=project, 
                         users=users,
                         designations=designations_list,
                         can_edit_stage=can_edit_stage,
                         can_complete_stage=can_complete_stage,
                         get_user_name=get_user_name,
                         get_all_users_list=get_all_users_list,
                         current_user_id=user_id,
                         today=date.today())
    
    # Force browser to not cache the page - ensure fresh data on every load
    response = make_response(html)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# Auto-schedule functionality removed - dates are now set directly in the database


@ui.get('/stages/<int:stage_id>')
@login_required
def stage_detail(stage_id: int):
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    # Fetch departments from Department table
    from models import Department, Designation
    departments = Department.query.filter_by(is_active=True).order_by(Department.department_name).all()
    departments_list = [{'id': d.id, 'code': d.department_code, 'name': d.department_name} for d in departments]
    
    # Fetch designations from Designation table
    designations = Designation.query.filter_by(is_active=True).order_by(Designation.designation_name).all()
    designations_list = [{'id': d.id, 'code': d.designation_code, 'name': d.designation_name} for d in designations]
    
    # Fetch users from unified database
    users_data = get_all_users()
    users = [{'id': u.id, 'name': u.full_name, 'username': u.username, 'designation': u.designation} for u in users_data]
    return render_template('stage_detail.html', stage=stage, users=users, departments=departments_list, designations=designations_list)


@ui.post('/stages/<int:stage_id>/update')
@login_required
def ui_update_stage(stage_id: int):
    from authz import check_stage_access
    from models import UserRole
    
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    # Get current user info
    user_id = session.get('user_id')
    user_role = session.get('role')
    
    # Check if trying to mark as complete
    status = request.form.get('status')
    is_marking_complete = (status == 'completed' and not stage.actual_end_date)
    
    # For completing a stage, check authorization
    # ONLY project head and stage responsible person can make changes
    if is_marking_complete:
        # Check if user has permission to complete this stage
        can_complete = False
        
        # Project head of this specific project can complete
        if stage.phase.project.head_id == user_id:
            can_complete = True
        # Responsible person for this stage can complete
        elif stage.responsible_user_id == user_id:
            can_complete = True
        
        if not can_complete:
            flash('You do not have permission to mark this stage as complete. Only the project head or stage responsible person can complete stages.', 'danger')
            return redirect(url_for('ui.project_detail', project_id=stage.phase.project_id))
    
    # For other updates (dates, assignments), check edit access
    else:
        can_edit = check_stage_access(user_id, user_role, stage, 'edit')
        if not can_edit:
            flash('You do not have permission to edit this stage. Only the project head or stage responsible person can edit stages.', 'danger')
            return redirect(url_for('ui.project_detail', project_id=stage.phase.project_id))
    
    # Update start date
    start_date_str = request.form.get('start_date')
    if start_date_str:
        try:
            stage.start_date = date.fromisoformat(start_date_str)
        except ValueError:
            pass
    
    # Update expected end date
    expected_end_date_str = request.form.get('expected_end_date')
    if expected_end_date_str:
        try:
            stage.expected_end_date = date.fromisoformat(expected_end_date_str)
        except ValueError:
            pass
    
    # Department cannot be changed in projects - only in templates
    # responsible_department_id is set from template and synced automatically
    
    # Update responsible designation
    responsible_designation_name = request.form.get('responsible_designation')
    if responsible_designation_name:
        # Look up designation by name
        designation = Designation.query.filter_by(designation_name=responsible_designation_name).first()
        if designation:
            stage.responsible_designation_id = designation.id
    
    # Alternative: Update by ID if provided
    responsible_designation_id = request.form.get('responsible_designation_id')
    if responsible_designation_id:
        stage.responsible_designation_id = int(responsible_designation_id)
    
    # Update responsible user
    responsible_user_id = request.form.get('responsible_user_id')
    if responsible_user_id:
        stage.responsible_user_id = int(responsible_user_id)
    elif responsible_user_id == '':  # Empty string means unassign
        stage.responsible_user_id = None
    
    # Update status - stages can be completed in any order
    if is_marking_complete:
        stage.actual_end_date = date.today()
        stage.completed_by_id = session.get('user_id')
        flash('Stage marked as complete successfully.', 'success')
    elif status != 'completed' and stage.actual_end_date:
        stage.actual_end_date = None
        stage.completed_by_id = None
    
    db.session.commit()
    return redirect(url_for('ui.project_detail', project_id=stage.phase.project_id))


@ui.post('/stages/<int:stage_id>/steps')
@stage_access_required('edit')
def ui_create_step(stage_id: int):
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    name = request.form.get('name')
    description = request.form.get('description')
    start = request.form.get('expected_start_date')
    end = request.form.get('expected_end_date')
    responsible = request.form.get('responsible_user_id')
    
    if name:
        start_date = None
        end_date = None
        
        if start:
            try:
                start_date = date.fromisoformat(start)
            except ValueError:
                flash('Invalid date format for start date. Use YYYY-MM-DD.', 'error')
                return redirect(url_for('ui.project_detail', project_id=stage.phase.project_id))
        
        if end:
            try:
                end_date = date.fromisoformat(end)
            except ValueError:
                flash('Invalid date format for end date. Use YYYY-MM-DD.', 'error')
                return redirect(url_for('ui.project_detail', project_id=stage.phase.project_id))
        
        step = Step(
            stage=stage,
            name=name,
            description=description,
            expected_start_date=start_date,
            expected_end_date=end_date,
            responsible_user_id=int(responsible) if responsible else None,
            status='pending',
        )
        db.session.add(step)
        db.session.commit()
        flash('Step added successfully.', 'success')
    return redirect(url_for('ui.project_detail', project_id=stage.project_id))


@ui.post('/steps/<int:step_id>/update')
@login_required
def ui_update_step(step_id: int):
    """Update step details (name, dates, description)"""
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    
    # Check permissions - only project head or stage responsible person
    user_id = session.get('user_id')
    stage = step.stage
    
    can_edit = False
    if stage.phase.project.head_id == user_id:
        can_edit = True
    elif stage.responsible_user_id == user_id:
        can_edit = True
    
    if not can_edit:
        flash('Only the project head or stage responsible person can update steps.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=step.stage.phase.project_id))
    
    # Update step name
    name = request.form.get('name', '').strip()
    if name:
        step.name = name
    
    # Update description
    description = request.form.get('description', '').strip()
    if description is not None:
        step.description = description if description else None
    
    # Update start date
    start_date_str = request.form.get('start_date', '').strip()
    if start_date_str:
        try:
            step.start_date = date.fromisoformat(start_date_str)
        except ValueError:
            flash('Invalid start date format. Use YYYY-MM-DD.', 'error')
            return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    # Update expected end date
    expected_end_date_str = request.form.get('expected_end_date', '').strip()
    if expected_end_date_str:
        try:
            step.expected_end_date = date.fromisoformat(expected_end_date_str)
        except ValueError:
            flash('Invalid expected end date format. Use YYYY-MM-DD.', 'error')
            return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    # Update status if provided
    new_status = request.form.get('status')
    if new_status and new_status in ('pending', 'in_progress', 'completed'):
        step.status = new_status
    
    db.session.commit()
    flash('Step updated successfully.', 'success')
    return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))


@ui.post('/steps/<int:step_id>/status')
@login_required
def ui_update_step_status(step_id: int):
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    
    # Check permissions - only project head or stage responsible person
    user_id = session.get('user_id')
    stage = step.stage
    
    can_edit = False
    if stage.phase.project.head_id == user_id:
        can_edit = True
    elif stage.responsible_user_id == user_id:
        can_edit = True
    
    if not can_edit:
        flash('Only the project head or stage responsible person can update step status.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=step.stage.phase.project_id))
    
    new_status = request.form.get('status')
    if new_status in ('pending', 'in_progress', 'completed'):
        step.status = new_status
        db.session.commit()
    return redirect(url_for('ui.project_detail', project_id=step.stage.phase.project_id))


@ui.post('/steps/<int:step_id>/delete')
@login_required
def ui_delete_step(step_id: int):
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    
    # Check permissions - only project head or stage responsible person
    user_id = session.get('user_id')
    stage = step.stage
    
    can_edit = False
    if stage.phase.project.head_id == user_id:
        can_edit = True
    elif stage.responsible_user_id == user_id:
        can_edit = True
    
    if not can_edit:
        flash('Only the project head or stage responsible person can delete steps.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=step.stage.phase.project_id))
    
    pid = step.stage.phase.project_id
    db.session.delete(step)
    db.session.commit()
    return redirect(url_for('ui.project_detail', project_id=pid))


@ui.route('/users', methods=['GET'])
@ui_role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def users_page():
    """Display all users from unified database with filtering support"""
    
    # Get filter parameters
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()
    department_filter = request.args.get('department', '').strip()
    location_filter = request.args.get('location', '').strip()
    designation_filter = request.args.get('designation', '').strip()
    search_filter = request.args.get('search', '').strip()
    
    # Build query with filters
    from sqlalchemy.orm import joinedload
    query = User.query.options(
        joinedload(User.department),
        joinedload(User.location)
    )
    
    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    
    if status_filter:
        if status_filter == 'active':
            query = query.filter(User.is_active == True)
        elif status_filter == 'inactive':
            query = query.filter(User.is_active == False)
    
    if department_filter:
        query = query.join(Department, User.department_id == Department.id, isouter=True)\
                    .filter(Department.department_name.ilike(f'%{department_filter}%'))
    
    if location_filter:
        query = query.join(Location, User.location_id == Location.id, isouter=True)\
                    .filter(Location.location_name.ilike(f'%{location_filter}%'))
    
    if designation_filter:
        query = query.filter(User.designation.ilike(f'%{designation_filter}%'))
    
    if search_filter:
        search_term = f'%{search_filter}%'
        query = query.filter(
            db.or_(
                User.full_name.ilike(search_term),
                User.username.ilike(search_term),
                User.employee_id.ilike(search_term)
            )
        )
    
    users = query.order_by(User.full_name.asc()).all()
    
    # Get filter options for dropdowns
    all_roles = db.session.query(User.role).filter(User.role.isnot(None)).distinct().all()
    all_departments = Department.query.filter_by(is_active=True).all()
    all_locations = Location.query.filter_by(is_active=True).all()
    all_designations = db.session.query(User.designation).filter(User.designation.isnot(None)).distinct().all()
    
    # Prepare filter data
    filter_data = {
        'roles': [r[0] for r in all_roles if r[0]],
        'departments': [{'id': d.id, 'name': d.department_name} for d in all_departments],
        'locations': [{'id': l.id, 'name': l.location_name} for l in all_locations],
        'designations': [d[0] for d in all_designations if d[0]],
        'current_filters': {
            'role': role_filter,
            'status': status_filter,
            'department': department_filter,
            'location': location_filter,
            'designation': designation_filter,
            'search': search_filter
        }
    }
    
    flash('Users are managed centrally across all MTPL apps. To add/edit users, use the Unified Page application.', 'info')
    return render_template('users.html', users=users, filter_data=filter_data)


@ui.post('/users/<int:user_id>/delete')
@ui_role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def delete_user(user_id: int):
    """Safely deactivate or delete a local user while clearing foreign key references.

    If form contains hard_delete=1 then perform a physical delete after nullifying
    all FK references. Otherwise perform a soft delete by setting is_active = False.
    """
    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    # Prevent deleting self to avoid locking out admin unintentionally
    from flask import session as flask_session
    current_user_id = flask_session.get('user_id')
    if current_user_id == user_id:
        flash('You cannot delete your own user account while logged in.', 'warning')
        return redirect(url_for('ui.users_page'))

    # Nullify all references to this user to satisfy FK constraints
    try:
        # Projects
        Project.query.filter(Project.head_id == user_id).update({Project.head_id: None})
        Project.query.filter(Project.created_by == user_id).update({Project.created_by: None})
        Project.query.filter(Project.updated_by == user_id).update({Project.updated_by: None})
        # Phases
        Phase.query.filter(Phase.responsible_user_id == user_id).update({Phase.responsible_user_id: None})
        # Stages
        Stage.query.filter(Stage.responsible_user_id == user_id).update({Stage.responsible_user_id: None})
        Stage.query.filter(Stage.completed_by_id == user_id).update({Stage.completed_by_id: None})
        # Steps
        Step.query.filter(Step.responsible_user_id == user_id).update({Step.responsible_user_id: None})
        # Departments (manager)
        Department.query.filter(Department.manager_user_id == user_id).update({Department.manager_user_id: None})
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing references before deletion: {e}', 'danger')
        return redirect(url_for('ui.users_page'))

    hard_delete = request.form.get('hard_delete') == '1'
    try:
        if hard_delete:
            db.session.delete(user)
            flash('User hard deleted and all references cleared.', 'success')
        else:
            user.is_active = False
            flash('User deactivated and references cleared.', 'success')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {e}', 'danger')
    return redirect(url_for('ui.users_page'))


def _collect_user_reference_counts(user_id: int):
    """Internal helper to count referencing rows for a user before deletion."""
    return {
        'projects_head': Project.query.filter(Project.head_id == user_id).count(),
        'projects_created': Project.query.filter(Project.created_by == user_id).count(),
        'projects_updated': Project.query.filter(Project.updated_by == user_id).count(),
        'phases_responsible': Phase.query.filter(Phase.responsible_user_id == user_id).count(),
        'stages_responsible': Stage.query.filter(Stage.responsible_user_id == user_id).count(),
        'stages_completed_by': Stage.query.filter(Stage.completed_by_id == user_id).count(),
        'steps_responsible': Step.query.filter(Step.responsible_user_id == user_id).count(),
        'departments_manager': Department.query.filter(Department.manager_user_id == user_id).count(),
    }


@ui.get('/users/<int:user_id>/refs')
@ui_role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def user_reference_counts(user_id: int):
    """Return JSON with counts of all FK references to a given user."""
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    from flask import jsonify
    return jsonify({
        'user_id': user_id,
        'is_active': user.is_active,
        'references': _collect_user_reference_counts(user_id)
    })


@ui.post('/stages/<int:stage_id>/attachment/upload')
@login_required
def upload_stage_attachment(stage_id: int):
    """Upload attachment to a stage (max 30MB)"""
    import os
    from werkzeug.utils import secure_filename
    from flask import send_file
    
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    # Check if user can edit this stage
    user_id = session.get('user_id')
    user_role = session.get('role')
    if not can_user_edit_stage(user_id, user_role, stage):
        flash('You do not have permission to upload attachments to this stage.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    # Check if file was uploaded
    if 'attachment' not in request.files:
        flash('No file selected.', 'warning')
        return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    file = request.files['attachment']
    if file.filename == '':
        flash('No file selected.', 'warning')
        return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    # Check file size (30MB = 30 * 1024 * 1024 bytes)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB
    if file_size > MAX_FILE_SIZE:
        flash(f'File size exceeds 30 MB limit. Your file is {file_size / (1024 * 1024):.2f} MB.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'stage_attachments')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Delete old attachment if exists
    if stage.attachment_path and os.path.exists(stage.attachment_path):
        try:
            os.remove(stage.attachment_path)
        except Exception:
            pass  # Ignore file deletion errors
    
    # Save new file
    filename = secure_filename(file.filename)
    # Add timestamp to avoid filename conflicts
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{stage_id}_{timestamp}_{filename}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    file.save(file_path)
    
    # Update stage record
    stage.attachment_filename = filename
    stage.attachment_path = file_path
    db.session.commit()
    
    flash(f'Attachment "{filename}" uploaded successfully.', 'success')
    return redirect(url_for('ui.project_detail', project_id=stage.project_id))


@ui.get('/stages/<int:stage_id>/attachment/download')
@login_required
def download_stage_attachment(stage_id: int):
    """Download or view stage attachment"""
    from flask import send_file
    import os
    import mimetypes
    
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    if not stage.attachment_path or not stage.attachment_filename:
        flash('No attachment found for this stage.', 'warning')
        return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    if not os.path.exists(stage.attachment_path):
        flash('Attachment file not found on server.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    # Determine if file should be viewed inline or downloaded
    mime_type, _ = mimetypes.guess_type(stage.attachment_filename)
    viewable_types = ['application/pdf', 'image/', 'text/', 'video/', 'audio/']
    as_attachment = not any(mime_type and mime_type.startswith(vt) for vt in viewable_types) if mime_type else True
    
    return send_file(stage.attachment_path, as_attachment=as_attachment, download_name=stage.attachment_filename, mimetype=mime_type)


@ui.post('/stages/<int:stage_id>/attachment/delete')
@login_required
def delete_stage_attachment(stage_id: int):
    """Delete stage attachment"""
    import os
    
    stage = db.session.get(Stage, stage_id)
    if not stage:
        abort(404)
    
    # Check if user can edit this stage
    user_id = session.get('user_id')
    user_role = session.get('role')
    if not can_user_edit_stage(user_id, user_role, stage):
        flash('You do not have permission to delete attachments from this stage.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    if stage.attachment_path and os.path.exists(stage.attachment_path):
        try:
            os.remove(stage.attachment_path)
        except Exception as e:
            flash(f'Error deleting file: {str(e)}', 'danger')
            return redirect(url_for('ui.project_detail', project_id=stage.project_id))
    
    # Clear attachment fields
    filename = stage.attachment_filename
    stage.attachment_filename = None
    stage.attachment_path = None
    db.session.commit()
    
    flash(f'Attachment "{filename}" deleted successfully.', 'success')
    return redirect(url_for('ui.project_detail', project_id=stage.project_id))


@ui.post('/steps/<int:step_id>/attachment/upload')
@login_required
def upload_step_attachment(step_id: int):
    """Upload attachment to a step (max 30MB)"""
    import os
    from werkzeug.utils import secure_filename
    
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    
    # Check if user can edit this stage
    user_id = session.get('user_id')
    user_role = session.get('role')
    if not can_user_edit_stage(user_id, user_role, step.stage):
        flash('You do not have permission to upload attachments to this step.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    # Check if file was uploaded
    if 'attachment' not in request.files:
        flash('No file selected.', 'warning')
        return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    file = request.files['attachment']
    if file.filename == '':
        flash('No file selected.', 'warning')
        return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    # Check file size (30MB = 30 * 1024 * 1024 bytes)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB
    if file_size > MAX_FILE_SIZE:
        flash(f'File size exceeds 30 MB limit. Your file is {file_size / (1024 * 1024):.2f} MB.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'step_attachments')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Delete old attachment if exists
    if step.attachment_path and os.path.exists(step.attachment_path):
        try:
            os.remove(step.attachment_path)
        except Exception:
            pass  # Ignore file deletion errors
    
    # Save new file
    filename = secure_filename(file.filename)
    # Add timestamp to avoid filename conflicts
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{step_id}_{timestamp}_{filename}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    file.save(file_path)
    
    # Update step record
    step.attachment_filename = filename
    step.attachment_path = file_path
    db.session.commit()
    
    flash(f'Attachment "{filename}" uploaded successfully.', 'success')
    return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))


@ui.get('/steps/<int:step_id>/attachment/download')
@login_required
def download_step_attachment(step_id: int):
    """Download or view step attachment"""
    from flask import send_file
    import os
    import mimetypes
    
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    
    if not step.attachment_path or not step.attachment_filename:
        flash('No attachment found for this step.', 'warning')
        return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    if not os.path.exists(step.attachment_path):
        flash('Attachment file not found on server.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    # Determine if file should be viewed inline or downloaded
    mime_type, _ = mimetypes.guess_type(step.attachment_filename)
    viewable_types = ['application/pdf', 'image/', 'text/', 'video/', 'audio/']
    as_attachment = not any(mime_type and mime_type.startswith(vt) for vt in viewable_types) if mime_type else True
    
    return send_file(step.attachment_path, as_attachment=as_attachment, download_name=step.attachment_filename, mimetype=mime_type)


@ui.post('/steps/<int:step_id>/attachment/delete')
@login_required
def delete_step_attachment(step_id: int):
    """Delete step attachment"""
    import os
    
    step = db.session.get(Step, step_id)
    if not step:
        abort(404)
    
    # Check if user can edit this stage
    user_id = session.get('user_id')
    user_role = session.get('role')
    if not can_user_edit_stage(user_id, user_role, step.stage):
        flash('You do not have permission to delete attachments from this step.', 'danger')
        return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    if step.attachment_path and os.path.exists(step.attachment_path):
        try:
            os.remove(step.attachment_path)
        except Exception as e:
            flash(f'Error deleting file: {str(e)}', 'danger')
            return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))
    
    # Clear attachment fields
    filename = step.attachment_filename
    step.attachment_filename = None
    step.attachment_path = None
    db.session.commit()
    
    flash(f'Attachment "{filename}" deleted successfully.', 'success')
    return redirect(url_for('ui.project_detail', project_id=step.stage.project_id))


# Admin Routes
@ui.get('/settings')
@login_required
@ui_role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def admin_settings():
    """System settings page - Admin only"""
    # Ensure JWT token exists in session for API calls
    if 'jwt_token' not in session and 'user_id' in session:
        # Regenerate JWT token if missing but user is logged in
        from flask_jwt_extended import create_access_token
        from datetime import timedelta
        
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
        session['jwt_token'] = access_token
        session.modified = True
        logger.info(f"Regenerated JWT token for user {session.get('username')}")
    
    return render_template('admin_settings.html')


@ui.get('/audit-logs')
@login_required
@ui_role_required(UserRole.ADMIN, UserRole.PROJECT_HEAD)
def admin_audit_logs():
    """Audit logs page - Admin only"""
    return render_template('admin_audit_logs.html')
