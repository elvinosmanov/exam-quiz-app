import flet as ft
from datetime import datetime, timedelta, date
from quiz_app.config import COLORS

class QuizManagement(ft.UserControl):
    def __init__(self, db, user_data):
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.exams_data = []
        self.all_exams_data = []  # Keep original data for filtering
        self.selected_exam = None

        # Search control
        self.search_field = ft.TextField(
            label="Search exams...",
            prefix_icon=ft.icons.SEARCH,
            on_change=self.apply_filters,
            width=300
        )
        
        # Status filter
        self.status_filter = ft.Dropdown(
            label="Filter by Status",
            options=[
                ft.dropdown.Option("all", "All Status"),
                ft.dropdown.Option("active", "Active"),
                ft.dropdown.Option("inactive", "Inactive"),
                ft.dropdown.Option("scheduled", "Scheduled")
            ],
            value="all",
            on_change=self.apply_filters,
            width=150
        )
        
        # Exams table
        self.exams_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Title")),
                ft.DataColumn(ft.Text("Category")),
                ft.DataColumn(ft.Text("Duration")),
                ft.DataColumn(ft.Text("Passing Score")),
                ft.DataColumn(ft.Text("Questions")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Created")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )
        
        # Action buttons
        self.add_exam_btn = ft.ElevatedButton(
            text="Create Exam",
            icon=ft.icons.ADD,
            on_click=self.show_add_exam_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )
        
        # Dialog for adding/editing exams
        self.exam_dialog = None
    
    def did_mount(self):
        """Called after the control is added to the page"""
        super().did_mount()
        self.load_exams()
    
    def build(self):
        return ft.Column([
            # Header
            ft.Row([
                ft.Text("Exam Management", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(expand=True),
                self.add_exam_btn
            ]),
            ft.Divider(),
            
            # Filters
            ft.Row([
                self.search_field,
                self.status_filter
            ], spacing=20),
            
            ft.Container(height=10),
            
            # Exams table
            ft.Container(
                content=ft.ListView(
                    controls=[self.exams_table],
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
    
    def load_exams(self):
        self.all_exams_data = self.db.execute_query("""
            SELECT e.*,
                   COUNT(q.id) as question_count,
                   u.full_name as creator_name
            FROM exams e
            LEFT JOIN questions q ON e.id = q.exam_id AND q.is_active = 1
            LEFT JOIN users u ON e.created_by = u.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
        """)
        self.exams_data = self.all_exams_data.copy()
        self.apply_filters(None)
    
    def update_table(self):
        self.exams_table.rows.clear()

        for idx, exam in enumerate(self.exams_data, 1):
            # Create enhanced status badges
            status_badges = self.calculate_exam_status_badges(exam)

            self.exams_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Text(exam['title'])),
                        ft.DataCell(ft.Text(exam.get('category') or "No Category")),
                        ft.DataCell(ft.Text(f"{exam['duration_minutes']} min")),
                        ft.DataCell(ft.Text(f"{exam['passing_score']}%")),
                        ft.DataCell(ft.Text(str(exam['question_count'] or 0))),
                        ft.DataCell(status_badges),
                        ft.DataCell(ft.Text(exam['created_at'][:10])),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip="Edit Exam",
                                    on_click=lambda e, ex=exam: self.show_edit_exam_dialog(ex)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.QUIZ,
                                    tooltip="Manage Questions",
                                    on_click=lambda e, ex=exam: self.manage_questions(ex)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.PEOPLE,
                                    tooltip="Manage Users",
                                    on_click=lambda e, ex=exam: self.show_user_assignment_dialog(ex)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.TOGGLE_ON if exam['is_active'] else ft.icons.TOGGLE_OFF,
                                    tooltip="Deactivate" if exam['is_active'] else "Activate",
                                    on_click=lambda e, ex=exam: self.toggle_exam_status(ex),
                                    icon_color=COLORS['success'] if exam['is_active'] else COLORS['error']
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    tooltip="Delete Exam",
                                    on_click=lambda e, ex=exam: self.delete_exam(ex),
                                    icon_color=COLORS['error']
                                )
                            ], spacing=5)
                        )
                    ]
                )
            )
        
        self.update()
    
    def apply_filters(self, e):
        """Apply both search and status filters together"""
        # Start with all exams
        filtered_exams = self.all_exams_data.copy()

        # Apply search filter
        search_term = self.search_field.value.lower() if self.search_field.value else ""
        if search_term:
            filtered_exams = [
                exam for exam in filtered_exams
                if search_term in exam['title'].lower() or
                   search_term in (exam['description'] or "").lower() or
                   search_term in (exam.get('category') or "").lower()
            ]

        # Apply status filter
        status_filter = self.status_filter.value
        if status_filter == "active":
            filtered_exams = [exam for exam in filtered_exams if exam['is_active'] == 1]
        elif status_filter == "inactive":
            filtered_exams = [exam for exam in filtered_exams if exam['is_active'] == 0]
        elif status_filter == "scheduled":
            # Check if exam has future availability_from date
            from datetime import datetime
            now = datetime.now()
            filtered_exams = [
                exam for exam in filtered_exams
                if exam.get('availability_from') and
                datetime.fromisoformat(exam['availability_from']) > now
            ]

        # Update displayed data
        self.exams_data = filtered_exams
        self.update_table()
    
    def show_add_exam_dialog(self, e):
        self.show_exam_dialog()
    
    def show_edit_exam_dialog(self, exam):
        self.show_exam_dialog(exam)
    
    def show_exam_dialog(self, exam=None):
        is_edit = exam is not None
        title = "Edit Exam" if is_edit else "Create New Exam"
        
        # Form fields
        exam_title_field = ft.TextField(
            label="Exam Title",
            value=exam['title'] if is_edit else "",
            content_padding=8,
            hint_text="Enter a descriptive exam title"
        )
        
        description_field = ft.TextField(
            label="Description (optional)",
            value=exam['description'] if is_edit else "",
            multiline=True,
            min_lines=3,
            max_lines=6,
            content_padding=8,
            hint_text="Provide exam instructions or description"
        )
        
        duration_field = ft.TextField(
            label="Duration (minutes)",
            value=str(exam['duration_minutes']) if is_edit else "60",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 90",
            width=180
        )
        
        passing_score_field = ft.TextField(
            label="Passing Score (%)",
            value=str(exam['passing_score']) if is_edit else "70",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 80",
            width=180
        )
        
        max_attempts_field = ft.TextField(
            label="Max Attempts",
            value=str(exam['max_attempts']) if is_edit else "1",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 3",
            width=180
        )
        
        category_field = ft.TextField(
            label="Category",
            value=exam.get('category', '') if is_edit else "",
            content_padding=8,
            hint_text="e.g., Mathematics, Programming",
            width=250
        )
        
        # Security Settings Section
        randomize_questions = ft.Checkbox(
            label="Randomize Questions",
            value=bool(exam['randomize_questions']) if is_edit else False
        )
        
        show_results = ft.Checkbox(
            label="Show Results to Students",
            value=bool(exam['show_results']) if is_edit else True
        )
        
        enable_fullscreen = ft.Checkbox(
            label="Enable Full Window Mode",
            value=bool(exam.get('enable_fullscreen', 0)) if is_edit else False
        )
        
        prevent_focus_loss = ft.Checkbox(
            label="Prevent Focus Loss",
            value=bool(exam.get('prevent_focus_loss', 0)) if is_edit else False
        )
        
        enable_logging = ft.Checkbox(
            label="Enable Activity Logging",
            value=bool(exam.get('enable_logging', 0)) if is_edit else False
        )
        
        enable_pattern_analysis = ft.Checkbox(
            label="Enable Answer Pattern Analysis",
            value=bool(exam.get('enable_pattern_analysis', 0)) if is_edit else False
        )
        
        # Question Pool Settings Section
        use_question_pool = ft.Checkbox(
            label="Use Question Pool (Random Selection)",
            value=bool(exam.get('use_question_pool', 0)) if is_edit else False,
            on_change=lambda e: toggle_question_pool_fields(e.control.value)
        )
        
        total_questions_in_pool_field = ft.TextField(
            label="Total Questions in Pool",
            value=str(exam.get('total_questions_in_pool', 0)) if is_edit else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 30",
            width=180,
            disabled=not bool(exam.get('use_question_pool', 0)) if is_edit else True
        )
        
        questions_to_select_field = ft.TextField(
            label="Questions to Select",
            value=str(exam.get('questions_to_select', 0)) if is_edit else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 10",
            width=180,
            disabled=not bool(exam.get('use_question_pool', 0)) if is_edit else True
        )
        
        easy_questions_count_field = ft.TextField(
            label="Easy Questions",
            value=str(exam.get('easy_questions_count', 0)) if is_edit else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 3",
            width=150,
            disabled=not bool(exam.get('use_question_pool', 0)) if is_edit else True
        )
        
        medium_questions_count_field = ft.TextField(
            label="Medium Questions",
            value=str(exam.get('medium_questions_count', 0)) if is_edit else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 4",
            width=150,
            disabled=not bool(exam.get('use_question_pool', 0)) if is_edit else True
        )
        
        hard_questions_count_field = ft.TextField(
            label="Hard Questions",
            value=str(exam.get('hard_questions_count', 0)) if is_edit else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=8,
            hint_text="e.g., 3",
            width=150,
            disabled=not bool(exam.get('use_question_pool', 0)) if is_edit else True
        )
        
        def toggle_question_pool_fields(enabled):
            """Enable/disable question pool fields based on checkbox state"""
            total_questions_in_pool_field.disabled = not enabled
            questions_to_select_field.disabled = not enabled
            easy_questions_count_field.disabled = not enabled
            medium_questions_count_field.disabled = not enabled
            hard_questions_count_field.disabled = not enabled
            if hasattr(self, 'page') and self.page:
                self.page.update()
        
        # Date picker components
        self.selected_start_date = None
        self.selected_end_date = None
        
        # Initialize dates from exam data if editing
        if is_edit and exam.get('start_date'):
            try:
                self.selected_start_date = datetime.fromisoformat(exam['start_date']).date()
            except:
                self.selected_start_date = None
        
        if is_edit and exam.get('end_date'):
            try:
                self.selected_end_date = datetime.fromisoformat(exam['end_date']).date()
            except:
                self.selected_end_date = None
        
        # Start date picker
        self.start_date_picker = ft.DatePicker(
            first_date=date.today(),
            last_date=date(2030, 12, 31),
            value=self.selected_start_date
        )
        
        # End date picker  
        self.end_date_picker = ft.DatePicker(
            first_date=date.today(),
            last_date=date(2030, 12, 31),
            value=self.selected_end_date
        )
        
        # Date display fields (clickable to open date pickers)
        start_date_field = ft.TextField(
            label="Start Date",
            value=self.selected_start_date.strftime("%Y-%m-%d") if self.selected_start_date else "",
            read_only=True,
            content_padding=8,
            hint_text="Click to select date",
            on_click=lambda e: self.page.open(self.start_date_picker),
            suffix=ft.IconButton(
                icon=ft.icons.CALENDAR_TODAY,
                on_click=lambda e: self.page.open(self.start_date_picker)
            )
        )
        
        end_date_field = ft.TextField(
            label="End Date",
            value=self.selected_end_date.strftime("%Y-%m-%d") if self.selected_end_date else "",
            read_only=True,
            content_padding=8,
            hint_text="Click to select date",
            on_click=lambda e: self.page.open(self.end_date_picker),
            suffix=ft.IconButton(
                icon=ft.icons.CALENDAR_TODAY,
                on_click=lambda e: self.page.open(self.end_date_picker)
            )
        )
        
        
        error_text = ft.Text("", color=COLORS['error'], visible=False)
        
        def save_exam(e):
            # Validate fields
            if not exam_title_field.value.strip():
                error_text.value = "Exam title is required"
                error_text.visible = True
                self.exam_dialog.update()
                return
            
            try:
                duration = int(duration_field.value)
                passing_score = float(passing_score_field.value)
                max_attempts = int(max_attempts_field.value)
                
                if duration <= 0 or passing_score <= 0 or passing_score > 100 or max_attempts <= 0:
                    error_text.value = "Invalid values for duration, passing score, or max attempts"
                    error_text.visible = True
                    self.exam_dialog.update()
                    return
                
                # Question pool validation
                use_pool = use_question_pool.value
                total_in_pool = int(total_questions_in_pool_field.value) if total_questions_in_pool_field.value else 0
                to_select = int(questions_to_select_field.value) if questions_to_select_field.value else 0
                easy_count = int(easy_questions_count_field.value) if easy_questions_count_field.value else 0
                medium_count = int(medium_questions_count_field.value) if medium_questions_count_field.value else 0
                hard_count = int(hard_questions_count_field.value) if hard_questions_count_field.value else 0
                
                if use_pool:
                    # Validate question pool settings
                    if to_select <= 0:
                        error_text.value = "Questions to select must be greater than 0"
                        error_text.visible = True
                        self.exam_dialog.update()
                        return
                    
                    if easy_count + medium_count + hard_count != to_select:
                        error_text.value = f"Difficulty distribution ({easy_count + medium_count + hard_count}) must equal questions to select ({to_select})"
                        error_text.visible = True
                        self.exam_dialog.update()
                        return
                    
                    if easy_count < 0 or medium_count < 0 or hard_count < 0:
                        error_text.value = "Difficulty counts cannot be negative"
                        error_text.visible = True
                        self.exam_dialog.update()
                        return
                
                # Prepare data
                exam_data = {
                    'title': exam_title_field.value.strip(),
                    'description': description_field.value.strip() or None,
                    'category': category_field.value.strip() or None,
                    'duration_minutes': duration,
                    'passing_score': passing_score,
                    'max_attempts': max_attempts,
                    'randomize_questions': 1 if randomize_questions.value else 0,
                    'show_results': 1 if show_results.value else 0,
                    'start_date': self.selected_start_date.isoformat() if self.selected_start_date else None,
                    'end_date': self.selected_end_date.isoformat() if self.selected_end_date else None,
                    'enable_fullscreen': 1 if enable_fullscreen.value else 0,
                    'prevent_focus_loss': 1 if prevent_focus_loss.value else 0,
                    'enable_logging': 1 if enable_logging.value else 0,
                    'enable_pattern_analysis': 1 if enable_pattern_analysis.value else 0,
                    'use_question_pool': 1 if use_pool else 0,
                    'total_questions_in_pool': total_in_pool,
                    'questions_to_select': to_select,
                    'easy_questions_count': easy_count,
                    'medium_questions_count': medium_count,
                    'hard_questions_count': hard_count
                }
                
                if is_edit:
                    # Update exam
                    query = """
                        UPDATE exams SET title = ?, description = ?, category = ?, duration_minutes = ?, 
                        passing_score = ?, max_attempts = ?, randomize_questions = ?, 
                        show_results = ?, start_date = ?, end_date = ?, enable_fullscreen = ?, 
                        prevent_focus_loss = ?, enable_logging = ?, enable_pattern_analysis = ?,
                        use_question_pool = ?, total_questions_in_pool = ?, questions_to_select = ?,
                        easy_questions_count = ?, medium_questions_count = ?, hard_questions_count = ?
                        WHERE id = ?
                    """
                    params = list(exam_data.values()) + [exam['id']]
                    self.db.execute_update(query, params)
                    exam_id = exam['id']
                else:
                    # Create new exam
                    query = """
                        INSERT INTO exams (title, description, category, duration_minutes, passing_score, 
                        max_attempts, randomize_questions, show_results, start_date, end_date, 
                        enable_fullscreen, prevent_focus_loss, enable_logging, enable_pattern_analysis,
                        use_question_pool, total_questions_in_pool, questions_to_select,
                        easy_questions_count, medium_questions_count, hard_questions_count, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = list(exam_data.values()) + [self.user_data['id']]
                    exam_id = self.db.execute_insert(query, params)
                
                
                # Close dialog and refresh
                self.exam_dialog.open = False
                if self.page:
                    self.page.update()
                
                # Reload exams and update UI
                self.load_exams()
                
                # Force update of the entire exam management component
                if self.page:
                    self.update()
                
            except ValueError:
                error_text.value = "Please enter valid numeric values"
                error_text.visible = True
                self.exam_dialog.update()
            except Exception as ex:
                error_text.value = f"Error saving exam: {str(ex)}"
                error_text.visible = True
                self.exam_dialog.update()
        
        def close_dialog(e):
            self.exam_dialog.open = False
            self.page.update()
        
        # Date picker event handlers
        def start_date_changed(e):
            self.selected_start_date = e.control.value
            start_date_field.value = self.selected_start_date.strftime("%Y-%m-%d") if self.selected_start_date else ""
            start_date_field.update()
        
        def end_date_changed(e):
            self.selected_end_date = e.control.value
            end_date_field.value = self.selected_end_date.strftime("%Y-%m-%d") if self.selected_end_date else ""
            end_date_field.update()
        
        # Update date picker handlers
        self.start_date_picker.on_change = start_date_changed
        self.end_date_picker.on_change = end_date_changed
        
        # Add date pickers to page overlays
        if self.page:
            self.page.overlay.extend([self.start_date_picker, self.end_date_picker])
        
        self.exam_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column([
                    exam_title_field,
                    description_field,
                    ft.Row([duration_field, passing_score_field, max_attempts_field], spacing=10),
                    ft.Row([category_field], spacing=10),
                    ft.Row([start_date_field, end_date_field], spacing=15),
                    ft.Container(height=15),  # Section separator
                    
                    # Security Settings Section
                    ft.Text("Security Settings", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                    ft.Divider(height=1, color=COLORS['primary']),
                    ft.Row([randomize_questions, show_results], spacing=20),
                    ft.Row([enable_fullscreen, prevent_focus_loss], spacing=20),
                    ft.Row([enable_logging, enable_pattern_analysis], spacing=20),
                    
                    ft.Container(height=15),  # Section separator
                    
                    # Question Pool Settings Section
                    ft.Text("Question Pool Settings", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                    ft.Divider(height=1, color=COLORS['primary']),
                    ft.Row([use_question_pool], spacing=20),
                    ft.Row([total_questions_in_pool_field, questions_to_select_field], spacing=15),
                    ft.Text("Difficulty Distribution:", size=14, weight=ft.FontWeight.W_500),
                    ft.Row([easy_questions_count_field, medium_questions_count_field, hard_questions_count_field], spacing=10),
                    
                    ft.Container(height=10),  # Section separator  
                    error_text
                ], spacing=15, tight=True, scroll=ft.ScrollMode.AUTO),
                width=800,
                height=800
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    "Save" if is_edit else "Create",
                    on_click=save_exam,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = self.exam_dialog
        self.exam_dialog.open = True
        self.page.update()
    
    
    def manage_questions(self, exam):
        """Navigate to question management with pre-selected exam"""
        print(f"Managing questions for exam: {exam['title']}")
        
        # Navigate to question management through the parent admin dashboard
        if hasattr(self, 'parent_dashboard') and self.parent_dashboard:
            # Show question management and pre-select this exam
            self.parent_dashboard.show_question_management_with_exam(exam['id'])
        else:
            # Fallback: show question management normally
            print("Parent dashboard not available, showing question management normally")
    
    def toggle_exam_status(self, exam):
        new_status = 0 if exam['is_active'] else 1
        self.db.execute_update(
            "UPDATE exams SET is_active = ? WHERE id = ?",
            (new_status, exam['id'])
        )
        
        # Reload exams and update UI
        self.load_exams()
        
        # Force update of the component
        if self.page:
            self.update()
    
    def delete_exam(self, exam):
        def confirm_delete(e):
            self.db.execute_update("DELETE FROM exams WHERE id = ?", (exam['id'],))
            self.db.execute_update("DELETE FROM questions WHERE exam_id = ?", (exam['id'],))
            confirm_dialog.open = False
            if self.page:
                self.page.update()
            
            # Reload exams and update UI
            self.load_exams()
            
            # Force update of the component
            if self.page:
                self.update()
        
        def cancel_delete(e):
            confirm_dialog.open = False
            self.page.update()
        
        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete the exam '{exam['title']}'? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_delete),
                ft.ElevatedButton(
                    "Delete",
                    on_click=confirm_delete,
                    style=ft.ButtonStyle(bgcolor=COLORS['error'], color=ft.colors.WHITE)
                )
            ]
        )
        
        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()
    
    def get_all_users(self):
        """Get all users for select all functionality"""
        try:
            return self.db.execute_query("SELECT id, username, full_name, role FROM users WHERE is_active = 1")
        except Exception as e:
            print(f"Error loading all users: {e}")
            return []
    
    def show_user_assignment_dialog(self, exam):
        """Show dialog for managing user assignments for an exam"""
        # Store exam ID for remove operations
        self.current_exam_id = exam['id']
        
        # Initialize selected items and currently assigned
        self.selected_users = []
        self.selected_departments = []
        self.all_users_selected = False  # Track select all state
        
        # Load assignment options
        user_options, department_options = self.load_assignment_dropdown_data(exam['id'])
        current_assignments = self.get_current_exam_assignments(exam['id'])
        
        # Get all available users for select all functionality
        self.all_available_users = self.get_all_users()
        
        # Determine initial checkbox state based on current assignments
        initial_all_users_state = self.are_all_users_assigned(exam['id'])
        self.all_users_selected = initial_all_users_state
        
        # Create Select All Users checkbox
        def on_select_all_users(e):
            self.all_users_selected = e.control.value
            if self.all_users_selected:
                # Select all users
                self.selected_users = [user['id'] for user in self.all_available_users if user['role'] != 'admin']
                user_dropdown.disabled = True
                department_dropdown.disabled = True
            else:
                # Deselect all users  
                self.selected_users = []
                user_dropdown.disabled = False
                department_dropdown.disabled = False
            self.update_selected_items_display()
            self.page.update()
        
        select_all_checkbox = ft.Checkbox(
            label="Select All Users",
            value=initial_all_users_state,
            on_change=on_select_all_users
        )
        
        # Create separate dropdowns for users and departments
        self.user_dropdown = ft.Dropdown(
            label="Select User",
            options=user_options,
            on_change=lambda e: self.on_user_selection(e),
            width=280,
            disabled=initial_all_users_state  # Disable if all users already selected
        )
        
        self.department_dropdown = ft.Dropdown(
            label="Select Department", 
            options=department_options,
            on_change=lambda e: self.on_department_selection(e),
            width=280,
            disabled=initial_all_users_state  # Disable if all users already selected
        )
        
        # Store references for dynamic updates
        user_dropdown = self.user_dropdown
        department_dropdown = self.department_dropdown
        
        # If all users are already assigned, set up initial state
        if initial_all_users_state:
            self.selected_users = [user['id'] for user in self.all_available_users if user['role'] != 'admin']
        
        # Container for selected items (chips)
        self.selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=5)
        
        # Container for currently assigned items
        self.current_assignments_container = ft.Column([
            ft.Text("Currently Assigned:", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=5)
        
        # Populate current assignments
        self.populate_current_assignments(current_assignments)
        
        error_text = ft.Text("", color=COLORS['error'], visible=False)
        
        def save_assignments(e):
            try:
                # Save the assignments
                self.save_exam_assignments(exam['id'])
                
                # Close dialog and refresh
                assignment_dialog.open = False
                if self.page:
                    self.page.update()
                
                # Reload exams and update UI
                self.load_exams()
                
                # Force update of the component
                if self.page:
                    self.update()
                    
            except Exception as ex:
                error_text.value = f"Error saving assignments: {str(ex)}"
                error_text.visible = True
                assignment_dialog.update()
        
        def close_assignment_dialog(e):
            assignment_dialog.open = False
            self.page.update()
        
        assignment_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Manage Users - {exam['title']}"),
            content=ft.Container(
                content=ft.Column([
                    # Select All checkbox
                    ft.Container(
                        content=select_all_checkbox,
                        padding=ft.padding.only(bottom=10),
                        border=ft.border.only(bottom=ft.BorderSide(1, COLORS['secondary'])),
                        margin=ft.margin.only(bottom=10)
                    ),
                    ft.Row([user_dropdown, department_dropdown], spacing=20),
                    ft.Container(height=20),
                    self.selected_items_container,
                    ft.Container(height=20),
                    self.current_assignments_container,
                    ft.Container(height=10),
                    error_text
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                width=600,
                height=500
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_assignment_dialog),
                ft.ElevatedButton(
                    "Save Assignments",
                    on_click=save_assignments,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = assignment_dialog
        assignment_dialog.open = True
        self.page.update()
    
    def load_assignment_dropdown_data(self, exam_id):
        """Load users and departments for the assignment dropdowns with disabled states for assigned items"""
        user_options = []
        department_options = []
        
        # Get currently assigned users for this exam
        assigned_users = self.db.execute_query("""
            SELECT u.id
            FROM exam_permissions ep
            JOIN users u ON ep.user_id = u.id
            WHERE ep.exam_id = ? AND ep.is_active = 1
        """, (exam_id,))
        assigned_user_ids = {user['id'] for user in assigned_users}
        
        # Get departments with assigned users for this exam
        assigned_departments = self.db.execute_query("""
            SELECT DISTINCT u.department
            FROM exam_permissions ep
            JOIN users u ON ep.user_id = u.id
            WHERE ep.exam_id = ? AND ep.is_active = 1 AND u.department IS NOT NULL
        """, (exam_id,))
        assigned_dept_names = {dept['department'] for dept in assigned_departments}
        
        # Load all examinee users
        users = self.db.execute_query("""
            SELECT id, full_name, username 
            FROM users 
            WHERE role = 'examinee' AND is_active = 1
            ORDER BY full_name
        """)
        
        for user in users:
            is_assigned = user['id'] in assigned_user_ids
            option_text = f"{user['full_name']} ({user['username']})"
            
            user_options.append(ft.dropdown.Option(
                key=f"user_{user['id']}", 
                text=option_text,
                disabled=is_assigned
            ))
        
        # Load all departments
        departments = self.db.execute_query("""
            SELECT DISTINCT department 
            FROM users 
            WHERE department IS NOT NULL AND department != '' AND role = 'examinee'
            ORDER BY department
        """)
        
        for dept in departments:
            is_assigned = dept['department'] in assigned_dept_names
            option_text = dept['department']
            
            department_options.append(ft.dropdown.Option(
                key=f"department_{dept['department']}", 
                text=option_text,
                disabled=is_assigned
            ))
        
        return user_options, department_options
    
    def get_current_exam_assignments(self, exam_id):
        """Get currently assigned users and departments for an exam"""
        # Get individual user assignments
        user_assignments = self.db.execute_query("""
            SELECT u.id, u.full_name, u.username, u.department
            FROM exam_permissions ep
            JOIN users u ON ep.user_id = u.id
            WHERE ep.exam_id = ? AND ep.is_active = 1
            ORDER BY u.full_name
        """, (exam_id,))
        
        return user_assignments
    
    def are_all_users_assigned(self, exam_id):
        """Check if all eligible users (examinees) are assigned to the exam"""
        try:
            # Get all eligible users (examinees only)
            all_eligible_users = [user for user in self.get_all_users() if user['role'] != 'admin']
            
            # Get currently assigned users
            current_assignments = self.get_current_exam_assignments(exam_id)
            assigned_user_ids = {user['id'] for user in current_assignments}
            
            # Check if all eligible users are assigned
            return len(all_eligible_users) > 0 and len(assigned_user_ids) == len(all_eligible_users)
        except Exception as e:
            print(f"Error checking if all users are assigned: {e}")
            return False
    
    def populate_current_assignments(self, current_assignments):
        """Populate the current assignments container"""
        if not current_assignments:
            self.current_assignments_container.controls.append(
                ft.Text("No users currently assigned", italic=True, color=COLORS['text_secondary'])
            )
        else:
            for assignment in current_assignments:
                chip = ft.Chip(
                    label=ft.Text(f"{assignment['full_name']} ({assignment['username']})"),
                    on_delete=lambda e, user_id=assignment['id']: self.remove_current_assignment(user_id),
                    delete_icon_color=COLORS['error'],
                    data=assignment['id']  # Add data attribute for identification
                )
                self.current_assignments_container.controls.append(chip)
    
    def on_user_selection(self, e):
        """Handle user selection from the user dropdown"""
        if not e.control.value:
            return
        
        selection_key = e.control.value
        selection_text = None
        
        # Find the text for the selected option
        for option in e.control.options:
            if option.key == selection_key:
                selection_text = option.text
                break
        
        if not selection_text:
            return
        
        # Check if already selected
        for control in self.selected_items_container.controls[1:]:  # Skip the title
            if hasattr(control, 'data') and control.data == selection_key:
                return  # Already selected
        
        # Add to selected items
        chip = ft.Chip(
            label=ft.Text(selection_text),
            on_delete=lambda e, key=selection_key: self.remove_selected_item(key),
            delete_icon_color=COLORS['error'],
            data=selection_key
        )
        
        self.selected_items_container.controls.append(chip)
        
        # Clear dropdown selection
        e.control.value = None
        
        if self.page:
            self.page.update()
    
    def on_department_selection(self, e):
        """Handle department selection from the department dropdown"""
        if not e.control.value:
            return
        
        selection_key = e.control.value
        selection_text = None
        
        # Find the text for the selected option
        for option in e.control.options:
            if option.key == selection_key:
                selection_text = option.text
                break
        
        if not selection_text:
            return
        
        # Check if already selected
        for control in self.selected_items_container.controls[1:]:  # Skip the title
            if hasattr(control, 'data') and control.data == selection_key:
                return  # Already selected
        
        # Add to selected items with "Department:" prefix
        chip = ft.Chip(
            label=ft.Text(f"Department: {selection_text}"),
            on_delete=lambda e, key=selection_key: self.remove_selected_item(key),
            delete_icon_color=COLORS['error'],
            data=selection_key
        )
        
        self.selected_items_container.controls.append(chip)
        
        # Clear dropdown selection
        e.control.value = None
        
        if self.page:
            self.page.update()
    
    def remove_selected_item(self, selection_key):
        """Remove item from selected items"""
        for i, control in enumerate(self.selected_items_container.controls[1:], 1):  # Skip title
            if hasattr(control, 'data') and control.data == selection_key:
                self.selected_items_container.controls.pop(i)
                break
        
        if self.page:
            self.page.update()
    
    def remove_current_assignment(self, user_id):
        """Remove user from current assignments"""
        # Remove from database
        self.db.execute_update("""
            DELETE FROM exam_permissions 
            WHERE user_id = ? AND exam_id = ?
        """, (user_id, self.current_exam_id))
        
        # Remove from UI - find the chip with matching user_id
        for i, control in enumerate(self.current_assignments_container.controls[1:], 1):  # Skip title
            if hasattr(control, 'data') and control.data == user_id:
                self.current_assignments_container.controls.pop(i)
                break
        
        # If no assignments left, show "No users currently assigned" message
        if len(self.current_assignments_container.controls) == 1:  # Only title left
            self.current_assignments_container.controls.append(
                ft.Text("No users currently assigned", italic=True, color=COLORS['text_secondary'])
            )
        
        # Refresh dropdown options to make removed user available again
        self.refresh_dropdown_options()
        
        if self.page:
            self.page.update()
    
    def refresh_dropdown_options(self):
        """Refresh dropdown options after assignment changes"""
        if hasattr(self, 'current_exam_id') and hasattr(self, 'user_dropdown') and hasattr(self, 'department_dropdown'):
            try:
                # Reload dropdown options with updated assignment states
                user_options, department_options = self.load_assignment_dropdown_data(self.current_exam_id)
                
                # Update dropdown options
                self.user_dropdown.options = user_options
                self.department_dropdown.options = department_options
                
                # Update the UI
                if self.page:
                    self.page.update()
            except Exception as e:
                print(f"Error refreshing dropdown options: {e}")
    
    def update_selected_items_display(self):
        """Update the selected items display based on current selection state"""
        # Clear current selection display (keep only the title)
        self.selected_items_container.controls = [
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD)
        ]
        
        if self.all_users_selected:
            # Show summary when all users selected
            user_count = len([u for u in self.all_available_users if u['role'] != 'admin'])
            self.selected_items_container.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"All Users Selected ({user_count} users)",
                        size=14,
                        color=COLORS['primary'],
                        weight=ft.FontWeight.BOLD
                    ),
                    padding=ft.padding.all(8),
                    bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                    border_radius=8
                )
            )
        else:
            # Show individual chips for manually selected users
            for user_id in self.selected_users:
                # Find user details
                user = next((u for u in self.all_available_users if u['id'] == user_id), None)
                if user:
                    chip = ft.Chip(
                        label=ft.Text(f"{user['full_name']} ({user['username']})"),
                        on_delete=lambda e, uid=user_id: self.remove_selected_user(uid),
                        delete_icon_color=COLORS['error'],
                        data=f"user_{user_id}"
                    )
                    self.selected_items_container.controls.append(chip)
    
    def remove_selected_user(self, user_id):
        """Remove a user from selected users list"""
        if user_id in self.selected_users:
            self.selected_users.remove(user_id)
        self.update_selected_items_display()
        if self.page:
            self.page.update()
    
    def save_exam_assignments(self, exam_id):
        """Save new user assignments for the exam"""
        self.current_exam_id = exam_id  # Store for remove operations
        
        # Handle all users selected case
        if self.all_users_selected:
            # Assign exam to all non-admin users
            for user in self.all_available_users:
                if user['role'] != 'admin':
                    # Check if already assigned
                    existing = self.db.execute_single("""
                        SELECT id FROM exam_permissions 
                        WHERE user_id = ? AND exam_id = ?
                    """, (user['id'], exam_id))
                    
                    if not existing:
                        self.db.execute_insert("""
                            INSERT INTO exam_permissions (user_id, exam_id, granted_by)
                            VALUES (?, ?, ?)
                        """, (user['id'], exam_id, self.user_data['id']))
            return
        
        # Handle manually selected users
        for user_id in self.selected_users:
            # Check if already assigned
            existing = self.db.execute_single("""
                SELECT id FROM exam_permissions 
                WHERE user_id = ? AND exam_id = ?
            """, (user_id, exam_id))
            
            if not existing:
                self.db.execute_insert("""
                    INSERT INTO exam_permissions (user_id, exam_id, granted_by)
                    VALUES (?, ?, ?)
                """, (user_id, exam_id, self.user_data['id']))
        
        # Process department selections (existing logic)
        for control in self.selected_items_container.controls[1:]:  # Skip title
            if hasattr(control, 'data'):
                selection_key = control.data
                
                if selection_key.startswith("user_"):
                    # Individual user assignment
                    user_id = int(selection_key.replace("user_", ""))
                    
                    # Check if already assigned
                    existing = self.db.execute_single("""
                        SELECT id FROM exam_permissions 
                        WHERE user_id = ? AND exam_id = ?
                    """, (user_id, exam_id))
                    
                    if not existing:
                        self.db.execute_insert("""
                            INSERT INTO exam_permissions (user_id, exam_id, granted_by)
                            VALUES (?, ?, ?)
                        """, (user_id, exam_id, self.user_data['id']))
                
                elif selection_key.startswith("department_"):
                    # Department assignment - assign to all users in department
                    department = selection_key.replace("department_", "")
                    
                    # Get all users in this department
                    dept_users = self.db.execute_query("""
                        SELECT id FROM users 
                        WHERE department = ? AND role = 'examinee' AND is_active = 1
                    """, (department,))
                    
                    for user in dept_users:
                        # Check if already assigned
                        existing = self.db.execute_single("""
                            SELECT id FROM exam_permissions 
                            WHERE user_id = ? AND exam_id = ?
                        """, (user['id'], exam_id))
                        
                        if not existing:
                            self.db.execute_insert("""
                                INSERT INTO exam_permissions (user_id, exam_id, granted_by)
                                VALUES (?, ?, ?)
                            """, (user['id'], exam_id, self.user_data['id']))
    
    def calculate_exam_status_badges(self, exam):
        """Calculate and return stacked status badges for an exam"""
        badges = []
        
        # 1. Assignment Status Badge
        # Get assignment count for this exam
        assignment_count = self.db.execute_single("""
            SELECT COUNT(*) as count FROM exam_permissions 
            WHERE exam_id = ? AND is_active = 1
        """, (exam['id'],))
        
        assigned_count = assignment_count['count'] if assignment_count else 0
        
        if assigned_count == 0:
            badges.append(ft.Container(
                content=ft.Text("No Users", size=10, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                bgcolor=ft.colors.ORANGE,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                border_radius=3
            ))
        else:
            # Check if all examinees are assigned
            total_examinees = self.db.execute_single("""
                SELECT COUNT(*) as count FROM users 
                WHERE role = 'examinee' AND is_active = 1
            """)
            
            total_count = total_examinees['count'] if total_examinees else 0
            
            if assigned_count >= total_count and total_count > 0:
                badges.append(ft.Container(
                    content=ft.Text("All Users", size=10, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.colors.PURPLE,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=3
                ))
            else:
                badges.append(ft.Container(
                    content=ft.Text(f"{assigned_count} Users", size=10, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=ft.colors.BLUE,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    border_radius=3
                ))
        
        # 2. Schedule Status Badge
        now = datetime.now()
        if exam['start_date'] and exam['end_date']:
            try:
                start_date = datetime.fromisoformat(exam['start_date'])
                end_date = datetime.fromisoformat(exam['end_date'])
                
                if now < start_date:
                    badges.append(ft.Container(
                        content=ft.Text("Scheduled", size=10, color=ft.colors.BLACK, weight=ft.FontWeight.BOLD),
                        bgcolor=COLORS['warning'],
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=3
                    ))
                elif now > end_date:
                    badges.append(ft.Container(
                        content=ft.Text("Expired", size=10, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor=ft.colors.GREY,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=3
                    ))
                else:
                    badges.append(ft.Container(
                        content=ft.Text("Live", size=10, color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                        bgcolor=COLORS['success'],
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=3
                    ))
            except:
                # If date parsing fails, show no schedule badge
                pass
        
        # Return a column with all badges stacked vertically
        return ft.Column(badges, spacing=2, tight=True)