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
                    ea.assignment_name,
                    u.id as user_id,
                    u.full_name as student_name,
                    u.username as student_username,
                    u.email as student_email,
                    COUNT(ua.id) as ungraded_count,
                    GROUP_CONCAT(q.question_type) as question_types,
                    (
                        SELECT GROUP_CONCAT(ex.title, ', ')
                        FROM assignment_exam_templates aet
                        JOIN exams ex ON aet.exam_id = ex.id
                        WHERE aet.assignment_id = es.assignment_id
                    ) as topic_titles
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                JOIN user_answers ua ON ua.session_id = es.id
                JOIN questions q ON ua.question_id = q.id
                JOIN exam_assignments ea ON es.assignment_id = ea.id
                WHERE q.question_type IN ('essay', 'short_answer')
                AND ua.points_earned IS NULL
                AND ua.answer_text IS NOT NULL
                AND ua.answer_text != ''
                AND es.is_completed = 1
                AND es.assignment_id IS NOT NULL
                {filter_clause}
                GROUP BY es.id
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
            # IMPORTANT: Only show sessions where ALL questions are graded (no pending essay/short_answer)
            query = """
                SELECT
                    es.id as session_id,
                    es.end_time,
                    es.score,
                    es.assignment_id,
                    ea.assignment_name,
                    u.id as user_id,
                    u.full_name as student_name,
                    u.email as student_email,
                    ea.passing_score,
                    (
                        SELECT GROUP_CONCAT(ex.title, ', ')
                        FROM assignment_exam_templates aet
                        JOIN exams ex ON aet.exam_id = ex.id
                        WHERE aet.assignment_id = es.assignment_id
                    ) as topic_titles
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                JOIN exam_assignments ea ON es.assignment_id = ea.id
                WHERE es.is_completed = 1
                AND es.score IS NOT NULL
                AND es.assignment_id IS NOT NULL
                -- Exclude sessions with ungraded essay/short_answer questions
                AND NOT EXISTS (
                    SELECT 1 FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    WHERE ua.session_id = es.id
                    AND q.question_type IN ('essay', 'short_answer')
                    AND ua.points_earned IS NULL
                    AND ua.answer_text IS NOT NULL
                    AND ua.answer_text != ''
                )
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
            assignment_display = session.get('assignment_name') or session.get('topic_titles') or t('no_data')
            if len(assignment_display) > 35:
                assignment_display = assignment_display[:32] + "..."

            # Email button with reload callback
            email_btn = create_email_button(
                page=self.page,
                db=self.db,
                session_id=session['session_id'],
                user_data=self.user_data,
                on_success=lambda: self.handle_email_sent()
            ) if self.page else ft.Container()

            self.completed_list.rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Text(assignment_display, weight=ft.FontWeight.BOLD, size=13)),
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

    def handle_email_sent(self):
        """Callback after email is sent - reload table to update icon colors"""
        # Reload completed sessions to refresh email_sent status
        self.load_completed_sessions()
        self.update_completed_table()

        if self.page:
            # Show success message
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(t('email_sent_successfully')),
                bgcolor=COLORS['success']
            )
            self.page.snack_bar.open = True
            self.update()
            self.page.update()

    def show_session_details(self, session):
        """Show detailed exam review dialog - same as examinee results view"""
        try:
            session_id = session['session_id']
            print(f"Loading exam session {session_id} for admin review...")

            # Get exam session details
            session_data = self.get_exam_session_details(session_id)
            if not session_data:
                self.show_error_dialog("Exam session not found")
                return

            # Get user answers with question details
            review_data = self.get_exam_review_data(session_id)
            if not review_data:
                self.show_error_dialog("No exam data found for review")
                return

            print(f"Loaded session: {session_data['exam_title']}")
            print(f"Questions found: {len(review_data)}")
            print(f"Score: {session_data['score']}%")

            # Show the exam review dialog
            self.show_exam_review_dialog(session_data, review_data)

        except Exception as e:
            print(f"Error loading exam details: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_dialog("Failed to load exam details")

    def update_answers_table(self):
        """Update the answers table with current data (assignment-based)"""
        self.answers_list.rows.clear()

        for session in self.ungraded_answers:
            # Create questions summary
            question_summary = f"{session['ungraded_count']} essay/short answer questions"

            topic_titles = session.get('topic_titles') or t('no_data')

            # Display assignment name (with topic in subtitle)
            assignment_display = session.get('assignment_name') or topic_titles
            if assignment_display and len(assignment_display) > 35:
                assignment_display = assignment_display[:32] + "..."

            self.answers_list.rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Column([
                        ft.Text(assignment_display or t('assignment'), weight=ft.FontWeight.BOLD, size=13),
                        ft.Text(f"{t('topic_title')}: {topic_titles}", size=11, color=COLORS['text_secondary'])
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
                ua.id as answer_id, ua.points_earned,
                ua.answer_text,
                q.id as question_id,
                q.question_text,
                q.question_type,
                q.points as max_points,
                q.correct_answer
            FROM user_answers ua
            JOIN questions q ON ua.question_id = q.id
            WHERE ua.session_id = ?
            AND q.question_type IN ('essay', 'short_answer')
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
                value=str(question['points_earned']) if question.get('points_earned') is not None else "",
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
                    ft.Container(height=15),

                    # Correct Answer / Sample Answer
                    ft.Text(t('correct_answer'), size=14, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                    ft.Container(
                        content=ft.Text(
                            question['correct_answer'] or t('no_data'),
                            size=14,
                            selectable=True
                        ),
                        padding=ft.padding.all(15),
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['success']),
                        border_radius=8,
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['success']))
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
                            ft.Text(f"{t('assignment')}: {session_data['assignment_name']}", size=16, weight=ft.FontWeight.BOLD),
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

    def show_error_dialog(self, message):
        """Show error dialog"""
        if not self.page:
            print(f"Error (no page): {message}")
            return

        try:
            error_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.icons.ERROR, color=COLORS['error'], size=24),
                    ft.Text(t('error'), color=COLORS['error'], weight=ft.FontWeight.BOLD)
                ], spacing=8),
                content=ft.Text(message, size=16),
                actions=[
                    ft.ElevatedButton(
                        "OK",
                        on_click=lambda e: self.close_error_dialog(),
                        style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                    )
                ]
            )

            self.page.dialog = error_dialog
            error_dialog.open = True
            self.page.update()
        except Exception as e:
            print(f"Error showing dialog: {e}, Original message: {message}")

    def close_error_dialog(self):
        """Close the current error dialog"""
        if self.page and self.page.dialog:
            self.page.dialog.open = False
            self.page.update()

    def get_exam_session_details(self, session_id):
        """Get comprehensive exam session information"""
        try:
            session_data = self.db.execute_single("""
                SELECT
                    es.*,
                    COALESCE(ea.assignment_name, e.title) as exam_title,
                    COALESCE(e.description, ea.assignment_name) as exam_description,
                    COALESCE(ea.passing_score, e.passing_score) as passing_score,
                    COALESCE(ea.show_results, e.show_results) as show_results,
                    COALESCE(ea.use_question_pool, e.use_question_pool) as use_question_pool,
                    COALESCE(ea.questions_to_select, e.questions_to_select) as questions_to_select,
                    COALESCE(ea.easy_questions_count, e.easy_questions_count) as easy_questions_count,
                    COALESCE(ea.medium_questions_count, e.medium_questions_count) as medium_questions_count,
                    COALESCE(ea.hard_questions_count, e.hard_questions_count) as hard_questions_count,
                    u.full_name as user_name
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
                JOIN users u ON es.user_id = u.id
                WHERE es.id = ?
            """, (session_id,))

            return session_data

        except Exception as e:
            print(f"Error getting session details: {e}")
            return None

    def get_exam_review_data(self, session_id):
        """Get all questions with user answers and correct answers for review"""
        try:
            # First get the session to find the exam_id
            session = self.db.execute_single("""
                SELECT exam_id FROM exam_sessions WHERE id = ?
            """, (session_id,))

            if not session:
                return None

            exam_id = session['exam_id']

            # Get questions for this session (handles both regular exams and question pool exams)
            session_questions = self.db.execute_query("""
                SELECT q.*
                FROM questions q
                JOIN session_questions sq ON q.id = sq.question_id
                WHERE sq.session_id = ?
                ORDER BY sq.order_index, q.order_index, q.id
            """, (session_id,))

            if session_questions:
                questions = session_questions
                print(f"Using question pool: {len(questions)} selected questions for session {session_id}")
            else:
                # Regular exam - get all questions from the exam
                questions = self.db.execute_query("""
                    SELECT * FROM questions
                    WHERE exam_id = ? AND is_active = 1
                    ORDER BY order_index, id
                """, (exam_id,))
                print(f"Using regular exam: {len(questions)} total questions for session {session_id}")

            review_data = []

            for question in questions:
                question_id = question['id']

                # Get user's LATEST answer for this question
                user_answer_data = self.db.execute_single("""
                    SELECT * FROM user_answers
                    WHERE session_id = ? AND question_id = ?
                    ORDER BY answered_at DESC
                    LIMIT 1
                """, (session_id, question_id))

                # Get question options (for choice questions)
                options = self.db.execute_query("""
                    SELECT * FROM question_options
                    WHERE question_id = ?
                    ORDER BY order_index, id
                """, (question_id,))

                # Process the question data for review
                question_review = {
                    'question_id': question_id,
                    'question_text': question['question_text'],
                    'question_type': question['question_type'],
                    'correct_answer': question.get('correct_answer'),
                    'explanation': question.get('explanation'),
                    'points': question.get('points', 1.0),
                    'options': options,
                    'user_answer': None,
                    'user_answer_text': None,
                    'is_correct': False,
                    'points_earned': None,
                    'grading_status': 'not_answered'
                }

                # Process user answer based on question type
                if user_answer_data:
                    points_earned = user_answer_data.get('points_earned')
                    question_review['points_earned'] = points_earned

                    if question['question_type'] == 'single_choice':
                        question_review['user_answer'] = user_answer_data.get('selected_option_id')
                        if question_review['user_answer']:
                            selected_option = next((opt for opt in options if opt['id'] == question_review['user_answer']), None)
                            if selected_option:
                                question_review['user_answer_text'] = selected_option['option_text']
                                question_review['is_correct'] = selected_option['is_correct']
                                question_review['grading_status'] = 'graded'

                    elif question['question_type'] == 'multiple_choice':
                        import json
                        selected_ids = user_answer_data.get('selected_option_ids')

                        if not selected_ids and user_answer_data.get('answer_text'):
                            question_review['user_answer'] = []
                            question_review['user_answer_text'] = [user_answer_data.get('answer_text')]
                            question_review['is_correct'] = user_answer_data.get('is_correct', False)
                            question_review['grading_status'] = 'graded'
                        elif selected_ids:
                            try:
                                if isinstance(selected_ids, str):
                                    question_review['user_answer'] = json.loads(selected_ids)
                                else:
                                    question_review['user_answer'] = selected_ids

                                selected_options = [opt for opt in options if opt['id'] in question_review['user_answer']]
                                question_review['user_answer_text'] = [opt['option_text'] for opt in selected_options]

                                correct_ids = [opt['id'] for opt in options if opt['is_correct']]
                                question_review['is_correct'] = set(question_review['user_answer']) == set(correct_ids)
                                question_review['grading_status'] = 'graded'
                            except (json.JSONDecodeError, TypeError) as e:
                                print(f"Error parsing multiple choice answer: {e}")
                                question_review['user_answer'] = []
                                question_review['user_answer_text'] = []
                                question_review['is_correct'] = False
                                question_review['grading_status'] = 'graded'
                        else:
                            question_review['user_answer'] = []
                            question_review['user_answer_text'] = []
                            question_review['is_correct'] = False
                            question_review['grading_status'] = 'graded'

                    elif question['question_type'] in ['true_false', 'short_answer', 'essay']:
                        question_review['user_answer_text'] = user_answer_data.get('answer_text')
                        if question['question_type'] == 'true_false':
                            correct_answer = question.get('correct_answer', '').lower()
                            user_answer = (user_answer_data.get('answer_text') or '').lower()
                            question_review['is_correct'] = correct_answer == user_answer
                            question_review['grading_status'] = 'graded'
                        else:
                            points_earned = user_answer_data.get('points_earned')
                            if points_earned is not None:
                                question_review['is_correct'] = points_earned > 0
                                question_review['points_earned'] = points_earned
                                question_review['grading_status'] = 'graded'
                            else:
                                question_review['is_correct'] = None
                                question_review['points_earned'] = None
                                question_review['grading_status'] = 'pending'

                # Get correct answer text for display
                if question['question_type'] in ['single_choice', 'multiple_choice']:
                    correct_options = [opt for opt in options if opt['is_correct']]
                    if question['question_type'] == 'single_choice':
                        question_review['correct_answer_text'] = correct_options[0]['option_text'] if correct_options else 'N/A'
                    else:
                        question_review['correct_answer_text'] = [opt['option_text'] for opt in correct_options]
                elif question['question_type'] == 'true_false':
                    correct_answer = question.get('correct_answer', '') or ''
                    correct_answer = correct_answer.strip().lower()
                    if correct_answer in ['true', 'false']:
                        question_review['correct_answer_text'] = correct_answer.capitalize()
                    else:
                        question_review['correct_answer_text'] = 'N/A (Missing correct answer)'
                else:
                    question_review['correct_answer_text'] = question.get('correct_answer', 'N/A')

                review_data.append(question_review)

            return review_data

        except Exception as e:
            print(f"Error getting exam review data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def show_exam_review_dialog(self, session_data, review_data):
        """Show responsive exam review dialog"""
        try:
            if not self.page:
                print("No page reference available for dialog")
                return

            # Calculate responsive dialog dimensions
            window_width = getattr(self.page.window, 'width', 1200) or 1200
            window_height = getattr(self.page.window, 'height', 800) or 800

            dialog_width = min(max(window_width * 0.85, 700), 1400)
            dialog_height = min(max(window_height * 0.8, 500), 900)

            # Calculate summary stats
            total_questions = len(review_data)
            correct_count = sum(1 for q in review_data if q['is_correct'])
            answered_count = sum(1 for q in review_data if q['user_answer_text'] is not None)

            # Create dialog header
            header_content = ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ASSESSMENT, color=COLORS['primary'], size=28),
                    ft.Text(
                        session_data['exam_title'],
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS['text_primary']
                    )
                ], spacing=12),

                ft.Container(height=10),

                self._create_summary_stats_row(session_data, total_questions, correct_count, answered_count),

                ft.Container(height=5),
                ft.Divider(color=COLORS['secondary'])
            ], spacing=5)

            # Create questions review content
            questions_content = self.create_questions_review_content(review_data)

            # Scrollable content area
            content_area = ft.Container(
                content=ft.Column([
                    ft.Text("📝 Questions Review", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(height=15),
                    questions_content
                ], spacing=0, scroll=ft.ScrollMode.AUTO),
                height=dialog_height - 250,
                padding=ft.padding.all(20)
            )

            # Create the dialog
            review_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Container(
                    content=header_content,
                    padding=ft.padding.only(bottom=10)
                ),
                content=ft.Container(
                    content=content_area,
                    width=dialog_width - 100,
                    height=dialog_height - 200
                ),
                actions=[
                    ft.Row([
                        ft.TextButton(
                            t('close'),
                            on_click=lambda e: self.close_exam_review_dialog()
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER
            )

            # Show the dialog
            self.page.dialog = review_dialog
            review_dialog.open = True
            self.page.update()

        except Exception as e:
            print(f"Error showing exam review dialog: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_dialog("Failed to display exam review")

    def close_exam_review_dialog(self):
        """Close the exam review dialog"""
        try:
            if self.page and self.page.dialog:
                self.page.dialog.open = False
                self.page.update()
        except Exception as e:
            print(f"Error closing exam review dialog: {e}")

    def _create_summary_stats_row(self, session_data, total_questions, correct_count, answered_count):
        """Create the summary statistics row"""
        stats_containers = [
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{session_data['score']:.1f}%", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(t('score'), size=12, color=COLORS['text_secondary'])
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=ft.padding.all(12),
                bgcolor=COLORS['success'] if session_data['score'] >= session_data['passing_score'] else COLORS['error'],
                border_radius=8,
                opacity=0.9
            ),

            ft.Container(
                content=ft.Column([
                    ft.Text(f"{correct_count}/{total_questions}", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Correct", size=12, color=COLORS['text_secondary'])
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=ft.padding.all(12),
                bgcolor=COLORS['surface'],
                border_radius=8,
                border=ft.border.all(1, COLORS['secondary'])
            ),

            ft.Container(
                content=ft.Column([
                    ft.Text(f"{answered_count}/{total_questions}", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Answered", size=12, color=COLORS['text_secondary'])
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=ft.padding.all(12),
                bgcolor=COLORS['surface'],
                border_radius=8,
                border=ft.border.all(1, COLORS['secondary'])
            ),

            ft.Container(
                content=ft.Column([
                    ft.Text(f"{session_data['duration_seconds']//60}m", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(t('duration'), size=12, color=COLORS['text_secondary'])
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=ft.padding.all(12),
                bgcolor=COLORS['surface'],
                border_radius=8,
                border=ft.border.all(1, COLORS['secondary'])
            )
        ]

        if session_data.get('use_question_pool', False):
            question_pool_container = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.SHUFFLE, size=16, color=COLORS['primary']),
                    ft.Text("Question Pool", size=10, color=COLORS['text_secondary'], text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=ft.padding.all(12),
                bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                border_radius=8,
                border=ft.border.all(1, COLORS['primary']),
                tooltip=f"Selected {session_data.get('questions_to_select', total_questions)} questions from question pool"
            )
            stats_containers.append(question_pool_container)

        return ft.Row(stats_containers, alignment=ft.MainAxisAlignment.SPACE_AROUND)

    def create_questions_review_content(self, review_data):
        """Create scrollable content showing all questions"""
        try:
            question_cards = []

            for i, question_data in enumerate(review_data, 1):
                # Determine status
                if question_data['user_answer_text'] is None:
                    status_color = COLORS['secondary']
                    status_icon = ft.icons.HELP_OUTLINE
                    status_text = "Not Answered"
                elif question_data['is_correct']:
                    status_color = COLORS['success']
                    status_icon = ft.icons.CHECK_CIRCLE
                    status_text = "Correct"
                else:
                    status_color = COLORS['error']
                    status_icon = ft.icons.CANCEL
                    status_text = "Incorrect"

                question_card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Question {i}", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            self.create_points_display(question_data),
                            ft.Container(width=15),
                            ft.Row([
                                ft.Icon(status_icon, color=status_color, size=20),
                                ft.Text(status_text, color=status_color, weight=ft.FontWeight.BOLD)
                            ], spacing=8)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                        ft.Container(height=10),

                        ft.Text(
                            question_data['question_text'],
                            size=14,
                            color=COLORS['text_primary'],
                            selectable=True
                        ),

                        ft.Container(height=15),

                        self.create_answer_comparison_section(question_data),

                        self.create_explanation_section(question_data)

                    ], spacing=0),
                    padding=ft.padding.all(20),
                    margin=ft.margin.only(bottom=15),
                    bgcolor=COLORS['surface'],
                    border_radius=8,
                    border=ft.border.all(1, COLORS['secondary']) if not question_data['is_correct'] and question_data['user_answer_text'] is not None
                           else ft.border.all(1, status_color) if question_data['user_answer_text'] is not None
                           else ft.border.all(1, COLORS['secondary'])
                )

                question_cards.append(question_card)

            return ft.Column(question_cards, spacing=0)

        except Exception as e:
            print(f"Error creating questions review content: {e}")
            return ft.Text("Error loading question review content", color=COLORS['error'])

    def create_points_display(self, question_data):
        """Create points display"""
        try:
            total_points = question_data.get('points', 1.0)
            points_earned = question_data.get('points_earned')
            grading_status = question_data.get('grading_status', 'not_answered')
            question_type = question_data.get('question_type', '')

            if question_type in ['essay', 'short_answer']:
                if grading_status == 'pending':
                    return ft.Text(
                        "Pending Grading",
                        size=12,
                        color=COLORS['warning'],
                        weight=ft.FontWeight.W_500,
                        italic=True
                    )
                elif grading_status == 'graded' and points_earned is not None:
                    return ft.Text(
                        f"{points_earned}/{total_points} pts",
                        size=12,
                        color=COLORS['success'],
                        weight=ft.FontWeight.W_500
                    )
                else:
                    return ft.Text(
                        f"Not Answered ({total_points} pts)",
                        size=12,
                        color=COLORS['text_secondary'],
                        weight=ft.FontWeight.W_500
                    )
            else:
                if points_earned is not None:
                    return ft.Text(
                        f"{points_earned}/{total_points} pts",
                        size=12,
                        color=COLORS['success'] if points_earned > 0 else COLORS['error'],
                        weight=ft.FontWeight.W_500
                    )
                else:
                    return ft.Text(
                        f"Total: {total_points} pts",
                        size=12,
                        color=COLORS['text_secondary'],
                        weight=ft.FontWeight.W_500
                    )

        except Exception as e:
            print(f"Error creating points display: {e}")
            return ft.Text(
                f"{question_data.get('points', 1.0)} pts",
                size=12,
                color=COLORS['text_secondary'],
                weight=ft.FontWeight.W_500
            )

    def create_answer_comparison_section(self, question_data):
        """Create answer comparison section"""
        try:
            question_type = question_data['question_type']

            if question_type == 'single_choice':
                return ft.Column([
                    ft.Text("Type: Single Choice", size=12, color=COLORS['text_secondary'], italic=True),
                    ft.Container(height=8),
                    ft.Column([
                        self.create_option_display(option, question_data)
                        for option in question_data['options']
                    ], spacing=6),
                    ft.Container(height=10),
                    self.create_answer_summary(question_data)
                ], spacing=0)

            elif question_type == 'multiple_choice':
                return ft.Column([
                    ft.Text("Type: Multiple Choice", size=12, color=COLORS['text_secondary'], italic=True),
                    ft.Container(height=8),
                    ft.Column([
                        self.create_option_display(option, question_data)
                        for option in question_data['options']
                    ], spacing=6),
                    ft.Container(height=10),
                    self.create_answer_summary(question_data)
                ], spacing=0)

            elif question_type == 'true_false':
                user_answer = question_data.get('user_answer_text', 'Not answered')
                correct_answer = question_data.get('correct_answer_text', 'N/A')
                return ft.Column([
                    ft.Text("Type: True/False", size=12, color=COLORS['text_secondary'], italic=True),
                    ft.Container(height=8),
                    self.create_text_answer_display(user_answer, correct_answer)
                ], spacing=0)

            elif question_type in ['short_answer', 'essay']:
                user_answer = question_data.get('user_answer_text', 'Not answered')
                correct_answer = question_data.get('correct_answer_text', 'Manual grading required')
                question_type_display = t('short_answer') if question_type == 'short_answer' else t('essay')
                return ft.Column([
                    ft.Text(f"Type: {question_type_display}", size=12, color=COLORS['text_secondary'], italic=True),
                    ft.Container(height=8),
                    self.create_text_answer_display(user_answer, correct_answer, is_text_question=True)
                ], spacing=0)

            else:
                return ft.Text(f"Unsupported question type: {question_type}", color=COLORS['error'])

        except Exception as e:
            print(f"Error creating answer comparison section: {e}")
            return ft.Text("Error loading answer comparison", color=COLORS['error'])

    def create_option_display(self, option, question_data):
        """Create display for a single option"""
        try:
            option_id = option['id']
            option_text = option['option_text']
            is_correct_option = option['is_correct']

            user_selected = False
            if question_data['question_type'] == 'single_choice':
                user_selected = question_data.get('user_answer') == option_id
            elif question_data['question_type'] == 'multiple_choice':
                user_answers = question_data.get('user_answer', [])
                user_selected = option_id in user_answers if user_answers else False

            if is_correct_option and user_selected:
                bg_color = ft.colors.with_opacity(0.1, COLORS['success'])
                border_color = COLORS['success']
                icon = ft.icons.CHECK_CIRCLE
                icon_color = COLORS['success']
            elif is_correct_option and not user_selected:
                bg_color = ft.colors.with_opacity(0.05, COLORS['success'])
                border_color = COLORS['success']
                icon = ft.icons.CHECK_CIRCLE_OUTLINE
                icon_color = COLORS['success']
            elif not is_correct_option and user_selected:
                bg_color = ft.colors.with_opacity(0.1, COLORS['error'])
                border_color = COLORS['error']
                icon = ft.icons.CANCEL
                icon_color = COLORS['error']
            else:
                bg_color = COLORS['background']
                border_color = COLORS['secondary']
                icon = ft.icons.RADIO_BUTTON_UNCHECKED
                icon_color = COLORS['text_secondary']

            return ft.Container(
                content=ft.Row([
                    ft.Icon(icon, color=icon_color, size=18),
                    ft.Text(option_text, size=14, expand=True),
                    ft.Text(
                        "✓ Correct" if is_correct_option else "",
                        size=12,
                        color=COLORS['success'],
                        weight=ft.FontWeight.BOLD
                    ) if is_correct_option else ft.Container()
                ], spacing=12),
                padding=ft.padding.all(12),
                bgcolor=bg_color,
                border_radius=6,
                border=ft.border.all(1, border_color)
            )

        except Exception as e:
            print(f"Error creating option display: {e}")
            return ft.Text(f"Error: {option_text}", color=COLORS['error'])

    def create_text_answer_display(self, user_answer, correct_answer, is_text_question=False):
        """Create display for text-based answers"""
        try:
            return ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Your Answer:", size=12, weight=ft.FontWeight.BOLD, color=COLORS['text_secondary']),
                        ft.Container(height=5),
                        ft.Text(
                            user_answer if user_answer else "Not answered",
                            size=14,
                            color=COLORS['text_primary'] if user_answer else COLORS['text_secondary'],
                            selectable=True
                        )
                    ], spacing=0),
                    padding=ft.padding.all(12),
                    bgcolor=COLORS['background'],
                    border_radius=6,
                    border=ft.border.all(1, COLORS['secondary'])
                ),

                ft.Container(height=10),

                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Correct Answer:" if not is_text_question else "Reference Answer:",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS['text_secondary']
                        ),
                        ft.Container(height=5),
                        ft.Text(
                            correct_answer if correct_answer else "N/A",
                            size=14,
                            color=COLORS['success'] if not is_text_question else COLORS['text_secondary'],
                            selectable=True
                        )
                    ], spacing=0),
                    padding=ft.padding.all(12),
                    bgcolor=ft.colors.with_opacity(0.05, COLORS['success']) if not is_text_question else COLORS['background'],
                    border_radius=6,
                    border=ft.border.all(1, COLORS['success']) if not is_text_question else ft.border.all(1, COLORS['secondary'])
                ) if correct_answer and correct_answer != "Manual grading required" else ft.Container(
                    content=ft.Text(
                        "📝 This answer requires manual grading by instructor",
                        size=12,
                        color=COLORS['text_secondary'],
                        italic=True
                    ),
                    padding=ft.padding.all(12),
                    bgcolor=COLORS['background'],
                    border_radius=6,
                    border=ft.border.all(1, COLORS['secondary'])
                )
            ], spacing=0)

        except Exception as e:
            print(f"Error creating text answer display: {e}")
            return ft.Text("Error displaying answer", color=COLORS['error'])

    def create_answer_summary(self, question_data):
        """Create answer summary for choice questions"""
        try:
            if question_data['question_type'] == 'single_choice':
                user_text = question_data.get('user_answer_text', 'Not answered')
                correct_text = question_data.get('correct_answer_text', 'N/A')

                return ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text("You selected:", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(user_text, size=12, color=COLORS['text_primary'])
                        ], spacing=2),
                        ft.Container(width=20),
                        ft.Column([
                            ft.Text("Correct answer:", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(correct_text, size=12, color=COLORS['success'])
                        ], spacing=2)
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.all(12),
                    bgcolor=COLORS['background'],
                    border_radius=6
                )

            elif question_data['question_type'] == 'multiple_choice':
                user_texts = question_data.get('user_answer_text', [])
                correct_texts = question_data.get('correct_answer_text', [])

                user_display = ", ".join(user_texts) if user_texts else "None selected"
                correct_display = ", ".join(correct_texts) if correct_texts else "N/A"

                return ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text("You selected:", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(user_display, size=12, color=COLORS['text_primary'])
                        ], spacing=2, expand=True),
                        ft.Container(width=20),
                        ft.Column([
                            ft.Text("Correct answers:", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(correct_display, size=12, color=COLORS['success'])
                        ], spacing=2, expand=True)
                    ], alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.all(12),
                    bgcolor=COLORS['background'],
                    border_radius=6
                )

            return ft.Container()

        except Exception as e:
            print(f"Error creating answer summary: {e}")
            return ft.Container()

    def create_explanation_section(self, question_data):
        """Create explanation section if available"""
        try:
            explanation = question_data.get('explanation')
            if explanation and explanation.strip():
                return ft.Column([
                    ft.Container(height=15),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.LIGHTBULB_OUTLINE, color=COLORS['warning'], size=18),
                                ft.Text("Explanation:", size=12, weight=ft.FontWeight.BOLD, color=COLORS['warning'])
                            ], spacing=8),
                            ft.Container(height=5),
                            ft.Text(
                                explanation,
                                size=13,
                                color=COLORS['text_primary'],
                                selectable=True
                            )
                        ], spacing=0),
                        padding=ft.padding.all(12),
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['warning']),
                        border_radius=6,
                        border=ft.border.all(1, COLORS['warning'])
                    )
                ], spacing=0)

            return ft.Container()

        except Exception as e:
            print(f"Error creating explanation section: {e}")
            return ft.Container()

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

            ft.Container(height=10),

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