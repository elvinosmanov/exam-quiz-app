import flet as ft
import os
import uuid
from quiz_app.config import COLORS, UPLOAD_FOLDER, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from quiz_app.utils.bulk_import import BulkImporter
from quiz_app.utils.question_selector import QuestionSelector

class QuestionManagement(ft.UserControl):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.questions_data = []
        self.all_questions_data = []  # Keep original data for filtering
        self.exams_data = []
        self.selected_exam_id = None

        # Load exams for dropdown
        self.load_exams()

        # Track preselected exam
        self.preselected_exam_id = None
        
        # Question pool statistics container
        self.question_pool_stats = ft.Container(
            content=ft.Text("Select an exam to view question pool statistics", 
                          color=COLORS['text_secondary'], italic=True),
            visible=False
        )
        
        # Image upload state
        self.current_image_path = None  # Relative path for database
        self.current_image_full_path = None  # Full path for display
        self.image_file_picker = None
        
        # Exam selector
        self.exam_selector = ft.Dropdown(
            label="Select Exam",
            options=[ft.dropdown.Option(str(exam['id']), exam['title']) for exam in self.exams_data],
            on_change=self.exam_selected,
            expand=True
        )

        # Search control
        self.search_field = ft.TextField(
            label="Search questions...",
            prefix_icon=ft.icons.SEARCH,
            on_change=self.apply_filters,
            expand=True
        )

        # Question type filter
        self.type_filter = ft.Dropdown(
            label="Filter by Type",
            options=[
                ft.dropdown.Option("all", "All Types"),
                ft.dropdown.Option("single_choice", "Single Choice"),
                ft.dropdown.Option("multiple_choice", "Multiple Choice"),
                ft.dropdown.Option("true_false", "True/False"),
                ft.dropdown.Option("short_answer", "Short Answer"),
                ft.dropdown.Option("essay", "Essay")
            ],
            value="all",
            on_change=self.apply_filters,
            width=200
        )
        
        # Questions table
        self.questions_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Question")),
                ft.DataColumn(ft.Text("Type")),
                ft.DataColumn(ft.Text("Image")),
                ft.DataColumn(ft.Text("Difficulty")),
                ft.DataColumn(ft.Text("Points")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )
        
        # Action buttons
        self.add_question_btn = ft.ElevatedButton(
            text="Add Question",
            icon=ft.icons.ADD,
            on_click=self.show_add_question_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )
        
        self.bulk_import_btn = ft.ElevatedButton(
            text="Bulk Import",
            icon=ft.icons.UPLOAD_FILE,
            on_click=self.show_bulk_import_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['success'], color=ft.colors.WHITE)
        )
        
        self.download_template_btn = ft.ElevatedButton(
            text="Download Template",
            icon=ft.icons.DOWNLOAD,
            on_click=self.download_template,
            style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
        )
        
        self.export_questions_btn = ft.ElevatedButton(
            text="Export Questions",
            icon=ft.icons.FILE_DOWNLOAD,
            on_click=self.export_questions,
            style=ft.ButtonStyle(bgcolor=COLORS['warning'], color=ft.colors.WHITE)
        )

        self.create_exam_btn = ft.ElevatedButton(
            text="Create Exam Template",
            icon=ft.icons.LIBRARY_ADD,
            on_click=self.show_create_exam_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )

        # Dialogs
        self.question_dialog = None
        self.bulk_import_dialog = None
        self.exam_dialog = None
    
    def preselect_exam(self, exam_id):
        """Pre-select an exam in the dropdown and load its questions"""
        try:
            # Set the exam selector value
            self.exam_selector.value = str(exam_id)
            self.selected_exam_id = exam_id
            
            # Load questions for the selected exam
            self.load_questions()
            
            # Update the UI if it's already mounted
            if hasattr(self, 'page') and self.page:
                self.update()
        except Exception as e:
            print(f"Error preselecting exam {exam_id}: {e}")
    
    def build(self):
        return ft.Column([
            # Header
            ft.Row([
                ft.Text("Question Bank", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(expand=True),
                ft.Row([self.create_exam_btn, self.download_template_btn, self.bulk_import_btn, self.export_questions_btn, self.add_question_btn], spacing=10)
            ]),
            ft.Divider(),
            
            # Filters
            ft.Row([
                self.exam_selector,
                self.search_field,
                self.type_filter
            ], spacing=20),
            
            # Question Pool Statistics
            self.question_pool_stats,
            
            ft.Container(height=10),
            
            # Questions table container
            ft.Container(
                content=ft.ListView(
                    controls=[self.questions_table],
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
        self.exams_data = self.db.execute_query("""
            SELECT id, title FROM exams 
            WHERE is_active = 1 
            ORDER BY title
        """)
    
    def exam_selected(self, e):
        old_exam_id = self.selected_exam_id
        self.selected_exam_id = int(e.control.value) if e.control.value else None
        print(f"DEBUG: Exam selected changed from {old_exam_id} to {self.selected_exam_id}")
        
        if self.selected_exam_id:
            print(f"DEBUG: Loading questions for exam {self.selected_exam_id}")
            self.load_questions()
            self.update_question_pool_stats()
        else:
            print("DEBUG: No exam selected, clearing questions")
            self.questions_data = []
            self.update_table()
            self.hide_question_pool_stats()
    
    def load_questions(self):
        if not self.selected_exam_id:
            print("DEBUG: No exam selected, clearing questions")
            self.questions_data = []
            self.all_questions_data = []
            self.update_table()
            return

        print(f"DEBUG: Loading questions for exam ID: {self.selected_exam_id}")
        self.all_questions_data = self.db.execute_query("""
            SELECT * FROM questions
            WHERE exam_id = ?
            ORDER BY order_index, created_at
        """, (self.selected_exam_id,))
        print(f"DEBUG: Retrieved {len(self.all_questions_data)} questions from database")
        self.questions_data = self.all_questions_data.copy()
        self.apply_filters(None)
    
    def update_table(self):
        print(f"DEBUG: update_table called with {len(self.questions_data)} questions")
        self.questions_table.rows.clear()
        
        # Show message if no exam selected or no questions
        if not self.selected_exam_id:
            self.questions_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text("Please select an exam to view questions", 
                                      color=COLORS['text_secondary'], 
                                      size=16)),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text(""))
                ])
            )
            print("DEBUG: Added 'select exam' message row")
            self.update()
            return
        
        if not self.questions_data:
            self.questions_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text("No questions found for this exam. Click 'Add Question' to create one.", 
                                      color=COLORS['text_secondary'], 
                                      size=16)),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text(""))
                ])
            )
            print("DEBUG: Added 'no questions' message row")
            self.update()
            return
        
        # Add actual question rows
        for idx, question in enumerate(self.questions_data, 1):
            # Truncate long questions for display
            question_text = question['question_text']
            if len(question_text) > 50:
                question_text = question_text[:47] + "..."

            status = "Active" if question['is_active'] else "Inactive"
            status_color = COLORS['success'] if question['is_active'] else COLORS['error']

            # Create image indicator
            image_cell = ft.DataCell(
                ft.Icon(
                    ft.icons.IMAGE if question.get('image_path') else ft.icons.IMAGE_NOT_SUPPORTED,
                    color=COLORS['success'] if question.get('image_path') else COLORS['text_secondary'],
                    size=20
                )
            )

            self.questions_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Text(question_text)),
                        ft.DataCell(ft.Text(question['question_type'].replace('_', ' ').title())),
                        image_cell,
                        ft.DataCell(ft.Text(question['difficulty_level'].title())),
                        ft.DataCell(ft.Text(str(question['points']))),
                        ft.DataCell(ft.Text(status, color=status_color)),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.icons.VISIBILITY,
                                    tooltip="View Question",
                                    on_click=lambda e, q=question: self.view_question(q)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip="Edit Question",
                                    on_click=lambda e, q=question: self.show_edit_question_dialog(q)
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    tooltip="Delete Question",
                                    on_click=lambda e, q=question: self.delete_question(q),
                                    icon_color=COLORS['error']
                                )
                            ], spacing=5)
                        )
                    ]
                )
            )
        
        print(f"DEBUG: Added {len(self.questions_data)} question rows to table")
        print(f"DEBUG: Total table rows: {len(self.questions_table.rows)}")
        self.update()
    
    def update_question_pool_stats(self):
        """Update question pool statistics display for the selected exam"""
        if not self.selected_exam_id:
            self.hide_question_pool_stats()
            return
        
        # Get exam data to check if it uses question pool
        exam_data = self.db.execute_single("""
            SELECT * FROM exams WHERE id = ?
        """, (self.selected_exam_id,))
        
        if not exam_data:
            self.hide_question_pool_stats()
            return
        
        # Get question pool statistics
        selector = QuestionSelector(self.db)
        stats = selector.get_question_pool_stats(self.selected_exam_id)
        
        # Create statistics display
        if exam_data.get('use_question_pool', False):
            # This exam uses question pool - show detailed stats
            easy_requested = exam_data.get('easy_questions_count', 0)
            medium_requested = exam_data.get('medium_questions_count', 0)
            hard_requested = exam_data.get('hard_questions_count', 0)
            total_requested = easy_requested + medium_requested + hard_requested
            
            # Validate configuration
            is_valid, error_msg = selector.validate_question_pool_config(exam_data)
            
            # Create status badges for each difficulty
            easy_status = self._create_difficulty_badge("Easy", stats['easy'], easy_requested)
            medium_status = self._create_difficulty_badge("Medium", stats['medium'], medium_requested)
            hard_status = self._create_difficulty_badge("Hard", stats['hard'], hard_requested)
            
            # Overall status
            if is_valid:
                overall_status = ft.Container(
                    content=ft.Text("✓ Question Pool Ready", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=COLORS['success'],
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    border_radius=6
                )
            else:
                overall_status = ft.Container(
                    content=ft.Text("⚠ Pool Configuration Issue", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=COLORS['error'],
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    border_radius=6
                )
            
            content = ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.SHUFFLE, color=COLORS['primary']),
                    ft.Text("Question Pool Configuration", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                    ft.Container(expand=True),
                    overall_status
                ], spacing=8),
                ft.Container(height=5),
                ft.Row([
                    ft.Text(f"Will select {total_requested} questions from {stats['total']} available", 
                           size=14, color=COLORS['text_secondary'])
                ]),
                ft.Container(height=10),
                ft.Row([easy_status, medium_status, hard_status], spacing=15),
                ft.Container(
                    content=ft.Text(error_msg, color=COLORS['error'], size=12),
                    visible=not is_valid
                ) if not is_valid else ft.Container()
            ], spacing=5)
            
        else:
            # Regular exam - show simple stats
            content = ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.LIST_ALT, color=COLORS['text_secondary']),
                    ft.Text("Question Bank Overview", size=16, weight=ft.FontWeight.BOLD, color=COLORS['text_secondary']),
                ], spacing=8),
                ft.Container(height=5),
                ft.Row([
                    ft.Text(f"Total: {stats['total']} questions", size=14, color=COLORS['text_secondary']),
                    ft.Text(f"Easy: {stats['easy']}", size=14, color=COLORS['text_secondary']),
                    ft.Text(f"Medium: {stats['medium']}", size=14, color=COLORS['text_secondary']),
                    ft.Text(f"Hard: {stats['hard']}", size=14, color=COLORS['text_secondary'])
                ], spacing=20)
            ], spacing=5)
        
        # Update the container
        self.question_pool_stats.content = content
        self.question_pool_stats.visible = True
        self.question_pool_stats.bgcolor = ft.colors.with_opacity(0.05, COLORS['primary'])
        self.question_pool_stats.padding = ft.padding.all(15)
        self.question_pool_stats.border_radius = 8
        self.question_pool_stats.border = ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['primary']))
        
        if self.page:
            self.page.update()
    
    def _create_difficulty_badge(self, label, available, requested):
        """Create a badge showing difficulty level statistics"""
        if requested == 0:
            # Not using this difficulty
            return ft.Container(
                content=ft.Column([
                    ft.Text(label, size=12, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text(f"{available} available", size=11, text_align=ft.TextAlign.CENTER),
                    ft.Text("Not used", size=10, color=COLORS['text_secondary'], text_align=ft.TextAlign.CENTER)
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=ft.colors.with_opacity(0.1, COLORS['text_secondary']),
                padding=ft.padding.all(8),
                border_radius=6,
                width=100
            )
        
        # Check if we have enough questions
        has_enough = available >= requested
        bg_color = COLORS['success'] if has_enough else COLORS['error']
        
        return ft.Container(
            content=ft.Column([
                ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{requested}/{available}", size=11, color=ft.colors.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text("✓ OK" if has_enough else "✗ Not enough", size=10, color=ft.colors.WHITE, text_align=ft.TextAlign.CENTER)
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=bg_color,
            padding=ft.padding.all(8),
            border_radius=6,
            width=100
        )
    
    def hide_question_pool_stats(self):
        """Hide the question pool statistics"""
        self.question_pool_stats.visible = False
        if self.page:
            self.page.update()
    
    def apply_filters(self, e):
        """Apply both search and type filters together"""
        if not self.selected_exam_id:
            return

        # Start with all questions
        filtered_questions = self.all_questions_data.copy()

        # Apply search filter
        search_term = self.search_field.value.lower() if self.search_field.value else ""
        if search_term:
            filtered_questions = [
                q for q in filtered_questions
                if search_term in q['question_text'].lower() or
                   search_term in (q.get('explanation') or "").lower()
            ]

        # Apply type filter
        question_type = self.type_filter.value
        if question_type != "all":
            filtered_questions = [q for q in filtered_questions if q['question_type'] == question_type]

        # Update displayed data
        self.questions_data = filtered_questions
        self.update_table()
    
    def show_add_question_dialog(self, e):
        print(f"DEBUG: show_add_question_dialog called, selected_exam_id={self.selected_exam_id}")
        if not self.selected_exam_id:
            print("DEBUG: No exam selected, showing error dialog")
            self.show_error_dialog("Please select an exam first")
            return
        
        print("DEBUG: Exam is selected, calling show_question_dialog")
        # Call the actual dialog method
        self.show_question_dialog()
    
    def show_simple_test_dialog(self):
        """Simple test dialog to verify dialog creation works"""
        print("DEBUG: Creating simple test dialog")
        try:
            if not self.page:
                print("ERROR: self.page is None")
                return
            
            test_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Test Dialog"),
                content=ft.Text("This is a test dialog to verify dialog creation works"),
                actions=[
                    ft.TextButton("Close", on_click=lambda e: self.close_test_dialog())
                ]
            )
            
            print("DEBUG: Setting test dialog on page")
            self.page.dialog = test_dialog
            test_dialog.open = True
            self.page.update()
            print("DEBUG: Test dialog should now be visible")
            
        except Exception as e:
            print(f"ERROR in show_simple_test_dialog: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def close_test_dialog(self):
        print("DEBUG: Closing test dialog")
        self.page.dialog.open = False
        self.page.update()
    
    def show_edit_question_dialog(self, question):
        self.show_question_dialog(question)
    
    def show_question_dialog(self, question=None):
        print(f"DEBUG: show_question_dialog called, is_edit={question is not None}")
        is_edit = question is not None
        title = "Edit Question" if is_edit else "Add New Question"
        print(f"DEBUG: Dialog title: {title}")
        
        # Check if page is available
        if not self.page:
            print("ERROR: self.page is None, cannot show dialog")
            return
        
        try:
            # Create a simple question dialog for now
            question_text_field = ft.TextField(
                label="Question Text",
                value=question['question_text'] if is_edit else "",
                multiline=True,
                min_lines=3,
                max_lines=8,
                content_padding=8
            )
            
            question_type_dropdown = ft.Dropdown(
                label="Question Type",
                options=[
                    ft.dropdown.Option("single_choice", "Single Choice"),
                    ft.dropdown.Option("multiple_choice", "Multiple Choice"),
                    ft.dropdown.Option("true_false", "True/False"),
                    ft.dropdown.Option("short_answer", "Short Answer"),
                    ft.dropdown.Option("essay", "Essay")
                ],
                value=question['question_type'] if is_edit else "single_choice",
                on_change=self.question_type_changed,
                content_padding=8
            )
            
            difficulty_dropdown = ft.Dropdown(
                label="Difficulty Level",
                options=[
                    ft.dropdown.Option("easy", "Easy"),
                    ft.dropdown.Option("medium", "Medium"),
                    ft.dropdown.Option("hard", "Hard")
                ],
                value=question['difficulty_level'] if is_edit else "medium",
                content_padding=8
            )
            
            points_field = ft.TextField(
                label="Points",
                value=str(question['points']) if is_edit else "1",
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=8
            )
            
            
            explanation_field = ft.TextField(
                label="Explanation (optional)",
                value=question['explanation'] if is_edit else "",
                multiline=True,
                min_lines=2,
                max_lines=4,
                content_padding=8
            )
            
            # Image upload section
            self.current_image_path = question.get('image_path') if is_edit else None
            # Set full path for display if image exists
            if self.current_image_path:
                self.current_image_full_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    self.current_image_path
                )
            else:
                self.current_image_full_path = None
            
            # Create file picker for images
            self.image_file_picker = ft.FilePicker(
                on_result=self.on_image_selected
            )
            self.page.overlay.append(self.image_file_picker)
            
            # Image upload container
            self.image_container = ft.Container(
                content=self.build_image_upload_ui(),
                padding=ft.padding.all(10),
                bgcolor=ft.colors.with_opacity(0.05, COLORS['secondary']),
                border_radius=8
            )
            
            # Dynamic options container for choice-based questions
            self.options_container = ft.Column([])
            self.options_data = []
            
            # Store current question type for easy access
            self.current_question_type = question['question_type'] if is_edit else "single_choice"
            
            # Load existing options for edit mode or initialize for new questions
            if is_edit:
                # Load existing options for choice-based questions
                if question['question_type'] in ['single_choice', 'multiple_choice', 'true_false']:
                    options = self.db.execute_query("""
                        SELECT * FROM question_options 
                        WHERE question_id = ? 
                        ORDER BY order_index
                    """, (question['id'],))
                    self.options_data = []
                    for opt in options:
                        self.options_data.append({
                            'text': opt['option_text'],
                            'is_correct': bool(opt['is_correct'])
                        })
                elif question['question_type'] in ['short_answer', 'essay']:
                    # Load sample answer for text questions
                    if question.get('correct_answer'):
                        self._text_answer_data = {'sample_answer': question['correct_answer']}
            else:
                # Initialize default options for new questions
                if question_type_dropdown.value in ['single_choice', 'multiple_choice']:
                    self.add_default_options()
                elif question_type_dropdown.value == 'true_false':
                    self.setup_true_false_ui()
                elif question_type_dropdown.value in ['short_answer', 'essay']:
                    self.setup_text_answer_ui(question_type_dropdown.value)
            
            error_text = ft.Text("", color=COLORS['error'], visible=False)
            
            def save_question(e):
                try:
                    if not question_text_field.value.strip():
                        error_text.value = "Question text is required"
                        error_text.visible = True
                        self.question_dialog.update()
                        return
                    
                    points = float(points_field.value)
                    if points <= 0:
                        error_text.value = "Points must be greater than 0"
                        error_text.visible = True
                        self.question_dialog.update()
                        return
                    
                    # Prepare question data
                    question_data = {
                        'exam_id': self.selected_exam_id,
                        'question_text': question_text_field.value.strip(),
                        'question_type': question_type_dropdown.value,
                        'difficulty_level': difficulty_dropdown.value,
                        'points': points,
                        'explanation': explanation_field.value.strip() or None,
                        'image_path': self.current_image_path
                    }
                    
                    if is_edit:
                        # Update existing question
                        question_id = question['id']
                        query = """
                            UPDATE questions SET question_text = ?, question_type = ?, 
                            difficulty_level = ?, points = ?, explanation = ?, image_path = ?
                            WHERE id = ?
                        """
                        params = [
                            question_data['question_text'],
                            question_data['question_type'],
                            question_data['difficulty_level'],
                            question_data['points'],
                            question_data['explanation'],
                            question_data['image_path'],
                            question['id']
                        ]
                        self.db.execute_update(query, params)
                    else:
                        # Create new question
                        query = """
                            INSERT INTO questions (exam_id, question_text, question_type, difficulty_level, points, explanation, image_path)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """
                        params = [
                            question_data['exam_id'],
                            question_data['question_text'],
                            question_data['question_type'],
                            question_data['difficulty_level'],
                            question_data['points'],
                            question_data['explanation'],
                            question_data['image_path']
                        ]
                        question_id = self.db.execute_insert(query, params)
                    
                    # Save options for choice-based questions
                    if question_type_dropdown.value in ['single_choice', 'multiple_choice', 'true_false']:
                        # For edit mode, delete existing options first to prevent duplication
                        if is_edit:
                            self.db.execute_update("DELETE FROM question_options WHERE question_id = ?", (question_id,))
                        
                        # Insert new/updated options
                        for i, option_data in enumerate(self.options_data):
                            if option_data['text'].strip():
                                self.db.execute_insert("""
                                    INSERT INTO question_options (question_id, option_text, is_correct, order_index)
                                    VALUES (?, ?, ?, ?)
                                """, (question_id, option_data['text'].strip(), option_data['is_correct'], i))
                    
                    # Save sample answer for text-based questions
                    elif question_type_dropdown.value in ['short_answer', 'essay']:
                        if hasattr(self, '_text_answer_data') and self._text_answer_data.get('sample_answer'):
                            # Store sample answer in correct_answer field
                            self.db.execute_update("""
                                UPDATE questions SET correct_answer = ? WHERE id = ?
                            """, (self._text_answer_data['sample_answer'], question_id))
                    
                    # Close dialog and refresh
                    self.question_dialog.open = False
                    self.page.update()
                    self.load_questions()
                    
                except ValueError:
                    error_text.value = "Please enter valid numeric values"
                    error_text.visible = True
                    self.question_dialog.update()
                except Exception as ex:
                    error_text.value = f"Error saving question: {str(ex)}"
                    error_text.visible = True
                    self.question_dialog.update()
            
            def close_dialog(e):
                self.question_dialog.open = False
                self.page.update()
            
            # Create dialog
            self.question_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(title),
                content=ft.Container(
                    content=ft.Column([
                        question_text_field,
                        ft.Row([question_type_dropdown, difficulty_dropdown], spacing=10),
                        points_field,
                        explanation_field,
                        self.image_container,
                        self.options_container,
                        error_text
                    ], spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
                    width=800,
                    height=700
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=close_dialog),
                    ft.ElevatedButton(
                        "Save" if is_edit else "Create",
                        on_click=save_question,
                        style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            # Initialize options UI based on question type
            if is_edit:
                if question['question_type'] == 'true_false':
                    self.setup_true_false_ui()
                elif question['question_type'] in ['single_choice', 'multiple_choice']:
                    self.rebuild_options_ui(question['question_type'])
                elif question['question_type'] in ['short_answer', 'essay']:
                    self.setup_text_answer_ui(question['question_type'])
            else:
                if question_type_dropdown.value in ['single_choice', 'multiple_choice']:
                    self.rebuild_options_ui(question_type_dropdown.value)
                elif question_type_dropdown.value == 'true_false':
                    self.setup_true_false_ui()
                elif question_type_dropdown.value in ['short_answer', 'essay']:
                    self.setup_text_answer_ui(question_type_dropdown.value)
            
            print("DEBUG: Setting dialog on page")
            self.page.dialog = self.question_dialog
            self.question_dialog.open = True
            self.page.update()
            print("DEBUG: Dialog should now be visible")
            
        except Exception as e:
            print(f"ERROR in show_question_dialog: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Show fallback error dialog
            error_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Error"),
                content=ft.Text(f"Failed to create question dialog: {str(e)}"),
                actions=[ft.TextButton("OK", on_click=lambda e: self.close_error_dialog())]
            )
            self.page.dialog = error_dialog
            error_dialog.open = True
            self.page.update()
    
    def question_type_changed(self, e):
        question_type = e.control.value
        self.current_question_type = question_type  # Store current type
        self.options_container.controls.clear()
        self.options_data = []
        
        if question_type in ['single_choice', 'multiple_choice']:
            # Both single and multiple choice need options
            if not self.options_data:
                self.add_default_options()
            self.rebuild_options_ui(question_type)
        elif question_type == 'true_false':
            self.setup_true_false_ui()
        elif question_type in ['short_answer', 'essay']:
            self.setup_text_answer_ui(question_type)
        
        self.question_dialog.update()
    
    def add_default_options(self):
        self.options_data = [
            {'text': '', 'is_correct': True},
            {'text': '', 'is_correct': False},
            {'text': '', 'is_correct': False},
            {'text': '', 'is_correct': False}
        ]
    
    def rebuild_options_ui(self, question_type='single_choice'):
        try:
            print(f"DEBUG: rebuild_options_ui called with question_type={question_type}")
            self.options_container.controls.clear()
            
            if question_type == 'single_choice':
                self.options_container.controls.append(
                    ft.Text("Answer Options (Select ONE correct answer):", 
                           weight=ft.FontWeight.BOLD, size=16, color=COLORS['primary'])
                )
            else:  # multiple_choice
                self.options_container.controls.append(
                    ft.Text("Answer Options (Select ALL correct answers):", 
                           weight=ft.FontWeight.BOLD, size=16, color=COLORS['success'])
                )
            
            for i, option in enumerate(self.options_data):
                if question_type == 'single_choice':
                    # Use checkbox for single choice but with single-selection logic
                    correct_control = ft.Checkbox(
                        label="Correct",
                        value=option['is_correct'],
                        on_change=lambda e, idx=i: self.update_single_choice_correct(idx, e.control.value)
                    )
                else:  # multiple_choice
                    # Checkbox behavior for multiple choice
                    correct_control = ft.Checkbox(
                        label="Correct",
                        value=option['is_correct'],
                        on_change=lambda e, idx=i: self.update_multiple_choice_correct(idx, e.control.value)
                    )
                
                option_row = ft.Row([
                    ft.TextField(
                        label=f"Option {i+1}",
                        value=option['text'],
                        on_change=lambda e, idx=i: self.update_option_text(idx, e.control.value),
                        expand=True,
                        content_padding=8
                    ),
                    correct_control,
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        on_click=lambda e, idx=i: self.remove_option(idx),
                        icon_color=COLORS['error']
                    ) if len(self.options_data) > 2 else ft.Container()
                ], spacing=10)
                
                self.options_container.controls.append(option_row)
            
            # Add Option button (no limit)
            add_option_btn = ft.ElevatedButton(
                text="Add Option",
                icon=ft.icons.ADD,
                on_click=self.add_option,
                style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
            )
            self.options_container.controls.append(add_option_btn)
            
        except Exception as e:
            print(f"ERROR in rebuild_options_ui: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def setup_true_false_ui(self):
        """Setup UI for true/false questions"""
        self.options_container.controls.clear()
        
        # Create true/false options
        self.options_data = [
            {'text': 'True', 'is_correct': True},
            {'text': 'False', 'is_correct': False}
        ]
        
        # Add header
        self.options_container.controls.append(
            ft.Text("Select the correct answer:", 
                   weight=ft.FontWeight.BOLD, size=16, color=COLORS['primary'])
        )
        
        # Create radio buttons for True/False
        def update_true_false_answer(e):
            is_true_selected = e.control.value == "true"
            self.options_data[0]['is_correct'] = is_true_selected  # True option
            self.options_data[1]['is_correct'] = not is_true_selected  # False option
        
        correct_answer_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="true", label="True"),
                ft.Radio(value="false", label="False")
            ]),
            value="true" if self.options_data[0]['is_correct'] else "false",
            on_change=update_true_false_answer
        )
        
        self.options_container.controls.append(
            ft.Container(
                content=correct_answer_group,
                padding=ft.padding.symmetric(vertical=10, horizontal=20),
                bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                border_radius=8
            )
        )
    
    def setup_text_answer_ui(self, question_type):
        """Setup UI for short answer and essay questions"""
        self.options_container.controls.clear()
        self.options_data = []
        
        if question_type == 'short_answer':
            header_text = "Short Answer Question"
            help_text = "Students will type a brief text response. You can provide sample answers or keywords for grading reference."
        else:  # essay
            header_text = "Essay Question"
            help_text = "Students will write a longer text response. This will require manual grading."
        
        # Add header
        self.options_container.controls.append(
            ft.Text(header_text, 
                   weight=ft.FontWeight.BOLD, size=16, color=COLORS['primary'])
        )
        
        # Add help text
        self.options_container.controls.append(
            ft.Text(help_text, 
                   size=14, color=COLORS['text_secondary'], 
                   italic=True)
        )
        
        # Add sample answer field (optional)
        sample_answer_field = ft.TextField(
            label="Sample Answer / Keywords (Optional)",
            hint_text="Provide sample answers or keywords for grading reference",
            multiline=True,
            min_lines=2,
            max_lines=4 if question_type == 'short_answer' else 6,
            content_padding=8
        )
        
        self.options_container.controls.append(
            ft.Container(
                content=sample_answer_field,
                padding=ft.padding.symmetric(vertical=10),
                bgcolor=ft.colors.with_opacity(0.05, COLORS['secondary']),
                border_radius=8
            )
        )
        
        # Store sample answer in options_data for consistency
        def update_sample_answer(e):
            if not hasattr(self, '_text_answer_data'):
                self._text_answer_data = {}
            self._text_answer_data['sample_answer'] = e.control.value
        
        sample_answer_field.on_change = update_sample_answer
    
    def update_option_text(self, index, text):
        if index < len(self.options_data):
            self.options_data[index]['text'] = text
    
    def update_single_choice_correct(self, index, is_checked):
        """Update correct answer for single choice questions (checkbox with single-selection behavior)"""
        if index < len(self.options_data):
            if is_checked:
                # If this option is being checked, uncheck all others (single selection)
                for i, opt in enumerate(self.options_data):
                    opt['is_correct'] = (i == index)
            else:
                # If this option is being unchecked, just uncheck it
                self.options_data[index]['is_correct'] = False
            
            # Rebuild UI to reflect changes
            self.rebuild_options_ui(self.current_question_type)
            self.question_dialog.update()
    
    def update_multiple_choice_correct(self, index, is_correct):
        """Update correct answer for multiple choice questions (checkbox behavior)"""
        if index < len(self.options_data):
            self.options_data[index]['is_correct'] = is_correct
            self.question_dialog.update()
    
    def add_option(self, e):
        self.options_data.append({'text': '', 'is_correct': False})
        # Use stored question type instead of trying to detect it
        self.rebuild_options_ui(self.current_question_type)
        self.question_dialog.update()
    
    def remove_option(self, index):
        if len(self.options_data) > 2:
            self.options_data.pop(index)
            # Use stored question type instead of trying to detect it
            self.rebuild_options_ui(self.current_question_type)
            self.question_dialog.update()
    
    def view_question(self, question):
        # Get question options if it's a choice-based question
        options = []
        if question['question_type'] in ['single_choice', 'multiple_choice', 'true_false']:
            options = self.db.execute_query("""
                SELECT * FROM question_options 
                WHERE question_id = ? 
                ORDER BY order_index
            """, (question['id'],))
        
        # Question header card
        header_content = [
            ft.Text(question['question_text'], 
                   size=18, 
                   weight=ft.FontWeight.BOLD, 
                   color=COLORS['text_primary']),
            ft.Row([
                ft.Chip(
                    label=ft.Text(question['question_type'].replace('_', ' ').title()),
                    bgcolor=COLORS['primary']
                ),
                ft.Chip(
                    label=ft.Text(question['difficulty_level'].title()),
                    bgcolor=COLORS['secondary']
                ),
                ft.Chip(
                    label=ft.Text(f"{question['points']} pts"),
                    bgcolor=COLORS['success']
                )
            ], spacing=8)
        ]
        
        # Add image if present
        if question.get('image_path'):
            header_content.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text("Question Image:", size=14, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Image(
                                src=question['image_path'],
                                width=400,
                                height=250,
                                fit=ft.ImageFit.CONTAIN,
                                border_radius=8
                            ),
                            bgcolor=ft.colors.WHITE,
                            border_radius=8,
                            border=ft.border.all(1, ft.colors.OUTLINE),
                            padding=ft.padding.all(5),
                            on_click=lambda e: self.show_fullscreen_image(question['image_path'])
                        ),
                        ft.Text("Click image to view full size", size=12, italic=True, color=COLORS['text_secondary'])
                    ], spacing=8),
                    margin=ft.margin.only(top=12)
                )
            )
        
        header_card = ft.Container(
            content=ft.Column(header_content, spacing=12),
            padding=ft.padding.all(16),
            bgcolor=COLORS['surface'],
            border_radius=8,
            border=ft.border.all(1, COLORS['secondary'])
        )
        
        content_sections = [header_card]
        
        # Options section for choice-based questions
        if options:
            options_items = []
            for i, option in enumerate(options):
                is_correct = option['is_correct']
                option_container = ft.Container(
                    content=ft.Row([
                        ft.Icon(
                            ft.icons.CHECK_CIRCLE if is_correct else ft.icons.RADIO_BUTTON_UNCHECKED,
                            color=COLORS['success'] if is_correct else COLORS['text_secondary'],
                            size=20
                        ),
                        ft.Text(
                            option['option_text'],
                            size=14,
                            color=COLORS['success'] if is_correct else COLORS['text_primary'],
                            weight=ft.FontWeight.BOLD if is_correct else ft.FontWeight.NORMAL
                        )
                    ], spacing=8),
                    padding=ft.padding.symmetric(vertical=6, horizontal=12),
                    bgcolor=ft.colors.with_opacity(0.1, COLORS['success']) if is_correct else ft.colors.with_opacity(0.05, COLORS['text_secondary']),
                    border_radius=6,
                    border=ft.border.all(1, COLORS['success']) if is_correct else ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['text_secondary']))
                )
                options_items.append(option_container)
            
            options_card = ft.Container(
                content=ft.Column([
                    ft.Text("Answer Options", 
                           size=16, 
                           weight=ft.FontWeight.BOLD, 
                           color=COLORS['text_primary']),
                    ft.Column(options_items, spacing=8)
                ], spacing=12),
                padding=ft.padding.all(16),
                bgcolor=COLORS['surface'],
                border_radius=8,
                border=ft.border.all(1, COLORS['secondary'])
            )
            content_sections.append(options_card)
        
        # Sample answer for text-based questions
        elif question['question_type'] in ['short_answer', 'essay'] and question.get('correct_answer'):
            answer_card = ft.Container(
                content=ft.Column([
                    ft.Text("Sample Answer / Keywords", 
                           size=16, 
                           weight=ft.FontWeight.BOLD, 
                           color=COLORS['text_primary']),
                    ft.Text(question['correct_answer'], 
                           size=14, 
                           color=COLORS['text_secondary'])
                ], spacing=8),
                padding=ft.padding.all(16),
                bgcolor=COLORS['surface'],
                border_radius=8,
                border=ft.border.all(1, COLORS['secondary'])
            )
            content_sections.append(answer_card)
        
        # Explanation section
        if question.get('explanation'):
            explanation_card = ft.Container(
                content=ft.Column([
                    ft.Text("Explanation", 
                           size=16, 
                           weight=ft.FontWeight.BOLD, 
                           color=COLORS['text_primary']),
                    ft.Text(question['explanation'], 
                           size=14, 
                           color=COLORS['text_secondary'])
                ], spacing=8),
                padding=ft.padding.all(16),
                bgcolor=COLORS['surface'],
                border_radius=8,
                border=ft.border.all(1, COLORS['secondary'])
            )
            content_sections.append(explanation_card)
        
        def close_preview(e):
            preview_dialog.open = False
            self.page.update()
        
        preview_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Question Preview", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(content_sections, spacing=16, scroll=ft.ScrollMode.AUTO),
                width=800,
                height=600
            ),
            actions=[
                ft.TextButton(
                    "Close", 
                    on_click=close_preview,
                    style=ft.ButtonStyle(color=COLORS['primary'])
                )
            ]
        )
        
        self.page.dialog = preview_dialog
        preview_dialog.open = True
        self.page.update()
    
    def delete_question(self, question):
        def confirm_delete(e):
            self.db.execute_update("DELETE FROM questions WHERE id = ?", (question['id'],))
            self.db.execute_update("DELETE FROM question_options WHERE question_id = ?", (question['id'],))
            confirm_dialog.open = False
            if self.page:
                self.page.update()
            
            # Reload questions and update UI
            self.load_questions()
            
            # Force update of the entire question management component
            if self.page:
                self.update()
        
        def cancel_delete(e):
            confirm_dialog.open = False
            self.page.update()
        
        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Delete"),
            content=ft.Text("Are you sure you want to delete this question? This action cannot be undone."),
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
    
    def show_bulk_import_dialog(self, e):
        if not self.selected_exam_id:
            self.show_error_dialog("Please select an exam first")
            return
        
        # File picker for upload
        file_picker = ft.FilePicker(
            on_result=self.process_bulk_import
        )
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files(
            dialog_title="Select Questions File",
            allowed_extensions=["csv", "xlsx", "xls"]
        )
    
    def process_bulk_import(self, e):
        """Process the selected file for bulk import"""
        # Check if user cancelled file selection
        if not e.files:
            return
        
        # Get the selected file
        file_path = e.files[0].path
        if not file_path:
            self.show_error_dialog("No file selected")
            return
        
        # Show loading dialog
        self.show_import_progress_dialog()
        
        try:
            # Import questions using BulkImporter
            from quiz_app.utils.bulk_import import BulkImporter
            importer = BulkImporter(self.db)
            
            result = importer.import_questions(file_path, self.selected_exam_id)
            
            # Close loading dialog
            self.close_import_progress_dialog()
            
            if result['success']:
                # Show success dialog with results
                self.show_import_success_dialog(result)
                # Refresh the questions table
                self.load_questions()
            else:
                # Show error dialog with details
                self.show_import_error_dialog(result['error'])
                
        except Exception as ex:
            # Close loading dialog and show error
            self.close_import_progress_dialog()
            self.show_error_dialog(f"Import failed: {str(ex)}")
    
    def download_template(self, e):
        try:
            from quiz_app.utils.bulk_import import BulkImporter
            importer = BulkImporter()
            
            # Create template file in Downloads folder
            template_path = importer.create_template()
            
            # Show success message
            success_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Template Downloaded"),
                content=ft.Text(f"Template file saved to:\n{template_path}"),
                actions=[ft.TextButton("OK", on_click=lambda e: self.close_success_dialog())]
            )
            self.page.dialog = success_dialog
            success_dialog.open = True
            self.page.update()
            
        except Exception as ex:
            self.show_error_dialog(f"Error downloading template: {str(ex)}")
    
    def export_questions(self, e):
        if not self.selected_exam_id:
            self.show_error_dialog("Please select an exam first")
            return
        
        try:
            import pandas as pd
            from datetime import datetime
            import os
            
            # Get exam info
            exam = self.db.execute_single("SELECT title FROM exams WHERE id = ?", (self.selected_exam_id,))
            exam_title = exam['title'] if exam else f"Exam_{self.selected_exam_id}"
            
            # Get questions for the selected exam
            questions = self.db.execute_query("""
                SELECT * FROM questions 
                WHERE exam_id = ? 
                ORDER BY order_index, created_at
            """, (self.selected_exam_id,))
            
            if not questions:
                self.show_error_dialog("No questions found in this exam")
                return
            
            # Convert to template format
            export_data = []
            for question in questions:
                # Get options for choice-based questions
                options = {}
                if question['question_type'] in ['single_choice', 'multiple_choice', 'true_false']:
                    question_options = self.db.execute_query("""
                        SELECT * FROM question_options 
                        WHERE question_id = ? 
                        ORDER BY order_index
                    """, (question['id'],))
                    
                    correct_answers = []
                    for i, opt in enumerate(question_options):
                        options[f'option_{i+1}'] = opt['option_text']
                        if opt['is_correct']:
                            correct_answers.append(opt['option_text'])
                    
                    # Set correct answer format
                    if question['question_type'] == 'multiple_choice':
                        correct_answer = ', '.join(correct_answers)
                    else:
                        correct_answer = correct_answers[0] if correct_answers else ''
                else:
                    correct_answer = question['correct_answer'] or ''
                
                # Build row data
                row_data = {
                    'question_text': question['question_text'],
                    'question_type': question['question_type'],
                    'difficulty_level': question['difficulty_level'],
                    'points': question['points'],
                    'correct_answer': correct_answer,
                    'explanation': question['explanation'] or ''
                }
                
                # Add option columns
                for i in range(1, 7):
                    row_data[f'option_{i}'] = options.get(f'option_{i}', '')
                
                export_data.append(row_data)
            
            # Create DataFrame
            df = pd.DataFrame(export_data)
            
            # Save to Downloads folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_exam_title = "".join(c for c in exam_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"questions_{safe_exam_title}_{timestamp}.xlsx"
            
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            file_path = os.path.join(downloads_path, filename)
            
            df.to_excel(file_path, index=False)
            
            # Show success message
            success_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Questions Exported"),
                content=ft.Text(f"Exported {len(questions)} questions to:\n{file_path}"),
                actions=[ft.TextButton("OK", on_click=lambda e: self.close_success_dialog())]
            )
            self.page.dialog = success_dialog
            success_dialog.open = True
            self.page.update()
            
        except Exception as ex:
            self.show_error_dialog(f"Error exporting questions: {str(ex)}")
    
    def close_success_dialog(self):
        self.page.dialog.open = False
        self.page.update()
    
    def show_error_dialog(self, message):
        error_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: self.close_error_dialog())]
        )
        self.page.dialog = error_dialog
        error_dialog.open = True
        self.page.update()
    
    def close_error_dialog(self):
        self.page.dialog.open = False
        self.page.update()
    
    def show_import_progress_dialog(self):
        """Show progress dialog during import"""
        progress_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Importing Questions"),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Processing your file, please wait...", text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, height=100),
        )
        self.page.dialog = progress_dialog
        progress_dialog.open = True
        self.page.update()
    
    def close_import_progress_dialog(self):
        """Close the import progress dialog"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def show_import_success_dialog(self, result):
        """Show success dialog with import results"""
        success_text = f"Import completed successfully!\n\n"
        success_text += f"✅ Imported: {result['imported_count']} questions\n"
        if result.get('skipped_count', 0) > 0:
            success_text += f"⚠️ Skipped: {result['skipped_count']} questions\n"
        if result.get('error_count', 0) > 0:
            success_text += f"❌ Errors: {result['error_count']} questions\n"
        success_text += f"📝 Total processed: {result.get('total', result['imported_count'] + result.get('skipped_count', 0))}"
        
        success_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Import Successful", color=COLORS['success']),
            content=ft.Text(success_text),
            actions=[
                ft.TextButton(
                    "OK", 
                    on_click=lambda e: self.close_import_success_dialog(),
                    style=ft.ButtonStyle(color=COLORS['primary'])
                )
            ]
        )
        self.page.dialog = success_dialog
        success_dialog.open = True
        self.page.update()
    
    def close_import_success_dialog(self):
        """Close the import success dialog"""
        self.page.dialog.open = False
        self.page.update()
    
    def show_import_error_dialog(self, error_message):
        """Show detailed error dialog for import failures"""
        error_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Import Failed", color=COLORS['error']),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("The import failed with the following error:"),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text(
                            error_message,
                            selectable=True,
                            size=12
                        ),
                        bgcolor=COLORS['secondary'],
                        padding=ft.padding.all(10),
                        border_radius=4,
                        width=500
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        "💡 Tips:\n"
                        "• Download the template to see the correct format\n"
                        "• Ensure all required columns are present\n"
                        "• Check that question types are valid\n"
                        "• Verify choice questions have at least 2 options",
                        size=12,
                        color=COLORS['text_secondary']
                    )
                ], scroll=ft.ScrollMode.AUTO),
                height=400,
                width=500
            ),
            actions=[
                ft.TextButton(
                    "Download Template", 
                    on_click=lambda e: [self.close_import_error_dialog(), self.download_template(e)],
                    style=ft.ButtonStyle(color=COLORS['primary'])
                ),
                ft.TextButton(
                    "Close", 
                    on_click=lambda e: self.close_import_error_dialog(),
                    style=ft.ButtonStyle(color=COLORS['text_secondary'])
                )
            ]
        )
        self.page.dialog = error_dialog
        error_dialog.open = True
        self.page.update()
    
    def close_import_error_dialog(self):
        """Close the import error dialog"""
        self.page.dialog.open = False
        self.page.update()
    
    def build_image_upload_ui(self):
        """Build the image upload interface"""
        # Image preview and upload controls with horizontal layout
        header = ft.Text("Question Image (Optional):", size=14, weight=ft.FontWeight.BOLD)
        
        if self.current_image_full_path:
            # State 1: Image on left, action buttons on right
            image_container = ft.Container(
                content=ft.Image(
                    src=self.current_image_full_path,
                    width=200,
                    height=120,
                    fit=ft.ImageFit.CONTAIN,
                    border_radius=8
                ),
                bgcolor=ft.colors.with_opacity(0.1, ft.colors.BLUE_GREY),
                border_radius=8,
                border=ft.border.all(1, ft.colors.OUTLINE),
                padding=ft.padding.all(5)
            )
            
            buttons = ft.Column([
                ft.ElevatedButton(
                    "Change Image",
                    icon=ft.icons.EDIT,
                    on_click=self.select_image,
                    style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
                ),
                ft.ElevatedButton(
                    "Remove Image",
                    icon=ft.icons.DELETE,
                    on_click=self.remove_image,
                    style=ft.ButtonStyle(bgcolor=COLORS['error'], color=ft.colors.WHITE)
                )
            ], spacing=8)
            
            content_row = ft.Row([image_container, buttons], spacing=15, alignment=ft.MainAxisAlignment.START)
        else:
            # State 2: Placeholder on left, upload button on right
            placeholder_container = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.IMAGE, size=32, color=ft.colors.OUTLINE),
                    ft.Text("No image selected", size=12, color=ft.colors.OUTLINE)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                width=200,
                height=120,
                bgcolor=ft.colors.with_opacity(0.05, ft.colors.OUTLINE),
                border_radius=8,
                border=ft.border.all(1, ft.colors.OUTLINE),
                padding=ft.padding.all(15),
                alignment=ft.alignment.center
            )
            
            upload_button = ft.ElevatedButton(
                "Upload Image",
                icon=ft.icons.UPLOAD,
                on_click=self.select_image,
                style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
            )
            
            content_row = ft.Row([placeholder_container, upload_button], spacing=15, alignment=ft.MainAxisAlignment.START)
        
        return ft.Column([header, content_row], spacing=8)
    
    def select_image(self, e):
        """Open file picker to select an image"""
        if self.image_file_picker:
            self.image_file_picker.pick_files(
                dialog_title="Select Question Image",
                allowed_extensions=list(ALLOWED_EXTENSIONS),
                allow_multiple=False
            )
    
    def on_image_selected(self, e):
        """Handle image file selection"""
        if e.files and len(e.files) > 0:
            file = e.files[0]
            
            # Validate file size
            if file.size > MAX_FILE_SIZE:
                self.show_error_dialog(f"File size too large. Maximum allowed: {MAX_FILE_SIZE // (1024*1024)}MB")
                return
            
            # Validate file extension
            file_ext = file.name.split('.')[-1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                self.show_error_dialog(f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
                return
            
            try:
                # Create unique filename
                unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                
                # Ensure upload directory exists
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
                # Copy file to upload directory
                destination_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                
                # Read and write file (Flet file handling)
                with open(file.path, 'rb') as src:
                    with open(destination_path, 'wb') as dst:
                        dst.write(src.read())
                
                # Store paths
                self.current_image_path = f"assets/images/{unique_filename}"  # Relative for database
                self.current_image_full_path = destination_path  # Full path for display
                
                # Update UI
                self.update_image_upload_ui()
                
            except Exception as ex:
                self.show_error_dialog(f"Error uploading image: {str(ex)}")
    
    def remove_image(self, e):
        """Remove the current image"""
        # Remove physical file if it exists
        if self.current_image_path:
            try:
                full_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    self.current_image_path
                )
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as ex:
                print(f"Warning: Could not remove file {full_path}: {ex}")
        
        # Clear image paths
        self.current_image_path = None
        self.current_image_full_path = None
        
        # Update UI
        self.update_image_upload_ui()
    
    def update_image_upload_ui(self):
        """Update the image upload interface"""
        if hasattr(self, 'image_container') and self.image_container:
            self.image_container.content = self.build_image_upload_ui()
            if hasattr(self, 'question_dialog') and self.question_dialog:
                self.question_dialog.update()
    
    def show_fullscreen_image(self, image_path):
        """Show image in fullscreen dialog"""
        def close_image_dialog(e):
            image_dialog.open = False
            self.page.update()
        
        image_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Question Image", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Image(
                    src=image_path,
                    width=800,
                    height=600,
                    fit=ft.ImageFit.CONTAIN
                ),
                width=800,
                height=600,
                alignment=ft.alignment.center
            ),
            actions=[
                ft.TextButton(
                    "Close",
                    on_click=close_image_dialog,
                    style=ft.ButtonStyle(color=COLORS['primary'])
                )
            ]
        )
        
        self.page.dialog = image_dialog
        image_dialog.open = True
        self.page.update()

    def show_create_exam_dialog(self, e):
        """Show dialog to create a new exam template"""
        self.show_exam_dialog()

    def show_exam_dialog(self, exam=None):
        """Create or edit exam template dialog"""
        is_edit = exam is not None
        title = "Edit Exam Template" if is_edit else "Create New Exam Template"

        # Form fields - Only basic template information
        exam_title_field = ft.TextField(
            label="Exam Title *",
            value=exam['title'] if is_edit else "",
            content_padding=8,
            hint_text="Enter a descriptive exam title",
            width=600
        )

        description_field = ft.TextField(
            label="Description (optional)",
            value=exam['description'] if is_edit else "",
            multiline=True,
            min_lines=3,
            max_lines=6,
            content_padding=8,
            hint_text="Provide exam instructions or description",
            width=600
        )

        category_field = ft.TextField(
            label="Category (optional)",
            value=exam.get('category', '') if is_edit else "",
            content_padding=8,
            hint_text="e.g., Mathematics, Programming, Science",
            width=600
        )

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_exam(e):
            # Validate required fields
            if not exam_title_field.value.strip():
                error_text.value = "Exam title is required"
                error_text.visible = True
                self.exam_dialog.update()
                return

            try:
                if is_edit:
                    # Update existing exam
                    query = """
                        UPDATE exams
                        SET title = ?, description = ?, category = ?
                        WHERE id = ?
                    """
                    params = (
                        exam_title_field.value.strip(),
                        description_field.value.strip() or None,
                        category_field.value.strip() or None,
                        exam['id']
                    )
                    self.db.execute_update(query, params)
                else:
                    # Create new exam - need user_id from somewhere
                    # Get current user from session or pass it in
                    query = """
                        INSERT INTO exams (title, description, category, created_by)
                        VALUES (?, ?, ?, ?)
                    """
                    params = (
                        exam_title_field.value.strip(),
                        description_field.value.strip() or None,
                        category_field.value.strip() or None,
                        1  # TODO: Get actual user ID
                    )
                    self.db.execute_insert(query, params)

                # Close dialog and refresh
                self.exam_dialog.open = False
                if self.page:
                    self.page.update()

                # Reload exams dropdown
                self.load_exams()
                self.exam_selector.options = [ft.dropdown.Option(str(exam['id']), exam['title']) for exam in self.exams_data]

                # Update UI
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
                    category_field,
                    ft.Container(height=10),
                    error_text
                ], spacing=15, tight=True),
                width=600,
                height=350
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
