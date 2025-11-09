import flet as ft
from quiz_app.utils.auth import AuthManager
from quiz_app.config import COLORS, DEPARTMENTS, get_units_for_department
from quiz_app.utils.permissions import UnitPermissionManager

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
            label="Search users...",
            prefix_icon=ft.icons.SEARCH,
            on_change=self.apply_filters,
            expand=True
        )

        self.role_filter = ft.Dropdown(
            label="Filter by Role",
            options=[
                ft.dropdown.Option("all", "All Roles"),
                ft.dropdown.Option("admin", "Admin"),
                ft.dropdown.Option("expert", "Expert"),
                ft.dropdown.Option("examinee", "Examinee")
            ],
            value="all",
            on_change=self.apply_filters,
            width=200
        )
        
        # Users table
        self.users_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Username")),
                ft.DataColumn(ft.Text("Full Name")),
                ft.DataColumn(ft.Text("Email")),
                ft.DataColumn(ft.Text("Role")),
                ft.DataColumn(ft.Text("Department")),
                ft.DataColumn(ft.Text("Unit")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )
        
        # Action buttons
        self.add_user_btn = ft.ElevatedButton(
            text="Add User",
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
                ft.Text("User Management", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
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
        # Experts can only see examinees in their unit
        if self.user_data['role'] == 'expert':
            department = self.user_data.get('department', '')
            unit = self.user_data.get('unit', '')

            self.all_users_data = self.db.execute_query("""
                SELECT id, username, full_name, email, role, department, unit, is_active, created_at
                FROM users
                WHERE role = 'examinee'
                AND department = ?
                AND unit = ?
                ORDER BY created_at DESC
            """, (department, unit))
        else:
            # Admins see all users
            self.all_users_data = self.db.execute_query("""
                SELECT id, username, full_name, email, role, department, unit, is_active, created_at
                FROM users
                ORDER BY created_at DESC
            """)
        self.users_data = self.all_users_data.copy()
        self.apply_filters(None)
    
    def update_table(self):
        self.users_table.rows.clear()

        for idx, user in enumerate(self.users_data, 1):
            status = "Active" if user['is_active'] else "Inactive"
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
                        ft.DataCell(ft.Text(user['unit'] or "N/A")),
                        ft.DataCell(ft.Text(status, color=status_color)),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip="Edit User",
                                    on_click=lambda e, u=user: self.show_edit_user_dialog(u)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE if user['is_active'] else ft.icons.RESTORE,
                                    tooltip="Deactivate User" if user['is_active'] else "Activate User",
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
        title = "Edit User" if is_edit else "Add New User"
        
        # Form fields
        username_field = ft.TextField(
            label="Username",
            value=user['username'] if is_edit else "",
            disabled=is_edit  # Don't allow username changes
        )
        
        email_field = ft.TextField(
            label="Email",
            value=user['email'] if is_edit else ""
        )
        
        full_name_field = ft.TextField(
            label="Full Name",
            value=user['full_name'] if is_edit else ""
        )
        
        password_field = ft.TextField(
            label="Password" if not is_edit else "New Password (leave empty to keep current)",
            password=True,
            can_reveal_password=True
        )
        
        # Role dropdown - restrict for experts
        if self.user_data['role'] == 'expert':
            # Experts can only create examinees
            role_dropdown = ft.Dropdown(
                label="Role",
                options=[ft.dropdown.Option("examinee", "Examinee")],
                value="examinee",
                disabled=True,  # Force examinee role
                on_change=None
            )
        else:
            # Admins can create any role
            role_dropdown = ft.Dropdown(
                label="Role",
                options=[
                    ft.dropdown.Option("admin", "Admin"),
                    ft.dropdown.Option("expert", "Expert"),
                    ft.dropdown.Option("examinee", "Examinee")
                ],
                value=user['role'] if is_edit else "examinee",
                on_change=None  # Will set below
            )

        # Department/Unit - auto-fill and lock for experts
        if self.user_data['role'] == 'expert':
            # Experts can only create users in their own unit
            department_dropdown = ft.TextField(
                label="Department",
                value=self.user_data.get('department', ''),
                disabled=True,  # Locked to expert's department
                width=300
            )

            unit_dropdown = ft.TextField(
                label="Unit",
                value=self.user_data.get('unit', ''),
                disabled=True,  # Locked to expert's unit
                width=300
            )
        else:
            # Admins can select any department/unit
            department_dropdown = ft.Dropdown(
                label="Department" + (" *" if not is_edit else ""),
                hint_text="Select department",
                options=[ft.dropdown.Option(dept) for dept in DEPARTMENTS],
                value=user['department'] if is_edit else None,
                width=300,
                on_change=None  # Will set below
            )

            # Unit dropdown (cascading - populated when department selected)
            unit_dropdown = ft.Dropdown(
                label="Unit" + (" *" if not is_edit else ""),
                hint_text="First select department",
                options=[],
                value=user['unit'] if is_edit else None,
                width=300,
                disabled=True
            )

        # Cascading dropdown logic - only for admins
        if self.user_data['role'] == 'admin':
            # If editing and has department, populate units
            if is_edit and user.get('department'):
                units = get_units_for_department(user['department'])
                unit_dropdown.options = [ft.dropdown.Option(unit) for unit in units]
                unit_dropdown.disabled = False

            def on_department_change(e):
                """When department changes, populate units dropdown"""
                selected_dept = e.control.value

                if selected_dept:
                    # Get units for selected department
                    units = get_units_for_department(selected_dept)
                    unit_dropdown.options = [ft.dropdown.Option(unit) for unit in units]
                    unit_dropdown.disabled = False
                    unit_dropdown.value = None  # Reset selection
                else:
                    unit_dropdown.options = []
                    unit_dropdown.disabled = True
                    unit_dropdown.value = None

                unit_dropdown.update()

            def on_role_change(e):
                """When role changes, show/hide department/unit requirement"""
                selected_role = e.control.value

                # Expert requires department and unit
                if selected_role == 'expert':
                    department_dropdown.label = "Department *"
                    unit_dropdown.label = "Unit *"
                else:
                    department_dropdown.label = "Department"
                    unit_dropdown.label = "Unit"

                department_dropdown.update()
                unit_dropdown.update()

            department_dropdown.on_change = on_department_change
            role_dropdown.on_change = on_role_change

        error_text = ft.Text("", color=COLORS['error'], visible=False)
        
        def save_user(e):
            # Validate fields
            if not username_field.value.strip() or not email_field.value.strip() or not full_name_field.value.strip():
                error_text.value = "Please fill in all required fields"
                error_text.visible = True
                self.user_dialog.update()
                return

            if not is_edit and not password_field.value:
                error_text.value = "Password is required for new users"
                error_text.visible = True
                self.user_dialog.update()
                return

            # Validate expert role requirements
            if role_dropdown.value == 'expert':
                if not department_dropdown.value or not unit_dropdown.value:
                    error_text.value = "Department and Unit are required for Expert role"
                    error_text.visible = True
                    self.user_dialog.update()
                    return
            
            try:
                if is_edit:
                    # Update user
                    query = """
                        UPDATE users SET email = ?, full_name = ?, role = ?, department = ?, unit = ?
                        WHERE id = ?
                    """
                    params = (
                        email_field.value.strip(),
                        full_name_field.value.strip(),
                        role_dropdown.value,
                        department_dropdown.value or None,
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
                        unit_dropdown.value or None
                    )
                    
                    if not user_id:
                        error_text.value = "Username or email already exists"
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
                error_text.value = f"Error saving user: {str(ex)}"
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
                    unit_dropdown,
                    error_text
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                width=500,
                padding=ft.padding.all(10)
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    "Save" if is_edit else "Create",
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