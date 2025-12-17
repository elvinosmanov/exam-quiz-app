import flet as ft
from quiz_app.utils.auth import AuthManager
from quiz_app.config import COLORS, get_departments, get_sections_for_department, get_units_for_department, ORGANIZATIONAL_STRUCTURE
from quiz_app.utils.permissions import UnitPermissionManager
from quiz_app.utils.localization import t, get_language
from quiz_app.utils.password_generator import generate_secure_password, send_password_email
from quiz_app.config import (
    AUTO_GENERATE_PASSWORD, EMAIL_ENABLED, SMTP_SERVER, SMTP_PORT,
    SENDER_EMAIL, SENDER_PASSWORD, APP_URL, GENERATED_PASSWORD_LENGTH
)
import pyperclip
import re

class UserManagement(ft.UserControl):
    def __init__(self, db, user_data=None):
        super().__init__()
        self.db = db
        self.user_data = user_data or {'role': 'admin'}  # Default to admin if not provided
        self.auth_manager = AuthManager()
        self.users_data = []
        self.all_users_data = []  # Keep original data for filtering
        self.selected_user = None

        # Search and filter controls
        self.search_field = ft.TextField(
            label=t('search_users'),
            prefix_icon=ft.icons.SEARCH,
            on_change=self.apply_filters,
            expand=True
        )

        self.role_filter = ft.Dropdown(
            label=t('filter_by_role'),
            options=[
                ft.dropdown.Option("all", t('all')),
                ft.dropdown.Option("admin", t('admin')),
                ft.dropdown.Option("expert", t('expert')),
                ft.dropdown.Option("examinee", t('examinee'))
            ],
            value="all",
            on_change=self.apply_filters,
            width=200
        )
        
        # Users table
        self.users_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t('username'))),
                ft.DataColumn(ft.Text(t('full_name'))),
                ft.DataColumn(ft.Text(t('email'))),
                ft.DataColumn(ft.Text(t('role'))),
                ft.DataColumn(ft.Text(t('department'))),
                ft.DataColumn(ft.Text(t('section'))),
                ft.DataColumn(ft.Text(t('unit'))),
                ft.DataColumn(ft.Text(t('status'))),
                ft.DataColumn(ft.Text(t('actions')))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )

        # Action buttons
        self.add_user_btn = ft.ElevatedButton(
            text=t('add_user'),
            icon=ft.icons.ADD,
            on_click=self.show_add_user_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )
        
        # Dialog for adding/editing users
        self.user_dialog = None
    
    def did_mount(self):
        super().did_mount()
        self.load_users()
    
    def build(self):
        return ft.Column([
            # Header
            ft.Row([
                ft.Text(t('user_management'), size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(expand=True),
                self.add_user_btn
            ]),
            ft.Divider(),
            
            # Filters
            ft.Row([
                self.search_field,
                self.role_filter
            ], spacing=20),
            
            ft.Container(height=10),
            
            # Users table
            ft.Container(
                content=ft.ListView(
                    controls=[self.users_table],
                    expand=True,
                    auto_scroll=False
                ),
                bgcolor=COLORS['surface'],
                padding=ft.padding.all(20),
                border_radius=8,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=5,
                    color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
                ),
                expand=True
            )
        ], spacing=10, expand=True)
    
    def get_localized_text(self, text, field_type='department'):
        """Get localized name for department/section/unit based on ORGANIZATIONAL_STRUCTURE"""
        if not text:
            return "N/A"

        current_lang = get_language()
        lang_suffix = '_en' if current_lang == 'en' else '_az'

        # Search in ORGANIZATIONAL_STRUCTURE for matching name
        for dept_key, dept_data in ORGANIZATIONAL_STRUCTURE.items():
            # Check department names
            if field_type == 'department':
                if dept_data.get('name_az') == text or dept_data.get('name_en') == text or dept_data.get('abbr_az') == text or dept_data.get('abbr_en') == text:
                    return dept_data.get(f'name{lang_suffix}', text)

            # Check section names
            if field_type == 'section' and 'sections' in dept_data:
                for section_key, section_data in dept_data['sections'].items():
                    if section_data.get('name_az') == text or section_data.get('name_en') == text or section_data.get('abbr_az') == text or section_data.get('abbr_en') == text:
                        return section_data.get(f'name{lang_suffix}', text)

            # Check unit names in department-level units
            if field_type == 'unit' and 'units' in dept_data:
                for unit in dept_data['units']:
                    if unit.get('name_az') == text or unit.get('name_en') == text or unit.get('abbr_az') == text or unit.get('abbr_en') == text:
                        return unit.get(f'name{lang_suffix}', text)

            # Check unit names in section-level units
            if field_type == 'unit' and 'sections' in dept_data:
                for section_key, section_data in dept_data['sections'].items():
                    if 'units' in section_data:
                        for unit in section_data['units']:
                            if unit.get('name_az') == text or unit.get('name_en') == text or unit.get('abbr_az') == text or unit.get('abbr_en') == text:
                                return unit.get(f'name{lang_suffix}', text)

        # If not found in structure, try splitting bilingual text
        if " / " in text:
            parts = text.split(" / ")
            if len(parts) == 2:
                return parts[1].strip() if current_lang == 'en' else parts[0].strip()

        return text

    def load_users(self):
        """
        Load users based on role and hierarchical permissions.

        Permission Levels for Experts:
        - Department only: See all users (experts and examinees) in entire department
        - Department + Section: See all users in that section
        - Department + Section + Unit: See users in that specific unit
        """
        if self.user_data['role'] == 'expert':
            department = self.user_data.get('department', '')
            section = self.user_data.get('section')
            unit = self.user_data.get('unit')

            # Build query based on hierarchical level
            # SAFETY FIX: Experts should NOT see themselves in the list (prevent accidental self-removal)
            expert_user_id = self.user_data.get('id')

            if unit:
                # Most specific: Department + Section + Unit
                # Show all users (experts + examinees) in this specific unit, excluding self
                self.all_users_data = self.db.execute_query("""
                    SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                    FROM users
                    WHERE (role = 'expert' OR role = 'examinee')
                    AND department = ?
                    AND unit = ?
                    AND id != ?
                    ORDER BY created_at DESC
                """, (department, unit, expert_user_id))
            elif section:
                # Medium specific: Department + Section
                # Show all users (experts + examinees) in this section, excluding self
                self.all_users_data = self.db.execute_query("""
                    SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                    FROM users
                    WHERE (role = 'expert' OR role = 'examinee')
                    AND department = ?
                    AND section = ?
                    AND id != ?
                    ORDER BY created_at DESC
                """, (department, section, expert_user_id))
            else:
                # Least specific: Department only (department-level expert)
                # Show all users (experts and examinees) in entire department, excluding self
                self.all_users_data = self.db.execute_query("""
                    SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                    FROM users
                    WHERE (role = 'expert' OR role = 'examinee')
                    AND department = ?
                    AND id != ?
                    ORDER BY created_at DESC
                """, (department, expert_user_id))
        else:
            # Admins see all users
            self.all_users_data = self.db.execute_query("""
                SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                FROM users
                ORDER BY created_at DESC
            """)
        # Normalize is_active values: convert None to 0 (SQLite may return None for boolean columns)
        for user in self.all_users_data:
            if user['is_active'] is None:
                user['is_active'] = 0
        
        self.users_data = self.all_users_data.copy()
        self.apply_filters(None)
    
    def update_table(self):
        self.users_table.rows.clear()

        for idx, user in enumerate(self.users_data, 1):
            status = t('active') if user['is_active'] else t('inactive')
            status_color = COLORS['success'] if user['is_active'] else COLORS['error']

            self.users_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Text(user['username'])),
                        ft.DataCell(ft.Text(user['full_name'])),
                        ft.DataCell(ft.Text(user['email'])),
                        ft.DataCell(ft.Text(user['role'].title())),
                        ft.DataCell(ft.Text(self.get_localized_text(user['department'], 'department'))),
                        ft.DataCell(ft.Text(self.get_localized_text(user['section'], 'section'))),
                        ft.DataCell(ft.Text(self.get_localized_text(user['unit'], 'unit'))),
                        ft.DataCell(ft.Text(status, color=status_color)),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip=t('edit_user'),
                                    on_click=lambda e, u=user: self.show_edit_user_dialog(u)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.BLOCK if user['is_active'] else ft.icons.CHECK_CIRCLE,
                                    tooltip=t('user_deactivated') if user['is_active'] else t('user_activated'),
                                    on_click=lambda e, u=user: self.toggle_user_status(u),
                                    icon_color=COLORS['error'] if user['is_active'] else COLORS['success']
                                )
                            ], spacing=5)
                        )
                    ]
                )
            )

        self.update()
    
    def apply_filters(self, e):
        """Apply both search and role filters together"""
        # Start with all users
        filtered_users = self.all_users_data.copy()

        # Apply search filter
        search_term = self.search_field.value.lower() if self.search_field.value else ""
        if search_term:
            filtered_users = [
                user for user in filtered_users
                if search_term in user['username'].lower() or
                   search_term in user['full_name'].lower() or
                   search_term in user['email'].lower() or
                   search_term in (user['department'] or "").lower()
            ]

        # Apply role filter
        role_filter = self.role_filter.value
        if role_filter != "all":
            filtered_users = [user for user in filtered_users if user['role'] == role_filter]

        # Update displayed data
        self.users_data = filtered_users
        self.update_table()
    
    def show_add_user_dialog(self, e):
        self.show_user_dialog()
    
    def show_edit_user_dialog(self, user):
        self.show_user_dialog(user)
    
    def show_user_dialog(self, user=None):
        is_edit = user is not None
        title = t('edit_user') if is_edit else t('create_user_account')

        # Form fields
        username_field = ft.TextField(
            label=t('username'),
            value=user['username'] if is_edit else "",
            disabled=is_edit  # Don't allow username changes
        )

        # Email validation error text
        email_error_text = ft.Text("", color=COLORS['error'], size=12, visible=False)

        email_field = ft.TextField(
            label=t('email'),
            value=user['email'] if is_edit else ""
        )

        full_name_field = ft.TextField(
            label=t('full_name'),
            value=user['full_name'] if is_edit else ""
        )

        # Auto-generate password for new users
        auto_password = generate_secure_password(GENERATED_PASSWORD_LENGTH) if not is_edit else ""

        password_field = ft.TextField(
            label=t('password') if not is_edit else t('new_password'),
            password=True,
            can_reveal_password=True,
            value=auto_password,
            hint_text="Auto-generated secure password (you can edit)" if not is_edit else None
        )

        # Role dropdown - restrict based on expert level
        if self.user_data['role'] == 'expert':
            # Check if this is a department-level expert
            is_department_level_expert = (
                self.user_data.get('department') and
                not self.user_data.get('section') and
                not self.user_data.get('unit')
            )

            if is_department_level_expert:
                # Department-level experts can create both expert and examinee users
                role_dropdown = ft.Dropdown(
                    label=t('role'),
                    options=[
                        ft.dropdown.Option("expert", t('expert')),
                        ft.dropdown.Option("examinee", t('examinee'))
                    ],
                    value=user['role'] if is_edit else "examinee",
                    on_change=None  # Will set below if needed
                )
            else:
                # Section/unit-level experts can only create examinees
                role_dropdown = ft.Dropdown(
                    label=t('role'),
                    options=[ft.dropdown.Option("examinee", t('examinee'))],
                    value="examinee",
                    disabled=True,  # Force examinee role
                    on_change=None
                )
        else:
            # Admins can create any role
            role_dropdown = ft.Dropdown(
                label=t('role'),
                options=[
                    ft.dropdown.Option("admin", t('admin')),
                    ft.dropdown.Option("expert", t('expert')),
                    ft.dropdown.Option("examinee", t('examinee'))
                ],
                value=user['role'] if is_edit else "examinee",
                on_change=None  # Will set below
            )

        # Department/Section/Unit - hierarchical permissions for experts
        if self.user_data['role'] == 'expert':
            """
            Expert permissions are hierarchical:
            - Department only: Can select any section/unit in their department
            - Department + Section: Can select any unit in their section
            - Department + Section + Unit: Locked to their specific unit

            For department-level experts creating expert users:
            - They can assign department only (no section/unit) for department-level expert
            - Or assign department + section/unit for section/unit-level expert
            """
            expert_dept = self.user_data.get('department', '')
            expert_section = self.user_data.get('section')
            expert_unit = self.user_data.get('unit')
            current_lang = get_language()

            # Department is always locked to expert's department
            department_dropdown = ft.TextField(
                label=t('department') + (" *" if not is_edit else ""),
                value=expert_dept,
                disabled=True,  # Always locked to expert's department
                expand=True
            )

            if expert_unit:
                # Expert has unit: Lock section and unit
                section_dropdown = ft.TextField(
                    label=t('section'),
                    value=expert_section or 'N/A',
                    disabled=True,
                    expand=True
                )

                unit_dropdown = ft.TextField(
                    label=t('unit'),
                    value=expert_unit,
                    disabled=True,
                    expand=True
                )
            elif expert_section:
                # Expert has section but no unit: Lock section, allow unit selection
                section_dropdown = ft.TextField(
                    label=t('section'),
                    value=expert_section,
                    disabled=True,
                    expand=True
                )

                # Get units under expert's section
                units = get_units_for_department(expert_dept, expert_section, current_lang)
                unit_options = [ft.dropdown.Option("", "-- Select Unit --")]
                if units:
                    unit_options.extend([ft.dropdown.Option(u) for u in units])

                unit_dropdown = ft.Dropdown(
                    label=t('unit'),
                    hint_text=t('select_unit'),
                    options=unit_options,
                    value=user.get('unit') if is_edit else "",
                    expand=True,
                    disabled=len(units) == 0
                )
            else:
                # Expert has only department: Allow section and unit selection
                sections = get_sections_for_department(expert_dept, current_lang)
                direct_units = get_units_for_department(expert_dept, None, current_lang)

                # Build section options with "-- Select Section --" as first option (no selection)
                section_options = [ft.dropdown.Option("", "-- Select Section --")]
                if sections:
                    section_options.extend([ft.dropdown.Option(sec) for sec in sections])

                section_dropdown = ft.Dropdown(
                    label=t('section'),
                    hint_text=t('select_section'),
                    options=section_options,
                    value=user.get('section') if is_edit else "",
                    expand=True,
                    disabled=len(sections) == 0
                )

                # Build unit options with "-- Select Unit --" as first option (no selection)
                unit_options = [ft.dropdown.Option("", "-- Select Unit --")]
                if direct_units:
                    unit_options.extend([ft.dropdown.Option(u) for u in direct_units])

                # Initially populate with direct units under department (no section selected yet)
                unit_dropdown = ft.Dropdown(
                    label=t('unit'),
                    hint_text=t('select_unit'),
                    options=unit_options,
                    value=user.get('unit') if is_edit else "",
                    expand=True,
                    disabled=len(direct_units) == 0
                )

                # If editing and has section selected, populate units from that section
                if is_edit and user.get('section'):
                    units = get_units_for_department(expert_dept, user['section'], current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")] + [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False

                # Add cascading logic for department-level experts
                def on_section_change_expert(e):
                    """When section changes for department-level expert"""
                    selected_section = e.control.value
                    current_lang = get_language()

                    if selected_section and selected_section != "":
                        # Section selected: show units under that section
                        units = get_units_for_department(expert_dept, selected_section, current_lang)
                        unit_options = [ft.dropdown.Option("", "-- Select Unit --")]
                        if units:
                            unit_options.extend([ft.dropdown.Option(u) for u in units])
                            unit_dropdown.options = unit_options
                            unit_dropdown.disabled = False
                            unit_dropdown.value = ""
                        else:
                            unit_dropdown.options = unit_options
                            unit_dropdown.disabled = True
                            unit_dropdown.value = ""
                    else:
                        # No section selected (or "-- Select Section --" chosen): show direct units under department
                        direct_units = get_units_for_department(expert_dept, None, current_lang)
                        unit_options = [ft.dropdown.Option("", "-- Select Unit --")]
                        if direct_units:
                            unit_options.extend([ft.dropdown.Option(u) for u in direct_units])
                            unit_dropdown.options = unit_options
                            unit_dropdown.disabled = False
                            unit_dropdown.value = ""
                        else:
                            unit_dropdown.options = unit_options
                            unit_dropdown.disabled = True
                            unit_dropdown.value = ""

                    unit_dropdown.update()

                section_dropdown.on_change = on_section_change_expert
        else:
            # Admins can select any department/section/unit
            # Get current language for displaying department names
            current_lang = get_language()
            departments = get_departments(current_lang)

            # Create department dropdown with "-- Select Department --" as first option (no selection)
            dept_options = [ft.dropdown.Option("", "-- Select Department --")] + [ft.dropdown.Option(dept) for dept in departments]

            department_dropdown = ft.Dropdown(
                label=t('department') + (" *" if not is_edit else ""),
                hint_text=t('select_department'),
                options=dept_options,
                value=user['department'] if is_edit else "",  # Empty string for "Select..." option
                expand=True,
                on_change=None  # Will set below
            )

            # Section dropdown (cascading - populated when department selected)
            section_dropdown = ft.Dropdown(
                label=t('section'),
                hint_text=t('select_section'),
                options=[ft.dropdown.Option("", "-- Select Section --")],
                value=user['section'] if is_edit else "",
                expand=True,
                disabled=True
            )

            # Unit dropdown (cascading - populated when department or section selected)
            unit_dropdown = ft.Dropdown(
                label=t('unit'),
                hint_text=t('select_unit'),
                options=[ft.dropdown.Option("", "-- Select Unit --")],
                value=user['unit'] if is_edit else "",
                expand=True,
                disabled=True
            )

        # Cascading dropdown logic - only for admins
        if self.user_data['role'] == 'admin':
            # Get current language
            current_lang = get_language()

            # If editing and has department, populate sections and units
            if is_edit and user.get('department'):
                sections = get_sections_for_department(user['department'], current_lang)
                if sections:
                    section_dropdown.options = [ft.dropdown.Option("", "-- Select Section --")] + [ft.dropdown.Option(sec) for sec in sections]
                    section_dropdown.disabled = False

                # If has section, get units from section
                if user.get('section'):
                    units = get_units_for_department(user['department'], user['section'], current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")] + [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False
                else:
                    # Get direct units under department
                    units = get_units_for_department(user['department'], None, current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")] + [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False

            def on_department_change(e):
                """When department changes, populate sections and units dropdowns"""
                selected_dept = e.control.value
                current_lang = get_language()

                if selected_dept and selected_dept != "":  # Check if not "Select..." option
                    # Get sections for selected department
                    sections = get_sections_for_department(selected_dept, current_lang)

                    if sections:
                        # Department has sections
                        section_dropdown.options = [ft.dropdown.Option("", "-- Select Section --")] + [ft.dropdown.Option(sec) for sec in sections]
                        section_dropdown.disabled = False
                        section_dropdown.value = ""

                        # Disable units until section is selected
                        unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")]
                        unit_dropdown.disabled = True
                        unit_dropdown.value = ""
                    else:
                        # No sections - get direct units
                        section_dropdown.options = [ft.dropdown.Option("", "-- Select Section --")]
                        section_dropdown.disabled = True
                        section_dropdown.value = ""

                        units = get_units_for_department(selected_dept, None, current_lang)
                        if units:
                            unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")] + [ft.dropdown.Option(u) for u in units]
                            unit_dropdown.disabled = False
                            unit_dropdown.value = ""
                        else:
                            unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")]
                            unit_dropdown.disabled = True
                            unit_dropdown.value = ""
                else:
                    # Clear all (user selected "Select..." option)
                    section_dropdown.options = [ft.dropdown.Option("", "-- Select Section --")]
                    section_dropdown.disabled = True
                    section_dropdown.value = ""
                    unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")]
                    unit_dropdown.disabled = True
                    unit_dropdown.value = ""

                section_dropdown.update()
                unit_dropdown.update()

            def on_section_change(e):
                """When section changes, populate units dropdown"""
                selected_section = e.control.value
                selected_dept = department_dropdown.value
                current_lang = get_language()

                if selected_section and selected_section != "" and selected_dept and selected_dept != "":
                    # Get units for selected section
                    units = get_units_for_department(selected_dept, selected_section, current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")] + [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False
                        unit_dropdown.value = ""
                    else:
                        unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")]
                        unit_dropdown.disabled = True
                        unit_dropdown.value = ""
                else:
                    unit_dropdown.options = [ft.dropdown.Option("", "-- Select Unit --")]
                    unit_dropdown.disabled = True
                    unit_dropdown.value = ""

                unit_dropdown.update()

            def on_role_change(e):
                """When role changes, show/hide department/section/unit requirement"""
                selected_role = e.control.value

                if selected_role == 'admin':
                    # Admin: hide/disable department/section/unit
                    department_dropdown.visible = False
                    section_dropdown.visible = False
                    unit_dropdown.visible = False
                elif selected_role == 'expert':
                    # Expert: department required, section/unit optional
                    department_dropdown.visible = True
                    department_dropdown.disabled = False
                    department_dropdown.label = t('department') + " *"
                    section_dropdown.visible = True
                    unit_dropdown.visible = True
                else:
                    # Examinee: show all fields (validation will check section OR unit)
                    department_dropdown.visible = True
                    department_dropdown.disabled = False
                    department_dropdown.label = t('department')
                    section_dropdown.visible = True
                    unit_dropdown.visible = True

                department_dropdown.update()
                section_dropdown.update()
                unit_dropdown.update()

            department_dropdown.on_change = on_department_change
            section_dropdown.on_change = on_section_change
            role_dropdown.on_change = on_role_change

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_user(e):
            # Validate fields individually with specific error messages
            if not username_field.value.strip():
                error_text.value = "Username is required"
                error_text.visible = True
                email_error_text.visible = False
                self.user_dialog.update()
                return

            if not email_field.value.strip():
                error_text.value = "Email is required"
                error_text.visible = True
                email_error_text.visible = False
                self.user_dialog.update()
                return

            if not full_name_field.value.strip():
                error_text.value = "Full name is required"
                error_text.visible = True
                email_error_text.visible = False
                self.user_dialog.update()
                return

            # Email validation with regex
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email_field.value.strip()):
                email_error_text.value = "Please enter a valid email address (e.g., user@example.com)"
                email_error_text.visible = True
                error_text.visible = False
                self.user_dialog.update()
                return
            else:
                # Clear email error if valid
                email_error_text.visible = False

            # Password validation for new users (should always have value since auto-generated)
            if not is_edit and not password_field.value.strip():
                error_text.value = t('password_required')
                error_text.visible = True
                self.user_dialog.update()
                return

            # Server-side role validation (SECURITY FIX)
            valid_roles = ['admin', 'expert', 'examinee']
            if role_dropdown.value not in valid_roles:
                error_text.value = f"Invalid role: {role_dropdown.value}. Must be admin, expert, or examinee."
                error_text.visible = True
                self.user_dialog.update()
                return

            # Get department/section/unit values (handle both Dropdown and TextField)
            dept_value = department_dropdown.value if hasattr(department_dropdown, 'value') else None
            section_value = section_dropdown.value if hasattr(section_dropdown, 'value') else None
            unit_value = unit_dropdown.value if hasattr(unit_dropdown, 'value') else None

            # Convert empty strings to None
            if dept_value == "":
                dept_value = None
            if section_value == "":
                section_value = None
            if unit_value == "":
                unit_value = None

            # Role-based validation
            if role_dropdown.value == 'expert':
                # Expert: department required, section/unit optional
                if not dept_value:
                    error_text.value = t('department_required_for_expert')
                    error_text.visible = True
                    self.user_dialog.update()
                    return
                # Section and unit are optional for experts (allows department-level experts)

            elif role_dropdown.value == 'examinee':
                # Examinee: either section OR unit must be selected (at least one)
                if not section_value and not unit_value:
                    error_text.value = "Examinee must have at least a section or unit assigned"
                    error_text.visible = True
                    self.user_dialog.update()
                    return

            # Admin role: no department/section/unit required (already hidden in UI)

            try:
                if is_edit:
                    # Update user
                    query = """
                        UPDATE users SET email = ?, full_name = ?, role = ?, department = ?, section = ?, unit = ?
                        WHERE id = ?
                    """
                    params = (
                        email_field.value.strip(),
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        dept_value or None,
                        section_value or None,
                        unit_value or None,
                        user['id']
                    )
                    self.db.execute_update(query, params)

                    # Update password if provided
                    if password_field.value:
                        self.auth_manager.update_password(user['id'], password_field.value)
                else:
                    # Create new user (password already auto-generated and pre-filled)
                    user_password = password_field.value.strip()

                    user_id = self.auth_manager.create_user(
                        username_field.value.strip(),
                        email_field.value.strip(),
                        user_password,
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        dept_value or None,
                        section_value or None,
                        unit_value or None
                    )

                    if not user_id:
                        error_text.value = t('user_already_exists')
                        error_text.visible = True
                        self.user_dialog.update()
                        return

                    # Set password_change_required flag for new users
                    self.db.execute_update(
                        "UPDATE users SET password_change_required = 1 WHERE id = ?",
                        (user_id,)
                    )

                    # Close dialog
                    self.user_dialog.open = False
                    if self.page:
                        self.page.update()

                    # Show success dialog with password
                    self.show_password_success_dialog(
                        username_field.value.strip(),
                        user_password,
                        email_field.value.strip(),
                        full_name_field.value.strip()
                    )
                    return  # Success dialog will handle reload

                # For edit mode: Close dialog and refresh
                self.user_dialog.open = False
                if self.page:
                    self.page.update()

                # Reload users and update UI
                self.load_users()

                # Force update of the entire user management component
                if self.page:
                    self.update()
                
            except Exception as ex:
                error_text.value = f"{t('error')}: {str(ex)}"
                error_text.visible = True
                self.user_dialog.update()
        
        def close_dialog(e):
            self.user_dialog.open = False
            self.page.update()
        
        # Build dialog content
        dialog_content_items = [
            username_field,
            email_field,
            email_error_text,  # Show email validation error below email field
            full_name_field,
            password_field,
            role_dropdown,
            department_dropdown,
            section_dropdown,
            unit_dropdown,
            error_text
        ]

        self.user_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column(dialog_content_items, spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                width=500,
                padding=ft.padding.all(10)
            ),
            actions=[
                ft.TextButton(t('cancel'), on_click=close_dialog),
                ft.ElevatedButton(
                    t('save') if is_edit else t('create'),
                    on_click=save_user,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = self.user_dialog
        self.user_dialog.open = True
        self.page.update()
    
    def toggle_user_status(self, user):
        # Normalize is_active: ensure it's 0 or 1 (handle None values)
        is_active_value = user.get('is_active')
        if is_active_value is None:
            is_active_value = 0
        
        # Convert to boolean (SQLite returns 0/1 as integers)
        is_currently_active = bool(is_active_value)
        
        # Check if trying to deactivate an admin
        if is_currently_active and user['role'] == 'admin':
            # Count active admins
            active_admins = self.db.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE role = 'admin' AND is_active = 1"
            )
            admin_count = active_admins[0]['count'] if active_admins else 0

            # Prevent deactivation if this is the last active admin
            if admin_count <= 1:
                # Show error dialog
                error_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(t('error'), color=COLORS['error']),
                    content=ft.Text(t('cannot_deactivate_last_admin')),
                    actions=[
                        ft.TextButton(
                            t('ok'),
                            on_click=lambda e: self.close_error_dialog(error_dialog)
                        )
                    ],
                    actions_alignment=ft.MainAxisAlignment.END
                )
                self.page.dialog = error_dialog
                error_dialog.open = True
                self.page.update()
                return

        # Toggle status: if active (1), set to inactive (0), otherwise set to active (1)
        new_status = 0 if is_currently_active else 1
        
        # Handle case where id might be None (use username as fallback)
        user_id = user.get('id')
        username = user.get('username')
        
        if user_id is not None:
            # Use ID if available (normal case)
            self.db.execute_update(
                "UPDATE users SET is_active = ? WHERE id = ?",
                (new_status, user_id)
            )
        elif username:
            # Fallback to username if ID is None (data integrity issue)
            self.db.execute_update(
                "UPDATE users SET is_active = ? WHERE username = ?",
                (new_status, username)
            )
        else:
            # No identifier available - show error
            if self.page:
                self.page.show_snack_bar(ft.SnackBar(
                    content=ft.Text("Error: Cannot update user status - missing user identifier"),
                    bgcolor=COLORS['error']
                ))
                self.page.update()
            return

        # Reload users and update UI
        self.load_users()
        
        # Force update of the component
        if self.page:
            self.update()

    def close_error_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def show_password_success_dialog(self, username, password, email, full_name):
        """
        Show dialog with generated password and option to send email via Outlook
        """
        from quiz_app.utils.password_email import open_email_draft

        # Password display (copyable, revealed)
        password_display = ft.TextField(
            value=password,
            read_only=True,
            password=False,  # Show password
            border_color=COLORS['success'],
            text_size=16,
            width=350
        )

        def copy_password(e):
            try:
                pyperclip.copy(password)
                copy_btn.icon = ft.icons.CHECK
                copy_btn.icon_color = COLORS['success']
                copy_btn.tooltip = "Copied!"
                copy_btn.update()
                self.page.show_snack_bar(ft.SnackBar(
                    content=ft.Text("✓ Password copied to clipboard"),
                    bgcolor=COLORS['success']
                ))
            except Exception as ex:
                self.page.show_snack_bar(ft.SnackBar(
                    content=ft.Text(f"Failed to copy: {str(ex)}"),
                    bgcolor=COLORS['error']
                ))

        copy_btn = ft.IconButton(
            icon=ft.icons.COPY,
            tooltip="Copy password",
            on_click=copy_password,
            icon_color=COLORS['primary']
        )

        def open_email_clicked(e):
            success = open_email_draft(email, username, password, full_name)
            if success:
                self.page.show_snack_bar(ft.SnackBar(
                    content=ft.Text(f"✓ Email draft opened in Outlook for {email}"),
                    bgcolor=COLORS['success']
                ))
            else:
                self.page.show_snack_bar(ft.SnackBar(
                    content=ft.Text("Failed to open email client"),
                    bgcolor=COLORS['error']
                ))

        def close_success_dialog(e):
            success_dialog.open = False
            self.page.update()
            # Reload users and update UI
            self.load_users()
            self.update()

        success_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.CHECK_CIRCLE, color=COLORS['success'], size=28),
                ft.Text("User Created Successfully!", weight=ft.FontWeight.BOLD)
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("The user account has been created. Please share these credentials:", size=14),
                    ft.Divider(height=20),

                    # Username
                    ft.Row([
                        ft.Text("Username:", weight=ft.FontWeight.BOLD, size=14, width=120),
                        ft.Text(username, size=14, selectable=True)
                    ]),

                    # Password with copy button
                    ft.Row([
                        ft.Text("Password:", weight=ft.FontWeight.BOLD, size=14, width=120),
                        ft.Container(
                            content=ft.Row([
                                password_display,
                                copy_btn
                            ], spacing=5),
                            expand=True
                        )
                    ]),

                    ft.Divider(height=10),

                    # Warning box
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.WARNING_AMBER, color=COLORS['warning'], size=20),
                                ft.Text(
                                    "Security Notice",
                                    weight=ft.FontWeight.BOLD,
                                    color=COLORS['warning'],
                                    size=14
                                )
                            ], spacing=10),
                            ft.Text(
                                "• User MUST change password on first login",
                                size=12,
                                color=COLORS['text_primary']
                            ),
                            ft.Text(
                                "• Password will be required to be changed immediately",
                                size=12,
                                color=COLORS['text_primary']
                            ),
                            ft.Text(
                                "• Keep this password secure until delivered to user",
                                size=12,
                                color=COLORS['text_primary']
                            )
                        ], spacing=5),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                        padding=15,
                        border_radius=8,
                        border=ft.border.all(1, COLORS['warning'])
                    ),
                ], spacing=10, tight=True),
                width=500
            ),
            actions=[
                ft.ElevatedButton(
                    "Open Email in Outlook",
                    icon=ft.icons.EMAIL_OUTLINED,
                    on_click=open_email_clicked,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                ),
                ft.TextButton("Close", on_click=close_success_dialog)
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        self.page.dialog = success_dialog
        success_dialog.open = True
        self.page.update()