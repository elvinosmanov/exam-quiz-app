import flet as ft
from datetime import datetime
from quiz_app.config import COLORS
from quiz_app.utils.localization import t
from quiz_app.utils.permissions import UnitPermissionManager
from quiz_app.utils.email_ui_components import create_email_button

class Grading(ft.UserControl):
    def __init__(self, db, user_data=None):
        super().__init__()
        self.db = db
        self.user_data = user_data or {'role': 'admin'}  # Default to admin if not provided
        self.ungraded_answers = []
        self.completed_sessions = []
        self.current_answer = None
        self.parent_dashboard = None  # Reference to parent dashboard for badge updates

        # Load ungraded essay/short answer submissions
        self.load_ungraded_answers()

        # Load completed sessions
        self.load_completed_sessions()

        # Main content - Ungraded table
        self.answers_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t('assignment'))),
                ft.DataColumn(ft.Text(t('student_answer'))),
                ft.DataColumn(ft.Text(t('questions'))),
                ft.DataColumn(ft.Text(t('exam_date'))),
                ft.DataColumn(ft.Text(t('status'))),
                ft.DataColumn(ft.Text(t('actions')))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )

        # Completed sessions table
        self.completed_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(t('assignment'))),
                ft.DataColumn(ft.Text(t('student_answer'))),
                ft.DataColumn(ft.Text(t('score'))),
                ft.DataColumn(ft.Text(t('status'))),
                ft.DataColumn(ft.Text(t('exam_date'))),
                ft.DataColumn(ft.Text(t('actions')))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )

        self.update_answers_table()
        self.update_completed_table()

    def did_mount(self):
        """Called after component is mounted - rebuild tables with page reference"""
        super().did_mount()
        # Rebuild completed table now that self.page is available for email buttons
        self.update_completed_table()
        self.update()

    def load_ungraded_answers(self):
        """Load exam sessions that have ungraded essay/short answer questions (assignment-based)"""
        try:
            # Apply unit-level filtering for experts
            perm_manager = UnitPermissionManager(self.db)
            filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data)

            # Get exam sessions with ungraded essay/short_answer questions (assignment-based)
            query = """
                SELECT
                    es.id as session_id,
                    es.start_time,
                    es.end_time,
                    es.assignment_id,
                    e.id as exam_id,
                    e.title as exam_title,
                    ea.assignment_name,
                    u.id as user_id,
                    u.full_name as student_name,
                    u.username as student_username,
                    u.email as student_email,
                    COUNT(ua.id) as ungraded_count,
                    GROUP_CONCAT(q.question_type) as question_types
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                JOIN user_answers ua ON ua.session_id = es.id
                JOIN questions q ON ua.question_id = q.id
                JOIN exam_assignments ea ON es.assignment_id = ea.id
                JOIN exams e ON ea.exam_id = e.id
                WHERE q.question_type IN ('essay', 'short_answer')
                AND ua.points_earned IS NULL
                AND ua.answer_text IS NOT NULL
                AND ua.answer_text != ''
                AND es.is_completed = 1
                AND es.assignment_id IS NOT NULL
                {filter_clause}
                GROUP BY es.id, ea.id, e.id, u.id
                HAVING COUNT(ua.id) > 0
                ORDER BY es.end_time DESC
            """.format(filter_clause=filter_clause)

            self.ungraded_answers = self.db.execute_query(query, tuple(filter_params))

            print(f"Found {len(self.ungraded_answers)} exam sessions with ungraded essay/short answer submissions (assignment-based)")

        except Exception as e:
            print(f"Error loading ungraded sessions: {e}")
            self.ungraded_answers = []
    
    def format_date(self, date_string):
        """Format date string to human-readable format"""
        if not date_string:
            return ""
        try:
            # Parse the datetime string (format: 2025-06-29T21:40:...)
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            # Format as: Jun 29, 21:40
            return dt.strftime("%b %d, %H:%M")
        except Exception as e:
            print(f"Error formatting date {date_string}: {e}")
            # Fallback to original format
            return date_string[:16] if date_string else ""

    def load_completed_sessions(self):
        """Load completed exam sessions for email notifications (assignment-based)"""
        try:
            # Apply unit-level filtering for experts
            perm_manager = UnitPermissionManager(self.db)
            filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data)

            # Get completed sessions - MUST have assignment_id (assignment-based system)
            query = """
                SELECT
                    es.id as session_id,
                    es.end_time,
                    es.score,
                    es.assignment_id,
                    e.id as exam_id,
                    e.title as exam_title,
                    ea.assignment_name,
                    u.id as user_id,
                    u.full_name as student_name,
                    u.email as student_email,
                    COALESCE(ea.passing_score, e.passing_score) as passing_score
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                JOIN exam_assignments ea ON es.assignment_id = ea.id
                JOIN exams e ON ea.exam_id = e.id
                WHERE es.is_completed = 1
                AND es.score IS NOT NULL
                AND es.assignment_id IS NOT NULL
                {filter_clause}
                ORDER BY es.end_time DESC
                LIMIT 50
            """.format(filter_clause=filter_clause)

            self.completed_sessions = self.db.execute_query(query, tuple(filter_params))

            print(f"Loaded {len(self.completed_sessions)} completed exam sessions (assignment-based)")

        except Exception as e:
            print(f"Error loading completed sessions: {e}")
            self.completed_sessions = []

    def update_completed_table(self):
        """Update the completed sessions table (assignment-based)"""
        self.completed_list.rows.clear()

        for session in self.completed_sessions:
            score = round(session['score'], 1) if session['score'] is not None else 0
            passing_score = session['passing_score'] or 70
            passed = score >= passing_score

            # Status indicator
            status_text = t('passed') + " ✅" if passed else t('failed') + " ❌"
            status_color = COLORS['success'] if passed else COLORS['error']

            # Display assignment name (with topic in tooltip)
            assignment_display = session.get('assignment_name', session['exam_title'])
            if len(assignment_display) > 35:
                assignment_display = assignment_display[:32] + "..."

            # Email button
            email_btn = create_email_button(
                page=self.page,
                db=self.db,
                session_id=session['session_id'],
                user_data=self.user_data,
                on_success=lambda: self.show_email_sent_message()
            ) if self.page else ft.Container()

            self.completed_list.rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Column([
                        ft.Text(assignment_display, weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(f"{t('exam_title')}: {session['exam_title']}", size=11, color=COLORS['text_secondary'])
                    ], spacing=2)),
                    ft.DataCell(ft.Text(session['student_name'])),
                    ft.DataCell(ft.Text(f"{score}%", weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(status_text, color=status_color)),
                    ft.DataCell(ft.Text(self.format_date(session['end_time']))),
                    ft.DataCell(
                        ft.Row([
                            email_btn if email_btn else ft.Container(),
                            ft.IconButton(
                                icon=ft.icons.VISIBILITY,
                                tooltip=t('view_results'),
                                icon_color=COLORS['secondary'],
                                on_click=lambda e, s=session: self.show_session_details(s)
                            )
                        ], spacing=5)
                    )
                ])
            )

        # Show message if no completed sessions
        if not self.completed_sessions:
            self.completed_list.rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Text(t('no_results'))),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text(""))
                ])
            )

    def show_email_sent_message(self):
        """Callback after email is sent"""
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(t('email_failed')),
                bgcolor=COLORS['success']
            )
            self.page.snack_bar.open = True
            self.page.update()

    def show_session_details(self, session):
        """Show detailed view of exam session (placeholder)"""
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Session details for {session['student_name']} - {session['exam_title']}")
            )
            self.page.snack_bar.open = True
            self.page.update()

    def update_answers_table(self):
        """Update the answers table with current data (assignment-based)"""
        self.answers_list.rows.clear()

        print(f"[DEBUG] Updating answers table with {len(self.ungraded_answers)} sessions")

        for session in self.ungraded_answers:
            print(f"[DEBUG] Session: id={session.get('session_id')}, assignment={session.get('assignment_name')}, topic={session.get('exam_title')}")

            # Create questions summary
            question_summary = f"{session['ungraded_count']} essay/short answer questions"

            # Display assignment name (with topic in subtitle)
            assignment_display = session.get('assignment_name') or session.get('exam_title', t('no_data'))
            if assignment_display and len(assignment_display) > 35:
                assignment_display = assignment_display[:32] + "..."

            self.answers_list.rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Column([
                        ft.Text(assignment_display or t('assignment'), weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(f"{t('exam_title')}: {session.get('exam_title', 'N/A')}", size=11, color=COLORS['text_secondary'])
                    ], spacing=2)),
                    ft.DataCell(ft.Text(session.get('student_name', t('no_data')))),
                    ft.DataCell(ft.Text(question_summary)),
                    ft.DataCell(ft.Text(self.format_date(session.get('end_time')))),
                    ft.DataCell(ft.Text(t('pending_grading'), color=COLORS['warning'])),
                    ft.DataCell(
                        ft.ElevatedButton(
                            t('grade_exam'),
                            on_click=lambda e, session_data=session: self.show_session_grading_dialog(session_data),
                            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                        )
                    )
                ])
            )

        print(f"[DEBUG] Added {len(self.answers_list.rows)} rows to pending grading table")
        
        # Show message if no ungraded sessions
        if not self.ungraded_answers:
            self.answers_list.rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Text(t('no_questions_found'))),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text("")),
                    ft.DataCell(ft.Text(""))
                ])
            )
    
    def show_session_grading_dialog(self, session_data):
        """Show grading dialog for all essay questions in an exam session"""
        self.current_session = session_data

        # Get all ungraded essay/short_answer questions for this session
        session_questions = self.db.execute_query("""
            SELECT DISTINCT
                ua.id as answer_id,
                ua.answer_text,
                q.id as question_id,
                q.question_text,
                q.question_type,
                q.points as max_points
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            WHERE ua.session_id = ?
            AND q.question_type IN ('essay', 'short_answer')
            AND ua.points_earned IS NULL
            AND ua.answer_text IS NOT NULL
            AND ua.answer_text != ''
            ORDER BY q.order_index, q.id
        """, (session_data['session_id'],))

        print(f"[DEBUG] Found {len(session_questions)} ungraded questions for session {session_data['session_id']}")
        for q in session_questions:
            print(f"  - Question {q['question_id']}: {q['question_type']} - Answer ID: {q['answer_id']}")

        if not session_questions:
            # Debug: Check what's in the database
            debug_query = self.db.execute_query("""
                SELECT ua.id, ua.points_earned, ua.answer_text, q.question_type
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                WHERE ua.session_id = ?
                AND q.question_type IN ('essay', 'short_answer')
            """, (session_data['session_id'],))

            print(f"[DEBUG] All essay/short_answer answers for session {session_data['session_id']}:")
            for a in debug_query:
                print(f"  - Answer {a['id']}: type={a['question_type']}, points_earned={a['points_earned']}, has_answer={bool(a['answer_text'])}")

            if self.page:
                self.page.snack_bar = ft.SnackBar(content=ft.Text(t('no_questions_found')))
                self.page.snack_bar.open = True
                self.page.update()
            return
        
        # Create grading sections for each question
        question_sections = []
        self.points_inputs = {}  # Store points inputs for each question
        
        for i, question in enumerate(session_questions):
            # Points input for this question
            points_input = ft.TextField(
                label=f"Points (0 - {question['max_points']})",
                value="",
                width=150,
                keyboard_type=ft.KeyboardType.NUMBER
            )
            self.points_inputs[question['answer_id']] = points_input
            
            # Question section
            question_section = ft.Container(
                content=ft.Column([
                    # Question header
                    ft.Row([
                        ft.Text(f"{t('question')} {i+1}:", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.Text(f"{t('question_type')}: {question['question_type'].replace('_', ' ').title()}",
                               size=12, color=COLORS['text_secondary'])
                    ]),
                    ft.Container(height=5),

                    # Question text
                    ft.Text(question['question_text'], size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=10),

                    # Student answer
                    ft.Text(t('student_answer') + ":", size=14, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(
                            question['answer_text'] or t('no_data'),
                            size=14,
                            selectable=True
                        ),
                        padding=ft.padding.all(15),
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                        border_radius=8,
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['primary'])),
                        width=650
                    ),
                    ft.Container(height=10),
                    
                    # Points input
                    ft.Row([
                        points_input,
                        ft.Text(f"{t('points')}: {question['max_points']}", size=12, color=COLORS['text_secondary'])
                    ], spacing=10)
                ], spacing=5),
                padding=ft.padding.all(15),
                bgcolor=ft.colors.with_opacity(0.02, COLORS['surface']),
                border_radius=8,
                border=ft.border.all(1, ft.colors.with_opacity(0.1, COLORS['text_secondary']))
            )
            question_sections.append(question_section)
        
        # Create main dialog content
        grading_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.GRADING, color=COLORS['primary']),
                ft.Text(t('grade_exam'), color=COLORS['primary'], weight=ft.FontWeight.BOLD)
            ], spacing=8),
            content=ft.Container(
                content=ft.Column([
                    # Session info header (fixed)
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"{t('exam_title')}: {session_data['exam_title']}", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{t('student_answer')}: {session_data['student_name']}", size=14, weight=ft.FontWeight.W_500),
                            ft.Text(f"{t('exam_date')}: {self.format_date(session_data['end_time'])}", size=12, color=COLORS['text_secondary']),
                        ], spacing=5),
                        padding=ft.padding.only(bottom=15)
                    ),
                    
                    # Scrollable questions area
                    ft.Container(
                        content=ft.Column(
                            question_sections,
                            spacing=15,
                            scroll=ft.ScrollMode.AUTO
                        ),
                        expand=True
                    )
                ], spacing=0),
                width=700,
                height=500
            ),
            actions=[
                ft.TextButton(
                    t('cancel'),
                    on_click=self.close_session_grading_dialog
                ),
                ft.ElevatedButton(
                    t('save'),
                    on_click=lambda e: self.save_session_grades(session_questions),
                    style=ft.ButtonStyle(bgcolor=COLORS['success'], color=ft.colors.WHITE)
                )
            ]
        )
        
        # Show dialog
        if self.page:
            self.page.dialog = grading_dialog
            grading_dialog.open = True
            self.page.update()
    
    def save_session_grades(self, session_questions):
        """Save grades for all questions in the session"""
        try:
            grades_saved = 0
            errors = []
            
            for question in session_questions:
                answer_id = question['answer_id']
                max_points = float(question['max_points'])
                
                # Get points input for this question
                points_input = self.points_inputs.get(answer_id)
                if not points_input or not points_input.value.strip():
                    errors.append(f"Please enter points for: {question['question_text'][:50]}...")
                    continue
                
                try:
                    points = float(points_input.value)
                    
                    # Validate points
                    if points < 0 or points > max_points:
                        errors.append(f"Points must be 0-{max_points} for: {question['question_text'][:50]}...")
                        continue
                    
                    # Update database
                    self.db.execute_update("""
                        UPDATE user_answers 
                        SET points_earned = ?, is_correct = ?
                        WHERE id = ?
                    """, (points, 1 if points > 0 else 0, answer_id))
                    
                    grades_saved += 1
                    
                except ValueError:
                    errors.append(f"Invalid number for: {question['question_text'][:50]}...")
                    continue
            
            # Show results
            if errors:
                error_message = f"Saved {grades_saved} grades. Errors:\n" + "\n".join(errors[:3])
                if len(errors) > 3:
                    error_message += f"\n...and {len(errors) - 3} more errors"
                
                if self.page:
                    self.page.show_snack_bar(
                        ft.SnackBar(content=ft.Text(error_message))
                    )
            else:
                # All grades saved successfully
                
                # Recalculate exam session score with new grades BEFORE closing dialog
                if self.current_session and 'session_id' in self.current_session:
                    self.recalculate_exam_session_score(self.current_session['session_id'])
                else:
                    print("Warning: No current session found for score recalculation")
                
                self.close_session_grading_dialog(None)
                
                # Reload data
                self.load_ungraded_answers()
                self.load_completed_sessions()
                self.update_answers_table()
                self.update_completed_table()

                # Update tab counts if tabs exist
                if hasattr(self, 'tabs_control'):
                    self.tabs_control.tabs[0].text = f"{t('pending_grading')} ({len(self.ungraded_answers)})"
                    self.tabs_control.tabs[1].text = f"{t('exam_completed')} ({len(self.completed_sessions)})"

                self.update()

                # Update grading badge in parent dashboard
                if self.parent_dashboard:
                    self.parent_dashboard.update_grading_badge()

                # Show success message
                if self.page:
                    self.page.show_snack_bar(
                        ft.SnackBar(content=ft.Text(f"Successfully saved {grades_saved} grades!"))
                    )
                
        except Exception as ex:
            print(f"Error saving session grades: {ex}")
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text(t('operation_failed')))
                )
    
    def close_session_grading_dialog(self, e):
        """Close the session grading dialog"""
        if self.page and self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
        self.current_session = None
        self.points_inputs = {}
    
    def recalculate_exam_session_score(self, session_id):
        """Recalculate the total score for an exam session after instructor grading"""
        try:
            print(f"Recalculating score for exam session {session_id}")
            
            # Get questions for this session (handles both regular exams and question pool exams)
            # First check if this session has selected questions in session_questions table
            session_questions = self.db.execute_query("""
                SELECT q.id, q.points, q.question_type
                FROM questions q
                JOIN session_questions sq ON q.id = sq.question_id
                WHERE sq.session_id = ?
                ORDER BY sq.order_index, q.order_index, q.id
            """, (session_id,))
            
            if session_questions:
                # This session uses question pool - use selected questions
                exam_questions = session_questions
                print(f"Using question pool: {len(exam_questions)} selected questions for session {session_id}")
            else:
                # Regular exam - get all questions from the exam
                exam_questions = self.db.execute_query("""
                    SELECT q.id, q.points, q.question_type
                    FROM questions q
                    JOIN exam_sessions es ON es.id = ?
                    JOIN exams e ON e.id = es.exam_id AND e.id = q.exam_id
                    ORDER BY q.order_index, q.id
                """, (session_id,))
                print(f"Using regular exam: {len(exam_questions)} total questions for session {session_id}")
            
            if not exam_questions:
                print(f"No questions found for session {session_id}")
                return
            
            # Calculate total points for ALL questions
            total_points = sum(q['points'] for q in exam_questions)
            earned_points = 0
            correct_answers = 0
            answered_questions = 0
            
            # Get user answers for each question (avoid duplicates)
            for question in exam_questions:
                question_id = question['id']
                
                # Get the latest answer for this question (avoid duplicates)
                answer = self.db.execute_single("""
                    SELECT points_earned, is_correct
                    FROM user_answers 
                    WHERE session_id = ? AND question_id = ?
                    ORDER BY answered_at DESC
                    LIMIT 1
                """, (session_id, question_id))
                
                if answer and answer['points_earned'] is not None:
                    answered_questions += 1
                    earned_points += answer['points_earned']
                    
                    if answer['is_correct']:
                        correct_answers += 1
            
            # Calculate percentage score
            score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
            
            print(f"📊 SCORING SUMMARY:")
            print(f"   Total questions in exam: {len(exam_questions)}")
            print(f"   Questions answered: {answered_questions}")
            print(f"   Correct answers: {correct_answers}")
            print(f"   Points earned: {earned_points}/{total_points}")
            print(f"   Final score: {score_percentage:.1f}%")
            
            # Update the exam session with new score
            self.db.execute_update("""
                UPDATE exam_sessions 
                SET score = ?, correct_answers = ?, total_questions = ?
                WHERE id = ?
            """, (score_percentage, correct_answers, len(exam_questions), session_id))
            
            print(f"✅ Successfully updated exam session {session_id} score to {score_percentage:.1f}%")
            
        except Exception as e:
            print(f"Error recalculating exam session score: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_data(self, e):
        """Refresh the ungraded answers and completed sessions data"""
        self.load_ungraded_answers()
        self.load_completed_sessions()
        self.update_answers_table()
        self.update_completed_table()
        self.update()
    
    def build(self):
        return ft.Column([
            # Header
            ft.Row([
                ft.Text(t('grading'), size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    t('refresh'),
                    icon=ft.icons.REFRESH,
                    on_click=self.refresh_data,
                    style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Container(height=20),

                # Tabs for ungraded and completed sessions
                self._create_tabs()
        ], spacing=0, expand=True)

    def _create_tabs(self):
        """Create tabs control and store reference for updates"""
        self.tabs_control = ft.Tabs(
                    selected_index=0,
                    tabs=[
                        # Ungraded tab
                        ft.Tab(
                            text=f"{t('pending_grading')} ({len(self.ungraded_answers)})",
                            icon=ft.icons.PENDING_ACTIONS,
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text(
                                        t('manual_grading_required'),
                                        size=13,
                                        color=COLORS['text_secondary']
                                    ),
                                    ft.Container(height=5),
                                    ft.Container(
                                        content=ft.ListView(
                                            controls=[self.answers_list],
                                            expand=True,
                                            auto_scroll=False
                                        ),
                                        bgcolor=COLORS['surface'],
                                        border_radius=8,
                                        padding=ft.padding.all(8),
                                        expand=True
                                    )
                                ], spacing=0),
                                padding=ft.padding.all(5),
                                expand=True
                            )
                        ),

                        # Completed tab
                        ft.Tab(
                            text=f"{t('exam_completed')} ({len(self.completed_sessions)})",
                            icon=ft.icons.CHECK_CIRCLE,
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Text(
                                            t('grading_completed'),
                                            size=13,
                                            color=COLORS['text_secondary']
                                        ),
                                        ft.Container(expand=True),
                                        ft.Icon(ft.icons.EMAIL_OUTLINED, color=COLORS['primary'], size=18),
                                        ft.Text(
                                            t('send'),
                                            size=11,
                                            color=COLORS['primary'],
                                            italic=True
                                        )
                                    ]),
                                    ft.Container(height=5),
                                    ft.Container(
                                        content=ft.ListView(
                                            controls=[self.completed_list],
                                            expand=True,
                                            auto_scroll=False
                                        ),
                                        bgcolor=COLORS['surface'],
                                        border_radius=8,
                                        padding=ft.padding.all(8),
                                        expand=True
                                    )
                                ], spacing=0),
                                padding=ft.padding.all(5),
                                expand=True
                            )
                        )
                    ],
                    expand=True
                )
        return self.tabs_control