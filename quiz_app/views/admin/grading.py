import flet as ft
from datetime import datetime
from quiz_app.config import COLORS

class Grading(ft.UserControl):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.ungraded_answers = []
        self.current_answer = None
        self.parent_dashboard = None  # Reference to parent dashboard for badge updates
        
        # Load ungraded essay/short answer submissions
        self.load_ungraded_answers()
        
        # Main content
        self.answers_list = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Exam")),
                ft.DataColumn(ft.Text("Student")),
                ft.DataColumn(ft.Text("Questions")),
                ft.DataColumn(ft.Text("Submitted")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )
        
        self.update_answers_table()
    
    def load_ungraded_answers(self):
        """Load exam sessions that have ungraded essay/short answer questions"""
        try:
            # Get ALL exam sessions with ungraded essay/short_answer questions
            # (regardless of exam's "show_results" setting - that only controls result release)
            self.ungraded_answers = self.db.execute_query("""
                SELECT 
                    es.id as session_id,
                    es.start_time,
                    es.end_time,
                    e.id as exam_id,
                    e.title as exam_title,
                    u.id as user_id,
                    u.full_name as student_name,
                    u.username as student_username,
                    COUNT(ua.id) as ungraded_count,
                    GROUP_CONCAT(q.question_type) as question_types
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                JOIN users u ON es.user_id = u.id
                JOIN user_answers ua ON ua.session_id = es.id
                JOIN questions q ON ua.question_id = q.id
                WHERE q.question_type IN ('essay', 'short_answer')
                AND ua.points_earned IS NULL
                AND ua.answer_text IS NOT NULL
                AND ua.answer_text != ''
                AND es.is_completed = 1
                GROUP BY es.id, e.id, u.id
                HAVING COUNT(ua.id) > 0
                ORDER BY es.end_time DESC
            """)
            
            print(f"Found {len(self.ungraded_answers)} exam sessions with ungraded essay/short answer submissions")
            
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
    
    def update_answers_table(self):
        """Update the answers table with current data"""
        self.answers_list.rows.clear()
        
        for session in self.ungraded_answers:
            # Create questions summary
            question_summary = f"{session['ungraded_count']} essay/short answer questions"
            
            self.answers_list.rows.append(
                ft.DataRow([
                    ft.DataCell(ft.Text(session['exam_title'][:30] + "..." if len(session['exam_title']) > 30 else session['exam_title'])),
                    ft.DataCell(ft.Text(session['student_name'])),
                    ft.DataCell(ft.Text(question_summary)),
                    ft.DataCell(ft.Text(self.format_date(session['end_time']))),
                    ft.DataCell(ft.Text("Needs Grading", color=COLORS['warning'])),
                    ft.DataCell(
                        ft.ElevatedButton(
                            "Grade Exam",
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
                    ft.DataCell(ft.Text("No exam sessions with ungraded essay/short answer questions found")),
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
        
        # Get all ungraded essay/short_answer questions for this session (avoid duplicates)
        session_questions = self.db.execute_query("""
            SELECT 
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
            AND ua.id = (
                SELECT MAX(ua2.id) 
                FROM user_answers ua2 
                WHERE ua2.session_id = ua.session_id 
                AND ua2.question_id = ua.question_id
            )
            ORDER BY q.order_index, q.id
        """, (session_data['session_id'],))
        
        if not session_questions:
            if self.page:
                self.page.show_snack_bar(
                    ft.SnackBar(content=ft.Text("No ungraded questions found for this session"))
                )
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
                        ft.Text(f"Question {i+1}:", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.Text(f"Type: {question['question_type'].replace('_', ' ').title()}", 
                               size=12, color=COLORS['text_secondary'])
                    ]),
                    ft.Container(height=5),
                    
                    # Question text
                    ft.Text(question['question_text'], size=14, weight=ft.FontWeight.W_500),
                    ft.Container(height=10),
                    
                    # Student answer
                    ft.Text("Student Answer:", size=14, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(
                            question['answer_text'] or "No answer provided",
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
                        ft.Text(f"Max: {question['max_points']}", size=12, color=COLORS['text_secondary'])
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
                ft.Text("Grade Exam Session", color=COLORS['primary'], weight=ft.FontWeight.BOLD)
            ], spacing=8),
            content=ft.Container(
                content=ft.Column([
                    # Session info header (fixed)
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Exam: {session_data['exam_title']}", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Student: {session_data['student_name']}", size=14, weight=ft.FontWeight.W_500),
                            ft.Text(f"Submitted: {self.format_date(session_data['end_time'])}", size=12, color=COLORS['text_secondary']),
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
                    "Cancel",
                    on_click=self.close_session_grading_dialog
                ),
                ft.ElevatedButton(
                    "Save All Grades",
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
                self.update_answers_table()
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
                    ft.SnackBar(content=ft.Text("Error saving grades"))
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
        """Refresh the ungraded answers data"""
        self.load_ungraded_answers()
        self.update_answers_table()
        self.update()
    
    def build(self):
        return ft.Container(
            content=ft.Column([
                # Header
                ft.Container(
                    content=ft.Row([
                        ft.Text("Grading Center", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "Refresh",
                            icon=ft.icons.REFRESH,
                            on_click=self.refresh_data,
                            style=ft.ButtonStyle(bgcolor=COLORS['secondary'], color=ft.colors.WHITE)
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(bottom=20)
                ),
                
                # Info text
                ft.Text(
                    f"Exam sessions with ungraded essay/short answer questions: {len(self.ungraded_answers)}",
                    size=16,
                    color=COLORS['text_secondary']
                ),
                ft.Container(height=10),
                
                # Answers table
                ft.Container(
                    content=ft.ListView(
                        controls=[self.answers_list],
                        expand=True,
                        auto_scroll=False
                    ),
                    bgcolor=COLORS['surface'],
                    border_radius=8,
                    padding=ft.padding.all(16),
                    expand=True
                )
            ], spacing=0),
            padding=ft.padding.all(20),
            expand=True
        )