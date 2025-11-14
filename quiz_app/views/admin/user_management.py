import flet as ft
from quiz_app.utils.auth import AuthManager
from quiz_app.config import COLORS, get_departments, get_sections_for_department, get_units_for_department
from quiz_app.utils.permissions import UnitPermissionManager
from quiz_app.utils.localization import t, get_language

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
    
    def load_users(self):
        """
        Load users based on role and hierarchical permissions.

        Permission Levels for Experts:
        - Department only: See all users in entire department
        - Department + Section: See all users in that section
        - Department + Section + Unit: See users in that specific unit
        """
        if self.user_data['role'] == 'expert':
            department = self.user_data.get('department', '')
            section = self.user_data.get('section')
            unit = self.user_data.get('unit')

            # Build query based on hierarchical level
            if unit:
                # Most specific: Department + Section + Unit
                # Show only users in this specific unit
                self.all_users_data = self.db.execute_query("""
                    SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                    FROM users
                    WHERE role = 'examinee'
                    AND department = ?
                    AND (section = ? OR section IS NULL)
                    AND (unit = ? OR unit IS NULL)
                    ORDER BY created_at DESC
                """, (department, section or '', unit))
            elif section:
                # Medium specific: Department + Section
                # Show all users in this section (all units under this section)
                self.all_users_data = self.db.execute_query("""
                    SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                    FROM users
                    WHERE role = 'examinee'
                    AND department = ?
                    AND (section = ? OR section IS NULL)
                    ORDER BY created_at DESC
                """, (department, section))
            else:
                # Least specific: Department only
                # Show all users in entire department (all sections and units)
                self.all_users_data = self.db.execute_query("""
                    SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                    FROM users
                    WHERE role = 'examinee'
                    AND department = ?
                    ORDER BY created_at DESC
                """, (department,))
        else:
            # Admins see all users
            self.all_users_data = self.db.execute_query("""
                SELECT id, username, full_name, email, role, department, section, unit, is_active, created_at
                FROM users
                ORDER BY created_at DESC
            """)
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
                        ft.DataCell(ft.Text(user['department'] or "N/A")),
                        ft.DataCell(ft.Text(user['section'] or "N/A")),
                        ft.DataCell(ft.Text(user['unit'] or "N/A")),
                        ft.DataCell(ft.Text(status, color=status_color)),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip=t('edit_user'),
                                    on_click=lambda e, u=user: self.show_edit_user_dialog(u)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE if user['is_active'] else ft.icons.RESTORE,
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

        email_field = ft.TextField(
            label=t('email'),
            value=user['email'] if is_edit else ""
        )

        full_name_field = ft.TextField(
            label=t('full_name'),
            value=user['full_name'] if is_edit else ""
        )

        password_field = ft.TextField(
            label=t('password') if not is_edit else t('new_password'),
            password=True,
            can_reveal_password=True
        )
        
        # Role dropdown - restrict for experts
        if self.user_data['role'] == 'expert':
            # Experts can only create examinees
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
            """
            expert_dept = self.user_data.get('department', '')
            expert_section = self.user_data.get('section')
            expert_unit = self.user_data.get('unit')
            current_lang = get_language()

            # Department is always locked to expert's department
            department_dropdown = ft.TextField(
                label=t('department'),
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
                unit_dropdown = ft.Dropdown(
                    label=t('unit'),
                    hint_text=t('select_unit'),
                    options=[ft.dropdown.Option(u) for u in units] if units else [],
                    value=user.get('unit') if is_edit else None,
                    expand=True,
                    disabled=len(units) == 0
                )
            else:
                # Expert has only department: Allow section and unit selection
                sections = get_sections_for_department(expert_dept, current_lang)
                direct_units = get_units_for_department(expert_dept, None, current_lang)

                section_dropdown = ft.Dropdown(
                    label=t('section'),
                    hint_text=t('select_section'),
                    options=[ft.dropdown.Option(sec) for sec in sections] if sections else [],
                    value=user.get('section') if is_edit else None,
                    expand=True,
                    disabled=len(sections) == 0
                )

                # Initially populate with direct units under department (no section selected yet)
                unit_dropdown = ft.Dropdown(
                    label=t('unit'),
                    hint_text=t('select_unit'),
                    options=[ft.dropdown.Option(u) for u in direct_units] if direct_units else [],
                    value=user.get('unit') if is_edit else None,
                    expand=True,
                    disabled=len(direct_units) == 0
                )

                # If editing and has section selected, populate units from that section
                if is_edit and user.get('section'):
                    units = get_units_for_department(expert_dept, user['section'], current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False

                # Add cascading logic for department-level experts
                def on_section_change_expert(e):
                    """When section changes for department-level expert"""
                    selected_section = e.control.value
                    current_lang = get_language()

                    if selected_section:
                        # Section selected: show units under that section
                        units = get_units_for_department(expert_dept, selected_section, current_lang)
                        if units:
                            unit_dropdown.options = [ft.dropdown.Option(u) for u in units]
                            unit_dropdown.disabled = False
                            unit_dropdown.value = None
                        else:
                            unit_dropdown.options = []
                            unit_dropdown.disabled = True
                            unit_dropdown.value = None
                    else:
                        # No section selected: show direct units under department
                        direct_units = get_units_for_department(expert_dept, None, current_lang)
                        if direct_units:
                            unit_dropdown.options = [ft.dropdown.Option(u) for u in direct_units]
                            unit_dropdown.disabled = False
                            unit_dropdown.value = None
                        else:
                            unit_dropdown.options = []
                            unit_dropdown.disabled = True
                            unit_dropdown.value = None

                    unit_dropdown.update()

                section_dropdown.on_change = on_section_change_expert
        else:
            # Admins can select any department/section/unit
            # Get current language for displaying department names
            current_lang = get_language()
            departments = get_departments(current_lang)

            department_dropdown = ft.Dropdown(
                label=t('department') + (" *" if not is_edit else ""),
                hint_text=t('select_department'),
                options=[ft.dropdown.Option(dept) for dept in departments],
                value=user['department'] if is_edit else None,
                expand=True,
                on_change=None  # Will set below
            )

            # Section dropdown (cascading - populated when department selected)
            section_dropdown = ft.Dropdown(
                label=t('section'),
                hint_text=t('select_section'),
                options=[],
                value=user['section'] if is_edit else None,
                expand=True,
                disabled=True
            )

            # Unit dropdown (cascading - populated when department or section selected)
            unit_dropdown = ft.Dropdown(
                label=t('unit'),
                hint_text=t('select_unit'),
                options=[],
                value=user['unit'] if is_edit else None,
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
                    section_dropdown.options = [ft.dropdown.Option(sec) for sec in sections]
                    section_dropdown.disabled = False

                # If has section, get units from section
                if user.get('section'):
                    units = get_units_for_department(user['department'], user['section'], current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False
                else:
                    # Get direct units under department
                    units = get_units_for_department(user['department'], None, current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False

            def on_department_change(e):
                """When department changes, populate sections and units dropdowns"""
                selected_dept = e.control.value
                current_lang = get_language()

                if selected_dept:
                    # Get sections for selected department
                    sections = get_sections_for_department(selected_dept, current_lang)

                    if sections:
                        # Department has sections
                        section_dropdown.options = [ft.dropdown.Option(sec) for sec in sections]
                        section_dropdown.disabled = False
                        section_dropdown.value = None

                        # Disable units until section is selected
                        unit_dropdown.options = []
                        unit_dropdown.disabled = True
                        unit_dropdown.value = None
                    else:
                        # No sections - get direct units
                        section_dropdown.options = []
                        section_dropdown.disabled = True
                        section_dropdown.value = None

                        units = get_units_for_department(selected_dept, None, current_lang)
                        if units:
                            unit_dropdown.options = [ft.dropdown.Option(u) for u in units]
                            unit_dropdown.disabled = False
                            unit_dropdown.value = None
                        else:
                            unit_dropdown.options = []
                            unit_dropdown.disabled = True
                            unit_dropdown.value = None
                else:
                    # Clear all
                    section_dropdown.options = []
                    section_dropdown.disabled = True
                    section_dropdown.value = None
                    unit_dropdown.options = []
                    unit_dropdown.disabled = True
                    unit_dropdown.value = None

                section_dropdown.update()
                unit_dropdown.update()

            def on_section_change(e):
                """When section changes, populate units dropdown"""
                selected_section = e.control.value
                selected_dept = department_dropdown.value
                current_lang = get_language()

                if selected_section and selected_dept:
                    # Get units for selected section
                    units = get_units_for_department(selected_dept, selected_section, current_lang)
                    if units:
                        unit_dropdown.options = [ft.dropdown.Option(u) for u in units]
                        unit_dropdown.disabled = False
                        unit_dropdown.value = None
                    else:
                        unit_dropdown.options = []
                        unit_dropdown.disabled = True
                        unit_dropdown.value = None
                else:
                    unit_dropdown.options = []
                    unit_dropdown.disabled = True
                    unit_dropdown.value = None

                unit_dropdown.update()

            def on_role_change(e):
                """When role changes, show/hide department/section/unit requirement"""
                selected_role = e.control.value

                # Expert requires only department (section and unit optional)
                if selected_role == 'expert':
                    department_dropdown.label = t('department') + " *"
                else:
                    department_dropdown.label = t('department')

                department_dropdown.update()

            department_dropdown.on_change = on_department_change
            section_dropdown.on_change = on_section_change
            role_dropdown.on_change = on_role_change

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_user(e):
            # Validate fields
            if not username_field.value.strip() or not email_field.value.strip() or not full_name_field.value.strip():
                error_text.value = t('field_required')
                error_text.visible = True
                self.user_dialog.update()
                return

            if not is_edit and not password_field.value:
                error_text.value = t('password_required')
                error_text.visible = True
                self.user_dialog.update()
                return

            # Validate expert role requirements
            if role_dropdown.value == 'expert':
                if not department_dropdown.value:
                    error_text.value = t('department_required_for_expert')
                    error_text.visible = True
                    self.user_dialog.update()
                    return
                # Section and unit are optional for experts
            
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
                        department_dropdown.value or None,
                        section_dropdown.value or None,
                        unit_dropdown.value or None,
                        user['id']
                    )
                    self.db.execute_update(query, params)

                    # Update password if provided
                    if password_field.value:
                        self.auth_manager.update_password(user['id'], password_field.value)
                else:
                    # Create new user
                    user_id = self.auth_manager.create_user(
                        username_field.value.strip(),
                        email_field.value.strip(),
                        password_field.value,
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        department_dropdown.value or None,
                        section_dropdown.value or None,
                        unit_dropdown.value or None
                    )
                    
                    if not user_id:
                        error_text.value = t('user_already_exists')
                        error_text.visible = True
                        self.user_dialog.update()
                        return
                
                # Close dialog and refresh
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
        
        self.user_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column([
                    username_field,
                    email_field,
                    full_name_field,
                    password_field,
                    role_dropdown,
                    department_dropdown,
                    section_dropdown,
                    unit_dropdown,
                    error_text
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
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
        # Check if trying to deactivate an admin
        if user['is_active'] and user['role'] == 'admin':
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

        new_status = 0 if user['is_active'] else 1
        self.db.execute_update(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (new_status, user['id'])
        )

        # Reload users and update UI
        self.load_users()

        # Force update of the component
        if self.page:
            self.update()

    def close_error_dialog(self, dialog):
        dialog.open = False
        self.page.update()