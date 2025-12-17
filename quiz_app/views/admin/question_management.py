import flet as ft
import os
import uuid
from quiz_app.config import COLORS, UPLOAD_FOLDER, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from quiz_app.utils.localization import t
from quiz_app.utils.bulk_import import BulkImporter
from quiz_app.utils.question_selector import QuestionSelector
from quiz_app.utils.permissions import UnitPermissionManager

class QuestionManagement(ft.UserControl):
    def __init__(self, db, user_data=None):
        super().__init__()
        self.db = db
        self.user_data = user_data or {'role': 'admin'}  # Default to admin if not provided
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
            content=ft.Text(t('select_exam'),
                          color=COLORS['text_secondary'], italic=True),
            visible=False
        )
        
        # Image upload state
        self.current_image_path = None  # Relative path for database
        self.current_image_full_path = None  # Full path for display
        self.image_file_picker = None
        
        # Topic selector
        self.exam_selector = ft.Dropdown(
            label=t('select_topic'),
            options=[ft.dropdown.Option(str(exam['id']), exam['title']) for exam in self.exams_data],
            on_change=self.exam_selected,
            expand=True
        )

        # Edit topic button (enabled when a topic is selected)
        self.edit_exam_btn = ft.IconButton(
            icon=ft.icons.EDIT,
            tooltip=t('edit_topic'),
            on_click=self.edit_selected_exam,
            disabled=True,  # Disabled until an exam is selected
            icon_color=COLORS['primary']
        )

        # Search control
        self.search_field = ft.TextField(
            label=t('search_questions'),
            prefix_icon=ft.icons.SEARCH,
            on_change=self.apply_filters,
            expand=True
        )

        # Question type filter
        self.type_filter = ft.Dropdown(
            label=t('filter_by_type'),
            options=[
                ft.dropdown.Option("all", t('all_types')),
                ft.dropdown.Option("single_choice", t('single_choice')),
                ft.dropdown.Option("multiple_choice", t('multiple_choice')),
                ft.dropdown.Option("true_false", t('true_false')),
                ft.dropdown.Option("short_answer", t('short_answer')),
                ft.dropdown.Option("essay", t('essay'))
            ],
            value="all",
            on_change=self.apply_filters,
            width=200
        )

        # Status filter
        self.status_filter = ft.Dropdown(
            label=t('filter_by_status'),
            options=[
                ft.dropdown.Option("all", t('all')),
                ft.dropdown.Option("active", t('active')),
                ft.dropdown.Option("inactive", t('inactive'))
            ],
            value="all",
            on_change=self.apply_filters,
            width=150
        )
        
        # Questions table
        self.questions_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t('question'))),
                ft.DataColumn(ft.Text(t('type'))),
                ft.DataColumn(ft.Text(t('image'))),
                ft.DataColumn(ft.Text(t('difficulty'))),
                ft.DataColumn(ft.Text(t('points'))),
                ft.DataColumn(ft.Text(t('status'))),
                ft.DataColumn(ft.Text(t('actions')))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )
        
        # Action buttons
        self.add_question_btn = ft.ElevatedButton(
            text=t('add_question'),
            icon=ft.icons.ADD,
            on_click=self.show_add_question_dialog,
            disabled=True,  # Initially disabled
            tooltip=t('select_exam_to_import'),
            style=ft.ButtonStyle(
                bgcolor={
                    ft.MaterialState.DEFAULT: COLORS['primary'],
                    ft.MaterialState.DISABLED: ft.colors.with_opacity(0.2, COLORS['primary'])
                },
                color={
                    ft.MaterialState.DEFAULT: ft.colors.WHITE,
                    ft.MaterialState.DISABLED: ft.colors.WHITE70
                }
            )
        )
        
        self.bulk_import_btn = ft.ElevatedButton(
            text=t('bulk_import'),
            icon=ft.icons.UPLOAD_FILE,
            on_click=self.show_bulk_import_dialog,
            disabled=True,  # Initially disabled
            tooltip=t('select_exam_to_import'),
            style=ft.ButtonStyle(
                bgcolor={
                    ft.MaterialState.DEFAULT: COLORS['success'],
                    ft.MaterialState.DISABLED: ft.colors.with_opacity(0.2, COLORS['success'])
                },
                color={
                    ft.MaterialState.DEFAULT: ft.colors.WHITE,
                    ft.MaterialState.DISABLED: ft.colors.WHITE70
                }
            )
        )

        self.download_template_btn = ft.ElevatedButton(
            text=t('download_template'),
            icon=ft.icons.DOWNLOAD,
            on_click=self.download_template,
            style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
        )

        self.export_questions_btn = ft.ElevatedButton(
            text=t('export_questions'),
            icon=ft.icons.FILE_DOWNLOAD,
            on_click=self.export_questions,
            disabled=True,  # Initially disabled
            tooltip=t('select_exam_to_export'),
            style=ft.ButtonStyle(
                bgcolor={
                    ft.MaterialState.DEFAULT: COLORS['warning'],
                    ft.MaterialState.DISABLED: ft.colors.with_opacity(0.2, COLORS['warning'])
                },
                color={
                    ft.MaterialState.DEFAULT: ft.colors.WHITE,
                    ft.MaterialState.DISABLED: ft.colors.WHITE70
                }
            )
        )

        self.create_exam_btn = ft.ElevatedButton(
            text=t('new_topic'),
            icon=ft.icons.LIBRARY_ADD,
            on_click=self.show_create_exam_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )
        
        self.manage_observers_btn = ft.ElevatedButton(
            text=t('observers'),
            icon=ft.icons.REMOVE_RED_EYE,
            on_click=self.show_observers_dialog,
            disabled=True,
            tooltip=t('select_exam_to_manage_observers'),
            style=ft.ButtonStyle(
                bgcolor={
                    ft.MaterialState.DEFAULT: COLORS['info'],
                    ft.MaterialState.DISABLED: ft.colors.with_opacity(0.2, COLORS['info'])
                },
                color={
                    ft.MaterialState.DEFAULT: ft.colors.WHITE,
                    ft.MaterialState.DISABLED: ft.colors.WHITE70
                }
            )
        )

        # Dialogs
        self.question_dialog = None
        self.bulk_import_dialog = None
        self.exam_dialog = None
        self.observers_dialog = None
        self.delete_topic_dialog = None
        
        # Observer management state
        self.current_observers = []
        self.observer_candidates = []
        self.observer_dropdown = None
        self.observers_list_column = None
        self.observers_message_text = None
    
    def preselect_exam(self, exam_id):
        """Pre-select an exam in the dropdown and load its questions"""
        try:
            # Set the exam selector value
            self.exam_selector.value = str(exam_id)
            self.selected_exam_id = exam_id

            # Load questions for the selected exam
            self.load_questions()

            # Update button availability
            self.update_observers_button_state()
            self.update_add_question_button_state()
            self.update_import_export_buttons_state()
            self.update_edit_exam_button_state()

            # Update the UI if it's already mounted
            if hasattr(self, 'page') and self.page:
                self.update()
        except Exception as e:
            print(f"Error preselecting exam {exam_id}: {e}")
    
    def build(self):
        return ft.Column([
            # Header
            ft.Row([
                ft.Text(t('question_bank'), size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(expand=True),
                ft.Row([
                    self.create_exam_btn,
                    self.manage_observers_btn,
                    self.download_template_btn,
                    self.bulk_import_btn,
                    self.export_questions_btn,
                    self.add_question_btn
                ], spacing=10)
            ]),
            ft.Divider(),
            
            # Filters
            ft.Row([
                self.exam_selector,
                self.edit_exam_btn,
                self.search_field,
                self.type_filter,
                self.status_filter
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
        # Apply unit-level filtering for experts
        perm_manager = UnitPermissionManager(self.db)
        filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data, table_alias='e')

        # Build query with unit filtering
        query = """
            SELECT e.id, e.title, e.created_by, u.full_name as creator_name, u.unit as creator_unit
            FROM exams e
            LEFT JOIN users u ON e.created_by = u.id
            WHERE e.is_active = 1 {filter_clause}
            ORDER BY e.title
        """.format(filter_clause=filter_clause)

        base_exams = self.db.execute_query(query, tuple(filter_params))
        current_user_id = self.user_data.get('id')
        for exam in base_exams:
            if current_user_id and exam.get('created_by') == current_user_id:
                exam['access_type'] = 'own'
            else:
                exam['access_type'] = 'direct'

        # Include observer access for experts
        if self.user_data.get('role') == 'expert' and self.user_data.get('id'):
            observer_query = """
                SELECT e.id, e.title, e.created_by, owner.full_name as creator_name, owner.unit as creator_unit
                FROM exam_observers eo
                JOIN exams e ON eo.exam_id = e.id
                LEFT JOIN users owner ON e.created_by = owner.id
                WHERE eo.observer_id = ? AND e.is_active = 1
            """
            observer_exams = self.db.execute_query(observer_query, (self.user_data['id'],))

            exam_map = {exam['id']: exam for exam in base_exams}
            for exam in observer_exams:
                exam['access_type'] = 'observer'
                exam_map.setdefault(exam['id'], exam)

            self.exams_data = sorted(
                exam_map.values(),
                key=lambda ex: (ex['title'] or '').lower()
            )
        else:
            self.exams_data = base_exams

        self.refresh_exam_selector_options()
        self.update_observers_button_state()
        self.update_add_question_button_state()
        self.update_import_export_buttons_state()

    def refresh_exam_selector_options(self):
        """Update the exam dropdown with the latest exam list"""
        if not hasattr(self, 'exam_selector') or not self.exam_selector:
            return

        current_value = self.exam_selector.value
        options = [
            ft.dropdown.Option(str(exam['id']), self.get_exam_option_label(exam))
            for exam in self.exams_data
        ]
        self.exam_selector.options = options

        if current_value:
            option_keys = {opt.key or opt.text for opt in options}
            if current_value not in option_keys:
                self.exam_selector.value = None
                self.selected_exam_id = None
                self.questions_data = []
                self.update_table()
                self.update_observers_button_state()
                self.update_add_question_button_state()
                self.update_import_export_buttons_state()

        if self.page:
            self.exam_selector.update()
        self.update_add_question_button_state()
        self.update_import_export_buttons_state()

    def update_observers_button_state(self):
        """Enable or disable observer button based on exam selection"""
        if not hasattr(self, 'manage_observers_btn') or not self.manage_observers_btn:
            return

        selected_exam = self.get_selected_exam()
        can_manage = bool(
            selected_exam and (
                self.user_data.get('role') == 'admin' or
                selected_exam.get('created_by') == self.user_data.get('id')
            )
        )
        self.manage_observers_btn.disabled = not can_manage

        # Update tooltip based on state
        if not selected_exam:
            # No exam selected
            self.manage_observers_btn.tooltip = t('select_exam_to_manage_observers')
        elif not can_manage:
            # Exam selected but user doesn't have permission
            self.manage_observers_btn.tooltip = t('observer_manage_forbidden')
        else:
            # User has permission
            self.manage_observers_btn.tooltip = None

        if self.page:
            self.manage_observers_btn.update()

    def get_selected_exam(self):
        """Return the dictionary of the currently selected exam"""
        if not self.selected_exam_id:
            return None

        for exam in self.exams_data:
            if exam['id'] == self.selected_exam_id:
                return exam
        return None
    
    def get_exam_option_label(self, exam):
        """Human-friendly option label with ownership indicator"""
        base_title = exam.get('title') or "Untitled"
        if self.user_data.get('role') == 'admin':
            return base_title

        access_type = exam.get('access_type')
        if access_type == 'observer':
            return f"{base_title} [{t('observer_topic_label')}]"
        if access_type == 'own':
            return f"{base_title} [{t('my_topic_label')}]"
        return base_title

    def user_can_add_questions(self):
        """Determine if current user can add questions for selected exam"""
        exam = self.get_selected_exam()
        if not exam:
            return False
        if self.user_data.get('role') == 'admin':
            return True
        return exam.get('access_type') != 'observer'

    def update_add_question_button_state(self):
        """Enable/disable add question button based on access level"""
        if not hasattr(self, 'add_question_btn') or not self.add_question_btn:
            return

        self.add_question_btn.disabled = not self.user_can_add_questions()
        if self.page and getattr(self.add_question_btn, 'page', None):
            self.add_question_btn.update()

    def update_import_export_buttons_state(self):
        """Enable/disable import and export buttons based on exam selection"""
        has_exam = bool(self.selected_exam_id)

        # Update add question button
        if hasattr(self, 'add_question_btn') and self.add_question_btn:
            self.add_question_btn.disabled = not has_exam
            self.add_question_btn.tooltip = None if has_exam else t('select_exam_to_import')
            if self.page and getattr(self.add_question_btn, 'page', None):
                self.add_question_btn.update()

        # Update bulk import button
        if hasattr(self, 'bulk_import_btn') and self.bulk_import_btn:
            self.bulk_import_btn.disabled = not has_exam
            self.bulk_import_btn.tooltip = None if has_exam else t('select_exam_to_import')
            if self.page and getattr(self.bulk_import_btn, 'page', None):
                self.bulk_import_btn.update()

        # Update export questions button
        if hasattr(self, 'export_questions_btn') and self.export_questions_btn:
            self.export_questions_btn.disabled = not has_exam
            self.export_questions_btn.tooltip = None if has_exam else t('select_exam_to_export')
            if self.page and getattr(self.export_questions_btn, 'page', None):
                self.export_questions_btn.update()

    def update_edit_exam_button_state(self):
        """Enable/disable edit exam button based on exam selection"""
        if not hasattr(self, 'edit_exam_btn') or not self.edit_exam_btn:
            return

        has_exam = bool(self.selected_exam_id)
        self.edit_exam_btn.disabled = not has_exam
        self.edit_exam_btn.tooltip = t('edit_topic') if has_exam else t('select_exam_to_edit')

        if self.page and getattr(self.edit_exam_btn, 'page', None):
            self.edit_exam_btn.update()

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

        self.update_observers_button_state()
        self.update_add_question_button_state()
        self.update_import_export_buttons_state()
        self.update_edit_exam_button_state()
    
    def load_questions(self):
        if not self.selected_exam_id:
            print("DEBUG: No exam selected, clearing questions")
            self.questions_data = []
            self.all_questions_data = []
            self.update_table()
            return

        print(f"DEBUG: Loading questions for exam ID: {self.selected_exam_id}")
        # Load questions with exam's created_by for permission checking
        self.all_questions_data = self.db.execute_query("""
            SELECT q.*, e.created_by as exam_created_by
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE q.exam_id = ?
            ORDER BY q.order_index, q.created_at
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
                    ft.DataCell(ft.Text(t('please_select_exam_questions'),
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
                    ft.DataCell(ft.Text(t('no_questions_found'),
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
        perm_manager = UnitPermissionManager(self.db)

        for idx, question in enumerate(self.questions_data, 1):
            # Truncate long questions for display
            question_text = question['question_text']
            if len(question_text) > 50:
                question_text = question_text[:47] + "..."

            status = t('active') if question['is_active'] else t('inactive')
            status_color = COLORS['success'] if question['is_active'] else COLORS['error']

            # Create image indicator
            image_cell = ft.DataCell(
                ft.Icon(
                    ft.icons.IMAGE if question.get('image_path') else ft.icons.IMAGE_NOT_SUPPORTED,
                    color=COLORS['success'] if question.get('image_path') else COLORS['text_secondary'],
                    size=20
                )
            )

            # Check if user can edit this question (based on exam ownership)
            can_edit = perm_manager.can_edit_content(question.get('exam_created_by'), self.user_data)

            # Build action buttons based on permissions
            action_buttons = []

            if can_edit:
                # Add toggle status button (like exam management)
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.icons.TOGGLE_ON if question['is_active'] else ft.icons.TOGGLE_OFF,
                        tooltip=t('toggle_status'),
                        icon_color=COLORS['success'] if question['is_active'] else COLORS['text_secondary'],
                        on_click=lambda e, q=question: self.toggle_question_status(q)
                    )
                )
                action_buttons.extend([
                    ft.IconButton(
                        icon=ft.icons.EDIT,
                        tooltip=t('edit_question_tooltip'),
                        on_click=lambda e, q=question: self.show_edit_question_dialog(q)
                    ),
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        tooltip=t('delete_question_tooltip'),
                        on_click=lambda e, q=question: self.delete_question(q),
                        icon_color=COLORS['error']
                    )
                ])

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
                        ft.DataCell(ft.Row(action_buttons, spacing=5))
                    ],
                    on_select_changed=lambda e, q=question: self.view_question(q)
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
            easy_status = self._create_difficulty_badge(t('easy'), stats['easy'], easy_requested)
            medium_status = self._create_difficulty_badge(t('medium'), stats['medium'], medium_requested)
            hard_status = self._create_difficulty_badge(t('hard'), stats['hard'], hard_requested)

            # Check if user can delete this topic
            selected_exam = self.get_selected_exam()
            can_delete = bool(
                selected_exam and (
                    self.user_data.get('role') == 'admin' or
                    selected_exam.get('created_by') == self.user_data.get('id')
                )
            )

            # Create delete button for the pool config view
            delete_button = ft.IconButton(
                icon=ft.icons.DELETE_OUTLINE,
                icon_color=COLORS['error'],
                tooltip=t('delete_topic') if can_delete else t('no_permission_delete_topic'),
                disabled=not can_delete,
                on_click=self.show_delete_topic_dialog,
                icon_size=20
            )

            # Overall status
            if is_valid:
                overall_status = ft.Container(
                    content=ft.Text(t('pool_ready'), color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=COLORS['success'],
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    border_radius=6
                )
            else:
                overall_status = ft.Container(
                    content=ft.Text(t('pool_issue'), color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
                    bgcolor=COLORS['error'],
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    border_radius=6
                )

            content = ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.SHUFFLE, color=COLORS['primary']),
                    ft.Text(t('question_pool_config'), size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                    ft.Container(expand=True),
                    overall_status,
                    delete_button
                ], spacing=8),
                ft.Container(height=5),
                ft.Row([
                    ft.Text(t('will_select_questions').format(total_requested, stats['total']),
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
            # Check if user can delete this topic
            selected_exam = self.get_selected_exam()
            can_delete = bool(
                selected_exam and (
                    self.user_data.get('role') == 'admin' or
                    selected_exam.get('created_by') == self.user_data.get('id')
                )
            )

            # Create delete button for the overview
            delete_button = ft.IconButton(
                icon=ft.icons.DELETE_OUTLINE,
                icon_color=COLORS['error'],
                tooltip=t('delete_topic') if can_delete else t('no_permission_delete_topic'),
                disabled=not can_delete,
                on_click=self.show_delete_topic_dialog,
                icon_size=20
            )

            content = ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.LIST_ALT, color=COLORS['text_secondary']),
                    ft.Text(t('question_bank_overview'), size=16, weight=ft.FontWeight.BOLD, color=COLORS['text_secondary']),
                    ft.Container(expand=True),
                    delete_button
                ], spacing=8),
                ft.Container(height=5),
                ft.Row([
                    ft.Text(t('total_questions') + f": {stats['total']}", size=14, color=COLORS['text_secondary']),
                    ft.Text(f"{t('easy')}: {stats['easy']}", size=14, color=COLORS['text_secondary']),
                    ft.Text(f"{t('medium')}: {stats['medium']}", size=14, color=COLORS['text_secondary']),
                    ft.Text(f"{t('hard')}: {stats['hard']}", size=14, color=COLORS['text_secondary'])
                ], spacing=20)
            ], spacing=5)
        
        # Update the container
        self.question_pool_stats.content = content
        self.question_pool_stats.visible = True
        self.question_pool_stats.bgcolor = ft.colors.with_opacity(0.05, COLORS['primary'])
        self.question_pool_stats.padding = ft.padding.all(15)
        self.question_pool_stats.border_radius = 8
        self.question_pool_stats.border = ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['primary']))

        # Update the container and parent
        if hasattr(self, 'page') and self.page:
            self.question_pool_stats.update()
            self.update()
    
    def _create_difficulty_badge(self, label, available, requested):
        """Create a badge showing difficulty level statistics"""
        if requested == 0:
            # Not using this difficulty
            return ft.Container(
                content=ft.Column([
                    ft.Text(label, size=12, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    ft.Text(t('available_count').format(available), size=11, text_align=ft.TextAlign.CENTER),
                    ft.Text(t('not_used'), size=10, color=COLORS['text_secondary'], text_align=ft.TextAlign.CENTER)
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
                ft.Text(t('requested_available').format(requested, available), size=11, color=ft.colors.WHITE, text_align=ft.TextAlign.CENTER),
                ft.Text(t('ok') if has_enough else t('not_enough'), size=10, color=ft.colors.WHITE, text_align=ft.TextAlign.CENTER)
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=bg_color,
            padding=ft.padding.all(8),
            border_radius=6,
            width=100
        )
    
    def hide_question_pool_stats(self):
        """Hide the question pool statistics"""
        self.question_pool_stats.visible = False
        if hasattr(self, 'page') and self.page:
            self.question_pool_stats.update()
            self.update()
    
    def apply_filters(self, e):
        """Apply search, type, and status filters together"""
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

        # Apply status filter
        status_filter = self.status_filter.value
        if status_filter == "active":
            filtered_questions = [q for q in filtered_questions if q['is_active'] == 1]
        elif status_filter == "inactive":
            filtered_questions = [q for q in filtered_questions if q['is_active'] == 0]

        # Update displayed data
        self.questions_data = filtered_questions
        self.update_table()
    
    def show_add_question_dialog(self, e):
        print(f"DEBUG: show_add_question_dialog called, selected_exam_id={self.selected_exam_id}")
        if not self.selected_exam_id:
            print("DEBUG: No exam selected, showing error dialog")
            self.show_error_dialog(t('please_select_exam'))
            return
        if not self.user_can_add_questions():
            self.show_error_dialog(t('observer_add_forbidden'))
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
                    ft.TextButton(t('close'), on_click=lambda e: self.close_test_dialog())
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
        title = t('edit_question') if is_edit else t('add_new_question')
        print(f"DEBUG: Dialog title: {title}")
        
        # Check if page is available
        if not self.page:
            print("ERROR: self.page is None, cannot show dialog")
            return
        
        try:
            # Create a simple question dialog for now
            question_text_field = ft.TextField(
                label=t('question_text'),
                value=question['question_text'] if is_edit else "",
                multiline=True,
                min_lines=3,
                max_lines=8,
                content_padding=8
            )

            question_type_dropdown = ft.Dropdown(
                label=t('question_type'),
                options=[
                    ft.dropdown.Option("single_choice", t('single_choice')),
                    ft.dropdown.Option("multiple_choice", t('multiple_choice')),
                    ft.dropdown.Option("true_false", t('true_false')),
                    ft.dropdown.Option("short_answer", t('short_answer')),
                    ft.dropdown.Option("essay", t('essay'))
                ],
                value=question['question_type'] if is_edit else "single_choice",
                on_change=self.question_type_changed,
                content_padding=8
            )

            difficulty_dropdown = ft.Dropdown(
                label=t('difficulty_level'),
                options=[
                    ft.dropdown.Option("easy", t('easy')),
                    ft.dropdown.Option("medium", t('medium')),
                    ft.dropdown.Option("hard", t('hard'))
                ],
                value=question['difficulty_level'] if is_edit else "medium",
                content_padding=8
            )

            points_field = ft.TextField(
                label=t('points'),
                value=str(question['points']) if is_edit else "1",
                keyboard_type=ft.KeyboardType.NUMBER,
                content_padding=8
            )


            explanation_field = ft.TextField(
                label=t('explanation_optional'),
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
                        error_text.value = t('question_text_required')
                        error_text.visible = True
                        self.question_dialog.update()
                        return

                    points = float(points_field.value)
                    if points <= 0:
                        error_text.value = t('points_greater_zero')
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
                        # Create new question (default status is Active)
                        query = """
                            INSERT INTO questions (exam_id, question_text, question_type, difficulty_level, points, explanation, image_path, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
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
                    error_text.value = t('valid_numeric')
                    error_text.visible = True
                    self.question_dialog.update()
                except Exception as ex:
                    error_text.value = t('error_saving_question').format(str(ex))
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
                    ft.TextButton(t('cancel'), on_click=close_dialog),
                    ft.ElevatedButton(
                        t('save') if is_edit else t('create'),
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
                title=ft.Text(t('error')),
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
                    ft.Text(t('answer_options_single'),
                           weight=ft.FontWeight.BOLD, size=16, color=COLORS['primary'])
                )
            else:  # multiple_choice
                self.options_container.controls.append(
                    ft.Text(t('answer_options_multiple'),
                           weight=ft.FontWeight.BOLD, size=16, color=COLORS['success'])
                )
            
            for i, option in enumerate(self.options_data):
                if question_type == 'single_choice':
                    # Use checkbox for single choice but with single-selection logic
                    correct_control = ft.Checkbox(
                        label=t('correct'),
                        value=option['is_correct'],
                        on_change=lambda e, idx=i: self.update_single_choice_correct(idx, e.control.value)
                    )
                else:  # multiple_choice
                    # Checkbox behavior for multiple choice
                    correct_control = ft.Checkbox(
                        label=t('correct'),
                        value=option['is_correct'],
                        on_change=lambda e, idx=i: self.update_multiple_choice_correct(idx, e.control.value)
                    )
                
                option_row = ft.Row([
                    ft.TextField(
                        label=t('option_number').format(i+1),
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
                text=t('add_option_text'),
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
            {'text': t('true'), 'is_correct': True},
            {'text': t('false'), 'is_correct': False}
        ]

        # Add header
        self.options_container.controls.append(
            ft.Text(t('select_correct_answer'),
                   weight=ft.FontWeight.BOLD, size=16, color=COLORS['primary'])
        )

        # Create radio buttons for True/False
        def update_true_false_answer(e):
            is_true_selected = e.control.value == "true"
            self.options_data[0]['is_correct'] = is_true_selected  # True option
            self.options_data[1]['is_correct'] = not is_true_selected  # False option

        correct_answer_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="true", label=t('true')),
                ft.Radio(value="false", label=t('false'))
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
            header_text = t('short_answer_question')
            help_text = t('short_answer_help')
        else:  # essay
            header_text = t('essay_question')
            help_text = t('essay_help')
        
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
            label=t('sample_answer_label'),
            hint_text=t('sample_answers'),
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
                        ft.Text(t('question_image_label'), size=14, weight=ft.FontWeight.BOLD),
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
                        ft.Text(t('click_to_view'), size=12, italic=True, color=COLORS['text_secondary'])
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
                    ft.Text(t('answer_options'),
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
                    ft.Text(t('sample_answer_keywords'),
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
                    ft.Text(t('explanation'),
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
            title=ft.Text(t('question_preview'), size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column(content_sections, spacing=16, scroll=ft.ScrollMode.AUTO),
                width=800,
                height=600
            ),
            actions=[
                ft.TextButton(
                    t('close'),
                    on_click=close_preview,
                    style=ft.ButtonStyle(color=COLORS['primary'])
                )
            ]
        )
        
        self.page.dialog = preview_dialog
        preview_dialog.open = True
        self.page.update()
    
    def toggle_question_status(self, question):
        """Toggle question active/inactive status"""
        try:
            new_status = 0 if question['is_active'] else 1
            self.db.execute_update(
                "UPDATE questions SET is_active = ? WHERE id = ?",
                (new_status, question['id'])
            )

            # Reload questions to reflect the change
            self.load_questions()

        except Exception as ex:
            print(f"Error toggling question status: {ex}")
            # Show error dialog
            error_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(t('error')),
                content=ft.Text(f"{t('error_updating_status')}: {str(ex)}"),
                actions=[
                    ft.TextButton(t('ok'), on_click=lambda e: self.close_error_dialog(error_dialog))
                ]
            )
            self.page.dialog = error_dialog
            error_dialog.open = True
            self.page.update()

    def close_error_dialog(self, dialog):
        """Close error dialog"""
        dialog.open = False
        self.page.update()

    def delete_question(self, question):
        def confirm_delete(e):
            # Delete associated image file if it exists
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
            title=ft.Text(t('confirm_delete_title')),
            content=ft.Text(t('confirm_delete_question')),
            actions=[
                ft.TextButton(t('cancel'), on_click=cancel_delete),
                ft.ElevatedButton(
                    t('delete'),
                    on_click=confirm_delete,
                    style=ft.ButtonStyle(bgcolor=COLORS['error'], color=ft.colors.WHITE)
                )
            ]
        )
        
        self.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.page.update()
    
    def show_bulk_import_dialog(self, e):
        # Note: Button should be disabled if no exam is selected
        # but keeping this check as safety measure
        if not self.selected_exam_id:
            return

        # File picker for upload
        file_picker = ft.FilePicker(
            on_result=self.process_bulk_import
        )
        self.page.overlay.append(file_picker)
        self.page.update()
        file_picker.pick_files(
            dialog_title=t('select_questions_file'),
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
            self.show_error_dialog(t('no_file_selected'))
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

            # Create file picker for save location
            def on_save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    try:
                        importer = BulkImporter()
                        # Create template and save to selected path
                        template_path = importer.create_template(file_path=e.path)

                        # Show success message
                        success_dialog = ft.AlertDialog(
                            modal=True,
                            title=ft.Text(t('template_downloaded')),
                            content=ft.Text(t('template_saved_to').format(template_path)),
                            actions=[ft.TextButton("OK", on_click=lambda e: self.close_success_dialog())]
                        )
                        self.page.dialog = success_dialog
                        success_dialog.open = True
                        self.page.update()
                    except Exception as ex:
                        self.show_error_dialog(t('error_downloading_template').format(str(ex)))

            # Create and show file picker
            save_file_dialog = ft.FilePicker(on_result=on_save_result)
            self.page.overlay.append(save_file_dialog)
            self.page.update()

            save_file_dialog.save_file(
                file_name="questions_template.xlsx",
                allowed_extensions=["xlsx"]
            )

        except Exception as ex:
            self.show_error_dialog(t('error_downloading_template').format(str(ex)))
    
    def export_questions(self, e):
        # Note: Button should be disabled if no exam is selected
        # but keeping this check as safety measure
        if not self.selected_exam_id:
            return

        try:
            import pandas as pd
            from datetime import datetime

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
                self.show_error_dialog(t('no_questions_found_exam'))
                return

            # Create file picker callback
            def on_save_result(e: ft.FilePickerResultEvent):
                if e.path:
                    try:
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

                        # Create DataFrame and save
                        df = pd.DataFrame(export_data)
                        df.to_excel(e.path, index=False)

                        # Show success message
                        success_dialog = ft.AlertDialog(
                            modal=True,
                            title=ft.Text(t('questions_exported_title')),
                            content=ft.Text(t('questions_exported_message').format(len(questions), e.path)),
                            actions=[ft.TextButton("OK", on_click=lambda e: self.close_success_dialog())]
                        )
                        self.page.dialog = success_dialog
                        success_dialog.open = True
                        self.page.update()
                    except Exception as ex:
                        self.show_error_dialog(t('error_exporting_questions').format(str(ex)))

            # Create and show file picker
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_exam_title = "".join(c for c in exam_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            default_filename = f"questions_{safe_exam_title}_{timestamp}.xlsx"

            save_file_dialog = ft.FilePicker(on_result=on_save_result)
            self.page.overlay.append(save_file_dialog)
            self.page.update()

            save_file_dialog.save_file(
                file_name=default_filename,
                allowed_extensions=["xlsx"]
            )

        except Exception as ex:
            self.show_error_dialog(t('error_exporting_questions').format(str(ex)))
    
    def close_success_dialog(self):
        self.page.dialog.open = False
        self.page.update()
    
    def show_error_dialog(self, message):
        error_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t('error')),
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
            title=ft.Text(t('importing_questions')),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text(t('processing_file'), text_align=ft.TextAlign.CENTER)
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
        success_text = t('import_completed') + "\n\n"
        success_text += t('imported_count').format(result['imported_count']) + "\n"
        if result.get('skipped_count', 0) > 0:
            success_text += t('skipped_count').format(result['skipped_count']) + "\n"
        if result.get('error_count', 0) > 0:
            success_text += t('error_count').format(result['error_count']) + "\n"
        success_text += t('total_processed').format(result.get('total', result['imported_count'] + result.get('skipped_count', 0)))

        success_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t('import_successful'), color=COLORS['success']),
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
            title=ft.Text(t('import_failed_title'), color=COLORS['error']),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(t('import_failed_message')),
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
                        t('import_tips'),
                        size=12,
                        color=COLORS['text_secondary']
                    )
                ], scroll=ft.ScrollMode.AUTO),
                height=400,
                width=500
            ),
            actions=[
                ft.TextButton(
                    t('download_template'),
                    on_click=lambda e: [self.close_import_error_dialog(), self.download_template(e)],
                    style=ft.ButtonStyle(color=COLORS['primary'])
                ),
                ft.TextButton(
                    t('close'),
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
        header = ft.Text(t('question_image_title'), size=14, weight=ft.FontWeight.BOLD)
        
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
                    t('change_image'),
                    icon=ft.icons.EDIT,
                    on_click=self.select_image,
                    style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
                ),
                ft.ElevatedButton(
                    t('remove_image'),
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
                    ft.Text(t('no_image_selected'), size=12, color=ft.colors.OUTLINE)
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
                t('upload_image_btn'),
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
                dialog_title=t('select_question_image'),
                allowed_extensions=list(ALLOWED_EXTENSIONS),
                allow_multiple=False
            )
    
    def on_image_selected(self, e):
        """Handle image file selection"""
        if e.files and len(e.files) > 0:
            file = e.files[0]
            
            # Validate file size
            if file.size > MAX_FILE_SIZE:
                self.show_error_dialog(t('file_size_too_large').format(MAX_FILE_SIZE // (1024*1024)))
                return

            # Validate file extension
            file_ext = file.name.split('.')[-1].lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                self.show_error_dialog(t('invalid_file_type').format(', '.join(ALLOWED_EXTENSIONS)))
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
                self.show_error_dialog(t('error_uploading_image').format(str(ex)))
    
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
            title=ft.Text(t('question_image_title'), size=18, weight=ft.FontWeight.BOLD),
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
                    t('close'),
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

    def edit_selected_exam(self, e):
        """Edit the currently selected exam/topic"""
        if not self.selected_exam_id:
            return

        # Find the selected exam data
        exam_data = next((exam for exam in self.exams_data if exam['id'] == self.selected_exam_id), None)

        if exam_data:
            self.show_exam_dialog(exam_data)

    def show_exam_dialog(self, exam=None):
        """Create or edit exam template dialog"""
        is_edit = exam is not None
        title = t('edit_topic') if is_edit else t('create_exam')

        # Form fields - Only basic topic information
        exam_title_field = ft.TextField(
            label=t('title') + " *",
            value=exam.get('title', '') if is_edit else "",
            content_padding=8,
            hint_text=t('enter_descriptive_title'),
            width=600
        )

        description_field = ft.TextField(
            label=t('description'),
            value=exam.get('description', '') if is_edit else "",
            multiline=True,
            min_lines=3,
            max_lines=6,
            content_padding=8,
            hint_text=t('provide_instructions'),
            width=600
        )

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_exam(e):
            # Validate required fields
            if not exam_title_field.value.strip():
                error_text.value = t('exam_title_required')
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
                        exam.get('id')
                    )
                    self.db.execute_update(query, params)
                else:
                    # Create new exam with default values
                    from datetime import datetime
                    user_id = self.user_data.get('id', 1) if self.user_data else 1
                    query = """
                        INSERT INTO exams (
                            title, description, created_by, created_at,
                            duration_minutes, passing_score,
                            max_attempts, randomize_questions, show_results
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    params = (
                        exam_title_field.value.strip(),
                        description_field.value.strip() or None,
                        user_id,
                        datetime.now().isoformat(),
                        60,  # Default 60 minutes
                        70.0,  # Default 70% passing score
                        3,  # Default 3 attempts
                        0,  # Don't randomize by default
                        1   # Show results by default
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
                    ft.Container(height=10),
                    error_text
                ], spacing=15, tight=True),
                width=600,
                height=300
            ),
            actions=[
                ft.TextButton(t('cancel'), on_click=close_dialog),
                ft.ElevatedButton(
                    t('save') if is_edit else t('create'),
                    on_click=save_exam,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = self.exam_dialog
        self.exam_dialog.open = True
        self.page.update()

    def show_delete_topic_dialog(self, e):
        """Show confirmation dialog to delete the selected topic/exam"""
        if not self.selected_exam_id:
            self.show_error_dialog(t('please_select_exam'))
            return

        selected_exam = self.get_selected_exam()
        if not selected_exam:
            self.show_error_dialog(t('please_select_exam'))
            return

        # Check permissions - only admin or topic owner can delete
        if self.user_data.get('role') != 'admin' and selected_exam.get('created_by') != self.user_data.get('id'):
            self.show_error_dialog(t('no_permission_delete_topic'))
            return

        # Check if there are questions associated with this topic
        questions_count = self.db.execute_query(
            "SELECT COUNT(*) as count FROM questions WHERE exam_id = ?",
            (self.selected_exam_id,)
        )
        question_count = questions_count[0]['count'] if questions_count else 0

        # Check if this topic is used in any presets
        preset_usage = self.db.execute_query("""
            SELECT DISTINCT ept.id, ept.name
            FROM exam_preset_templates ept
            INNER JOIN preset_template_exams pte ON ept.id = pte.template_id
            WHERE pte.exam_id = ?
            ORDER BY ept.name
        """, (self.selected_exam_id,))

        # Build warning message
        warning_message = t('delete_topic_confirmation').format(title=selected_exam['title'])

        # Add question count warning
        if question_count > 0:
            warning_message += f"\n\n{t('delete_topic_warning_questions').format(count=question_count)}"

        # Add preset warning
        if preset_usage:
            preset_count = len(preset_usage)
            warning_message += f"\n\n{t('delete_topic_warning_presets').format(count=preset_count)}"
            for preset in preset_usage:
                warning_message += f"\n  • {preset['name']}"
            warning_message += f"\n\n{t('delete_topic_preset_impact')}"

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def confirm_delete(ev):
            try:
                # Delete all associated image files from questions in this exam (before deleting DB records)
                questions_with_images = self.db.execute_query(
                    "SELECT image_path FROM questions WHERE exam_id = ? AND image_path IS NOT NULL",
                    (self.selected_exam_id,)
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

                # Delete all related data in the correct order (due to foreign keys)
                # 1. Delete user answers
                self.db.execute_update("""
                    DELETE FROM user_answers
                    WHERE session_id IN (
                        SELECT id FROM exam_sessions WHERE exam_id = ?
                    )
                """, (self.selected_exam_id,))

                # 2. Delete exam sessions
                self.db.execute_update(
                    "DELETE FROM exam_sessions WHERE exam_id = ?",
                    (self.selected_exam_id,)
                )

                # 3. Delete exam permissions
                self.db.execute_update(
                    "DELETE FROM exam_permissions WHERE exam_id = ?",
                    (self.selected_exam_id,)
                )

                # 4. Delete question options
                self.db.execute_update("""
                    DELETE FROM question_options
                    WHERE question_id IN (
                        SELECT id FROM questions WHERE exam_id = ?
                    )
                """, (self.selected_exam_id,))

                # 5. Delete questions
                self.db.execute_update(
                    "DELETE FROM questions WHERE exam_id = ?",
                    (self.selected_exam_id,)
                )

                # 6. Delete exam observers
                self.db.execute_update(
                    "DELETE FROM exam_observers WHERE exam_id = ?",
                    (self.selected_exam_id,)
                )

                # 7. Finally, delete the exam itself
                self.db.execute_update(
                    "DELETE FROM exams WHERE id = ?",
                    (self.selected_exam_id,)
                )

                # Close dialog
                self.delete_topic_dialog.open = False
                if self.page:
                    self.page.update()

                # Reset selection
                self.selected_exam_id = None

                # Reload exams and refresh UI
                self.load_exams()
                self.exam_selector.options = [
                    ft.dropdown.Option(str(exam['id']), exam['title'])
                    for exam in self.exams_data
                ]
                self.exam_selector.value = None
                self.questions_data = []
                self.update_table()
                self.hide_question_pool_stats()
                self.update_observers_button_state()
                self.update_add_question_button_state()
                self.update_import_export_buttons_state()

                if self.page:
                    self.update()

            except Exception as ex:
                error_text.value = f"{t('error_deleting_topic')}: {str(ex)}"
                error_text.visible = True
                self.delete_topic_dialog.update()

        def cancel_delete(ev):
            self.delete_topic_dialog.open = False
            self.page.update()

        self.delete_topic_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.WARNING_AMBER_ROUNDED, color=COLORS['error'], size=30),
                ft.Text(t('delete_topic'), size=20, weight=ft.FontWeight.BOLD)
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(warning_message, size=14),
                    ft.Container(height=10),
                    error_text
                ], spacing=10, tight=True),
                width=500
            ),
            actions=[
                ft.TextButton(t('cancel'), on_click=cancel_delete),
                ft.ElevatedButton(
                    t('delete'),
                    on_click=confirm_delete,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS['error'],
                        color=ft.colors.WHITE
                    ),
                    icon=ft.icons.DELETE_FOREVER
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = self.delete_topic_dialog
        self.delete_topic_dialog.open = True
        self.page.update()

    def show_observers_dialog(self, e):
        """Display dialog for managing topic observers"""
        if not self.selected_exam_id:
            self.show_error_dialog(t('please_select_exam'))
            return

        selected_exam = self.get_selected_exam()
        if not selected_exam:
            self.show_error_dialog(t('please_select_exam'))
            return

        # Only admins or topic owners can manage observers
        if self.user_data.get('role') != 'admin' and selected_exam.get('created_by') != self.user_data.get('id'):
            self.show_error_dialog(t('observer_manage_forbidden'))
            return

        self.current_observers = self.load_exam_observers(self.selected_exam_id)
        self.observer_candidates = self.load_observer_candidates(selected_exam.get('created_by'))
        self.observer_dropdown = ft.Dropdown(
            label=t('select_observer'),
            width=500
        )
        self.observers_message_text = ft.Text("", visible=False, color=COLORS['error'])
        add_button = ft.ElevatedButton(
            text=t('add_observer'),
            icon=ft.icons.PERSON_ADD_ALT_1,
            on_click=self.handle_add_observer,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )
        self.observers_list_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        self.update_observers_dropdown()
        self.populate_observers_list()

        info_text = ft.Text(
            t('observer_instructions'),
            color=COLORS['text_secondary'],
            size=13
        )

        dialog_content = ft.Container(
            content=ft.Column([
                info_text,
                ft.Row(
                    controls=[self.observer_dropdown, add_button],
                    spacing=10,
                    wrap=True
                ),
                self.observers_message_text,
                ft.Divider(),
                ft.Text(t('current_observers'), size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.observers_list_column,
                    bgcolor=COLORS['surface'],
                    padding=ft.padding.all(10),
                    border_radius=8,
                    width=750,
                    height=300
                )
            ], spacing=12),
            width=750,
            height=480
        )

        def close_dialog(ev):
            self.observers_dialog.open = False
            self.page.update()

        self.observers_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t('manage_observers'), size=20, weight=ft.FontWeight.BOLD),
            content=dialog_content,
            actions=[
                ft.TextButton(t('close'), on_click=close_dialog)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = self.observers_dialog
        self.observers_dialog.open = True
        self.page.update()

    def load_exam_observers(self, exam_id):
        """Load observers for a given exam"""
        try:
            return self.db.execute_query("""
                SELECT eo.observer_id, eo.granted_at, u.full_name, u.department, u.unit, u.email
                FROM exam_observers eo
                JOIN users u ON eo.observer_id = u.id
                WHERE eo.exam_id = ?
                ORDER BY u.full_name
            """, (exam_id,))
        except Exception as ex:
            print(f"Error loading observers: {ex}")
            return []

    def load_observer_candidates(self, owner_id):
        """Load eligible expert observers except the topic owner"""
        owner_id = owner_id or -1
        try:
            return self.db.execute_query("""
                SELECT id, full_name, department, unit
                FROM users
                WHERE role = 'expert' AND is_active = 1 AND id != ?
                ORDER BY full_name
            """, (owner_id,))
        except Exception as ex:
            print(f"Error loading observer candidates: {ex}")
            return []

    def get_dept_unit_abbreviation(self, dept_or_unit_name):
        """Get abbreviation for department or unit from config ORGANIZATIONAL_STRUCTURE"""
        if not dept_or_unit_name:
            return ''

        from quiz_app.config import ORGANIZATIONAL_STRUCTURE
        from quiz_app.utils.localization import get_language

        current_lang = get_language()
        abbr_key = f'abbr_{current_lang}'

        # Try both language keys since database might have either Az or En names
        for lang in ['az', 'en']:
            lang_key = f'name_{lang}'

            # Search in departments
            for dept_key, dept_data in ORGANIZATIONAL_STRUCTURE.items():
                # Check if it's a department match
                if dept_data.get(lang_key) == dept_or_unit_name:
                    return dept_data.get(abbr_key, dept_or_unit_name)

                # Check in sections
                for section_key, section_data in dept_data.get('sections', {}).items():
                    if section_data.get(lang_key) == dept_or_unit_name:
                        return section_data.get(abbr_key, dept_or_unit_name)

                    # Check in units under sections
                    for unit in section_data.get('units', []):
                        if unit.get(lang_key) == dept_or_unit_name:
                            return unit.get(abbr_key, dept_or_unit_name)

                # Check in direct units under department
                for unit in dept_data.get('units', []):
                    if unit.get(lang_key) == dept_or_unit_name:
                        return unit.get(abbr_key, dept_or_unit_name)

        # If not found in config, return original name
        return dept_or_unit_name

    def update_observers_dropdown(self):
        """Refresh dropdown options with available observers"""
        if not self.observer_dropdown:
            return

        assigned_ids = {observer['observer_id'] for observer in self.current_observers}
        options = []
        for candidate in self.observer_candidates:
            if candidate['id'] in assigned_ids:
                continue

            dept = self.get_dept_unit_abbreviation(candidate.get('department') or '')
            unit = self.get_dept_unit_abbreviation(candidate.get('unit') or '')
            descriptor = ""
            if dept or unit:
                parts = [part for part in [dept, unit] if part]
                descriptor = f" ({' / '.join(parts)})"

            label = f"{candidate['full_name']}{descriptor}"
            options.append(ft.dropdown.Option(str(candidate['id']), label))

        self.observer_dropdown.options = options

        if not options:
            self.observer_dropdown.value = None
            self.observer_dropdown.disabled = True
        else:
            self.observer_dropdown.disabled = False

        # Control may not be mounted yet when dialog is being assembled,
        # so only call update when it is already part of the page tree.
        if self.page and getattr(self.observer_dropdown, 'page', None):
            self.observer_dropdown.update()

    def populate_observers_list(self):
        """Render the list of observers inside the dialog"""
        if not self.observers_list_column:
            return

        self.observers_list_column.controls = []

        if not self.current_observers:
            self.observers_list_column.controls.append(
                ft.Text(
                    t('no_observers_assigned'),
                    color=COLORS['text_secondary'],
                    italic=True
                )
            )
        else:
            for observer in self.current_observers:
                dept = self.get_dept_unit_abbreviation(observer.get('department') or '')
                unit = self.get_dept_unit_abbreviation(observer.get('unit') or '')
                dept_unit = ' / '.join([val for val in [dept, unit] if val]) or '-'

                observer_row = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.BADGE, color=COLORS['primary'], size=20),
                        ft.Column([
                            ft.Text(observer['full_name'], weight=ft.FontWeight.BOLD),
                            ft.Text(dept_unit, color=COLORS['text_secondary'], size=12)
                        ], tight=True, expand=True),
                        ft.IconButton(
                            icon=ft.icons.DELETE_OUTLINE,
                            icon_color=COLORS['error'],
                            tooltip=t('delete'),
                            on_click=lambda ev, obs_id=observer['observer_id']: self.handle_remove_observer(obs_id)
                        )
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    bgcolor=ft.colors.with_opacity(0.04, COLORS['primary']),
                    border_radius=6
                )
                self.observers_list_column.controls.append(observer_row)

        if self.page and getattr(self.observers_list_column, 'page', None):
            self.observers_list_column.update()

    def handle_add_observer(self, e):
        """Handle adding a new observer"""
        if not self.selected_exam_id or not self.observer_dropdown:
            return

        if not self.observer_dropdown.value:
            self.show_observers_message(t('observer_select_prompt'))
            return

        observer_id = int(self.observer_dropdown.value)
        status, error = self.add_exam_observer_record(self.selected_exam_id, observer_id)

        if status == 'success':
            self.observer_dropdown.value = None
            if self.page:
                self.observer_dropdown.update()
            self.show_observers_message(t('observer_added'), success=True)
        elif status == 'duplicate':
            self.show_observers_message(t('observer_already_assigned'))
        else:
            message = t('error')
            if error:
                message = f"{t('error')}: {error}"
            self.show_observers_message(message)
            return

        self.reload_observer_state()

    def handle_remove_observer(self, observer_id):
        """Remove observer access"""
        if not self.selected_exam_id:
            return

        status, error = self.remove_exam_observer_record(self.selected_exam_id, observer_id)

        if status:
            self.show_observers_message(t('observer_removed'), success=True)
            self.reload_observer_state()
        else:
            message = t('error')
            if error:
                message = f"{t('error')}: {error}"
            self.show_observers_message(message)

    def add_exam_observer_record(self, exam_id, observer_id):
        """Persist observer assignment"""
        try:
            existing = self.db.execute_single("""
                SELECT id FROM exam_observers
                WHERE exam_id = ? AND observer_id = ?
            """, (exam_id, observer_id))

            if existing:
                return 'duplicate', None

            granted_by = self.user_data.get('id')
            self.db.execute_insert("""
                INSERT INTO exam_observers (exam_id, observer_id, granted_by)
                VALUES (?, ?, ?)
            """, (exam_id, observer_id, granted_by))

            return 'success', None
        except Exception as ex:
            print(f"Error saving observer: {ex}")
            return 'error', str(ex)

    def remove_exam_observer_record(self, exam_id, observer_id):
        """Delete observer assignment"""
        try:
            self.db.execute_update("""
                DELETE FROM exam_observers
                WHERE exam_id = ? AND observer_id = ?
            """, (exam_id, observer_id))
            return True, None
        except Exception as ex:
            print(f"Error removing observer: {ex}")
            return False, str(ex)

    def reload_observer_state(self):
        """Reload dropdown options and list after changes"""
        if not self.selected_exam_id:
            return

        selected_exam = self.get_selected_exam()
        owner_id = selected_exam.get('created_by') if selected_exam else None
        self.current_observers = self.load_exam_observers(self.selected_exam_id)
        self.observer_candidates = self.load_observer_candidates(owner_id)
        self.update_observers_dropdown()
        self.populate_observers_list()
        if self.page and self.observers_dialog:
            self.observers_dialog.update()

    def show_observers_message(self, message, success=False):
        """Display inline feedback inside the observers dialog"""
        if not self.observers_message_text:
            return

        self.observers_message_text.value = message
        self.observers_message_text.color = COLORS['success'] if success else COLORS['error']
        self.observers_message_text.visible = True

        if self.page:
            self.observers_message_text.update()
