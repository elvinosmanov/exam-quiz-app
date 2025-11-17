import flet as ft
import random
import json
import os
from datetime import datetime, timedelta, date
from quiz_app.config import COLORS
from quiz_app.utils.permissions import UnitPermissionManager
from quiz_app.utils.localization import t, get_language

class QuizManagement(ft.UserControl):
    def __init__(self, db, user_data):
        super().__init__()
        self.db = db
        self.user_data = user_data
        self.exams_data = []
        self.all_exams_data = []  # Keep original data for filtering
        self.selected_exam = None

        # Initialize file picker for PDF downloads
        self.file_picker = ft.FilePicker(on_result=self.on_file_picker_result)
        self.pending_pdf_data = None  # Store PDF data temporarily
        self.pending_exam_pdfs = []  # Queue for multiple exam PDFs

        # Create temp directory for PDFs
        import tempfile
        self.temp_dir = tempfile.mkdtemp(prefix="exam_exports_")

        # Load default settings
        self.default_passing_score = self.get_setting('passing_score', '70')
        self.default_exam_duration = self.get_setting('default_exam_duration', '60')

        # Search control
        self.search_field = ft.TextField(
            label=t('search_exams'),
            prefix_icon=ft.icons.SEARCH,
            on_change=self.apply_filters,
            expand=True
        )

        # Status filter
        self.status_filter = ft.Dropdown(
            label=t('filter_by_status'),
            options=[
                ft.dropdown.Option("all", t('all')),
                ft.dropdown.Option("active", t('active')),
                ft.dropdown.Option("inactive", t('inactive')),
                ft.dropdown.Option("scheduled", t('scheduled'))
            ],
            value="all",
            on_change=self.apply_filters,
            width=200
        )

        # Assignments table
        self.exams_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t('assignment'))),
                ft.DataColumn(ft.Text(t('duration'))),
                ft.DataColumn(ft.Text("Passing Score")),
                ft.DataColumn(ft.Text(t('type'))),
                ft.DataColumn(ft.Text(t('questions'))),
                ft.DataColumn(ft.Text(t('completion'))),
                ft.DataColumn(ft.Text("Deadline")),
                ft.DataColumn(ft.Text(t('actions')))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )

        # Action buttons
        self.add_exam_btn = ft.ElevatedButton(
            text=t('create_exam'),
            icon=ft.icons.ADD,
            on_click=self.show_add_exam_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )

        # Dialog for adding/editing exams
        self.exam_dialog = None

    def get_setting(self, key, default_value):
        """Get a setting value from system_settings table"""
        try:
            result = self.db.execute_query(
                "SELECT setting_value FROM system_settings WHERE setting_key = ?",
                (key,)
            )
            if result:
                return result[0]['setting_value']
        except Exception as e:
            print(f"[DEBUG] Failed to load setting {key}: {e}")
        return default_value
    
    def did_mount(self):
        """Called after the control is added to the page"""
        super().did_mount()
        # Add file picker to overlay
        if self.page and hasattr(self.page, 'overlay'):
            self.page.overlay.append(self.file_picker)
            self.page.update()
        self.load_exams()

    def will_unmount(self):
        """Called before the control is removed from the page"""
        super().will_unmount()
        # Clean up temp directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
            except Exception as ex:
                print(f"Error cleaning up temp directory: {ex}")

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle file picker result"""
        if e.path and self.pending_pdf_data:
            try:
                # Save the PDF to the selected location
                import shutil
                shutil.move(self.pending_pdf_data['temp_path'], e.path)
                self.show_message(t('success'), f"{t('file_saved')}: {e.path}")
            except Exception as ex:
                self.show_message(t('error'), f"{t('file_save_error')}: {str(ex)}")
                # Try to clean up temp file on error
                if os.path.exists(self.pending_pdf_data['temp_path']):
                    try:
                        os.remove(self.pending_pdf_data['temp_path'])
                    except:
                        pass
            finally:
                self.pending_pdf_data = None
                # Check if there are more exam PDFs to save
                if hasattr(self, 'pending_exam_pdfs') and self.pending_exam_pdfs:
                    self.save_next_exam_pdf()

    def save_pdf_with_picker(self, temp_filepath, suggested_filename):
        """Show file picker to save PDF"""
        try:
            self.pending_pdf_data = {
                'temp_path': temp_filepath,
                'suggested_name': suggested_filename
            }
            self.file_picker.save_file(
                dialog_title=t('save_pdf_as'),
                file_name=suggested_filename,
                allowed_extensions=["pdf"]
            )
        except Exception as ex:
            self.show_message(t('error'), f"{t('file_save_error')}: {str(ex)}")

    def save_next_exam_pdf(self):
        """Save the next PDF in the queue"""
        if not hasattr(self, 'pending_exam_pdfs') or not self.pending_exam_pdfs:
            return

        # Get the next PDF to save
        pdf_info = self.pending_exam_pdfs.pop(0)
        self.save_pdf_with_picker(pdf_info['path'], pdf_info['default_name'])

    def export_assignment_as_pdf(self, assignment):
        """Show dialog to export assignment as PDF using configured variant count"""
        from quiz_app.utils.pdf_generator import ExamPDFGenerator

        # Check if assignment has randomization enabled
        has_randomize = bool(assignment.get('randomize_questions'))
        num_variants = assignment.get('pdf_variant_count') or 1
        try:
            num_variants = max(1, int(num_variants))
        except (TypeError, ValueError):
            num_variants = 1

        # Warning if no randomization
        warning = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.WARNING, color=COLORS['warning'], size=16),
                ft.Text(
                    t('randomization_disabled'),
                    size=11,
                    color=COLORS['warning']
                )
            ], spacing=5),
            visible=(not has_randomize and num_variants > 1),
            padding=8,
            bgcolor=ft.colors.with_opacity(0.05, COLORS['warning']),
            border_radius=6
        )

        def generate_pdfs(e):
            try:
                # Show progress
                export_dialog.content = ft.Container(
                    content=ft.Column([
                        ft.ProgressRing(),
                        ft.Text(t('generating_variants').format(num_variants), size=14)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=20
                )
                export_dialog.actions = []
                self.page.update()

                pdf_gen = ExamPDFGenerator(self.db)
                generated_files = []

                # Check if this is a multi-template assignment
                templates = self.db.execute_query("""
                    SELECT COUNT(*) as count FROM assignment_exam_templates
                    WHERE assignment_id = ?
                """, (assignment['id'],))
                is_multi_template = templates and templates[0]['count'] > 0

                # For multi-template assignments, always use assignment_id for caching
                # For single-template assignments, use exam_id for backward compatibility
                export_exam_id = assignment['id'] if is_multi_template else (assignment.get('exam_id') or assignment['id'])

                # Check if a master snapshot already exists for this assignment
                existing_snapshot = self.db.execute_single(
                    """SELECT question_snapshot FROM pdf_exports
                       WHERE exam_id = ? AND variant_number = 1""",
                    (export_exam_id,)
                )

                # Use existing snapshot or create new one (only once)
                if existing_snapshot and existing_snapshot['question_snapshot']:
                    print(f"[PDF] Using existing snapshot for assignment {assignment['id']}")
                    master_snapshot = json.loads(existing_snapshot['question_snapshot'])
                else:
                    print(f"[PDF] Creating new snapshot for assignment {assignment['id']}")
                    # Create snapshot WITHOUT randomization to get base question set
                    master_snapshot = pdf_gen.create_question_snapshot(assignment['id'], randomize=False)

                for variant in range(1, num_variants + 1):
                    # Use the same master snapshot but shuffle for each variant if randomization is enabled
                    if has_randomize and variant > 1:
                        # Shuffle questions within each topic for variants 2+
                        variant_snapshot = []
                        for topic_data in master_snapshot:
                            shuffled_questions = topic_data['questions'].copy()
                            random.shuffle(shuffled_questions)
                            variant_snapshot.append({
                                'topic_id': topic_data['topic_id'],
                                'topic_title': topic_data['topic_title'],
                                'questions': shuffled_questions
                            })
                    else:
                        # Variant 1 or no randomization - use master snapshot as-is
                        variant_snapshot = master_snapshot

                    # Generate file paths
                    exam_id = pdf_gen.generate_instance_id(assignment['id'], variant)
                    paper_path = os.path.join(self.temp_dir, f"{exam_id}_paper.pdf")
                    answers_path = os.path.join(self.temp_dir, f"{exam_id}_answers.pdf")

                    # Generate PDFs
                    pdf_gen.generate_exam_paper(assignment, variant_snapshot, variant, paper_path)
                    pdf_gen.generate_answer_key(assignment, variant_snapshot, variant, answers_path)

                    # Save snapshot to database (master snapshot for variant 1, variant snapshots for others)
                    snapshot_to_save = master_snapshot if variant == 1 else variant_snapshot
                    self.db.execute_insert(
                        """INSERT INTO pdf_exports (exam_id, variant_number, question_snapshot, exported_by, file_path)
                           VALUES (?, ?, ?, ?, ?)
                           ON CONFLICT(exam_id, variant_number)
                           DO UPDATE SET
                               exported_by=excluded.exported_by,
                               exported_at=CURRENT_TIMESTAMP,
                               file_path=excluded.file_path
                        """,
                        (export_exam_id, variant, json.dumps(snapshot_to_save), self.user_data['id'], paper_path)
                    )

                    generated_files.append({'exam_id': exam_id, 'paper': paper_path, 'answers': answers_path})

                # Show success
                self.show_pdf_success_dialog(generated_files)
                export_dialog.open = False
                self.page.update()

            except Exception as ex:
                # Show error
                export_dialog.content = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.ERROR, color=COLORS['error'], size=48),
                        ft.Text(t('error_generating_pdfs'), size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(str(ex), size=12, color=COLORS['error'])
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=20
                )
                export_dialog.actions = [ft.TextButton(t('close'), on_click=lambda e: self.close_export_dialog(export_dialog))]
                self.page.update()

        export_dialog = ft.AlertDialog(
            title=ft.Text(t('export_assignment_as_pdf')),
            content=ft.Column([
                ft.Text(f"{t('assignment')}: {assignment['assignment_name']}", weight=ft.FontWeight.BOLD),
                ft.Text(
                    f"{t('questions')}: "
                    + (
                        f"{assignment['question_count']} "
                        if not assignment.get('question_bank_count')
                        or assignment['question_bank_count'] == assignment['question_count']
                        else f"{assignment['question_count']} ({t('of')} {assignment['question_bank_count']})"
                    ),
                    size=12,
                    color=COLORS['text_secondary']
                ),
                ft.Divider(),
                ft.Text(
                    f"{t('variants_configured')}: {num_variants}",
                    size=12,
                    weight=ft.FontWeight.BOLD
                ),
                warning,
                ft.Container(height=10),
                ft.Text(t('this_will_generate'), size=13, weight=ft.FontWeight.BOLD),
                ft.Text("• " + t('exam_paper_each_variant'), size=12),
                ft.Text("• " + t('answer_key_each_variant'), size=12),
                ft.Container(height=5),
                ft.Text(f"📁 {t('files')}: EXAM-XXXXXX-VX_paper.pdf, etc.",
                       size=11, italic=True, color=COLORS['text_secondary'])
            ], tight=True, spacing=5, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton(t('cancel'), on_click=lambda e: self.close_export_dialog(export_dialog)),
                ft.ElevatedButton(
                    t('generate_pdfs'),
                    on_click=generate_pdfs,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = export_dialog
        export_dialog.open = True
        self.page.update()

    def close_export_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def show_pdf_success_dialog(self, generated_files):
        """Queue PDFs for saving via file picker"""
        # Store all generated files for sequential saving
        self.pending_exam_pdfs = []
        for file_info in generated_files:
            variant_num = file_info['exam_id'].split('-V')[1]
            self.pending_exam_pdfs.append({
                'path': file_info['paper'],
                'default_name': f"exam_paper_variant_{variant_num}.pdf"
            })
            self.pending_exam_pdfs.append({
                'path': file_info['answers'],
                'default_name': f"answer_key_variant_{variant_num}.pdf"
            })

        # Start saving the first PDF
        self.save_next_exam_pdf()

    def build(self):
        # Create Assignment button
        self.add_assignment_btn = ft.ElevatedButton(
            t('create_assignment'),
            icon=ft.icons.ASSIGNMENT_ADD,
            on_click=self.show_add_assignment_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
        )

        # Create Preset Template button
        self.add_preset_btn = ft.ElevatedButton(
            t('create_preset_template'),
            icon=ft.icons.BOOKMARK_ADD,
            on_click=self.show_create_preset_dialog,
            style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
        )

        # Manage Presets button
        self.manage_presets_btn = ft.OutlinedButton(
            t('manage_presets'),
            icon=ft.icons.BOOKMARKS,
            on_click=self.show_manage_presets_dialog,
        )

        # View Archived button
        self.view_archived_btn = ft.OutlinedButton(
            t('view_archived'),
            icon=ft.icons.ARCHIVE,
            on_click=self.show_archived_assignments_dialog,
        )

        return ft.Column([
            # Header
            ft.Row([
                ft.Text(t('assignment_management'), size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(expand=True),
                self.view_archived_btn,
                ft.Container(width=10),
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
        # Apply unit-level filtering for experts
        perm_manager = UnitPermissionManager(self.db)
        filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data, table_alias='ea')

        # Build query with unit filtering
        query = """
            WITH template_counts AS (
                SELECT
                    assignment_id,
                    SUM(COALESCE(easy_count, 0)) AS total_easy,
                    SUM(COALESCE(medium_count, 0)) AS total_medium,
                    SUM(COALESCE(hard_count, 0)) AS total_hard,
                    SUM(COALESCE(easy_count, 0) + COALESCE(medium_count, 0) + COALESCE(hard_count, 0)) AS total_selected
                FROM assignment_exam_templates
                GROUP BY assignment_id
            )
            SELECT ea.*,
                   e.title as exam_title,
                   e.description as exam_description,
                   COUNT(DISTINCT q.id) as question_bank_count,
                   COALESCE(tc.total_selected,
                            NULLIF(ea.easy_questions_count + ea.medium_questions_count + ea.hard_questions_count, 0),
                            COUNT(DISTINCT q.id)) as question_count,
                   COALESCE(tc.total_easy, ea.easy_questions_count) as selected_easy_count,
                   COALESCE(tc.total_medium, ea.medium_questions_count) as selected_medium_count,
                   COALESCE(tc.total_hard, ea.hard_questions_count) as selected_hard_count,
                   COUNT(DISTINCT au.user_id) as assigned_users_count,
                   COUNT(DISTINCT CASE WHEN es.is_completed = 1 THEN au.user_id END) as completed_users_count,
                   u.full_name as creator_name,
                   u.department as creator_department,
                   u.unit as creator_unit
            FROM exam_assignments ea
            JOIN exams e ON ea.exam_id = e.id
            LEFT JOIN template_counts tc ON tc.assignment_id = ea.id
            LEFT JOIN questions q ON e.id = q.exam_id AND q.is_active = 1
            LEFT JOIN assignment_users au ON ea.id = au.assignment_id AND au.is_active = 1
            LEFT JOIN exam_sessions es ON au.user_id = es.user_id AND e.id = es.exam_id
            LEFT JOIN users u ON ea.created_by = u.id
            WHERE ea.is_archived = 0 {filter_clause}
            GROUP BY ea.id
            ORDER BY ea.created_at DESC
        """.format(filter_clause=filter_clause)

        # Load assignments with unit filtering
        self.all_exams_data = self.db.execute_query(query, tuple(filter_params))
        self.exams_data = self.all_exams_data.copy()
        self.apply_filters(None)
    
    def update_table(self):
        self.exams_table.rows.clear()
        perm_manager = UnitPermissionManager(self.db)

        for idx, assignment in enumerate(self.exams_data, 1):
            # Create enhanced status badges
            status_badges = self.calculate_exam_status_badges(assignment)

            # Display assignment name with creator badge
            assignment_title_controls = [ft.Text(assignment['assignment_name'])]

            # Add creator badge for experts
            if assignment.get('creator_name'):
                creator_text = assignment['creator_name']
                if assignment.get('creator_unit'):
                    creator_text += f" ({assignment['creator_unit']})"

                assignment_title_controls.append(
                    ft.Container(
                        content=ft.Text(
                            creator_text,
                            size=10,
                            color=ft.colors.WHITE,
                            weight=ft.FontWeight.BOLD
                        ),
                        bgcolor=ft.colors.BLUE_400,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4,
                        margin=ft.margin.only(left=8)
                    )
                )

            # Format completion as "completed/total"
            completed_count = assignment['completed_users_count'] or 0
            total_count = assignment['assigned_users_count'] or 0
            completion_text = f"{completed_count}/{total_count}"

            # Delivery type badge
            delivery_type = assignment.get('delivery_method', 'online')
            type_badge = ft.Container(
                content=ft.Text(
                    "Online" if delivery_type == 'online' else "PDF",
                    size=11,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.WHITE
                ),
                bgcolor=COLORS['primary'] if delivery_type == 'online' else ft.colors.ORANGE,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=4
            )

            # Check if user can edit this content
            can_edit = perm_manager.can_edit_content(assignment['created_by'], self.user_data)

            # Action buttons - conditionally show edit/delete for experts
            action_buttons = []

            # Edit button - only if user can edit
            if can_edit:
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.icons.EDIT,
                        tooltip=t('edit'),
                        on_click=lambda e, ex=assignment: self.show_edit_assignment_dialog(ex)
                    )
                )

            # PDF export - available to all
            action_buttons.append(
                ft.IconButton(
                    icon=ft.icons.PICTURE_AS_PDF,
                    tooltip=t('export_pdf'),
                    on_click=lambda e, ex=assignment: self.export_assignment_as_pdf(ex),
                    icon_color=ft.colors.RED_400
                )
            )

            # Toggle status - only if user can edit
            if can_edit:
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.icons.TOGGLE_ON if assignment['is_active'] else ft.icons.TOGGLE_OFF,
                        tooltip=t('inactive') if assignment['is_active'] else t('active'),
                        on_click=lambda e, ex=assignment: self.toggle_assignment_status(ex),
                        icon_color=COLORS['success'] if assignment['is_active'] else COLORS['error']
                    )
                )

            # Delete button - only if user can edit
            if can_edit:
                action_buttons.append(
                    ft.IconButton(
                        icon=ft.icons.DELETE,
                        tooltip=t('delete'),
                        on_click=lambda e, ex=assignment: self.delete_assignment(ex),
                        icon_color=COLORS['error']
                    )
                )

            self.exams_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(idx))),
                        ft.DataCell(ft.Row(assignment_title_controls, spacing=5)),
                        ft.DataCell(ft.Text(f"{assignment['duration_minutes']} min")),
                        ft.DataCell(ft.Text(f"{assignment['passing_score']}%")),
                        ft.DataCell(type_badge),
                        ft.DataCell(ft.Text(
                            f"{assignment['question_count'] or 0}"
                            + (
                                f" / {assignment['question_bank_count']}"
                                if assignment.get('question_bank_count')
                                and assignment['question_bank_count'] != assignment['question_count']
                                else ""
                            )
                        )),
                        ft.DataCell(ft.Text(completion_text)),
                        ft.DataCell(ft.Text(assignment.get('deadline')[:10] if assignment.get('deadline') else "No deadline")),
                        ft.DataCell(ft.Row(action_buttons, spacing=5))
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
        title = "Edit Topic" if is_edit else t('create_exam')

        # Form fields - Only basic topic information
        exam_title_field = ft.TextField(
            label=t('title') + " *",
            value=exam['title'] if is_edit else "",
            content_padding=8,
            hint_text="e.g., Python Programming, Safety Training",
            width=600
        )

        description_field = ft.TextField(
            label=t('description'),
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
                    # Create new exam with required default values
                    from datetime import datetime
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
                        self.user_data['id'],
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
                ft.Radio(value="preset", label=t('use_preset_template')),
                ft.Radio(value="manual", label=t('select_exam_templates_manually'))
            ]),
            value="manual" if not preset_templates else "preset"
        )

        # Track selected exam templates
        self.selected_exam_templates = []
        self.selected_preset_id = None

        # Preset template dropdown
        preset_dropdown = ft.Dropdown(
            label=t('select_preset'),
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
            label=t('select_exam_templates'),
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
                ft.TextButton(t('cancel'), on_click=close_dialog),
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

        # If in edit mode and pool_configs not provided, load from exams data
        # (exams parameter contains easy_count, medium_count, hard_count from database)
        if is_edit and pool_configs is None and exams:
            # Check if any template has pool counts configured
            has_pool_config = any(
                (exam.get('easy_count', 0) or 0) > 0 or
                (exam.get('medium_count', 0) or 0) > 0 or
                (exam.get('hard_count', 0) or 0) > 0
                for exam in exams
            )

            if has_pool_config:
                # Create TextField controls with existing values for editing
                pool_configs = {}
                for exam in exams:
                    pool_configs[exam['id']] = {
                        'easy': ft.TextField(
                            label=t('easy'),
                            value=str(exam.get('easy_count', 0) or 0),
                            keyboard_type=ft.KeyboardType.NUMBER,
                            width=80,
                            content_padding=8
                        ),
                        'medium': ft.TextField(
                            label=t('medium'),
                            value=str(exam.get('medium_count', 0) or 0),
                            keyboard_type=ft.KeyboardType.NUMBER,
                            width=80,
                            content_padding=8
                        ),
                        'hard': ft.TextField(
                            label=t('hard'),
                            value=str(exam.get('hard_count', 0) or 0),
                            keyboard_type=ft.KeyboardType.NUMBER,
                            width=80,
                            content_padding=8
                        )
                    }

        # Calculate total question count from pool configs if provided, otherwise use all questions
        if pool_configs:
            total_questions = sum(
                int(config['easy'].value or 0) + int(config['medium'].value or 0) + int(config['hard'].value or 0)
                for config in pool_configs.values()
            )
        else:
            # For non-pool assignments, sum question_count if available
            total_questions = sum(exam.get('question_count', 0) for exam in exams)

        exam_titles = ", ".join([exam['title'] for exam in exams])

        # Assignment name
        assignment_name_field = ft.TextField(
            label=t('assignment_name') + " *",
            value=assignment['assignment_name'] if is_edit else f"Combined Exam - {datetime.now().strftime('%Y-%m-%d')}",
            content_padding=5,
            hint_text="e.g., Midterm Exam - All Subjects",
            expand=True
        )

        # Show selected exam templates with editable pool configs if in edit mode
        header_text = "Selected Exam Templates (Edit Pool Counts):" if (is_edit and pool_configs) else "Selected Exam Templates:"
        selected_exams_display = ft.Column([
            ft.Text(header_text, size=14, weight=ft.FontWeight.BOLD),
            ft.Container(height=5)
        ])

        for exam in exams:
            # Build question count display - editable if pool_configs exist, otherwise read-only
            if pool_configs and exam['id'] in pool_configs:
                config = pool_configs[exam['id']]

                # Show editable TextFields for pool counts
                exam_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.CHECK_CIRCLE, color=COLORS['success'], size=16),
                            ft.Text(f"{exam['title']}", size=13, weight=ft.FontWeight.BOLD),
                        ], spacing=8),
                        ft.Row([
                            config['easy'],
                            config['medium'],
                            config['hard']
                        ], spacing=10)
                    ], spacing=5),
                    padding=ft.padding.all(12),
                    bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                    border_radius=8,
                    border=ft.border.all(1, COLORS['secondary'])
                )
                selected_exams_display.controls.append(exam_card)
            else:
                # Read-only display for non-pool assignments
                question_text = f"{exam.get('question_count', 0)} questions"
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
            label=t('duration'),
            value=str(assignment['duration_minutes']) if is_edit else self.default_exam_duration,
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 90",
            width=150
        )

        passing_score_field = ft.TextField(
            label=t('passing_score'),
            value=str(assignment['passing_score']) if is_edit else self.default_passing_score,
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 80",
            width=150
        )

        max_attempts_field = ft.TextField(
            label=t('max_attempts'),
            value=str(assignment['max_attempts']) if is_edit else "1",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 3",
            width=150
        )

        # Security Settings
        randomize_questions = ft.Checkbox(
            label=t('randomize_questions'),
            value=bool(assignment['randomize_questions']) if is_edit else False
        )

        show_results = ft.Checkbox(
            label=t('show_results'),
            value=bool(assignment['show_results']) if is_edit else True
        )

        enable_fullscreen = ft.Checkbox(
            label=t('enable_fullscreen'),
            value=bool(assignment['enable_fullscreen']) if is_edit else False
        )

        # Delivery Method
        delivery_method = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="online", label=t('online_exam')),
                ft.Radio(value="pdf_export", label=t('pdf_export'))
            ]),
            value=assignment.get('delivery_method', 'online') if is_edit else "online"
        )

        # Variant count dropdown
        existing_variant_count = str(assignment.get('pdf_variant_count', 1)) if is_edit else "1"
        variant_count = ft.Dropdown(
            label=t('pdf_variants'),
            options=[
                ft.dropdown.Option("1", "1 Variant"),
                ft.dropdown.Option("2", "2 Variants"),
                ft.dropdown.Option("3", "3 Variants"),
                ft.dropdown.Option("4", "4 Variants")
            ],
            value=existing_variant_count,
            width=200,
            visible=is_edit and assignment.get('delivery_method') == "pdf_export"
        )

        # Variant note
        variant_note = ft.Container(
            content=ft.Column([
                ft.Text("💡 Variants Info:", size=11, weight=ft.FontWeight.BOLD),
                ft.Text("• Each variant has different question order", size=10),
                ft.Text("• Helps prevent cheating in classroom", size=10),
                ft.Text("• Only works if 'Randomize Questions' is enabled", size=10)
            ], spacing=2),
            padding=8,
            bgcolor=ft.colors.with_opacity(0.05, COLORS['warning']),
            border_radius=6,
            visible=is_edit and assignment.get('delivery_method') == "pdf_export" and bool(assignment.get('randomize_questions'))
        )

        # PDF assignment note
        pdf_note = ft.Container(
            content=ft.Column([
                ft.Text("📌 Note for PDF Export:", size=12, weight=ft.FontWeight.BOLD),
                ft.Text("• Questions will be saved when assignment is created", size=11),
                ft.Text("• You can export PDF multiple times (same questions)", size=11),
                ft.Text("• No need to assign to students", size=11)
            ], spacing=3),
            padding=10,
            bgcolor=ft.colors.with_opacity(0.05, COLORS['info']),
            border_radius=8,
            visible=False
        )

        user_selection_section = None  # Placeholder for visibility toggling

        def apply_delivery_method_state(is_pdf):
            variant_count.visible = is_pdf
            variant_note.visible = is_pdf and randomize_questions.value
            pdf_note.visible = is_pdf
            max_attempts_field.visible = not is_pdf
            deadline_field.visible = not is_pdf
            show_results.visible = not is_pdf
            enable_fullscreen.visible = not is_pdf
            if user_selection_section:
                user_selection_section.visible = not is_pdf

        def on_delivery_method_change(e):
            apply_delivery_method_state(e.control.value == "pdf_export")
            assignment_dialog.update()

        def on_randomize_change(e):
            apply_delivery_method_state(delivery_method.value == "pdf_export")
            assignment_dialog.update()

        delivery_method.on_change = on_delivery_method_change
        randomize_questions.on_change = on_randomize_change


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
            label=t('deadline'),
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
        self.selected_assignment_units = []

        # Load users and departments for selection (include both examinees and experts)
        users = self.db.execute_query("""
            SELECT id, full_name, username, role, department, unit
            FROM users
            WHERE role IN ('examinee', 'expert') AND is_active = 1
            ORDER BY full_name
        """)

        department_values = sorted({u['department'] for u in users if u.get('department')})
        unit_combo_set = {
            (u['department'], u['unit'])
            for u in users
            if u.get('department') and u.get('unit')
        }
        unit_combo_list = sorted(list(unit_combo_set), key=lambda combo: (combo[0], combo[1]))

        # Helper function to extract unit name in current language
        current_lang = get_language()
        def get_unit_display_name(dept, unit):
            """Extract unit name in current language"""
            # If unit contains " / ", it's bilingual
            if " / " in unit:
                parts = unit.split(" / ")
                if len(parts) == 2:
                    # First part is Azerbaijani, second is English
                    return parts[1].strip() if current_lang == 'en' else parts[0].strip()
            return unit

        user_dropdown = ft.Dropdown(
            label=t('search_users'),
            hint_text="Choose users to assign",
            options=[ft.dropdown.Option(key=str(user['id']), text=f"{user['full_name']} ({user['username']})") for user in users],
            expand=True,
            height=56,
            content_padding=5
        )

        department_dropdown = ft.Dropdown(
            label=t('assign_department'),
            hint_text="Choose departments",
            options=[ft.dropdown.Option(dept, dept) for dept in department_values],
            expand=True,
            height=56,
            content_padding=5
        )

        unit_dropdown = ft.Dropdown(
            label=t('assign_unit'),
            hint_text="Select unit",
            options=[
                ft.dropdown.Option(
                    f"{dept}|||{unit}",
                    f"{get_unit_display_name(dept, dept)} / {get_unit_display_name(dept, unit)}"
                )
                for dept, unit in unit_combo_list
            ],
            expand=True,
            height=56,
            content_padding=5
        )

        selected_chips_row = ft.Row(spacing=8, wrap=True)
        selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
            selected_chips_row,
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
                selected_chips_row.controls.append(chip)

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
                selected_chips_row.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_user(user_id):
            if user_id in self.selected_assignment_users:
                self.selected_assignment_users.remove(user_id)
                # Remove chip from UI
                for i, control in enumerate(selected_chips_row.controls):
                    if isinstance(control, ft.Chip) and "Department:" not in control.label.value:
                        user_name = control.label.value
                        # Check if this is the user to remove
                        if user_id in [u['id'] for u in users if f"{u['full_name']} ({u['username']})" == user_name]:
                            selected_chips_row.controls.pop(i)
                            break
                if self.page:
                    self.page.update()

        def remove_department(dept):
            if dept in self.selected_assignment_departments:
                self.selected_assignment_departments.remove(dept)
                # Remove chip from UI
                for i, control in enumerate(selected_chips_row.controls):
                    if isinstance(control, ft.Chip) and control.label.value == f"Department: {dept}":
                        selected_chips_row.controls.pop(i)
                        break
                if self.page:
                    self.page.update()

        def on_unit_selection(e):
            if not e.control.value:
                return

            dept, unit = e.control.value.split("|||")
            key = (dept, unit)
            if key not in self.selected_assignment_units:
                self.selected_assignment_units.append(key)

                chip = ft.Chip(
                    label=ft.Text(f"Unit: {dept} / {unit}"),
                    on_delete=lambda e, combo=key: remove_unit(combo),
                    delete_icon_color=COLORS['error']
                )
                selected_chips_row.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_unit(combo):
            if combo in self.selected_assignment_units:
                self.selected_assignment_units.remove(combo)
                # Remove chip from UI
                for i, control in enumerate(selected_chips_row.controls):
                    if isinstance(control, ft.Chip) and f"Unit: {combo[0]} / {combo[1]}" == control.label.value:
                        selected_chips_row.controls.pop(i)
                        break
                if self.page:
                    self.page.update()

        user_dropdown.on_change = on_user_selection
        department_dropdown.on_change = on_department_selection
        unit_dropdown.on_change = on_unit_selection

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_assignment(e):
            # Validate
            if not assignment_name_field.value.strip():
                error_text.value = "Assignment name is required"
                error_text.visible = True
                assignment_dialog.update()
                return

            # For create mode, validate user/department/unit selection (skip for PDF export)
            is_pdf_export = delivery_method.value == "pdf_export"
            if not is_edit and not is_pdf_export and not self.selected_assignment_users and not self.selected_assignment_departments and not self.selected_assignment_units:
                error_text.value = "Please select at least one user, department, or unit (not required for PDF Export)"
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

                pdf_variant_count = 1
                if is_pdf_export:
                    try:
                        pdf_variant_count = max(1, int(variant_count.value or "1"))
                    except (TypeError, ValueError):
                        pdf_variant_count = 1

                pdf_variant_count = 1
                if is_pdf_export:
                    try:
                        pdf_variant_count = max(1, int(variant_count.value or "1"))
                    except (TypeError, ValueError):
                        pdf_variant_count = 1

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

                            # Always add to pool_settings, even if all zeros
                            # (zeros mean "don't use any questions from this template")
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

                    # Check that at least one exam has questions configured
                    total_questions = sum(p['easy'] + p['medium'] + p['hard'] for p in pool_settings)
                    if total_questions == 0:
                        error_text.value = "Please configure at least one question across all exam templates"
                        error_text.visible = True
                        assignment_dialog.update()
                        return

                if is_edit:
                    # Update existing assignment
                    assignment_id = assignment['id']

                    self.db.execute_update("""
                        UPDATE exam_assignments
                        SET assignment_name = ?,
                            duration_minutes = ?,
                            passing_score = ?,
                            max_attempts = ?,
                            randomize_questions = ?,
                            show_results = ?,
                            enable_fullscreen = ?,
                            delivery_method = ?,
                            use_question_pool = ?,
                            deadline = ?,
                            pdf_variant_count = ?
                        WHERE id = ?
                    """, (
                        assignment_name_field.value.strip(),
                        duration,
                        passing_score,
                        max_attempts,
                        1 if randomize_questions.value else 0,
                        1 if show_results.value else 0,
                        1 if enable_fullscreen.value else 0,
                        delivery_method.value,
                        1 if using_pool else 0,
                        self.assignment_deadline.isoformat() if self.assignment_deadline else None,
                        pdf_variant_count,
                        assignment_id
                    ))

                    # Update template-level pool counts
                    for exam in exams:
                        exam_pool = next((p for p in pool_settings if p['exam_id'] == exam['id']), None)

                        if using_pool and exam_pool:
                            # Update or insert template pool configuration
                            existing = self.db.execute_single("""
                                SELECT id FROM assignment_exam_templates
                                WHERE assignment_id = ? AND exam_id = ?
                            """, (assignment_id, exam['id']))

                            if existing:
                                self.db.execute_update("""
                                    UPDATE assignment_exam_templates
                                    SET easy_count = ?, medium_count = ?, hard_count = ?
                                    WHERE assignment_id = ? AND exam_id = ?
                                """, (exam_pool['easy'], exam_pool['medium'], exam_pool['hard'],
                                      assignment_id, exam['id']))
                            else:
                                self.db.execute_insert("""
                                    INSERT INTO assignment_exam_templates (
                                        assignment_id, exam_id, order_index,
                                        easy_count, medium_count, hard_count
                                    ) VALUES (?, ?, 0, ?, ?, ?)
                                """, (assignment_id, exam['id'],
                                      exam_pool['easy'], exam_pool['medium'], exam_pool['hard']))

                    # Delete any cached PDF snapshots for this assignment to force regeneration
                    # Use assignment_id for multi-template assignments
                    self.db.execute_update("""
                        DELETE FROM pdf_exports WHERE exam_id = ?
                    """, (assignment_id,))

                else:
                    # Create new assignment (use first exam as primary, others stored in junction table)
                    primary_exam_id = exams[0]['id']

                    query = """
                        INSERT INTO exam_assignments (
                            exam_id, assignment_name, duration_minutes, passing_score, max_attempts,
                            randomize_questions, show_results, enable_fullscreen,
                            delivery_method,
                            use_question_pool, questions_to_select,
                            easy_questions_count, medium_questions_count, hard_questions_count,
                            deadline, created_at, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        delivery_method.value,
                        1 if using_pool else 0,
                        0, 0, 0, 0,  # Legacy question counts (not used for multi-template)
                        self.assignment_deadline.isoformat() if self.assignment_deadline else None,
                        datetime.now().isoformat(),
                        self.user_data['id']
                    )
                    assignment_id = self.db.execute_insert(query, params)

                    self.db.execute_update(
                        "UPDATE exam_assignments SET pdf_variant_count = ? WHERE id = ?",
                        (pdf_variant_count, assignment_id)
                    )

                    self.db.execute_update(
                        "UPDATE exam_assignments SET pdf_variant_count = ? WHERE id = ?",
                        (pdf_variant_count, assignment_id)
                    )

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
                        WHERE department = ? AND role IN ('examinee', 'expert') AND is_active = 1
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

                # Assign units
                for dept, unit in self.selected_assignment_units:
                    unit_users = self.db.execute_query("""
                        SELECT id FROM users
                        WHERE department = ? AND unit = ? AND role IN ('examinee', 'expert') AND is_active = 1
                    """, (dept, unit))

                    for user in unit_users:
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
                action = "updated" if is_edit else "created"
                success_message = f"Multi-template assignment '{assignment_name_field.value.strip()}' {action} successfully with {len(exams)} exam templates!"
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(success_message),
                    bgcolor=COLORS['success']
                )
                self.page.snack_bar.open = True
                self.page.update()

            except Exception as ex:
                action = "updating" if is_edit else "creating"
                error_text.value = f"Error {action} assignment: {str(ex)}"
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

            ft.Row([duration_field, passing_score_field, max_attempts_field, deadline_field], spacing=8),
            ft.Container(height=8),

            # Security Settings
            ft.Text("Security Settings", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([randomize_questions, show_results], spacing=15, wrap=True),
            ft.Row([enable_fullscreen], spacing=15, wrap=True),
            ft.Container(height=8),

            # Delivery Method
            ft.Text("📋 Delivery Method", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            delivery_method,
            variant_count,
            variant_note,
            pdf_note,
            ft.Container(height=8),
        ]

        # User Selection section (can be hidden for PDF export)
        user_selection_section = ft.Column([
            ft.Text("Assign to Users", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Text(
                "Select users, departments, or units to assign this exam.",
                size=12,
                color=COLORS['text_secondary']
            ),
            ft.Container(height=8),
            ft.Row([
                user_dropdown,
                ft.Container(width=12),
                department_dropdown,
                ft.Container(width=12),
                unit_dropdown
            ], spacing=0),
            ft.Container(height=12),
            selected_items_container,
            ft.Container(height=10),
        ], visible=True)

        apply_delivery_method_state(delivery_method.value == "pdf_export")

        dialog_content_controls.append(user_selection_section)
        dialog_content_controls.append(error_text)

        dialog_title = f"Edit Multi-Template Assignment ({len(exams)} exams)" if is_edit else f"Create Multi-Template Assignment ({len(exams)} exams)"
        button_text = t('update') + " " + t('assignment') if is_edit else t('create_assignment')

        assignment_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(dialog_title),
            content=ft.Container(
                content=ft.Column(dialog_content_controls, spacing=8, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 200 if self.page.width > 200 else 900,
                height=self.page.height - 150 if self.page.height > 150 else 650
            ),
            actions=[
                ft.TextButton(t('cancel'), on_click=close_dialog),
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
            label=t('assignment_name') + " *",
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
            label=t('duration'),
            value=self.default_exam_duration,
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 90",
            width=150
        )

        passing_score_field = ft.TextField(
            label=t('passing_score'),
            value=self.default_passing_score,
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 80",
            width=150
        )

        max_attempts_field = ft.TextField(
            label=t('max_attempts'),
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 3",
            width=150
        )

        # Security Settings
        randomize_questions = ft.Checkbox(
            label=t('randomize_questions'),
            value=True
        )

        show_results = ft.Checkbox(
            label=t('show_results'),
            value=True
        )

        enable_fullscreen = ft.Checkbox(
            label=t('enable_fullscreen'),
            value=False
        )

        # Delivery Method
        delivery_method = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="online", label=t('online_exam')),
                ft.Radio(value="pdf_export", label=t('pdf_export'))
            ]),
            value="online"
        )

        # Variant count dropdown
        variant_count = ft.Dropdown(
            label=t('pdf_variants'),
            options=[
                ft.dropdown.Option("1", "1 Variant"),
                ft.dropdown.Option("2", "2 Variants"),
                ft.dropdown.Option("3", "3 Variants"),
                ft.dropdown.Option("4", "4 Variants")
            ],
            value="1",
            width=200,
            visible=False
        )

        # Variant note
        variant_note = ft.Container(
            content=ft.Column([
                ft.Text("💡 Variants Info:", size=11, weight=ft.FontWeight.BOLD),
                ft.Text("• Each variant has different question order", size=10),
                ft.Text("• Helps prevent cheating in classroom", size=10),
                ft.Text("• Only works if 'Randomize Questions' is enabled", size=10)
            ], spacing=2),
            padding=8,
            bgcolor=ft.colors.with_opacity(0.05, COLORS['warning']),
            border_radius=6,
            visible=False
        )

        # PDF assignment note
        pdf_note = ft.Container(
            content=ft.Column([
                ft.Text("📌 Note for PDF Export:", size=12, weight=ft.FontWeight.BOLD),
                ft.Text("• Questions will be saved when assignment is created", size=11),
                ft.Text("• You can export PDF multiple times (same questions)", size=11),
                ft.Text("• No need to assign to students", size=11)
            ], spacing=3),
            padding=10,
            bgcolor=ft.colors.with_opacity(0.05, COLORS['info']),
            border_radius=8,
            visible=False
        )

        def on_delivery_method_change(e):
            is_pdf = (e.control.value == "pdf_export")
            variant_count.visible = is_pdf
            variant_note.visible = is_pdf and randomize_questions.value
            pdf_note.visible = is_pdf
            show_results.visible = not is_pdf
            enable_fullscreen.visible = not is_pdf
            user_selection_section.visible = not is_pdf  # Hide user selection for PDF
            assignment_dialog.update()

        def on_randomize_change(e):
            if delivery_method.value == "pdf_export":
                variant_note.visible = e.control.value
                assignment_dialog.update()

        delivery_method.on_change = on_delivery_method_change
        randomize_questions.on_change = on_randomize_change

        # Date picker
        self.assignment_deadline = None
        self.assignment_deadline_picker = ft.DatePicker(
            first_date=date.today(),
            last_date=date(2030, 12, 31)
        )

        deadline_field = ft.TextField(
            label=t('deadline'),
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

        # User selection (users, departments, units)
        self.selected_assignment_users = []
        self.selected_assignment_departments = []
        self.selected_assignment_units = []

        users = self.db.execute_query("""
            SELECT id, full_name, username, role, department, unit
            FROM users
            WHERE role IN ('examinee', 'expert') AND is_active = 1
            ORDER BY full_name
        """)

        department_values = sorted({u['department'] for u in users if u.get('department')})
        unit_combo_set = {
            (u['department'], u['unit'])
            for u in users
            if u.get('department') and u.get('unit')
        }
        unit_combo_list = sorted(list(unit_combo_set), key=lambda combo: (combo[0], combo[1]))

        # Helper function to extract unit name in current language
        current_lang = get_language()
        def get_unit_display_name(dept, unit):
            """Extract unit name in current language"""
            # If unit contains " / ", it's bilingual
            if " / " in unit:
                parts = unit.split(" / ")
                if len(parts) == 2:
                    # First part is Azerbaijani, second is English
                    return parts[1].strip() if current_lang == 'en' else parts[0].strip()
            return unit

        # User selection dropdown (searchable)
        user_search_dropdown = ft.Dropdown(
            label=t('search_users'),
            hint_text="Search users by name, username, or email",
            options=[
                ft.dropdown.Option(
                    key=str(user['id']),
                    text=f"{user['full_name']} ({user['username']})"
                )
                for user in users
            ],
            expand=True,
            height=56,
            content_padding=5
        )

        department_assign_dropdown = ft.Dropdown(
            label=t('assign_department'),
            hint_text="Select department",
            options=[ft.dropdown.Option(dept, dept) for dept in department_values],
            expand=True,
            height=56,
            content_padding=5
        )

        unit_assign_dropdown = ft.Dropdown(
            label=t('assign_unit'),
            hint_text="Select unit",
            options=[
                ft.dropdown.Option(
                    f"{dept}|||{unit}",
                    f"{get_unit_display_name(dept, dept)} / {get_unit_display_name(dept, unit)}"
                )
                for dept, unit in unit_combo_list
            ],
            expand=True,
            height=56,
            content_padding=5
        )

        selected_chips_row = ft.Row(spacing=8, wrap=True)
        selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
            selected_chips_row,
        ], spacing=5)

        def on_user_selection(e):
            """Handle user selection from dropdown"""
            if not e.control.value:
                return

            user_id = int(e.control.value)
            if user_id not in self.selected_assignment_users:
                self.selected_assignment_users.append(user_id)

                user_name = next((f"{u['full_name']} ({u['username']})" for u in users if u['id'] == user_id), "User")

                chip = ft.Chip(
                    label=ft.Text(user_name),
                    on_delete=lambda _, uid=user_id: remove_user(uid),
                    delete_icon_color=COLORS['error'],
                    data=('user', user_id)
                )
                selected_chips_row.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def on_department_assign(e):
            if not e.control.value:
                return

            dept = e.control.value
            if dept not in self.selected_assignment_departments:
                self.selected_assignment_departments.append(dept)

                chip = ft.Chip(
                    label=ft.Text(f"Department: {dept}"),
                    on_delete=lambda _, d=dept: remove_department(d),
                    delete_icon_color=COLORS['error'],
                    data=('dept', dept)
                )
                selected_chips_row.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def on_unit_assign(e):
            if not e.control.value:
                return

            dept, unit = e.control.value.split("|||")
            key = (dept, unit)
            if key not in self.selected_assignment_units:
                self.selected_assignment_units.append(key)

                chip = ft.Chip(
                    label=ft.Text(f"Unit: {dept} / {unit}"),
                    on_delete=lambda _, combo=key: remove_unit(combo),
                    delete_icon_color=COLORS['error'],
                    data=('unit', key[0], key[1])
                )
                selected_chips_row.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_user(user_id):
            if user_id in self.selected_assignment_users:
                self.selected_assignment_users.remove(user_id)
            for i, control in enumerate(selected_chips_row.controls):
                if getattr(control, 'data', None) == ('user', user_id):
                    selected_chips_row.controls.pop(i)
                    break
            if self.page:
                self.page.update()

        def remove_department(dept):
            if dept in self.selected_assignment_departments:
                self.selected_assignment_departments.remove(dept)
            for i, control in enumerate(selected_chips_row.controls):
                if getattr(control, 'data', None) == ('dept', dept):
                    selected_chips_row.controls.pop(i)
                    break
            if self.page:
                self.page.update()

        def remove_unit(combo):
            if combo in self.selected_assignment_units:
                self.selected_assignment_units.remove(combo)
            for i, control in enumerate(selected_chips_row.controls):
                if getattr(control, 'data', None) == ('unit', combo[0], combo[1]):
                    selected_chips_row.controls.pop(i)
                    break
            if self.page:
                self.page.update()

        user_search_dropdown.on_change = on_user_selection
        department_assign_dropdown.on_change = on_department_assign
        unit_assign_dropdown.on_change = on_unit_assign

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_assignment(e):
            # Validate
            if not assignment_name_field.value.strip():
                error_text.value = "Assignment name is required"
                error_text.visible = True
                assignment_dialog.update()
                return

            # For create mode, validate user/department selection (skip for PDF export)
            is_pdf_export = delivery_method.value == "pdf_export"
            if (
                not is_pdf_export
                and not self.selected_assignment_users
                and not self.selected_assignment_departments
                and not self.selected_assignment_units
            ):
                error_text.value = "Please select at least one user or department (not required for PDF Export)"
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
                        delivery_method,
                        use_question_pool, questions_to_select,
                        easy_questions_count, medium_questions_count, hard_questions_count,
                        deadline, created_at, created_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    delivery_method.value,
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
                        INSERT INTO assignment_exam_templates (
                            assignment_id, exam_id, order_index,
                            easy_count, medium_count, hard_count
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        assignment_id,
                        config['exam_id'],
                        order_idx,
                        config.get('easy_count', 0) or 0,
                        config.get('medium_count', 0) or 0,
                        config.get('hard_count', 0) or 0
                    ))

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
                        WHERE department = ? AND role IN ('examinee', 'expert') AND is_active = 1
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
                # Assign units
                for dept, unit in self.selected_assignment_units:
                    unit_users = self.db.execute_query("""
                        SELECT id FROM users
                        WHERE department = ? AND unit = ? AND role IN ('examinee', 'expert') AND is_active = 1
                    """, (dept, unit))

                    for user in unit_users:
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

            ft.Row([duration_field, passing_score_field, max_attempts_field, deadline_field], spacing=8, wrap=True),
            ft.Container(height=8),

            # Delivery Method (moved up for clarity)
            ft.Text("📋 Delivery Method", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            delivery_method,
            variant_count,
            variant_note,
            pdf_note,
            ft.Container(height=8),

            # Security Settings
            ft.Text("Security Settings", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([randomize_questions, show_results], spacing=15, wrap=True),
            ft.Row([enable_fullscreen], spacing=15, wrap=True),
            ft.Container(height=8),
        ]

        # User Selection section (can be hidden for PDF export)
        user_selection_section = ft.Column([
            ft.Text("Assign to Users", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Text(
                "Select users, departments, or units to assign this exam.",
                size=12,
                color=COLORS['text_secondary']
            ),
            ft.Container(height=8),
            # All 3 dropdowns in the same row
            ft.Row([
                user_search_dropdown,
                ft.Container(width=12),
                department_assign_dropdown,
                ft.Container(width=12),
                unit_assign_dropdown
            ], spacing=0),
            ft.Container(height=12),
            # Selected items only
            selected_items_container,
            ft.Container(height=10),
        ], visible=True)

        dialog_content_controls.append(user_selection_section)
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
                ft.TextButton(t('cancel'), on_click=close_dialog),
                ft.ElevatedButton(
                    t('create_assignment'),
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
            label=t('assignment_name') + " *",
            value=assignment['assignment_name'] if is_edit else f"{exam['title']} - Assignment",
            content_padding=5,
            hint_text="e.g., Midterm Exam - Section A",
            expand=True
        )

        # Duration, Passing Score, Max Attempts
        duration_field = ft.TextField(
            label=t('duration'),
            value=str(assignment['duration_minutes']) if is_edit else self.default_exam_duration,
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 90",
            width=150
        )

        passing_score_field = ft.TextField(
            label=t('passing_score'),
            value=str(assignment['passing_score']) if is_edit else self.default_passing_score,
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 80",
            width=150
        )

        max_attempts_field = ft.TextField(
            label=t('max_attempts'),
            value=str(assignment['max_attempts']) if is_edit else "1",
            keyboard_type=ft.KeyboardType.NUMBER,
            content_padding=5,
            hint_text="e.g., 3",
            width=150
        )

        # Security Settings
        randomize_questions = ft.Checkbox(
            label=t('randomize_questions'),
            value=bool(assignment['randomize_questions']) if is_edit else False
        )

        show_results = ft.Checkbox(
            label=t('show_results'),
            value=bool(assignment['show_results']) if is_edit else True
        )

        enable_fullscreen = ft.Checkbox(
            label=t('enable_fullscreen'),
            value=bool(assignment['enable_fullscreen']) if is_edit else False
        )

        # Delivery Method
        delivery_method = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="online", label=t('online_exam')),
                ft.Radio(value="pdf_export", label=t('pdf_export'))
            ]),
            value=assignment.get('delivery_method', 'online') if is_edit else "online"
        )

        # Variant count dropdown
        existing_variant_count = str(assignment.get('pdf_variant_count', 1)) if is_edit else "1"
        variant_count = ft.Dropdown(
            label=t('pdf_variants'),
            options=[
                ft.dropdown.Option("1", "1 Variant"),
                ft.dropdown.Option("2", "2 Variants"),
                ft.dropdown.Option("3", "3 Variants"),
                ft.dropdown.Option("4", "4 Variants")
            ],
            value=existing_variant_count,
            width=200,
            visible=is_edit and assignment.get('delivery_method') == "pdf_export"
        )

        # Variant note
        variant_note = ft.Container(
            content=ft.Column([
                ft.Text("💡 Variants Info:", size=11, weight=ft.FontWeight.BOLD),
                ft.Text("• Each variant has different question order", size=10),
                ft.Text("• Helps prevent cheating in classroom", size=10),
                ft.Text("• Only works if 'Randomize Questions' is enabled", size=10)
            ], spacing=2),
            padding=8,
            bgcolor=ft.colors.with_opacity(0.05, COLORS['warning']),
            border_radius=6,
            visible=is_edit and assignment.get('delivery_method') == "pdf_export" and bool(assignment.get('randomize_questions'))
        )

        # PDF assignment note
        pdf_note = ft.Container(
            content=ft.Column([
                ft.Text("📌 Note for PDF Export:", size=12, weight=ft.FontWeight.BOLD),
                ft.Text("• Questions will be saved when assignment is created", size=11),
                ft.Text("• You can export PDF multiple times (same questions)", size=11),
                ft.Text("• No need to assign to students", size=11)
            ], spacing=3),
            padding=10,
            bgcolor=ft.colors.with_opacity(0.05, COLORS['info']),
            border_radius=8,
            visible=False
        )


        # Delivery method change handlers
        def on_delivery_method_change(e):
            is_pdf = (e.control.value == "pdf_export")
            variant_count.visible = is_pdf
            variant_note.visible = is_pdf and randomize_questions.value
            pdf_note.visible = is_pdf
            show_results.visible = not is_pdf
            enable_fullscreen.visible = not is_pdf
            user_selection_section.visible = not is_pdf  # Hide user selection for PDF
            assignment_dialog.update()

        def on_randomize_change(e):
            if delivery_method.value == "pdf_export":
                variant_note.visible = e.control.value
                assignment_dialog.update()

        delivery_method.on_change = on_delivery_method_change
        randomize_questions.on_change = on_randomize_change

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

        # Check if template-level counts exist (for multi-template assignments or pool-based single-template)
        template_counts_exist = False
        template_easy = 0
        template_medium = 0
        template_hard = 0

        if is_edit and assignment:
            template_data = self.db.execute_single("""
                SELECT easy_count, medium_count, hard_count
                FROM assignment_exam_templates
                WHERE assignment_id = ? AND exam_id = ?
            """, (assignment['id'], exam['id']))

            if template_data:
                template_counts_exist = True
                template_easy = template_data['easy_count'] or 0
                template_medium = template_data['medium_count'] or 0
                template_hard = template_data['hard_count'] or 0

        # Use template-level counts if they exist, otherwise use assignment-level counts
        initial_easy = template_easy if template_counts_exist else (assignment['easy_questions_count'] if is_edit else 0)
        initial_medium = template_medium if template_counts_exist else (assignment['medium_questions_count'] if is_edit else 0)
        initial_hard = template_hard if template_counts_exist else (assignment['hard_questions_count'] if is_edit else 0)

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
            value=str(initial_easy),
            width=150,
            content_padding=5,
            disabled=not use_pool_value
        )

        medium_questions_count_field = ft.Dropdown(
            label=f"Medium (Available: {medium_q})",
            options=medium_options,
            value=str(initial_medium),
            width=150,
            content_padding=5,
            disabled=not use_pool_value
        )

        hard_questions_count_field = ft.Dropdown(
            label=f"Hard (Available: {hard_q})",
            options=hard_options,
            value=str(initial_hard),
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
            label=t('deadline'),
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

        # Load users and departments for selection (include both examinees and experts)
        users = self.db.execute_query("""
            SELECT id, full_name, username, role
            FROM users
            WHERE role IN ('examinee', 'expert') AND is_active = 1
            ORDER BY full_name
        """)

        departments = self.db.execute_query("""
            SELECT DISTINCT department
            FROM users
            WHERE department IS NOT NULL AND department != '' AND role IN ('examinee', 'expert')
            ORDER BY department
        """)

        user_dropdown = ft.Dropdown(
            label=t('select_users'),
            hint_text="Choose users to assign",
            options=[ft.dropdown.Option(key=str(user['id']), text=f"{user['full_name']} ({user['username']})") for user in users],
            width=250,
            height=56,
            content_padding=5
        )

        department_dropdown = ft.Dropdown(
            label=t('select_departments'),
            hint_text="Choose departments to assign",
            options=[ft.dropdown.Option(key=dept['department'], text=dept['department']) for dept in departments],
            width=250,
            height=56,
            content_padding=5
        )

        selected_chips_row = ft.Row(spacing=8, wrap=True)
        selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
            selected_chips_row,
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
                selected_chips_row.controls.append(chip)

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
                selected_chips_row.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_user(user_id):
            if user_id in self.selected_assignment_users:
                self.selected_assignment_users.remove(user_id)
                # Remove chip from UI
                for i, control in enumerate(selected_chips_row.controls):
                    if isinstance(control, ft.Chip) and "Department:" not in control.label.value:
                        user_name = control.label.value
                        # Check if this is the user to remove
                        if user_id in [u['id'] for u in users if f"{u['full_name']} ({u['username']})" == user_name]:
                            selected_chips_row.controls.pop(i)
                            break
                if self.page:
                    self.page.update()

        def remove_department(dept):
            if dept in self.selected_assignment_departments:
                self.selected_assignment_departments.remove(dept)
                # Remove chip from UI
                for i, control in enumerate(selected_chips_row.controls):
                    if isinstance(control, ft.Chip) and control.label.value == f"Department: {dept}":
                        selected_chips_row.controls.pop(i)
                        break
                if self.page:
                    self.page.update()

        def on_unit_selection(e):
            if not e.control.value:
                return

            dept, unit = e.control.value.split("|||")
            key = (dept, unit)
            if key not in self.selected_assignment_units:
                self.selected_assignment_units.append(key)

                chip = ft.Chip(
                    label=ft.Text(f"Unit: {dept} / {unit}"),
                    on_delete=lambda e, combo=key: remove_unit(combo),
                    delete_icon_color=COLORS['error']
                )
                selected_chips_row.controls.append(chip)

            e.control.value = None
            if self.page:
                self.page.update()

        def remove_unit(combo):
            if combo in self.selected_assignment_units:
                self.selected_assignment_units.remove(combo)
                # Remove chip from UI
                for i, control in enumerate(selected_chips_row.controls):
                    if isinstance(control, ft.Chip) and f"Unit: {combo[0]} / {combo[1]}" == control.label.value:
                        selected_chips_row.controls.pop(i)
                        break
                if self.page:
                    self.page.update()

        user_dropdown.on_change = on_user_selection
        department_dropdown.on_change = on_department_selection
        unit_dropdown.on_change = on_unit_selection

        error_text = ft.Text("", color=COLORS['error'], visible=False)

        def save_assignment(e):
            # Validate
            if not assignment_name_field.value.strip():
                error_text.value = "Assignment name is required"
                error_text.visible = True
                assignment_dialog.update()
                return

            # For create mode, validate user/department/unit selection (skip for PDF export)
            is_pdf_export = delivery_method.value == "pdf_export"
            if not is_edit and not is_pdf_export and not self.selected_assignment_users and not self.selected_assignment_departments and not self.selected_assignment_units:
                error_text.value = "Please select at least one user, department, or unit (not required for PDF Export)"
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
                            delivery_method = ?,
                            pdf_variant_count = ?,
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
                        delivery_method.value,
                        int(variant_count.value) if variant_count.value else 1,
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

                    # Update or create template-level counts if using question pool
                    if use_pool and (easy_count > 0 or medium_count > 0 or hard_count > 0):
                        # Check if template record exists
                        existing_template = self.db.execute_single("""
                            SELECT id FROM assignment_exam_templates
                            WHERE assignment_id = ? AND exam_id = ?
                        """, (assignment_id, exam['id']))

                        if existing_template:
                            # Update existing template record
                            self.db.execute_update("""
                                UPDATE assignment_exam_templates
                                SET easy_count = ?, medium_count = ?, hard_count = ?
                                WHERE assignment_id = ? AND exam_id = ?
                            """, (easy_count, medium_count, hard_count, assignment_id, exam['id']))
                        else:
                            # Create new template record
                            self.db.execute_insert("""
                                INSERT INTO assignment_exam_templates (assignment_id, exam_id, order_index, easy_count, medium_count, hard_count)
                                VALUES (?, ?, 0, ?, ?, ?)
                            """, (assignment_id, exam['id'], easy_count, medium_count, hard_count))

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
                            delivery_method, pdf_variant_count,
                            use_question_pool, questions_to_select,
                            easy_questions_count, medium_questions_count, hard_questions_count,
                            deadline, created_at, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        delivery_method.value,
                        int(variant_count.value) if variant_count.value else 1,
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

                    # Create template-level counts if using question pool
                    if use_pool and (easy_count > 0 or medium_count > 0 or hard_count > 0):
                        self.db.execute_insert("""
                            INSERT INTO assignment_exam_templates (assignment_id, exam_id, order_index, easy_count, medium_count, hard_count)
                            VALUES (?, ?, 0, ?, ?, ?)
                        """, (assignment_id, exam['id'], easy_count, medium_count, hard_count))

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

            # Delivery Method
            ft.Text("📋 Delivery Method", size=15, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            delivery_method,
            variant_count,
            variant_note,
            pdf_note,
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

        # User Selection section (can be hidden for PDF export)
        user_selection_section = ft.Column([
            ft.Text("Manage Assigned Users", size=16, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
            ft.Divider(height=1, color=COLORS['primary']),
            ft.Row([user_dropdown, department_dropdown], spacing=20),
            selected_items_container,
            ft.Container(height=10),
        ], visible=delivery_method.value != "pdf_export")

        dialog_content_controls.append(user_selection_section)

        dialog_content_controls.append(error_text)

        dialog_title = f"{'Edit' if is_edit else 'Create'} Assignment - {exam['title']}"
        button_text = t('save') + " " + t('changes') if is_edit else t('create_assignment')

        assignment_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(dialog_title),
            content=ft.Container(
                content=ft.Column(dialog_content_controls, spacing=8, tight=True, scroll=ft.ScrollMode.AUTO),
                width=self.page.width - 200 if self.page.width > 200 else 1000,
                height=self.page.height - 150 if self.page.height > 150 else 650
            ),
            actions=[
                ft.TextButton(t('cancel'), on_click=close_dialog),
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
        self.selected_items_row = ft.Row(spacing=8, wrap=True)
        self.selected_items_container = ft.Column([
            ft.Text("Selected for Assignment:", size=14, weight=ft.FontWeight.BOLD),
            self.selected_items_row,
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
                ft.TextButton(t('cancel'), on_click=close_assignment_dialog),
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

        # Load all examinee and expert users
        users = self.db.execute_query("""
            SELECT id, full_name, username, role
            FROM users
            WHERE role IN ('examinee', 'expert') AND is_active = 1
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
            WHERE department IS NOT NULL AND department != '' AND role IN ('examinee', 'expert')
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
        for control in self.selected_items_row.controls:
            if hasattr(control, 'data') and control.data == selection_key:
                return  # Already selected
        
        # Add to selected items
        chip = ft.Chip(
            label=ft.Text(selection_text),
            on_delete=lambda e, key=selection_key: self.remove_selected_item(key),
            delete_icon_color=COLORS['error'],
            data=selection_key
        )
        
        self.selected_items_row.controls.append(chip)
        
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
        for control in self.selected_items_row.controls:
            if hasattr(control, 'data') and control.data == selection_key:
                return  # Already selected
        
        # Add to selected items with "Department:" prefix
        chip = ft.Chip(
            label=ft.Text(f"Department: {selection_text}"),
            on_delete=lambda e, key=selection_key: self.remove_selected_item(key),
            delete_icon_color=COLORS['error'],
            data=selection_key
        )
        
        self.selected_items_row.controls.append(chip)
        
        # Clear dropdown selection
        e.control.value = None
        
        if self.page:
            self.page.update()
    
    def remove_selected_item(self, selection_key):
        """Remove item from selected items"""
        for i, control in enumerate(self.selected_items_row.controls):
            if hasattr(control, 'data') and control.data == selection_key:
                self.selected_items_row.controls.pop(i)
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
        # Clear chips in the row (keep the title above)
        self.selected_items_row.controls = []
        
        if self.all_users_selected:
            # Show summary when all users selected
            user_count = len([u for u in self.all_available_users if u['role'] != 'admin'])
            self.selected_items_row.controls.append(
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
                    self.selected_items_row.controls.append(chip)
    
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
        for control in self.selected_items_row.controls:
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
                        WHERE department = ? AND role IN ('examinee', 'expert') AND is_active = 1
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
            # Check if all examinees and experts are assigned
            total_examinees = self.db.execute_single("""
                SELECT COUNT(*) as count FROM users
                WHERE role IN ('examinee', 'expert') AND is_active = 1
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
                        content=ft.Text(t('scheduled'), size=10, color=ft.colors.BLACK, weight=ft.FontWeight.BOLD),
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
        # Check if this is a multi-template assignment
        templates = self.db.execute_query("""
            SELECT e.id, e.title, e.description,
                   aet.easy_count, aet.medium_count, aet.hard_count
            FROM assignment_exam_templates aet
            JOIN exams e ON aet.exam_id = e.id
            WHERE aet.assignment_id = ?
            ORDER BY aet.order_index
        """, (assignment['id'],))

        if templates and len(templates) > 0:
            # Multi-template assignment - use multi-template edit dialog
            # Note: pool_configs will be loaded inside the multi dialog from database
            self.show_assignment_creation_dialog_multi(templates, pool_configs=None, assignment=assignment)
        else:
            # Single-template assignment - use single-template dialog
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
        # Load users and departments for selection (include both examinees and experts)
        users = self.db.execute_query("""
            SELECT id, full_name, username, role
            FROM users
            WHERE role IN ('examinee', 'expert') AND is_active = 1
            ORDER BY full_name
        """)

        departments = self.db.execute_query("""
            SELECT DISTINCT department
            FROM users
            WHERE department IS NOT NULL AND department != '' AND role IN ('examinee', 'expert')
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
            check_and_archive()
            if self.page:
                self.page.update()

        def add_department(e):
            if not department_dropdown.value:
                return

            dept = department_dropdown.value

            # Get all users in department
            dept_users = self.db.execute_query("""
                SELECT id FROM users
                WHERE department = ? AND role IN ('examinee', 'expert') AND is_active = 1
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
            check_and_archive()
            if self.page:
                self.page.update()

        def remove_user(user_id):
            self.db.execute_update("""
                DELETE FROM assignment_users
                WHERE assignment_id = ? AND user_id = ?
            """, (assignment['id'], user_id))

            populate_current_users()
            check_and_archive()
            if self.page:
                self.page.update()

        def check_and_archive():
            """Check if all users completed and auto-archive if so"""
            try:
                # Get total assigned users count
                total_stats = self.db.execute_single("""
                    SELECT COUNT(DISTINCT user_id) as total_assigned
                    FROM assignment_users
                    WHERE assignment_id = ? AND is_active = 1
                """, (assignment['id'],))

                # Get completed users count
                completed_stats = self.db.execute_single("""
                    SELECT COUNT(DISTINCT user_id) as completed_count
                    FROM exam_sessions
                    WHERE assignment_id = ? AND is_completed = 1
                """, (assignment['id'],))

                if total_stats and completed_stats:
                    total_assigned = total_stats['total_assigned']
                    completed_count = completed_stats['completed_count']

                    print(f"📋 Assignment {assignment['id']}: {completed_count}/{total_assigned} users completed")

                    # If all users completed, archive the assignment
                    if total_assigned > 0 and completed_count == total_assigned:
                        self.db.execute_update("""
                            UPDATE exam_assignments
                            SET is_archived = 1
                            WHERE id = ?
                        """, (assignment['id'],))
                        print(f"✅ Assignment {assignment['id']} auto-archived - all users completed!")

                        # Show notification
                        if self.page:
                            self.page.snack_bar = ft.SnackBar(
                                content=ft.Text(f"Assignment auto-archived - all users completed!"),
                                bgcolor=COLORS['success']
                            )
                            self.page.snack_bar.open = True

                        # Close dialog since assignment is archived
                        users_dialog.open = False
                        self.load_exams()

            except Exception as e:
                print(f"Error checking assignment completion for auto-archive: {e}")

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
            label=t('description'),
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
            if total_questions_text.page:
                # Control must be attached to the page before update() is allowed
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
                bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                col={"xs": 12, "sm": 12, "md": 6, "lg": 6, "xl": 6}
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

        # Container for topic cards (two-column layout)
        topic_container = ft.ResponsiveRow([], spacing=10, run_spacing=10)

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
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                        col={"xs": 12, "sm": 12, "md": 6, "lg": 6, "xl": 6}
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

        # Calculate responsive heights
        dialog_height = self.page.height - 200 if self.page.height > 200 else 600
        scroll_container_height = dialog_height - 300  # Leave space for fields and total

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
                        height=scroll_container_height,
                        expand=True
                    ),
                    ft.Divider(),
                    total_questions_text,
                    error_text
                ], spacing=10),
                width=self.page.width - 300 if self.page.width > 300 else 700,
                height=dialog_height
            ),
            actions=[
                ft.TextButton(t('cancel'), on_click=close_dialog),
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
                        return delete_preset

                    preset_card = ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.BOOKMARK, color=COLORS['primary'], size=20),
                                ft.Text(preset['name'], size=16, weight=ft.FontWeight.BOLD),
                                ft.Container(expand=True),
                                ft.IconButton(
                                    icon=ft.icons.EDIT,
                                    tooltip=t('edit'),
                                    on_click=make_edit_preset(preset),
                                    icon_color=COLORS['primary']
                                ),
                                ft.IconButton(
                                    icon=ft.icons.DELETE,
                                    tooltip=t('delete'),
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
                    t('close'),
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

    def show_archived_assignments_dialog(self, e):
        """Show dialog to view archived assignments"""
        # Load archived assignments
        archived_assignments = self.db.execute_query("""
            SELECT ea.*,
                   e.title as exam_title,
                   e.description as exam_description,
                   COUNT(DISTINCT q.id) as question_count,
                   COUNT(DISTINCT au.user_id) as assigned_users_count,
                   COUNT(DISTINCT CASE WHEN es.is_completed = 1 THEN au.user_id END) as completed_users_count,
                   u.full_name as creator_name
            FROM exam_assignments ea
            JOIN exams e ON ea.exam_id = e.id
            LEFT JOIN questions q ON e.id = q.exam_id AND q.is_active = 1
            LEFT JOIN assignment_users au ON ea.id = au.assignment_id AND au.is_active = 1
            LEFT JOIN exam_sessions es ON au.user_id = es.user_id AND e.id = es.exam_id
            LEFT JOIN users u ON ea.created_by = u.id
            WHERE ea.is_archived = 1
            GROUP BY ea.id
            ORDER BY ea.created_at DESC
        """)

        # Create archived assignments table
        archived_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text(t('assignment'))),
                ft.DataColumn(ft.Text("Created By")),
                ft.DataColumn(ft.Text(t('completion'))),
                ft.DataColumn(ft.Text("Deadline")),
                ft.DataColumn(ft.Text(t('actions')))
            ],
            rows=[],
            width=float("inf")
        )

        def unarchive_assignment(assignment_id):
            """Unarchive an assignment"""
            self.db.execute_update("""
                UPDATE exam_assignments
                SET is_archived = 0
                WHERE id = ?
            """, (assignment_id,))

            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("Assignment unarchived successfully!"),
                bgcolor=COLORS['success']
            )
            self.page.snack_bar.open = True

            # Refresh the dialog
            refresh_archived_list()

            # Refresh main table
            self.load_exams()

        def refresh_archived_list():
            """Refresh archived assignments list"""
            updated_archived = self.db.execute_query("""
                SELECT ea.*,
                       e.title as exam_title,
                       e.description as exam_description,
                       COUNT(DISTINCT q.id) as question_count,
                       COUNT(DISTINCT au.user_id) as assigned_users_count,
                       COUNT(DISTINCT CASE WHEN es.is_completed = 1 THEN au.user_id END) as completed_users_count,
                       u.full_name as creator_name
                FROM exam_assignments ea
                JOIN exams e ON ea.exam_id = e.id
                LEFT JOIN questions q ON e.id = q.exam_id AND q.is_active = 1
                LEFT JOIN assignment_users au ON ea.id = au.assignment_id AND au.is_active = 1
                LEFT JOIN exam_sessions es ON au.user_id = es.user_id AND e.id = es.exam_id
                LEFT JOIN users u ON ea.created_by = u.id
                WHERE ea.is_archived = 1
                GROUP BY ea.id
                ORDER BY ea.created_at DESC
            """)

            archived_table.rows.clear()

            if not updated_archived:
                archived_table.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text("No archived assignments", italic=True, color=COLORS['text_secondary'])),
                            ft.DataCell(ft.Text("")),
                            ft.DataCell(ft.Text("")),
                            ft.DataCell(ft.Text("")),
                            ft.DataCell(ft.Text("")),
                            ft.DataCell(ft.Text(""))
                        ]
                    )
                )
            else:
                for idx, assignment in enumerate(updated_archived, 1):
                    assignment_title = f"{assignment['assignment_name']} ({assignment['exam_title']})"

                    # Format completion as "completed/total"
                    completed_count = assignment['completed_users_count'] or 0
                    total_count = assignment['assigned_users_count'] or 0
                    completion_text = f"{completed_count}/{total_count}"

                    archived_table.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(str(idx))),
                                ft.DataCell(ft.Text(assignment_title)),
                                ft.DataCell(ft.Text(assignment['creator_name'] or "Unknown")),
                                ft.DataCell(ft.Text(completion_text)),
                                ft.DataCell(ft.Text(assignment.get('deadline')[:10] if assignment.get('deadline') else "No deadline")),
                                ft.DataCell(
                                    ft.IconButton(
                                        icon=ft.icons.UNARCHIVE,
                                        tooltip="Unarchive Assignment",
                                        on_click=lambda e, aid=assignment['id']: unarchive_assignment(aid),
                                        icon_color=COLORS['primary']
                                    )
                                )
                            ]
                        )
                    )

            self.page.update()

        # Build initial table
        refresh_archived_list()

        # Create dialog
        archived_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.ARCHIVE, color=COLORS['primary']),
                ft.Text("Archived Assignments", weight=ft.FontWeight.BOLD)
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("These assignments have been automatically archived because all users completed them.",
                            size=12, color=COLORS['text_secondary']),
                    ft.Divider(),
                    ft.Container(
                        content=archived_table,
                        height=400,
                        width=900
                    )
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                width=900,
                height=500
            ),
            actions=[
                ft.TextButton(t('close'), on_click=lambda e: self.close_dialog())
            ]
        )

        self.page.dialog = archived_dialog
        archived_dialog.open = True
        self.page.update()

    def close_dialog(self):
        """Close the current dialog"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
