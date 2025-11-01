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
            expand=True
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
            width=200
        )
        
        # Assignments table
        self.exams_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Assignment (Exam)")),
                ft.DataColumn(ft.Text("Duration")),
                ft.DataColumn(ft.Text("Passing Score")),
                ft.DataColumn(ft.Text("Questions")),
                ft.DataColumn(ft.Text("Assigned To")),
                ft.DataColumn(ft.Text("Deadline")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )
        
        # Action buttons
        self.add_exam_btn = ft.ElevatedButton(
            text="Create Topic",
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
        # Create Assignment button
        self.add_assignment_btn = ft.ElevatedButton(
            "Create Assignment",
            icon=ft.icons.ASSIGNMENT_ADD,
            on_click=self.show_add_assignment_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )

        # Create Preset Template button
        self.add_preset_btn = ft.ElevatedButton(
            "Create Preset Template",
            icon=ft.icons.BOOKMARK_ADD,
            on_click=self.show_create_preset_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
        )

        # Manage Presets button
        self.manage_presets_btn = ft.OutlinedButton(
            "Manage Presets",
            icon=ft.icons.BOOKMARKS,
            on_click=self.show_manage_presets_dialog,
        )

        return ft.Column([
            # Header
            ft.Row([
                ft.Text("Assignment Management", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(expand=True),
                self.manage_presets_btn,
                ft.Container(width=10),
                self.add_preset_btn,
                ft.Container(width=10),
                self.add_assignment_btn
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
        # Load assignments (not exams) with exam template info
        self.all_exams_data = self.db.execute_query("""
            SELECT ea.*,
                   e.title as exam_title,
                   e.description as exam_description,
                   COUNT(DISTINCT q.id) as question_count,
                   COUNT(DISTINCT au.user_id) as assigned_users_count,
                   u.full_name as creator_name
            FROM exam_assignments ea
            JOIN exams e ON ea.exam_id = e.id
            LEFT JOIN questions q ON e.id = q.exam_id AND q.is_active = 1
            LEFT JOIN assignment_users au ON ea.id = au.assignment_id AND au.is_active = 1
            LEFT JOIN users u ON ea.created_by = u.id
            GROUP BY ea.id
            ORDER BY ea.created_at DESC
        """)
        self.exams_data = self.all_exams_data.copy()
        self.apply_filters(None)
    
    def update_table(self):
        self.exams_table.rows.clear()

        for idx, assignment in enumerate(self.exams_data, 1):
            # Create enhanced status badges
            status_badges = self.calculate_exam_status_badges(assignment)

            # Display assignment name and exam template name
            assignment_title = f"{assignment['assignment_name']} ({assignment['exam_title']})"

            self.exams_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Text(assignment_title)),
                        ft.DataCell(ft.Text(f"{assignment['duration_minutes']} min")),
                        ft.DataCell(ft.Text(f"{assignment['passing_score']}%")),
                        ft.DataCell(ft.Text(str(assignment['question_count'] or 0))),
                        ft.DataCell(ft.Text(str(assignment['assigned_users_count'] or 0) + " users")),
                        ft.DataCell(ft.Text(assignment.get('deadline')[:10] if assignment.get('deadline') else "No deadline")),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip="Edit Assignment",
                                    on_click=lambda e, ex=assignment: self.show_edit_assignment_dialog(ex)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.TOGGLE_ON if assignment['is_active'] else ft.icons.TOGGLE_OFF,
                                    tooltip="Deactivate" if assignment['is_active'] else "Activate",
                                    on_click=lambda e, ex=assignment: self.toggle_assignment_status(ex),
                                    icon_color=COLORS['success'] if assignment['is_active'] else COLORS['error']
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    tooltip="Delete Assignment",
                                    on_click=lambda e, ex=assignment: self.delete_assignment(ex),
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
                   search_term in (exam['description'] or "").lower()
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
        title = "Edit Topic" if is_edit else "Create Topic"

        # Form fields - Only basic topic information
        exam_title_field = ft.TextField(
            label="Topic Title *",
            value=exam['title'] if is_edit else "",
            content_padding=8,
            hint_text="e.g., Python Programming, Safety Training",
            width=600
        )

        description_field = ft.TextField(
            label="Description (optional)",
            value=exam['description'] if is_edit else "",
            multiline=True,
            min_lines=3,
            max_lines=6,
            content_padding=8,
            hint_text="Provide topic description",
            width=600
        )

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_exam(e):
            # Validate required fields
            if not exam_title_field.value.strip():
                error_text.value = "Topic title is required"
                error_text.visible = True
                self.exam_dialog.update()
                return

            try:
                if is_edit:
                    # Update existing exam
                    query = """
                        UPDATE exams
                        SET title = ?, description = ?
                        WHERE id = ?
                    """
                    params = (
                        exam_title_field.value.strip(),
                        description_field.value.strip() or None,
                        exam['id']
                    )
                    self.db.execute_update(query, params)
                else:
                    # Create new exam
                    query = """
                        INSERT INTO exams (title, description, created_by)
                        VALUES (?, ?, ?)
                    """
                    params = (
                        exam_title_field.value.strip(),
                        description_field.value.strip() or None,
                        self.user_data['id']
                    )
                    self.db.execute_insert(query, params)

                # Close dialog and refresh
                self.exam_dialog.open = False
                if self.page:
                    self.page.update()

                # Reload exams and update UI
                self.load_exams()

                # Force update of the entire exam management component
                if self.page:
                    self.update()

            except Exception as ex:
                error_text.value = f"Error saving exam: {str(ex)}"
                error_text.visible = True
                self.exam_dialog.update()

        def close_dialog(e):
            self.exam_dialog.open = False
            self.page.update()

        self.exam_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Container(
                content=ft.Column([
                    exam_title_field,
                    description_field,
                    ft.Container(height=10),
                    error_text
                ], spacing=15, tight=True),
                width=self.page.width - 400 if self.page.width > 400 else 600,
                height=self.page.height - 500 if self.page.height > 500 else 300
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
            # Delete all associated image files from questions in this exam
            import os
            questions_with_images = self.db.execute_query(
                "SELECT image_path FROM questions WHERE exam_id = ? AND image_path IS NOT NULL",
                (exam['id'],)
            )

            for question in questions_with_images:
                if question.get('image_path'):
                    try:
                        full_path = os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            question['image_path']
                        )
                        if os.path.exists(full_path):
                            os.remove(full_path)
                            print(f"Deleted image file: {full_path}")
                    except Exception as ex:
                        print(f"Warning: Could not delete image file {full_path}: {ex}")

            # Delete database records
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

    def show_add_assignment_dialog(self, e):
        """Show dialog to create a new assignment - with option to use preset template or manual selection"""
        # Load all available exam templates
        exam_templates = self.db.execute_query("""
            SELECT id, title, description,
                   (SELECT COUNT(*) FROM questions WHERE exam_id = exams.id AND is_active = 1) as question_count
            FROM exams
            ORDER BY title
        """)

        if not exam_templates:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("No exam templates available. Please create an exam template first."),
                bgcolor=COLORS['error']
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Load preset templates
        preset_templates = self.db.execute_query("""
            SELECT pt.id, pt.name, pt.description,
                   SUM(pte.easy_count + pte.medium_count + pte.hard_count) as total_questions
            FROM exam_preset_templates pt
            LEFT JOIN preset_template_exams pte ON pt.id = pte.template_id
            GROUP BY pt.id
            ORDER BY pt.name
        """)

        # Track selection mode
        self.assignment_mode = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="preset", label="Use Preset Template"),
                ft.Radio(value="manual", label="Select Exam Templates Manually")
            ]),
            value="manual" if not preset_templates else "preset"
        )

        # Track selected exam templates
        self.selected_exam_templates = []
        self.selected_preset_id = None

        # Preset template dropdown
        preset_dropdown = ft.Dropdown(
            label="Select Preset Template",
            hint_text="Choose a preset template",
            options=[
                ft.dropdown.Option(
                    key=str(preset['id']),
                    text=f"{preset['name']} - {preset['total_questions'] or 0} questions"
                )
                for preset in preset_templates
            ],
            width=600,
            visible=bool(preset_templates) and self.assignment_mode.value == "preset",
            disabled=not preset_templates
        )

        # Available exams dropdown (manual selection)
        exam_dropdown = ft.Dropdown(
            label="Select Exam Templates",
            hint_text="Choose exams to combine into one assignment",
            options=[
                ft.dropdown.Option(
                    key=str(exam['id']),
                    text=f"{exam['title']} - {exam['question_count']} questions"
                )
                for exam in exam_templates
            ],
            width=600,
            visible=self.assignment_mode.value == "manual"
        )

        def on_mode_change(e):
            """Toggle between preset and manual mode"""
            mode = e.control.value
            preset_dropdown.visible = (mode == "preset")
            exam_dropdown.visible = (mode == "manual")
            selected_exams_container.visible = (mode == "manual")
            preset_info_container.visible = (mode == "preset")
            select_dialog.update()

        self.assignment_mode.on_change = on_mode_change

        # Container for preset info
        preset_info_container = ft.Column([
            ft.Text("Preset Template Details:", size=13, weight=ft.FontWeight.BOLD),
        ], spacing=5, visible=self.assignment_mode.value == "preset")

        # Container for selected exam cards (manual mode) with question pool configuration
        selected_exams_container = ft.Column([
            ft.Text("Selected Exam Templates:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("(Configure questions per exam by difficulty)", size=12, color=COLORS['text_secondary'], italic=True)
        ], spacing=5, visible=self.assignment_mode.value == "manual")

        # Store question pool configurations for each exam {exam_id: {easy, medium, hard, dropdowns}}
        self.exam_pool_configs = {}

        def on_preset_selected(e):
            """Handle preset template selection"""
            if not e.control.value:
                return

            preset_id = int(e.control.value)
            self.selected_preset_id = preset_id

            # Load preset details
            preset_details = self.db.execute_query("""
                SELECT e.title, pte.easy_count, pte.medium_count, pte.hard_count
                FROM preset_template_exams pte
                JOIN exams e ON pte.exam_id = e.id
                WHERE pte.template_id = ?
            """, (preset_id,))

            # Display preset details
            preset_info_container.controls.clear()
            preset_info_container.controls.append(
                ft.Text("Preset Template Details:", size=13, weight=ft.FontWeight.BOLD)
            )

            for detail in preset_details:
                topic_total = detail['easy_count'] + detail['medium_count'] + detail['hard_count']
                preset_info_container.controls.append(
                    ft.Container(
                        content=ft.Text(
                            f"• {detail['title']}: {detail['easy_count']}E / {detail['medium_count']}M / {detail['hard_count']}H (Total: {topic_total})",
                            size=12
                        ),
                        padding=ft.padding.only(left=10)
                    )
                )

            total = sum(d['easy_count'] + d['medium_count'] + d['hard_count'] for d in preset_details)
            preset_info_container.controls.append(
                ft.Container(
                    content=ft.Text(f"Total Questions: {total}", weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                    padding=ft.padding.only(top=5)
                )
            )

            select_dialog.update()

        preset_dropdown.on_change = on_preset_selected

        def on_exam_selected(e):
            if not e.control.value:
                return

            exam_id = int(e.control.value)

            # Check if already selected
            if exam_id in [ex['id'] for ex in self.selected_exam_templates]:
                e.control.value = None
                select_dialog.update()
                return

            # Find exam details
            exam = next((ex for ex in exam_templates if ex['id'] == exam_id), None)
            if exam:
                self.selected_exam_templates.append(exam)

                # Get available questions by difficulty
                easy_available = self.db.execute_single(
                    "SELECT COUNT(*) as count FROM questions WHERE exam_id = ? AND difficulty_level = 'easy' AND is_active = 1",
                    (exam_id,)
                )['count']
                medium_available = self.db.execute_single(
                    "SELECT COUNT(*) as count FROM questions WHERE exam_id = ? AND difficulty_level = 'medium' AND is_active = 1",
                    (exam_id,)
                )['count']
                hard_available = self.db.execute_single(
                    "SELECT COUNT(*) as count FROM questions WHERE exam_id = ? AND difficulty_level = 'hard' AND is_active = 1",
                    (exam_id,)
                )['count']

                # Create dropdown options for Easy
                easy_options = [ft.dropdown.Option(key=str(i), text=str(i)) for i in range(0, easy_available + 1)]
                medium_options = [ft.dropdown.Option(key=str(i), text=str(i)) for i in range(0, medium_available + 1)]
                hard_options = [ft.dropdown.Option(key=str(i), text=str(i)) for i in range(0, hard_available + 1)]

                # Subtotal text
                subtotal_text = ft.Text("Subtotal: 0", size=14, weight=ft.FontWeight.BOLD)

                # Create dropdowns
                easy_dropdown = ft.Dropdown(
                    label=f"Easy (max: {easy_available})",
                    options=easy_options,
                    value="0",
                    width=180,
                    content_padding=5
                )
                medium_dropdown = ft.Dropdown(
                    label=f"Medium (max: {medium_available})",
                    options=medium_options,
                    value="0",
                    width=180,
                    content_padding=5
                )
                hard_dropdown = ft.Dropdown(
                    label=f"Hard (max: {hard_available})",
                    options=hard_options,
                    value="0",
                    width=180,
                    content_padding=5
                )

                def update_subtotal(e):
                    easy_val = int(easy_dropdown.value or 0)
                    medium_val = int(medium_dropdown.value or 0)
                    hard_val = int(hard_dropdown.value or 0)
                    subtotal = easy_val + medium_val + hard_val
                    subtotal_text.value = f"Subtotal: {subtotal}"
                    select_dialog.update()

                easy_dropdown.on_change = update_subtotal
                medium_dropdown.on_change = update_subtotal
                hard_dropdown.on_change = update_subtotal

                # Store config
                self.exam_pool_configs[exam_id] = {
                    'easy': easy_dropdown,
                    'medium': medium_dropdown,
                    'hard': hard_dropdown,
                    'easy_max': easy_available,
                    'medium_max': medium_available,
                    'hard_max': hard_available
                }

                # Create card for selected exam
                exam_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(exam['title'], size=13, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            subtotal_text,
                            ft.IconButton(
                                icon=ft.icons.CLOSE,
                                icon_size=16,
                                on_click=lambda e, ex_id=exam_id: remove_exam(ex_id),
                                icon_color=COLORS['error']
                            )
                        ]),
                        ft.Row([easy_dropdown, medium_dropdown, hard_dropdown], spacing=10)
                    ], spacing=5),
                    padding=ft.padding.all(12),
                    bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                    border_radius=8,
                    border=ft.border.all(1, COLORS['secondary'])
                )
                selected_exams_container.controls.append(exam_card)

            # Clear dropdown
            e.control.value = None
            select_dialog.update()

        def remove_exam(exam_id):
            # Remove from selected list
            self.selected_exam_templates = [ex for ex in self.selected_exam_templates if ex['id'] != exam_id]

            # Remove from configs
            if exam_id in self.exam_pool_configs:
                del self.exam_pool_configs[exam_id]

            # Rebuild UI
            selected_exams_container.controls.clear()
            selected_exams_container.controls.extend([
                ft.Text("Selected Exam Templates:", size=14, weight=ft.FontWeight.BOLD),
                ft.Text("(Configure questions per exam by difficulty)", size=12, color=COLORS['text_secondary'], italic=True)
            ])

            # Re-add remaining cards by re-triggering the add logic
            for exam in self.selected_exam_templates:
                # Need to recreate the card since we cleared everything
                # This is a bit inefficient but ensures consistency
                pass  # Cards will be recreated on next selection or we keep reference

            # Actually, let's just rebuild from scratch using stored configs
            for ex_id in list(self.exam_pool_configs.keys()):
                exam = next((e for e in self.selected_exam_templates if e['id'] == ex_id), None)
                if exam:
                    config = self.exam_pool_configs[ex_id]
                    subtotal_val = int(config['easy'].value or 0) + int(config['medium'].value or 0) + int(config['hard'].value or 0)
                    subtotal_text_rebuild = ft.Text(f"Subtotal: {subtotal_val}", size=14, weight=ft.FontWeight.BOLD)

                    exam_card = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(exam['title'], size=13, weight=ft.FontWeight.BOLD),
                                ft.Container(expand=True),
                                subtotal_text_rebuild,
                                ft.IconButton(
                                    icon=ft.icons.CLOSE,
                                    icon_size=16,
                                    on_click=lambda e, eid=ex_id: remove_exam(eid),
                                    icon_color=COLORS['error']
                                )
                            ]),
                            ft.Row([config['easy'], config['medium'], config['hard']], spacing=10)
                        ], spacing=5),
                        padding=ft.padding.all(12),
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                        border_radius=8,
                        border=ft.border.all(1, COLORS['secondary'])
                    )
                    selected_exams_container.controls.append(exam_card)

            select_dialog.update()

        exam_dropdown.on_change = on_exam_selected

        def on_create_assignment(e):
            """Handle assignment creation based on selected mode"""
            mode = self.assignment_mode.value

            if mode == "preset":
                if not self.selected_preset_id:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text("Please select a preset template"),
                        bgcolor=COLORS['error']
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                    return

                # Load exam templates from preset
                preset_config = self.db.execute_query("""
                    SELECT pte.exam_id, e.title, e.description,
                           pte.easy_count, pte.medium_count, pte.hard_count
                    FROM preset_template_exams pte
                    JOIN exams e ON pte.exam_id = e.id
                    WHERE pte.template_id = ?
                """, (self.selected_preset_id,))

                # Get preset name for assignment naming
                preset = next((p for p in preset_templates if p['id'] == self.selected_preset_id), None)

                select_dialog.open = False
                self.page.update()
                # Open preset-based assignment dialog
                self.show_assignment_creation_dialog_from_preset(preset_config, preset['name'] if preset else "Preset")

            elif mode == "manual":
                if not self.selected_exam_templates:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text("Please select at least one exam template"),
                        bgcolor=COLORS['error']
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                    return

                # Validate that at least one exam has questions configured
                total_questions = 0
                for exam_id, config in self.exam_pool_configs.items():
                    easy_count = int(config['easy'].value or 0)
                    medium_count = int(config['medium'].value or 0)
                    hard_count = int(config['hard'].value or 0)
                    total_questions += easy_count + medium_count + hard_count

                if total_questions == 0:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text("Please configure at least one question for selected exams"),
                        bgcolor=COLORS['error']
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                    return

                select_dialog.open = False
                self.page.update()
                # Open manual multi-template assignment dialog with pool configs
                self.show_assignment_creation_dialog_multi(self.selected_exam_templates, self.exam_pool_configs)

        def close_dialog(e):
            select_dialog.open = False
            self.page.update()

        select_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Create New Assignment"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Assignment Method:", size=15, weight=ft.FontWeight.BOLD),
                    self.assignment_mode,
                    ft.Divider(),
                    preset_dropdown,
                    preset_info_container,
                    exam_dropdown,
                    selected_exams_container
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 200 if self.page.width > 200 else 600,
                height=self.page.height - 200 if self.page.height > 200 else 500
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    "Continue",
                    on_click=on_create_assignment,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = select_dialog
        select_dialog.open = True
        self.page.update()

    def show_assignment_creation_dialog_multi(self, exams, pool_configs=None, assignment=None):
        """Show dialog for creating assignment from multiple exam templates

        Args:
            exams: List of selected exam templates
            pool_configs: Dict of {exam_id: {easy, medium, hard dropdowns}} if using question pool
            assignment: Existing assignment if editing
        """
        from datetime import datetime, date

        is_edit = assignment is not None

        # Calculate total question count from pool configs if provided, otherwise use all questions
        if pool_configs:
            total_questions = sum(
                int(config['easy'].value or 0) + int(config['medium'].value or 0) + int(config['hard'].value or 0)
                for config in pool_configs.values()
            )
        else:
            total_questions = sum(exam['question_count'] for exam in exams)

        exam_titles = ", ".join([exam['title'] for exam in exams])

        # Assignment name
        assignment_name_field = ft.TextField(
            label="Assignment Name *",
            value=assignment['assignment_name'] if is_edit else f"Combined Exam - {datetime.now().strftime('%Y-%m-%d')}",
            content_padding=5,
            hint_text="e.g., Midterm Exam - All Subjects",
            expand=True
        )

        # Show selected exam templates (read-only in creation dialog)
        selected_exams_display = ft.Column([
            ft.Text("Selected Exam Templates:", size=14, weight=ft.FontWeight.BOLD),
            ft.Container(height=5)
        ])

        for exam in exams:
            # Build question count text based on whether pool is used
            if pool_configs and exam['id'] in pool_configs:
                config = pool_configs[exam['id']]
                easy = int(config['easy'].value or 0)
                medium = int(config['medium'].value or 0)
                hard = int(config['hard'].value or 0)
                exam_total = easy + medium + hard
                question_text = f"E:{easy} M:{medium} H:{hard} (Total: {exam_total})"
            else:
                question_text = f"{exam['question_count']} questions"

            selected_exams_display.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color=COLORS['success'], size=16),
                        ft.Text(f"{exam['title']}", size=13),
                        ft.Container(expand=True),
                        ft.Text(question_text, size=12, color=COLORS['text_secondary'])
                    ], spacing=8),
                    padding=ft.padding.symmetric(vertical=4, horizontal=8),
                    bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                    border_radius=4
                )
            )

        selected_exams_display.controls.append(
            ft.Container(
                content=ft.Text(
                    f"Total: {total_questions} questions from {len(exams)} exam(s)",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS['primary']
                ),
                padding=ft.padding.only(top=8)
            )
        )

        # Duration, Passing Score, Max Attempts
        duration_field = ft.TextField(
            label="Duration (minutes)",
            value=str(assignment['duration_minutes']) if is_edit else "60",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 90",
            width=150
        )

        passing_score_field = ft.TextField(
            label="Passing Score (%)",
            value=str(assignment['passing_score']) if is_edit else "70",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 80",
            width=150
        )

        max_attempts_field = ft.TextField(
            label="Max Attempts",
            value=str(assignment['max_attempts']) if is_edit else "1",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 3",
            width=150
        )

        # Security Settings
        randomize_questions = ft.Checkbox(
            label="Randomize Questions (within each exam/topic)",
            value=bool(assignment['randomize_questions']) if is_edit else False
        )

        show_results = ft.Checkbox(
            label="Show Results to Students",
            value=bool(assignment['show_results']) if is_edit else True
        )

        enable_fullscreen = ft.Checkbox(
            label="Enable Full Window Mode",
            value=bool(assignment['enable_fullscreen']) if is_edit else False
        )


        # Date picker - Initialize with assignment deadline if editing
        self.assignment_deadline = None

        if is_edit:
            if assignment.get('deadline'):
                try:
                    self.assignment_deadline = datetime.fromisoformat(assignment['deadline']).date()
                except:
                    pass

        self.assignment_deadline_picker = ft.DatePicker(
            first_date=date.today(),
            last_date=date(2030, 12, 31)
        )

        deadline_field = ft.TextField(
            label="Deadline (optional)",
            value=self.assignment_deadline.strftime("%Y-%m-%d") if self.assignment_deadline else "",
            read_only=True,
            content_padding=5,
            hint_text="Click to select deadline",
            width=250,
            on_click=lambda e: self.page.open(self.assignment_deadline_picker),
            suffix=ft.IconButton(
                icon=ft.icons.CALENDAR_TODAY,
                on_click=lambda e: self.page.open(self.assignment_deadline_picker)
            )
        )

        # Date picker event handler
        def deadline_changed(e):
            self.assignment_deadline = e.control.value
            deadline_field.value = self.assignment_deadline.strftime("%Y-%m-%d") if self.assignment_deadline else ""
            deadline_field.update()

        self.assignment_deadline_picker.on_change = deadline_changed

        # User selection containers (same as single-template version)
        self.selected_assignment_users = []
        self.selected_assignment_departments = []

        # Load users and departments for selection
        users = self.db.execute_query("""
            SELECT id, full_name, username
            FROM users
            WHERE role = 'examinee' AND is_active = 1
            ORDER BY full_name
        """)

        departments = self.db.execute_query("""
            SELECT DISTINCT department
            FROM users
            WHERE department IS NOT NULL AND department != '' AND role = 'examinee'
            ORDER BY department
        """)

        user_dropdown = ft.Dropdown(
            label="Select Users",
            hint_text="Choose users to assign",
            options=[ft.dropdown.Option(key=str(user['id']), text=f"{user['full_name']} ({user['username']})") for user in users],
            width=250,
            content_padding=5
        )

        department_dropdown = ft.Dropdown(
            label="Select Departments",
            hint_text="Choose departments to assign",
            options=[ft.dropdown.Option(key=dept['department'], text=dept['department']) for dept in departments],
            width=250,
            content_padding=5
        )

        selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=5)

        def on_user_selection(e):
            if not e.control.value:
                return

            user_id = int(e.control.value)
            if user_id not in self.selected_assignment_users:
                self.selected_assignment_users.append(user_id)

                # Find user name
                user_name = next((f"{u['full_name']} ({u['username']})" for u in users if u['id'] == user_id), "User")

                chip = ft.Chip(
                    label=ft.Text(user_name),
                    on_delete=lambda e, uid=user_id: remove_user(uid),
                    delete_icon_color=COLORS['error']
                )
                selected_items_container.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def on_department_selection(e):
            if not e.control.value:
                return

            dept = e.control.value
            if dept not in self.selected_assignment_departments:
                self.selected_assignment_departments.append(dept)

                chip = ft.Chip(
                    label=ft.Text(f"Department: {dept}"),
                    on_delete=lambda e, d=dept: remove_department(d),
                    delete_icon_color=COLORS['error']
                )
                selected_items_container.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_user(user_id):
            if user_id in self.selected_assignment_users:
                self.selected_assignment_users.remove(user_id)
                # Remove chip from UI
                for i, control in enumerate(selected_items_container.controls[1:], 1):
                    if isinstance(control, ft.Chip) and "Department:" not in control.label.value:
                        user_name = control.label.value
                        # Check if this is the user to remove
                        if user_id in [u['id'] for u in users if f"{u['full_name']} ({u['username']})" == user_name]:
                            selected_items_container.controls.pop(i)
                            break
                if self.page:
                    self.page.update()

        def remove_department(dept):
            if dept in self.selected_assignment_departments:
                self.selected_assignment_departments.remove(dept)
                # Remove chip from UI
                for i, control in enumerate(selected_items_container.controls[1:], 1):
                    if isinstance(control, ft.Chip) and control.label.value == f"Department: {dept}":
                        selected_items_container.controls.pop(i)
                        break
                if self.page:
                    self.page.update()

        user_dropdown.on_change = on_user_selection
        department_dropdown.on_change = on_department_selection

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_assignment(e):
            # Validate
            if not assignment_name_field.value.strip():
                error_text.value = "Assignment name is required"
                error_text.visible = True
                assignment_dialog.update()
                return

            # For create mode, validate user/department selection
            if not is_edit and not self.selected_assignment_users and not self.selected_assignment_departments:
                error_text.value = "Please select at least one user or department"
                error_text.visible = True
                assignment_dialog.update()
                return

            try:
                duration = int(duration_field.value)
                passing_score = float(passing_score_field.value)
                max_attempts = int(max_attempts_field.value)

                if duration <= 0 or passing_score <= 0 or passing_score > 100 or max_attempts <= 0:
                    error_text.value = "Invalid values for duration, passing score, or max attempts"
                    error_text.visible = True
                    assignment_dialog.update()
                    return

                # Validate and collect question pool settings if enabled
                using_pool = bool(pool_configs)
                pool_settings = []

                if using_pool:
                    # Extract pool configuration from passed pool_configs
                    for exam_id, config in pool_configs.items():
                        try:
                            easy_count = int(config['easy'].value or 0)
                            medium_count = int(config['medium'].value or 0)
                            hard_count = int(config['hard'].value or 0)

                            if easy_count > 0 or medium_count > 0 or hard_count > 0:
                                pool_settings.append({
                                    'exam_id': exam_id,
                                    'easy': easy_count,
                                    'medium': medium_count,
                                    'hard': hard_count
                                })
                        except (ValueError, AttributeError) as ve:
                            error_text.value = f"Invalid question pool configuration: {str(ve)}"
                            error_text.visible = True
                            assignment_dialog.update()
                            return

                    if not pool_settings:
                        error_text.value = "Please configure at least one exam's question pool"
                        error_text.visible = True
                        assignment_dialog.update()
                        return

                # Create assignment (use first exam as primary, others stored in junction table)
                primary_exam_id = exams[0]['id']

                query = """
                    INSERT INTO exam_assignments (
                        exam_id, assignment_name, duration_minutes, passing_score, max_attempts,
                        randomize_questions, show_results, enable_fullscreen,
                        use_question_pool, questions_to_select,
                        easy_questions_count, medium_questions_count, hard_questions_count,
                        deadline, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                # Note: For multi-template with pool, we store config per template in junction table
                params = (
                    primary_exam_id,
                    assignment_name_field.value.strip(),
                    duration,
                    passing_score,
                    max_attempts,
                    1 if randomize_questions.value else 0,
                    1 if show_results.value else 0,
                    1 if enable_fullscreen.value else 0,
                    1 if using_pool else 0,
                    0, 0, 0, 0,  # Legacy question counts (not used for multi-template)
                    self.assignment_deadline.isoformat() if self.assignment_deadline else None,
                    datetime.now().isoformat(),
                    self.user_data['id']
                )
                assignment_id = self.db.execute_insert(query, params)

                # Store ALL selected exam templates in junction table with pool config
                for order_idx, exam in enumerate(exams):
                    # Find pool config for this exam if exists
                    exam_pool = next((p for p in pool_settings if p['exam_id'] == exam['id']), None)

                    if using_pool and exam_pool:
                        # Store with pool configuration
                        self.db.execute_insert("""
                            INSERT INTO assignment_exam_templates (
                                assignment_id, exam_id, order_index,
                                easy_count, medium_count, hard_count
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (assignment_id, exam['id'], order_idx,
                              exam_pool['easy'], exam_pool['medium'], exam_pool['hard']))
                    else:
                        # Store without pool configuration (use all questions)
                        self.db.execute_insert("""
                            INSERT INTO assignment_exam_templates (assignment_id, exam_id, order_index)
                            VALUES (?, ?, ?)
                        """, (assignment_id, exam['id'], order_idx))

                # Assign users (only for create mode)
                for user_id in self.selected_assignment_users:
                    self.db.execute_insert("""
                        INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                        VALUES (?, ?, ?)
                    """, (assignment_id, user_id, self.user_data['id']))

                # Assign departments (only for create mode)
                for dept in self.selected_assignment_departments:
                    dept_users = self.db.execute_query("""
                        SELECT id FROM users
                        WHERE department = ? AND role = 'examinee' AND is_active = 1
                    """, (dept,))

                    for user in dept_users:
                        # Check if already assigned
                        existing = self.db.execute_single("""
                            SELECT id FROM assignment_users
                            WHERE assignment_id = ? AND user_id = ?
                        """, (assignment_id, user['id']))

                        if not existing:
                            self.db.execute_insert("""
                                INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                                VALUES (?, ?, ?)
                            """, (assignment_id, user['id'], self.user_data['id']))

                # Close dialog
                assignment_dialog.open = False
                if self.page:
                    self.page.update()

                # Reload exams and update UI
                self.load_exams()
                if self.page:
                    self.update()

                # Show success message
                success_message = f"Multi-template assignment '{assignment_name_field.value.strip()}' created successfully with {len(exams)} exam templates!"
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(success_message),
                    bgcolor=COLORS['success']
                )
                self.page.snack_bar.open = True
                self.page.update()

            except Exception as ex:
                error_text.value = f"Error creating assignment: {str(ex)}"
                error_text.visible = True
                assignment_dialog.update()
                import traceback
                traceback.print_exc()

        def close_dialog(e):
            assignment_dialog.open = False
            self.page.update()

        # Add date picker to page overlay
        if self.page:
            self.page.overlay.append(self.assignment_deadline_picker)

        # Build dialog content
        dialog_content_controls = [
            assignment_name_field,
            ft.Container(height=10),

            # Selected exams display
            selected_exams_display,
            ft.Container(height=10),

            # Question Pool Selection
            use_question_pool,
            question_pool_config,
            ft.Container(height=10),

            ft.Row([duration_field, passing_score_field, max_attempts_field, deadline_field], spacing=8),
            ft.Container(height=8),

            # Security Settings
            ft.Text("Security Settings", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([randomize_questions, show_results], spacing=15, wrap=True),
            ft.Row([enable_fullscreen], spacing=15, wrap=True),
            ft.Container(height=8),

            # User Selection
            ft.Text("Assign to Users", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([user_dropdown, department_dropdown], spacing=20),
            selected_items_container,
            ft.Container(height=10),
        ]

        dialog_content_controls.append(error_text)

        dialog_title = f"Create Multi-Template Assignment ({len(exams)} exams)"
        button_text = "Create Assignment"

        assignment_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(dialog_title),
            content=ft.Container(
                content=ft.Column(dialog_content_controls, spacing=8, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 200 if self.page.width > 200 else 900,
                height=self.page.height - 150 if self.page.height > 150 else 650
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    button_text,
                    on_click=save_assignment,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = assignment_dialog
        assignment_dialog.open = True
        self.page.update()

    def show_assignment_creation_dialog_from_preset(self, preset_config, preset_name):
        """Show assignment dialog using preset template configuration"""
        from datetime import datetime, date

        # Calculate total questions from preset
        total_questions = sum(c['easy_count'] + c['medium_count'] + c['hard_count'] for c in preset_config)

        # Assignment name (auto-filled with preset name)
        assignment_name_field = ft.TextField(
            label="Assignment Name *",
            value=f"{preset_name} - {datetime.now().strftime('%Y-%m-%d')}",
            content_padding=5,
            hint_text="e.g., SOC Interview - John Doe",
            expand=True
        )

        # Show preset configuration (read-only)
        preset_display = ft.Column([
            ft.Text("Preset Configuration:", size=14, weight=ft.FontWeight.BOLD),
            ft.Text(f"Using preset: {preset_name}", size=12, italic=True, color=COLORS['text_secondary'])
        ])

        for config in preset_config:
            topic_total = config['easy_count'] + config['medium_count'] + config['hard_count']
            preset_display.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.CHECK_CIRCLE, color=COLORS['success'], size=16),
                        ft.Text(f"{config['title']}", size=13),
                        ft.Container(expand=True),
                        ft.Text(
                            f"{config['easy_count']}E / {config['medium_count']}M / {config['hard_count']}H = {topic_total}Q",
                            size=12,
                            color=COLORS['text_secondary']
                        )
                    ], spacing=8),
                    padding=ft.padding.symmetric(vertical=4, horizontal=8),
                    bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                    border_radius=4
                )
            )

        preset_display.controls.append(
            ft.Container(
                content=ft.Text(
                    f"Total: {total_questions} questions",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS['primary']
                ),
                padding=ft.padding.only(top=8)
            )
        )

        # Duration, Passing Score, Max Attempts
        duration_field = ft.TextField(
            label="Duration (minutes)",
            value="60",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 90",
            width=150
        )

        passing_score_field = ft.TextField(
            label="Passing Score (%)",
            value="70",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 80",
            width=150
        )

        max_attempts_field = ft.TextField(
            label="Max Attempts",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 3",
            width=150
        )

        # Security Settings
        randomize_questions = ft.Checkbox(
            label="Randomize Questions",
            value=True
        )

        show_results = ft.Checkbox(
            label="Show Results to Students",
            value=True
        )

        enable_fullscreen = ft.Checkbox(
            label="Enable Full Window Mode",
            value=False
        )


        # Date picker
        self.assignment_deadline = None
        self.assignment_deadline_picker = ft.DatePicker(
            first_date=date.today(),
            last_date=date(2030, 12, 31)
        )

        deadline_field = ft.TextField(
            label="Deadline (optional)",
            value="",
            read_only=True,
            content_padding=5,
            hint_text="Click to select deadline",
            width=250,
            on_click=lambda e: self.page.open(self.assignment_deadline_picker),
            suffix=ft.IconButton(
                icon=ft.icons.CALENDAR_TODAY,
                on_click=lambda e: self.page.open(self.assignment_deadline_picker)
            )
        )

        def deadline_changed(e):
            self.assignment_deadline = e.control.value
            deadline_field.value = self.assignment_deadline.strftime("%Y-%m-%d") if self.assignment_deadline else ""
            deadline_field.update()

        self.assignment_deadline_picker.on_change = deadline_changed

        # User selection
        self.selected_assignment_users = []
        self.selected_assignment_departments = []

        users = self.db.execute_query("""
            SELECT id, full_name, username
            FROM users
            WHERE role = 'examinee' AND is_active = 1
            ORDER BY full_name
        """)

        departments = self.db.execute_query("""
            SELECT DISTINCT department
            FROM users
            WHERE department IS NOT NULL AND department != '' AND role = 'examinee'
            ORDER BY department
        """)

        user_dropdown = ft.Dropdown(
            label="Select Users",
            hint_text="Choose users to assign",
            options=[ft.dropdown.Option(key=str(user['id']), text=f"{user['full_name']} ({user['username']})") for user in users],
            width=250,
            content_padding=5
        )

        department_dropdown = ft.Dropdown(
            label="Select Departments",
            hint_text="Choose departments to assign",
            options=[ft.dropdown.Option(key=dept['department'], text=dept['department']) for dept in departments],
            width=250,
            content_padding=5
        )

        selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=5)

        def on_user_selection(e):
            if not e.control.value:
                return

            user_id = int(e.control.value)
            if user_id not in self.selected_assignment_users:
                self.selected_assignment_users.append(user_id)

                user_name = next((f"{u['full_name']} ({u['username']})" for u in users if u['id'] == user_id), "User")

                chip = ft.Chip(
                    label=ft.Text(user_name),
                    on_delete=lambda e, uid=user_id: remove_user(uid),
                    delete_icon_color=COLORS['error']
                )
                selected_items_container.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def on_department_selection(e):
            if not e.control.value:
                return

            dept = e.control.value
            if dept not in self.selected_assignment_departments:
                self.selected_assignment_departments.append(dept)

                chip = ft.Chip(
                    label=ft.Text(f"Department: {dept}"),
                    on_delete=lambda e, d=dept: remove_department(d),
                    delete_icon_color=COLORS['error']
                )
                selected_items_container.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_user(user_id):
            if user_id in self.selected_assignment_users:
                self.selected_assignment_users.remove(user_id)
                for i, control in enumerate(selected_items_container.controls[1:], 1):
                    if isinstance(control, ft.Chip) and "Department:" not in control.label.value:
                        user_name = control.label.value
                        if user_id in [u['id'] for u in users if f"{u['full_name']} ({u['username']})" == user_name]:
                            selected_items_container.controls.pop(i)
                            break
                if self.page:
                    self.page.update()

        def remove_department(dept):
            if dept in self.selected_assignment_departments:
                self.selected_assignment_departments.remove(dept)
                for i, control in enumerate(selected_items_container.controls[1:], 1):
                    if isinstance(control, ft.Chip) and control.label.value == f"Department: {dept}":
                        selected_items_container.controls.pop(i)
                        break
                if self.page:
                    self.page.update()

        user_dropdown.on_change = on_user_selection
        department_dropdown.on_change = on_department_selection

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_assignment(e):
            # Validate
            if not assignment_name_field.value.strip():
                error_text.value = "Assignment name is required"
                error_text.visible = True
                assignment_dialog.update()
                return

            if not self.selected_assignment_users and not self.selected_assignment_departments:
                error_text.value = "Please select at least one user or department"
                error_text.visible = True
                assignment_dialog.update()
                return

            try:
                duration = int(duration_field.value)
                passing_score = float(passing_score_field.value)
                max_attempts = int(max_attempts_field.value)

                if duration <= 0 or passing_score <= 0 or passing_score > 100 or max_attempts <= 0:
                    error_text.value = "Invalid values for duration, passing score, or max attempts"
                    error_text.visible = True
                    assignment_dialog.update()
                    return

                # Use first exam as primary reference (for system compatibility)
                primary_exam_id = preset_config[0]['exam_id']

                # Create assignment with preset flag
                query = """
                    INSERT INTO exam_assignments (
                        exam_id, assignment_name, duration_minutes, passing_score, max_attempts,
                        randomize_questions, show_results, enable_fullscreen,
                        use_question_pool, questions_to_select,
                        easy_questions_count, medium_questions_count, hard_questions_count,
                        deadline, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    primary_exam_id,
                    assignment_name_field.value.strip(),
                    duration,
                    passing_score,
                    max_attempts,
                    1 if randomize_questions.value else 0,
                    1 if show_results.value else 0,
                    1 if enable_fullscreen.value else 0,
                    1,  # Use question pool mode for preset-based assignments
                    total_questions,  # Total questions
                    sum(c['easy_count'] for c in preset_config),
                    sum(c['medium_count'] for c in preset_config),
                    sum(c['hard_count'] for c in preset_config),
                    self.assignment_deadline.isoformat() if self.assignment_deadline else None,
                    datetime.now().isoformat(),
                    self.user_data['id']
                )
                assignment_id = self.db.execute_insert(query, params)

                # Store all exam templates from preset in junction table
                for order_idx, config in enumerate(preset_config):
                    self.db.execute_insert("""
                        INSERT INTO assignment_exam_templates (assignment_id, exam_id, order_index)
                        VALUES (?, ?, ?)
                    """, (assignment_id, config['exam_id'], order_idx))

                # Assign users
                for user_id in self.selected_assignment_users:
                    self.db.execute_insert("""
                        INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                        VALUES (?, ?, ?)
                    """, (assignment_id, user_id, self.user_data['id']))

                # Assign departments
                for dept in self.selected_assignment_departments:
                    dept_users = self.db.execute_query("""
                        SELECT id FROM users
                        WHERE department = ? AND role = 'examinee' AND is_active = 1
                    """, (dept,))

                    for user in dept_users:
                        existing = self.db.execute_single("""
                            SELECT id FROM assignment_users
                            WHERE assignment_id = ? AND user_id = ?
                        """, (assignment_id, user['id']))

                        if not existing:
                            self.db.execute_insert("""
                                INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                                VALUES (?, ?, ?)
                            """, (assignment_id, user['id'], self.user_data['id']))

                # Close dialog
                assignment_dialog.open = False
                if self.page:
                    self.page.update()

                # Reload exams and update UI
                self.load_exams()
                if self.page:
                    self.update()

                # Show success message
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Preset-based assignment '{assignment_name_field.value.strip()}' created successfully!"),
                    bgcolor=COLORS['success']
                )
                self.page.snack_bar.open = True
                self.page.update()

            except Exception as ex:
                error_text.value = f"Error creating assignment: {str(ex)}"
                error_text.visible = True
                assignment_dialog.update()
                import traceback
                traceback.print_exc()

        def close_dialog(e):
            assignment_dialog.open = False
            self.page.update()

        # Add date picker to page overlay
        if self.page:
            self.page.overlay.append(self.assignment_deadline_picker)

        # Build dialog content
        dialog_content_controls = [
            assignment_name_field,
            ft.Container(height=10),

            # Preset display
            preset_display,
            ft.Container(height=10),

            ft.Row([duration_field, passing_score_field, max_attempts_field, deadline_field], spacing=8),
            ft.Container(height=8),

            # Security Settings
            ft.Text("Security Settings", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([randomize_questions, show_results], spacing=15, wrap=True),
            ft.Row([enable_fullscreen], spacing=15, wrap=True),
            ft.Container(height=8),

            # User Selection
            ft.Text("Assign to Users", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([user_dropdown, department_dropdown], spacing=20),
            selected_items_container,
            ft.Container(height=10),
        ]

        dialog_content_controls.append(error_text)

        assignment_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Create Assignment from Preset: {preset_name}"),
            content=ft.Container(
                content=ft.Column(dialog_content_controls, spacing=8, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 200 if self.page.width > 200 else 900,
                height=self.page.height - 150 if self.page.height > 150 else 650
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    "Create Assignment",
                    on_click=save_assignment,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = assignment_dialog
        assignment_dialog.open = True
        self.page.update()

    def show_assignment_creation_dialog(self, exam, assignment=None):
        """Show dialog for creating/editing an assignment from an exam template"""
        from datetime import datetime, date

        is_edit = assignment is not None

        # Assignment name
        assignment_name_field = ft.TextField(
            label="Assignment Name *",
            value=assignment['assignment_name'] if is_edit else f"{exam['title']} - Assignment",
            content_padding=5,
            hint_text="e.g., Midterm Exam - Section A",
            expand=True
        )

        # Duration, Passing Score, Max Attempts
        duration_field = ft.TextField(
            label="Duration (minutes)",
            value=str(assignment['duration_minutes']) if is_edit else "60",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 90",
            width=150
        )

        passing_score_field = ft.TextField(
            label="Passing Score (%)",
            value=str(assignment['passing_score']) if is_edit else "70",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 80",
            width=150
        )

        max_attempts_field = ft.TextField(
            label="Max Attempts",
            value=str(assignment['max_attempts']) if is_edit else "1",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 3",
            width=150
        )

        # Security Settings
        randomize_questions = ft.Checkbox(
            label="Randomize Questions",
            value=bool(assignment['randomize_questions']) if is_edit else False
        )

        show_results = ft.Checkbox(
            label="Show Results to Students",
            value=bool(assignment['show_results']) if is_edit else True
        )

        enable_fullscreen = ft.Checkbox(
            label="Enable Full Window Mode",
            value=bool(assignment['enable_fullscreen']) if is_edit else False
        )


        # Get question counts for this exam
        question_count = self.db.execute_single(
            "SELECT COUNT(*) as count FROM questions WHERE exam_id = ? AND is_active = 1",
            (exam['id'],)
        )
        has_questions = question_count and question_count['count'] > 0
        total_q = question_count['count'] if has_questions else 0

        easy_q = 0
        medium_q = 0
        hard_q = 0

        if has_questions:
            difficulty_counts = self.db.execute_query("""
                SELECT difficulty_level, COUNT(*) as count
                FROM questions
                WHERE exam_id = ? AND is_active = 1
                GROUP BY difficulty_level
            """, (exam['id'],))

            for row in difficulty_counts:
                if row['difficulty_level'] == 'easy':
                    easy_q = row['count']
                elif row['difficulty_level'] == 'medium':
                    medium_q = row['count']
                elif row['difficulty_level'] == 'hard':
                    hard_q = row['count']

        # Random Question Selection Settings
        use_pool_value = bool(assignment['use_question_pool']) if is_edit else False
        use_question_pool = ft.Checkbox(
            label="Enable Random Question Selection - Each student gets different questions",
            value=use_pool_value,
            disabled=not has_questions
        )

        # Info text to explain the feature
        pool_info_text = ft.Container(
            content=ft.Text(
                "💡 When enabled, each student will receive a randomly selected subset of questions from the exam. "
                "This prevents cheating by ensuring no two students get exactly the same questions.",
                size=12,
                color=COLORS['text_secondary'],
                italic=True
            ),
            padding=ft.padding.only(left=10, top=5, bottom=10),
            visible=has_questions
        )

        easy_options = [ft.dropdown.Option(str(i), str(i)) for i in range(0, easy_q + 1)]
        medium_options = [ft.dropdown.Option(str(i), str(i)) for i in range(0, medium_q + 1)]
        hard_options = [ft.dropdown.Option(str(i), str(i)) for i in range(0, hard_q + 1)]

        easy_questions_count_field = ft.Dropdown(
            label=f"Easy (Available: {easy_q})",
            options=easy_options,
            value=str(assignment['easy_questions_count']) if is_edit and assignment['easy_questions_count'] else "0",
            width=150,
            content_padding=5,
            disabled=not use_pool_value
        )

        medium_questions_count_field = ft.Dropdown(
            label=f"Medium (Available: {medium_q})",
            options=medium_options,
            value=str(assignment['medium_questions_count']) if is_edit and assignment['medium_questions_count'] else "0",
            width=150,
            content_padding=5,
            disabled=not use_pool_value
        )

        hard_questions_count_field = ft.Dropdown(
            label=f"Hard (Available: {hard_q})",
            options=hard_options,
            value=str(assignment['hard_questions_count']) if is_edit and assignment['hard_questions_count'] else "0",
            width=150,
            content_padding=5,
            disabled=not use_pool_value
        )

        # Total questions counter (auto-calculated)
        total_questions_text = ft.Text(
            f"Total questions: 0",
            size=14,
            weight=ft.FontWeight.BOLD,
            color=COLORS['primary']
        )

        def update_total_questions(e=None):
            """Auto-calculate total from difficulty counts"""
            try:
                easy = int(easy_questions_count_field.value) if easy_questions_count_field.value else 0
                medium = int(medium_questions_count_field.value) if medium_questions_count_field.value else 0
                hard = int(hard_questions_count_field.value) if hard_questions_count_field.value else 0
                total = easy + medium + hard
                total_questions_text.value = f"Total questions: {total}"
                if self.page:
                    total_questions_text.update()
            except:
                pass

        easy_questions_count_field.on_change = update_total_questions
        medium_questions_count_field.on_change = update_total_questions
        hard_questions_count_field.on_change = update_total_questions

        # Initialize total
        update_total_questions()

        def toggle_question_pool_fields(e):
            enabled = e.control.value
            easy_questions_count_field.disabled = not enabled
            medium_questions_count_field.disabled = not enabled
            hard_questions_count_field.disabled = not enabled
            total_questions_text.visible = enabled
            if self.page:
                self.page.update()

        use_question_pool.on_change = toggle_question_pool_fields

        # Date picker - Initialize with assignment deadline if editing
        self.assignment_deadline = None

        if is_edit:
            if assignment.get('deadline'):
                try:
                    self.assignment_deadline = datetime.fromisoformat(assignment['deadline']).date()
                except:
                    pass

        self.assignment_deadline_picker = ft.DatePicker(
            first_date=date.today(),
            last_date=date(2030, 12, 31)
        )

        deadline_field = ft.TextField(
            label="Deadline (optional)",
            value=self.assignment_deadline.strftime("%Y-%m-%d") if self.assignment_deadline else "",
            read_only=True,
            content_padding=5,
            hint_text="Click to select deadline",
            width=250,
            on_click=lambda e: self.page.open(self.assignment_deadline_picker),
            suffix=ft.IconButton(
                icon=ft.icons.CALENDAR_TODAY,
                on_click=lambda e: self.page.open(self.assignment_deadline_picker)
            )
        )

        # Date picker event handler
        def deadline_changed(e):
            self.assignment_deadline = e.control.value
            deadline_field.value = self.assignment_deadline.strftime("%Y-%m-%d") if self.assignment_deadline else ""
            deadline_field.update()

        self.assignment_deadline_picker.on_change = deadline_changed

        # User selection containers
        self.selected_assignment_users = []
        self.selected_assignment_departments = []

        # Load users and departments for selection
        users = self.db.execute_query("""
            SELECT id, full_name, username
            FROM users
            WHERE role = 'examinee' AND is_active = 1
            ORDER BY full_name
        """)

        departments = self.db.execute_query("""
            SELECT DISTINCT department
            FROM users
            WHERE department IS NOT NULL AND department != '' AND role = 'examinee'
            ORDER BY department
        """)

        user_dropdown = ft.Dropdown(
            label="Select Users",
            hint_text="Choose users to assign",
            options=[ft.dropdown.Option(key=str(user['id']), text=f"{user['full_name']} ({user['username']})") for user in users],
            width=250,
            content_padding=5
        )

        department_dropdown = ft.Dropdown(
            label="Select Departments",
            hint_text="Choose departments to assign",
            options=[ft.dropdown.Option(key=dept['department'], text=dept['department']) for dept in departments],
            width=250,
            content_padding=5
        )

        selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=5)

        def on_user_selection(e):
            if not e.control.value:
                return

            user_id = int(e.control.value)
            if user_id not in self.selected_assignment_users:
                self.selected_assignment_users.append(user_id)

                # Find user name
                user_name = next((f"{u['full_name']} ({u['username']})" for u in users if u['id'] == user_id), "User")

                chip = ft.Chip(
                    label=ft.Text(user_name),
                    on_delete=lambda e, uid=user_id: remove_user(uid),
                    delete_icon_color=COLORS['error']
                )
                selected_items_container.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def on_department_selection(e):
            if not e.control.value:
                return

            dept = e.control.value
            if dept not in self.selected_assignment_departments:
                self.selected_assignment_departments.append(dept)

                chip = ft.Chip(
                    label=ft.Text(f"Department: {dept}"),
                    on_delete=lambda e, d=dept: remove_department(d),
                    delete_icon_color=COLORS['error']
                )
                selected_items_container.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_user(user_id):
            if user_id in self.selected_assignment_users:
                self.selected_assignment_users.remove(user_id)
                # Remove chip from UI
                for i, control in enumerate(selected_items_container.controls[1:], 1):
                    if isinstance(control, ft.Chip) and "Department:" not in control.label.value:
                        user_name = control.label.value
                        # Check if this is the user to remove
                        if user_id in [u['id'] for u in users if f"{u['full_name']} ({u['username']})" == user_name]:
                            selected_items_container.controls.pop(i)
                            break
                if self.page:
                    self.page.update()

        def remove_department(dept):
            if dept in self.selected_assignment_departments:
                self.selected_assignment_departments.remove(dept)
                # Remove chip from UI
                for i, control in enumerate(selected_items_container.controls[1:], 1):
                    if isinstance(control, ft.Chip) and control.label.value == f"Department: {dept}":
                        selected_items_container.controls.pop(i)
                        break
                if self.page:
                    self.page.update()

        user_dropdown.on_change = on_user_selection
        department_dropdown.on_change = on_department_selection

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_assignment(e):
            # Validate
            if not assignment_name_field.value.strip():
                error_text.value = "Assignment name is required"
                error_text.visible = True
                assignment_dialog.update()
                return

            # For create mode, validate user/department selection
            if not is_edit and not self.selected_assignment_users and not self.selected_assignment_departments:
                error_text.value = "Please select at least one user or department"
                error_text.visible = True
                assignment_dialog.update()
                return

            try:
                duration = int(duration_field.value)
                passing_score = float(passing_score_field.value)
                max_attempts = int(max_attempts_field.value)

                if duration <= 0 or passing_score <= 0 or passing_score > 100 or max_attempts <= 0:
                    error_text.value = "Invalid values for duration, passing score, or max attempts"
                    error_text.visible = True
                    assignment_dialog.update()
                    return

                use_pool = use_question_pool.value
                easy_count = int(easy_questions_count_field.value) if easy_questions_count_field.value else 0
                medium_count = int(medium_questions_count_field.value) if medium_questions_count_field.value else 0
                hard_count = int(hard_questions_count_field.value) if hard_questions_count_field.value else 0

                # Auto-calculate total questions from difficulty counts
                to_select = easy_count + medium_count + hard_count

                if is_edit:
                    # Update existing assignment
                    query = """
                        UPDATE exam_assignments SET
                            assignment_name = ?,
                            duration_minutes = ?,
                            passing_score = ?,
                            max_attempts = ?,
                            randomize_questions = ?,
                            show_results = ?,
                            enable_fullscreen = ?,
                            use_question_pool = ?,
                            questions_to_select = ?,
                            easy_questions_count = ?,
                            medium_questions_count = ?,
                            hard_questions_count = ?,
                            deadline = ?
                        WHERE id = ?
                    """
                    params = (
                        assignment_name_field.value.strip(),
                        duration,
                        passing_score,
                        max_attempts,
                        1 if randomize_questions.value else 0,
                        1 if show_results.value else 0,
                        1 if enable_fullscreen.value else 0,
                        1 if use_pool else 0,
                        to_select,
                        easy_count,
                        medium_count,
                        hard_count,
                        self.assignment_deadline.isoformat() if self.assignment_deadline else None,
                        assignment['id']
                    )
                    self.db.execute_update(query, params)
                    assignment_id = assignment['id']

                    # Update assignment_users in edit mode
                    # First, remove all current assignments
                    self.db.execute_update("""
                        DELETE FROM assignment_users WHERE assignment_id = ?
                    """, (assignment_id,))

                    # Then add the new selections
                    for user_id in self.selected_assignment_users:
                        self.db.execute_insert("""
                            INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                            VALUES (?, ?, ?)
                        """, (assignment_id, user_id, self.user_data['id']))

                    # Also add users from selected departments
                    for dept in self.selected_assignment_departments:
                        dept_users = self.db.execute_query("""
                            SELECT id FROM users
                            WHERE department = ? AND role = 'examinee' AND is_active = 1
                        """, (dept,))

                        for user in dept_users:
                            # Check if already assigned (to avoid duplicates)
                            existing = self.db.execute_single("""
                                SELECT id FROM assignment_users
                                WHERE assignment_id = ? AND user_id = ?
                            """, (assignment_id, user['id']))

                            if not existing:
                                self.db.execute_insert("""
                                    INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                                    VALUES (?, ?, ?)
                                """, (assignment_id, user['id'], self.user_data['id']))
                else:
                    # Create new assignment
                    query = """
                        INSERT INTO exam_assignments (
                            exam_id, assignment_name, duration_minutes, passing_score, max_attempts,
                            randomize_questions, show_results, enable_fullscreen,
                            use_question_pool, questions_to_select,
                            easy_questions_count, medium_questions_count, hard_questions_count,
                            deadline, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        exam['id'],
                        assignment_name_field.value.strip(),
                        duration,
                        passing_score,
                        max_attempts,
                        1 if randomize_questions.value else 0,
                        1 if show_results.value else 0,
                        1 if enable_fullscreen.value else 0,
                        1 if use_pool else 0,
                        to_select,
                        easy_count,
                        medium_count,
                        hard_count,
                        self.assignment_deadline.isoformat() if self.assignment_deadline else None,
                        datetime.now().isoformat(),
                        self.user_data['id']
                    )
                    assignment_id = self.db.execute_insert(query, params)

                    # Assign users (only for create mode)
                    for user_id in self.selected_assignment_users:
                        self.db.execute_insert("""
                            INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                            VALUES (?, ?, ?)
                        """, (assignment_id, user_id, self.user_data['id']))

                    # Assign departments (only for create mode)
                    for dept in self.selected_assignment_departments:
                        dept_users = self.db.execute_query("""
                            SELECT id FROM users
                            WHERE department = ? AND role = 'examinee' AND is_active = 1
                        """, (dept,))

                        for user in dept_users:
                            # Check if already assigned
                            existing = self.db.execute_single("""
                                SELECT id FROM assignment_users
                                WHERE assignment_id = ? AND user_id = ?
                            """, (assignment_id, user['id']))

                            if not existing:
                                self.db.execute_insert("""
                                    INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                                    VALUES (?, ?, ?)
                                """, (assignment_id, user['id'], self.user_data['id']))

                # Close dialog
                assignment_dialog.open = False
                if self.page:
                    self.page.update()

                # Reload exams and update UI
                self.load_exams()
                if self.page:
                    self.update()

                # Show success message
                success_message = f"Assignment '{assignment_name_field.value.strip()}' {'updated' if is_edit else 'created'} successfully!"
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(success_message),
                    bgcolor=COLORS['success']
                )
                self.page.snack_bar.open = True
                self.page.update()

            except Exception as ex:
                error_text.value = f"Error {'updating' if is_edit else 'creating'} assignment: {str(ex)}"
                error_text.visible = True
                assignment_dialog.update()

        def close_dialog(e):
            assignment_dialog.open = False
            self.page.update()

        # Add date picker to page overlay
        if self.page:
            self.page.overlay.append(self.assignment_deadline_picker)

        # Build dialog content based on mode (hide user selection in edit mode)
        dialog_content_controls = [
            assignment_name_field,
            ft.Row([duration_field, passing_score_field, max_attempts_field, deadline_field], spacing=8),
            ft.Container(height=8),

            # Security Settings
            ft.Text("Security Settings", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([randomize_questions, show_results], spacing=15, wrap=True),
            ft.Row([enable_fullscreen], spacing=15, wrap=True),
            ft.Container(height=8),

            # Random Question Selection
            ft.Text("Random Question Selection", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            use_question_pool,
            pool_info_text,
            ft.Text("Select questions by difficulty:", size=13, weight=ft.FontWeight.W_500),
            ft.Row([easy_questions_count_field, medium_questions_count_field, hard_questions_count_field, total_questions_text], spacing=10, alignment=ft.MainAxisAlignment.START),
            ft.Container(height=8),
        ]

        # Always show user selection section (in both create and edit modes)
        # In edit mode, load currently assigned users
        if is_edit:
            # Load currently assigned users for this assignment
            assigned_users_data = self.db.execute_query("""
                SELECT u.id, u.full_name, u.username
                FROM assignment_users au
                JOIN users u ON au.user_id = u.id
                WHERE au.assignment_id = ? AND au.is_active = 1
                ORDER BY u.full_name
            """, (assignment['id'],))

            # Populate selected_items_container with current users
            selected_items_container.controls.clear()
            selected_items_container.controls.append(
                ft.Text("Assigned Users:", size=14, weight=ft.FontWeight.BOLD)
            )
            for user in assigned_users_data:
                self.selected_assignment_users.append(user['id'])
                chip = ft.Chip(
                    label=ft.Text(f"{user['full_name']} ({user['username']})"),
                    on_delete=lambda e, uid=user['id']: remove_user(uid),
                    delete_icon_color=COLORS['error']
                )
                selected_items_container.controls.append(chip)

        dialog_content_controls.extend([
            # User Selection
            ft.Text("Manage Assigned Users", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([user_dropdown, department_dropdown], spacing=20),
            selected_items_container,
            ft.Container(height=10),
        ])

        dialog_content_controls.append(error_text)

        dialog_title = f"{'Edit' if is_edit else 'Create'} Assignment - {exam['title']}"
        button_text = "Save Changes" if is_edit else "Create Assignment"

        assignment_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(dialog_title),
            content=ft.Container(
                content=ft.Column(dialog_content_controls, spacing=8, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 200 if self.page.width > 200 else 1000,
                height=self.page.height - 150 if self.page.height > 150 else 650
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    button_text,
                    on_click=save_assignment,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = assignment_dialog
        assignment_dialog.open = True
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
                    ft.Container(height=10),
                    self.selected_items_container,
                    ft.Container(height=20),
                    self.current_assignments_container,
                    ft.Container(height=10),
                    error_text
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 300 if self.page.width > 300 else 600,
                height=self.page.height - 200 if self.page.height > 200 else 500
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
                        WHERE user_id = ? AND exam_id = ? AND is_active = 1
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
                WHERE user_id = ? AND exam_id = ? AND is_active = 1
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
                        WHERE user_id = ? AND exam_id = ? AND is_active = 1
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
                            WHERE user_id = ? AND exam_id = ? AND is_active = 1
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
    def show_edit_assignment_dialog(self, assignment):
        """Edit an existing assignment - reuses creation dialog with pre-filled values"""
        # Get the exam template info for this assignment
        exam = self.db.execute_single("""
            SELECT id, title, description
            FROM exams
            WHERE id = ?
        """, (assignment['exam_id'],))

        if not exam:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Exam template not found!"),
                bgcolor=COLORS['error']
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Call the creation dialog but in edit mode
        self.show_assignment_creation_dialog(exam, assignment)
    
    def show_assignment_user_dialog(self, assignment):
        """Manage users for an assignment"""
        # Load users and departments for selection
        users = self.db.execute_query("""
            SELECT id, full_name, username
            FROM users
            WHERE role = 'examinee' AND is_active = 1
            ORDER BY full_name
        """)

        departments = self.db.execute_query("""
            SELECT DISTINCT department
            FROM users
            WHERE department IS NOT NULL AND department != '' AND role = 'examinee'
            ORDER BY department
        """)

        # Get currently assigned users
        assigned_users = self.db.execute_query("""
            SELECT u.id, u.full_name, u.username
            FROM assignment_users au
            JOIN users u ON au.user_id = u.id
            WHERE au.assignment_id = ? AND au.is_active = 1
            ORDER BY u.full_name
        """, (assignment['id'],))

        assigned_user_ids = {user['id'] for user in assigned_users}

        # Dropdown for adding users
        user_dropdown = ft.Dropdown(
            label="Add Users",
            hint_text="Select users to add",
            options=[
                ft.dropdown.Option(
                    key=str(user['id']),
                    text=f"{user['full_name']} ({user['username']})",
                    disabled=user['id'] in assigned_user_ids
                )
                for user in users
            ],
            width=400
        )

        department_dropdown = ft.Dropdown(
            label="Add Department",
            hint_text="Select department to add",
            options=[ft.dropdown.Option(key=dept['department'], text=dept['department']) for dept in departments],
            width=400
        )

        # Container for currently assigned users
        current_users_container = ft.Column([
            ft.Text("Currently Assigned Users:", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=5)

        def populate_current_users():
            current_users_container.controls.clear()
            current_users_container.controls.append(
                ft.Text("Currently Assigned Users:", size=14, weight=ft.FontWeight.BOLD)
            )

            current_assigned = self.db.execute_query("""
                SELECT u.id, u.full_name, u.username
                FROM assignment_users au
                JOIN users u ON au.user_id = u.id
                WHERE au.assignment_id = ? AND au.is_active = 1
                ORDER BY u.full_name
            """, (assignment['id'],))

            if not current_assigned:
                current_users_container.controls.append(
                    ft.Text("No users assigned", italic=True, color=COLORS['text_secondary'])
                )
            else:
                for user in current_assigned:
                    chip = ft.Chip(
                        label=ft.Text(f"{user['full_name']} ({user['username']})"),
                        on_delete=lambda e, uid=user['id']: remove_user(uid),
                        delete_icon_color=COLORS['error']
                    )
                    current_users_container.controls.append(chip)

        populate_current_users()

        def add_user(e):
            if not user_dropdown.value:
                return

            user_id = int(user_dropdown.value)

            # Check if already assigned
            existing = self.db.execute_single("""
                SELECT id FROM assignment_users
                WHERE assignment_id = ? AND user_id = ?
            """, (assignment['id'], user_id))

            if not existing:
                self.db.execute_insert("""
                    INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                    VALUES (?, ?, ?)
                """, (assignment['id'], user_id, self.user_data['id']))

            user_dropdown.value = None
            populate_current_users()
            if self.page:
                self.page.update()

        def add_department(e):
            if not department_dropdown.value:
                return

            dept = department_dropdown.value

            # Get all users in department
            dept_users = self.db.execute_query("""
                SELECT id FROM users
                WHERE department = ? AND role = 'examinee' AND is_active = 1
            """, (dept,))

            for user in dept_users:
                existing = self.db.execute_single("""
                    SELECT id FROM assignment_users
                    WHERE assignment_id = ? AND user_id = ?
                """, (assignment['id'], user['id']))

                if not existing:
                    self.db.execute_insert("""
                        INSERT INTO assignment_users (assignment_id, user_id, granted_by)
                        VALUES (?, ?, ?)
                    """, (assignment['id'], user['id'], self.user_data['id']))

            department_dropdown.value = None
            populate_current_users()
            if self.page:
                self.page.update()

        def remove_user(user_id):
            self.db.execute_update("""
                DELETE FROM assignment_users
                WHERE assignment_id = ? AND user_id = ?
            """, (assignment['id'], user_id))

            populate_current_users()
            if self.page:
                self.page.update()

        user_dropdown.on_change = add_user
        department_dropdown.on_change = add_department

        def close_dialog(e):
            users_dialog.open = False
            self.page.update()
            # Reload assignments to update user count
            self.load_exams()

        users_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Manage Users - {assignment['assignment_name']}"),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([user_dropdown, department_dropdown], spacing=20),
                    ft.Container(height=20),
                    current_users_container
                ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 300 if self.page.width > 300 else 600,
                height=self.page.height - 300 if self.page.height > 300 else 400
            ),
            actions=[
                ft.ElevatedButton(
                    "Done",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = users_dialog
        users_dialog.open = True
        self.page.update()
    
    def toggle_assignment_status(self, assignment):
        """Toggle assignment active status"""
        new_status = 0 if assignment['is_active'] else 1
        self.db.execute_update(
            'UPDATE exam_assignments SET is_active = ? WHERE id = ?',
            (new_status, assignment['id'])
        )
        self.load_exams()
    
    def delete_assignment(self, assignment):
        """Delete an assignment"""
        def confirm_delete(e):
            self.db.execute_update('DELETE FROM exam_assignments WHERE id = ?', (assignment['id'],))
            self.db.execute_update('DELETE FROM assignment_users WHERE assignment_id = ?', (assignment['id'],))
            confirm_dialog.open = False
            if self.page:
                self.page.update()
            self.load_exams()
            if self.page:
                self.update()

        def cancel_delete(e):
            confirm_dialog.open = False
            self.page.update()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text('Confirm Delete'),
            content=ft.Text(f"Are you sure you want to delete assignment '{assignment['assignment_name']}'?"),
            actions=[
                ft.TextButton('Cancel', on_click=cancel_delete),
                ft.ElevatedButton(
                    'Delete',
                    on_click=confirm_delete,
                    style=ft.ButtonStyle(bgcolor=COLORS['error'], color=ft.colors.WHITE)
                )
            ]
        )

        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()

    def show_create_preset_dialog(self, e, preset=None):
        """Show dialog to create or edit a preset template"""
        is_edit = preset is not None

        # Load all available exam templates (topics)
        exam_templates = self.db.execute_query("""
            SELECT e.id, e.title,
                   COUNT(CASE WHEN q.difficulty_level = 'easy' THEN 1 END) as easy_count,
                   COUNT(CASE WHEN q.difficulty_level = 'medium' THEN 1 END) as medium_count,
                   COUNT(CASE WHEN q.difficulty_level = 'hard' THEN 1 END) as hard_count
            FROM exams e
            LEFT JOIN questions q ON e.id = q.exam_id AND q.is_active = 1
            GROUP BY e.id
            ORDER BY e.title
        """)

        if not exam_templates:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("No topics available. Please create topics first."),
                bgcolor=COLORS['error']
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Preset name field
        preset_name_field = ft.TextField(
            label="Preset Template Name *",
            value=preset['name'] if is_edit else "",
            hint_text="e.g., SOC Interview Template",
            width=600
        )

        preset_description_field = ft.TextField(
            label="Description (optional)",
            value=preset['description'] if is_edit else "",
            multiline=True,
            min_lines=2,
            max_lines=3,
            hint_text="Brief description of this preset",
            width=600
        )

        # Container for selected topics
        selected_topics_container = ft.Column([
            ft.Text("Selected Topics:", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=10)

        # Total questions counter
        total_questions_text = ft.Text(
            "Total Questions: 0",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=COLORS['primary']
        )

        # Track selected topics and their configurations
        self.preset_selected_topics = {}

        # Load existing preset configuration if editing
        if is_edit:
            preset_config = self.db.execute_query("""
                SELECT exam_id, easy_count, medium_count, hard_count
                FROM preset_template_exams
                WHERE template_id = ?
            """, (preset['id'],))

            for config in preset_config:
                self.preset_selected_topics[config['exam_id']] = {
                    'easy': config['easy_count'],
                    'medium': config['medium_count'],
                    'hard': config['hard_count']
                }

        def update_total_questions():
            """Calculate and display total questions"""
            total = 0
            for topic_id, counts in self.preset_selected_topics.items():
                total += counts.get('easy', 0) + counts.get('medium', 0) + counts.get('hard', 0)
            total_questions_text.value = f"Total Questions: {total}"
            total_questions_text.update()

        def add_topic_to_preset(exam_id):
            """Add a topic to the preset configuration"""
            if exam_id in self.preset_selected_topics:
                return  # Already added

            # Find exam details
            exam = next((e for e in exam_templates if e['id'] == exam_id), None)
            if not exam:
                return

            # Initialize counts
            self.preset_selected_topics[exam_id] = {'easy': 0, 'medium': 0, 'hard': 0}

            # Create UI for this topic
            easy_dropdown = ft.Dropdown(
                label=f"Easy (max: {exam['easy_count']})",
                options=[ft.dropdown.Option(str(i), str(i)) for i in range(0, exam['easy_count'] + 1)],
                value="0",
                width=120,
                content_padding=5
            )

            medium_dropdown = ft.Dropdown(
                label=f"Medium (max: {exam['medium_count']})",
                options=[ft.dropdown.Option(str(i), str(i)) for i in range(0, exam['medium_count'] + 1)],
                value="0",
                width=120,
                content_padding=5
            )

            hard_dropdown = ft.Dropdown(
                label=f"Hard (max: {exam['hard_count']})",
                options=[ft.dropdown.Option(str(i), str(i)) for i in range(0, exam['hard_count'] + 1)],
                value="0",
                width=120,
                content_padding=5
            )

            subtotal_text = ft.Text("Subtotal: 0", size=13, weight=ft.FontWeight.BOLD)

            def update_counts(e):
                self.preset_selected_topics[exam_id]['easy'] = int(easy_dropdown.value or 0)
                self.preset_selected_topics[exam_id]['medium'] = int(medium_dropdown.value or 0)
                self.preset_selected_topics[exam_id]['hard'] = int(hard_dropdown.value or 0)

                subtotal = sum(self.preset_selected_topics[exam_id].values())
                subtotal_text.value = f"Subtotal: {subtotal}"
                subtotal_text.update()
                update_total_questions()

            easy_dropdown.on_change = update_counts
            medium_dropdown.on_change = update_counts
            hard_dropdown.on_change = update_counts

            def remove_topic(e):
                del self.preset_selected_topics[exam_id]
                topic_container.controls.remove(topic_card)
                topic_container.update()
                update_total_questions()
                # Re-enable in dropdown
                topic_dropdown.options = [
                    ft.dropdown.Option(
                        key=str(ex['id']),
                        text=f"{ex['title']} (E:{ex['easy_count']}, M:{ex['medium_count']}, H:{ex['hard_count']})"
                    )
                    for ex in exam_templates if ex['id'] not in self.preset_selected_topics
                ]
                topic_dropdown.update()

            topic_card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(exam['title'], size=14, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_size=16,
                            on_click=remove_topic,
                            icon_color=COLORS['error']
                        )
                    ]),
                    ft.Row([easy_dropdown, medium_dropdown, hard_dropdown, subtotal_text], spacing=10),
                ], spacing=5),
                padding=10,
                border=ft.border.all(1, COLORS['secondary']),
                border_radius=8,
                bgcolor=ft.colors.with_opacity(0.05, COLORS['primary'])
            )

            topic_container.controls.append(topic_card)
            topic_container.update()

            # Remove from dropdown
            topic_dropdown.options = [
                ft.dropdown.Option(
                    key=str(ex['id']),
                    text=f"{ex['title']} (E:{ex['easy_count']}, M:{ex['medium_count']}, H:{ex['hard_count']})"
                )
                for ex in exam_templates if ex['id'] not in self.preset_selected_topics
            ]
            topic_dropdown.value = None
            topic_dropdown.update()
            update_total_questions()

        # Topic selection dropdown
        topic_dropdown = ft.Dropdown(
            label="Add Topic",
            hint_text="Select a topic to add",
            options=[
                ft.dropdown.Option(
                    key=str(exam['id']),
                    text=f"{exam['title']} (E:{exam['easy_count']}, M:{exam['medium_count']}, H:{exam['hard_count']})"
                )
                for exam in exam_templates if exam['id'] not in self.preset_selected_topics
            ],
            width=600,
            on_change=lambda e: add_topic_to_preset(int(e.control.value)) if e.control.value else None
        )

        # Container for topic cards
        topic_container = ft.Column([], spacing=10)

        # Load existing topics if editing
        if is_edit:
            for exam_id, counts in list(self.preset_selected_topics.items()):
                exam = next((e for e in exam_templates if e['id'] == exam_id), None)
                if exam:
                    # Initialize counts first
                    self.preset_selected_topics[exam_id] = counts

                    # Create topic card with saved values
                    easy_dropdown = ft.Dropdown(
                        label=f"Easy (max: {exam['easy_count']})",
                        options=[ft.dropdown.Option(str(i), str(i)) for i in range(0, exam['easy_count'] + 1)],
                        value=str(counts['easy']),
                        width=120,
                        content_padding=5
                    )

                    medium_dropdown = ft.Dropdown(
                        label=f"Medium (max: {exam['medium_count']})",
                        options=[ft.dropdown.Option(str(i), str(i)) for i in range(0, exam['medium_count'] + 1)],
                        value=str(counts['medium']),
                        width=120,
                        content_padding=5
                    )

                    hard_dropdown = ft.Dropdown(
                        label=f"Hard (max: {exam['hard_count']})",
                        options=[ft.dropdown.Option(str(i), str(i)) for i in range(0, exam['hard_count'] + 1)],
                        value=str(counts['hard']),
                        width=120,
                        content_padding=5
                    )

                    subtotal = counts['easy'] + counts['medium'] + counts['hard']
                    subtotal_text = ft.Text(f"Subtotal: {subtotal}", size=13, weight=ft.FontWeight.BOLD)

                    def make_update_counts(eid, e_drop, m_drop, h_drop, st_text):
                        def update_counts(e):
                            self.preset_selected_topics[eid]['easy'] = int(e_drop.value or 0)
                            self.preset_selected_topics[eid]['medium'] = int(m_drop.value or 0)
                            self.preset_selected_topics[eid]['hard'] = int(h_drop.value or 0)

                            subtotal = sum(self.preset_selected_topics[eid].values())
                            st_text.value = f"Subtotal: {subtotal}"
                            st_text.update()
                            update_total_questions()
                        return update_counts

                    update_fn = make_update_counts(exam_id, easy_dropdown, medium_dropdown, hard_dropdown, subtotal_text)
                    easy_dropdown.on_change = update_fn
                    medium_dropdown.on_change = update_fn
                    hard_dropdown.on_change = update_fn

                    def make_remove_topic(eid, t_card):
                        def remove_topic(e):
                            del self.preset_selected_topics[eid]
                            topic_container.controls.remove(t_card)
                            topic_container.update()
                            update_total_questions()
                            # Re-enable in dropdown
                            topic_dropdown.options = [
                                ft.dropdown.Option(
                                    key=str(ex['id']),
                                    text=f"{ex['title']} (E:{ex['easy_count']}, M:{ex['medium_count']}, H:{ex['hard_count']})"
                                )
                                for ex in exam_templates if ex['id'] not in self.preset_selected_topics
                            ]
                            topic_dropdown.update()
                        return remove_topic

                    topic_card = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(exam['title'], size=14, weight=ft.FontWeight.BOLD),
                                ft.Container(expand=True),
                                ft.IconButton(
                                    icon=ft.icons.CLOSE,
                                    icon_size=16,
                                    on_click=make_remove_topic(exam_id, None),
                                    icon_color=COLORS['error']
                                )
                            ]),
                            ft.Row([easy_dropdown, medium_dropdown, hard_dropdown, subtotal_text], spacing=10),
                        ], spacing=5),
                        padding=10,
                        border=ft.border.all(1, COLORS['secondary']),
                        border_radius=8,
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['primary'])
                    )

                    # Update the remove function with correct card reference
                    topic_card.content.controls[0].controls[2].on_click = make_remove_topic(exam_id, topic_card)

                    topic_container.controls.append(topic_card)

            # Update dropdown to exclude already selected topics
            topic_dropdown.options = [
                ft.dropdown.Option(
                    key=str(exam['id']),
                    text=f"{exam['title']} (E:{exam['easy_count']}, M:{exam['medium_count']}, H:{exam['hard_count']})"
                )
                for exam in exam_templates if exam['id'] not in self.preset_selected_topics
            ]

            update_total_questions()

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_preset(e):
            # Validate
            if not preset_name_field.value.strip():
                error_text.value = "Preset name is required"
                error_text.visible = True
                preset_dialog.update()
                return

            if not self.preset_selected_topics:
                error_text.value = "Please add at least one topic"
                error_text.visible = True
                preset_dialog.update()
                return

            try:
                if is_edit:
                    # Update preset
                    self.db.execute_update("""
                        UPDATE exam_preset_templates
                        SET name = ?, description = ?
                        WHERE id = ?
                    """, (preset_name_field.value.strip(), preset_description_field.value.strip(), preset['id']))

                    # Delete old configurations
                    self.db.execute_update("""
                        DELETE FROM preset_template_exams WHERE template_id = ?
                    """, (preset['id'],))

                    preset_id = preset['id']
                else:
                    # Create new preset
                    preset_id = self.db.execute_insert("""
                        INSERT INTO exam_preset_templates (name, description, created_by_user_id)
                        VALUES (?, ?, ?)
                    """, (preset_name_field.value.strip(), preset_description_field.value.strip(), self.user_data['id']))

                # Save topic configurations
                for exam_id, counts in self.preset_selected_topics.items():
                    self.db.execute_insert("""
                        INSERT INTO preset_template_exams (template_id, exam_id, easy_count, medium_count, hard_count)
                        VALUES (?, ?, ?, ?, ?)
                    """, (preset_id, exam_id, counts['easy'], counts['medium'], counts['hard']))

                # Close dialog
                preset_dialog.open = False
                self.page.update()

                # Show success message
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Preset template '{preset_name_field.value.strip()}' {'updated' if is_edit else 'created'} successfully!"),
                    bgcolor=COLORS['success']
                )
                self.page.snack_bar.open = True
                self.page.update()

            except Exception as ex:
                error_text.value = f"Error saving preset: {str(ex)}"
                error_text.visible = True
                preset_dialog.update()
                import traceback
                traceback.print_exc()

        def close_dialog(e):
            preset_dialog.open = False
            self.page.update()

        preset_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"{'Edit' if is_edit else 'Create'} Preset Template"),
            content=ft.Container(
                content=ft.Column([
                    preset_name_field,
                    preset_description_field,
                    ft.Container(height=10),
                    topic_dropdown,
                    ft.Container(height=5),
                    ft.Container(
                        content=ft.Column([
                            topic_container,
                        ], scroll=ft.ScrollMode.AUTO),
                        height=250
                    ),
                    ft.Divider(),
                    total_questions_text,
                    ft.Container(height=5),
                    error_text
                ], spacing=10, tight=True),
                width=self.page.width - 300 if self.page.width > 300 else 700,
                height=self.page.height - 200 if self.page.height > 200 else 600
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog),
                ft.ElevatedButton(
                    "Save Preset",
                    on_click=save_preset,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = preset_dialog
        preset_dialog.open = True
        self.page.update()

    def show_manage_presets_dialog(self, e):
        """Show dialog to manage existing preset templates"""
        # Load all presets
        presets = self.db.execute_query("""
            SELECT pt.id, pt.name, pt.description, pt.created_at,
                   u.full_name as creator_name,
                   COUNT(pte.id) as topic_count,
                   SUM(pte.easy_count + pte.medium_count + pte.hard_count) as total_questions
            FROM exam_preset_templates pt
            LEFT JOIN users u ON pt.created_by_user_id = u.id
            LEFT JOIN preset_template_exams pte ON pt.id = pte.template_id
            GROUP BY pt.id
            ORDER BY pt.created_at DESC
        """)

        if not presets:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("No preset templates found. Create one first!"),
                bgcolor=COLORS['warning']
            )
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Container for preset cards
        presets_container = ft.Column([], spacing=10, scroll=ft.ScrollMode.AUTO)

        def refresh_presets():
            """Reload and display presets"""
            updated_presets = self.db.execute_query("""
                SELECT pt.id, pt.name, pt.description, pt.created_at,
                       u.full_name as creator_name,
                       COUNT(pte.id) as topic_count,
                       SUM(pte.easy_count + pte.medium_count + pte.hard_count) as total_questions
                FROM exam_preset_templates pt
                LEFT JOIN users u ON pt.created_by_user_id = u.id
                LEFT JOIN preset_template_exams pte ON pt.id = pte.template_id
                GROUP BY pt.id
                ORDER BY pt.created_at DESC
            """)

            presets_container.controls.clear()

            if not updated_presets:
                presets_container.controls.append(
                    ft.Text("No preset templates available", italic=True, color=COLORS['text_secondary'])
                )
            else:
                for preset in updated_presets:
                    # Get topic names for this preset
                    topics = self.db.execute_query("""
                        SELECT e.title, pte.easy_count, pte.medium_count, pte.hard_count
                        FROM preset_template_exams pte
                        JOIN exams e ON pte.exam_id = e.id
                        WHERE pte.template_id = ?
                    """, (preset['id'],))

                    topics_summary = ", ".join([
                        f"{t['title']} ({t['easy_count']}E/{t['medium_count']}M/{t['hard_count']}H)"
                        for t in topics
                    ])

                    def make_edit_preset(p):
                        def edit_preset(e):
                            manage_dialog.open = False
                            self.page.update()
                            self.show_create_preset_dialog(None, p)
                        return edit_preset

                    def make_delete_preset(p):
                        def delete_preset(e):
                            def confirm_delete(e):
                                self.db.execute_update("DELETE FROM exam_preset_templates WHERE id = ?", (p['id'],))
                                self.db.execute_update("DELETE FROM preset_template_exams WHERE template_id = ?", (p['id'],))
                                confirm_dialog.open = False
                                self.page.update()
                                refresh_presets()
                                presets_container.update()

                            def cancel_delete(e):
                                confirm_dialog.open = False
                                self.page.update()

                            confirm_dialog = ft.AlertDialog(
                                title=ft.Text("Confirm Delete"),
                                content=ft.Text(f"Are you sure you want to delete preset '{p['name']}'?"),
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
                        return delete_preset

                    preset_card = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.BOOKMARK, color=COLORS['primary'], size=20),
                                ft.Text(preset['name'], size=16, weight=ft.FontWeight.BOLD),
                                ft.Container(expand=True),
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip="Edit",
                                    on_click=make_edit_preset(preset),
                                    icon_color=COLORS['primary']
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    tooltip="Delete",
                                    on_click=make_delete_preset(preset),
                                    icon_color=COLORS['error']
                                )
                            ]),
                            ft.Text(
                                preset['description'] or "No description",
                                size=12,
                                color=COLORS['text_secondary'],
                                italic=not preset['description']
                            ),
                            ft.Divider(height=1),
                            ft.Text(f"Topics: {topics_summary}", size=12),
                            ft.Row([
                                ft.Text(f"Total Questions: {preset['total_questions'] or 0}", size=12, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                                ft.Container(expand=True),
                                ft.Text(f"Created by: {preset['creator_name'] or 'Unknown'}", size=11, color=COLORS['text_secondary'])
                            ])
                        ], spacing=5),
                        padding=15,
                        border=ft.border.all(1, COLORS['secondary']),
                        border_radius=8,
                        bgcolor=ft.colors.with_opacity(0.02, COLORS['primary'])
                    )

                    presets_container.controls.append(preset_card)

            if self.page:
                manage_dialog.update()

        def close_dialog(e):
            manage_dialog.open = False
            self.page.update()

        manage_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Manage Preset Templates"),
            content=ft.Container(
                content=presets_container,
                width=self.page.width - 300 if self.page.width > 300 else 700,
                height=self.page.height - 200 if self.page.height > 200 else 500
            ),
            actions=[
                ft.ElevatedButton(
                    "Close",
                    on_click=close_dialog,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = manage_dialog
        manage_dialog.open = True
        self.page.update()

        # Refresh presets after dialog is opened
        refresh_presets()

