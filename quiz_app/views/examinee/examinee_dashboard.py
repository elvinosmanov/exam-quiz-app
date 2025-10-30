import flet as ft
from datetime import datetime
from quiz_app.config import COLORS

class ExamineeDashboard(ft.UserControl):
    def __init__(self, session_manager, user_data, logout_callback):
        super().__init__()
        self.session_manager = session_manager
        self.user_data = user_data
        self.logout_callback = logout_callback
        self.db = None  # Will be set when needed
        
        # Initialize database
        from quiz_app.database.database import Database
        self.db = Database()
        
        # Navigation state
        self.selected_nav_index = 0
        self.nav_items = [
            {"title": "Dashboard", "icon": ft.icons.DASHBOARD},
            {"title": "Available Exams", "icon": ft.icons.QUIZ},
            {"title": "My Results", "icon": ft.icons.ASSESSMENT},
            {"title": "Profile", "icon": ft.icons.PERSON}
        ]
        
        # Dynamic height properties
        self.dynamic_height = 700  # Default fallback height
        self.TOP_BAR_HEIGHT = 65   # Top bar height (padding + font size + border)
        self.BUFFER = 20           # Buffer for margins/padding
        self.MIN_HEIGHT = 600      # Minimum height for small windows
        
        # Create navigation rail WITHOUT expand - let parent container handle constraints
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=item["icon"],
                    label=item["title"]
                ) for item in self.nav_items
            ],
            on_change=self.nav_changed,
            bgcolor=COLORS['surface']
        )
        
        # Main content area
        self.content_area = ft.Container(
            expand=True,
            padding=ft.padding.all(20),
            bgcolor=COLORS['background']
        )
        
        # Top bar
        self.top_bar = self.create_top_bar()
        
        # Main container (will be set in build method)
        self.main_container = None
        
        # Don't initialize dashboard view here - wait until added to page
    
    def did_mount(self):
        """Called after the control is added to the page"""
        super().did_mount()
        if self.page:
            # Set up resize event handler
            self.page.on_resized = self.page_resized
            # Calculate initial height
            self.update_height()
        self.show_dashboard()
    
    def create_top_bar(self):
        return ft.Container(
            content=ft.Row([
                ft.Text(
                    "Quiz Examination System",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS['text_primary']
                ),
                ft.Row([
                    ft.Icon(ft.icons.PERSON, color=COLORS['text_secondary']),
                    ft.Text(
                        f"Welcome, {self.user_data['full_name']}",
                        color=COLORS['text_secondary']
                    ),
                    ft.IconButton(
                        icon=ft.icons.LOGOUT,
                        tooltip="Logout",
                        on_click=self.logout_clicked,
                        icon_color=COLORS['error']
                    )
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            bgcolor=COLORS['surface'],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS['secondary']))
        )
    
    def calculate_dynamic_height(self):
        """Calculate dynamic height based on current window size"""
        if self.page and hasattr(self.page, 'window') and self.page.window.height:
            available_height = self.page.window.height - self.TOP_BAR_HEIGHT - self.BUFFER
            return max(available_height, self.MIN_HEIGHT)
        return self.dynamic_height  # Return current height if page not available
    
    def update_height(self):
        """Update the dynamic height and refresh the layout"""
        new_height = self.calculate_dynamic_height()
        if new_height != self.dynamic_height:
            self.dynamic_height = new_height
            if self.main_container:
                self.main_container.height = self.dynamic_height
                if self.page:  # Only update if control is added to page
                    self.update()
    
    def page_resized(self, e):
        """Handle window resize events"""
        self.update_height()
    
    def build(self):
        # Create main container with dynamic height
        self.main_container = ft.Container(
            content=ft.Row([
                self.nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area
            ], spacing=0),
            expand=True,
            height=self.dynamic_height  # Dynamic height to bound NavigationRail
        )
        
        return ft.Column([
            self.top_bar,
            self.main_container
        ], spacing=0)
    
    def nav_changed(self, e):
        self.selected_nav_index = e.control.selected_index
        if self.selected_nav_index == 0:
            self.show_dashboard()
        elif self.selected_nav_index == 1:
            self.show_available_exams()
        elif self.selected_nav_index == 2:
            self.show_my_results()
        elif self.selected_nav_index == 3:
            self.show_profile()
    
    def set_content(self, content):
        self.content_area.content = content
        if self.page:  # Only update if control is added to page
            self.update()
    
    def show_dashboard(self):
        # Get user statistics
        stats = self.get_user_stats()
        
        # Create dashboard cards
        cards = ft.Row([
            self.create_stat_card("Total Exams", str(stats['total_exams']), ft.icons.ASSIGNMENT, COLORS['primary']),
            self.create_stat_card("Completed Exams", str(stats['completed_exams']), ft.icons.CHECK_CIRCLE, COLORS['success']),
            self.create_stat_card("Average Score", f"{stats['average_score']:.1f}%", ft.icons.GRADE, COLORS['warning']),
            self.create_stat_card("Available Exams", str(stats['available_exams']), ft.icons.QUIZ, COLORS['error'])
        ], spacing=20, wrap=True)
        
        # Recent activity
        recent_exams = self.get_recent_exam_sessions()
        
        recent_activity = ft.Column([
            ft.Text("Recent Exam Activity", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            *[ft.ListTile(
                leading=ft.Icon(
                    ft.icons.CHECK_CIRCLE if exam['is_completed'] else ft.icons.TIMER,
                    color=COLORS['success'] if exam['is_completed'] else COLORS['warning']
                ),
                title=ft.Text(exam['exam_title']),
                subtitle=ft.Text(
                    self.get_exam_score_display(exam)
                ),
                trailing=ft.Text(
                    "Completed" if exam['is_completed'] else "In Progress"
                )
            ) for exam in recent_exams[:5]]
        ], spacing=5)
        
        content = ft.Column([
            ft.Text("Dashboard", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
            ft.Divider(),
            cards,
            ft.Container(height=20),
            ft.Container(
                content=recent_activity,
                padding=ft.padding.all(20),
                bgcolor=COLORS['surface'],
                border_radius=8,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=5,
                    color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
                )
            )
        ], spacing=10)
        
        self.set_content(content)
    
    def create_stat_card(self, title, value, icon, color):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=color, size=32),
                    ft.Column([
                        ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                        ft.Text(title, size=14, color=COLORS['text_secondary'])
                    ], spacing=0)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ]),
            width=250,
            height=100,
            padding=ft.padding.all(20),
            bgcolor=COLORS['surface'],
            border_radius=8,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
            )
        )
    
    def show_available_exams(self):
        # Get available assignments for the user
        available_exams = self.get_available_exams()

        exam_cards = []
        for exam in available_exams:
            # Check if user has already taken this assignment
            sessions = self.db.execute_query("""
                SELECT COUNT(*) as attempt_count, MAX(is_completed) as has_completed
                FROM exam_sessions
                WHERE user_id = ? AND assignment_id = ?
            """, (self.user_data['id'], exam['assignment_id']))
            
            attempt_count = sessions[0]['attempt_count'] if sessions else 0
            has_completed = sessions[0]['has_completed'] if sessions else False
            
            can_take = attempt_count < exam['max_attempts']
            
            # Determine exam status
            now = datetime.now()
            if exam['start_date'] and exam['end_date']:
                start_date = datetime.fromisoformat(exam['start_date'])
                end_date = datetime.fromisoformat(exam['end_date'])
                if now < start_date:
                    status = "Scheduled"
                    status_color = COLORS['warning']
                elif now > end_date:
                    status = "Expired"
                    status_color = COLORS['error']
                    can_take = False
                else:
                    status = "Available"
                    status_color = COLORS['success']
            else:
                status = "Available"
                status_color = COLORS['success']
            
            # Create compact list-style exam card
            exam_card = ft.Container(
                content=ft.Column([
                    # Top row: Title on left, Status on right
                    ft.Row([
                        ft.Text(
                            exam['title'],
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS['text_primary'],
                            expand=True
                        ),
                        ft.Row([
                            ft.Icon(
                                ft.icons.CIRCLE,
                                color=status_color,
                                size=12
                            ),
                            ft.Text(
                                status,
                                size=14,
                                color=status_color,
                                weight=ft.FontWeight.W_500
                            )
                        ], spacing=6)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    
                    # Second row: Duration + Pass score + Attempts
                    ft.Row([
                        ft.Text(
                            f"Duration: {exam['duration_minutes']} min",
                            size=12,
                            color=COLORS['text_secondary'],
                            weight=ft.FontWeight.W_500
                        ),
                        ft.Text("|", size=12, color=COLORS['text_secondary']),
                        ft.Text(
                            f"Pass: {exam['passing_score']}%",
                            size=12,
                            color=COLORS['text_secondary']
                        ),
                        ft.Text("|", size=12, color=COLORS['text_secondary']),
                        ft.Text(
                            f"Attempts: {exam['max_attempts'] - attempt_count}/{exam['max_attempts']} left",
                            size=12,
                            color=COLORS['success'] if can_take else COLORS['error']
                        )
                    ], spacing=6),
                    
                    # Third row: Description (expanded to fill center space)
                    ft.Text(
                        exam['description'] or "No description available",
                        size=14,
                        color=COLORS['text_secondary'],
                        max_lines=4,
                        overflow=ft.TextOverflow.ELLIPSIS
                    ),
                    
                    # Bottom row: Date info + Action button
                    ft.Row([
                        ft.Row([
                            ft.Icon(ft.icons.CALENDAR_TODAY, size=14, color=COLORS['text_secondary']),
                            ft.Text(
                                f"Deadline: {exam['deadline'][:10] if exam.get('deadline') else 'No Deadline'}" if status != "Scheduled"
                                else f"Starts {exam['start_date'][:10] if exam.get('start_date') else 'TBD'}",
                                size=12,
                                color=COLORS['text_secondary']
                            )
                        ], spacing=4, expand=True),
                        ft.ElevatedButton(
                            text="Take Exam" if not has_completed else "Retake",
                            icon=ft.icons.PLAY_ARROW if can_take else ft.icons.BLOCK,
                            on_click=lambda e, assignment_id=exam['assignment_id']: self.start_exam(assignment_id),
                            disabled=not can_take,
                            style=ft.ButtonStyle(
                                bgcolor=COLORS['primary'] if can_take else COLORS['secondary'],
                                color=ft.colors.WHITE,
                                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                                text_style=ft.TextStyle(
                                    size=14,
                                    weight=ft.FontWeight.W_500
                                )
                            ),
                            height=36
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=8),
                padding=ft.padding.all(12),
                bgcolor=COLORS['surface'],
                border_radius=8,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=5,
                    color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
                )
            )
            exam_cards.append(exam_card)
        
        content = ft.Column([
            ft.Text("Available Exams", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
            ft.Divider(),
            ft.Container(
                content=ft.Column(exam_cards, spacing=20, scroll=ft.ScrollMode.AUTO) if exam_cards else ft.Text(
                    "No exams available at the moment.",
                    size=16,
                    color=COLORS['text_secondary']
                ),
                bgcolor=COLORS['surface'],
                padding=ft.padding.all(20),
                border_radius=8,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=5,
                    color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
                )
            )
        ], spacing=10)
        
        self.set_content(content)
    
    def show_my_results(self):
        # Get user's exam results
        results = self.get_user_results()
        
        if not results:
            content = ft.Column([
                ft.Text("My Results", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Divider(),
                ft.Text("No exam results yet.", size=16, color=COLORS['text_secondary'])
            ])
            self.set_content(content)
            return
        
        # Create results table
        results_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Exam")),
                ft.DataColumn(ft.Text("Date")),
                ft.DataColumn(ft.Text("Score")),
                ft.DataColumn(ft.Text("Status")),
                ft.DataColumn(ft.Text("Duration")),
                ft.DataColumn(ft.Text("Actions"))
            ],
            rows=[],
            width=float("inf"),
            column_spacing=20
        )
        
        for result in results:
            # Check if results should be shown to students
            show_results = result.get('show_results', 1)
            
            # Check if exam has ungraded essay/short_answer questions
            has_ungraded_manual = False
            try:
                ungraded_manual = self.db.execute_query("""
                    SELECT COUNT(*) as count
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    WHERE ua.session_id = ?
                    AND q.question_type IN ('essay', 'short_answer')
                    AND ua.points_earned IS NULL
                    AND ua.answer_text IS NOT NULL
                    AND ua.answer_text != ''
                """, (result['id'],))
                
                has_ungraded_manual = ungraded_manual[0]['count'] > 0 if ungraded_manual else False
            except Exception as e:
                print(f"Error checking ungraded questions for session {result['id']}: {e}")
                has_ungraded_manual = False
            
            # Show results only if: 1) show_results is enabled AND 2) no ungraded manual questions
            if show_results and not has_ungraded_manual:
                # Show normal results
                status = "Passed" if result['score'] >= result['passing_score'] else "Failed"
                status_color = COLORS['success'] if status == "Passed" else COLORS['error']
                score_text = f"{result['score']:.1f}%"
                status_text = status
                
                # Show View Details button
                action_cell = ft.DataCell(
                    ft.IconButton(
                        icon=ft.icons.VISIBILITY,
                        tooltip="View Details",
                        on_click=lambda e, session_id=result['id']: self.view_exam_details(session_id)
                    )
                )
            else:
                # Results not available - determine why
                if has_ungraded_manual:
                    # Exam has ungraded essay/short_answer questions
                    score_text = "Pending"
                    status_text = "Pending Grading"
                    status_color = COLORS['warning']
                elif not show_results:
                    # All questions graded but results not released by instructor
                    score_text = "Graded"
                    status_text = "Pending Release"
                    status_color = COLORS['warning']
                else:
                    # Fallback
                    score_text = "Hidden"
                    status_text = "Results Hidden"
                    status_color = COLORS['text_secondary']
                
                # No action button for unreleased results
                action_cell = ft.DataCell(ft.Text("-", color=COLORS['text_secondary']))
            
            duration = f"{result['duration_seconds']//60}m {result['duration_seconds']%60}s" if result['duration_seconds'] else "N/A"
            
            results_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(result['exam_title'])),
                        ft.DataCell(ft.Text(result['start_time'][:10])),
                        ft.DataCell(ft.Text(score_text)),
                        ft.DataCell(ft.Text(status_text, color=status_color)),
                        ft.DataCell(ft.Text(duration)),
                        action_cell
                    ]
                )
            )
        
        content = ft.Column([
            ft.Text("My Results", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
            ft.Divider(),
            ft.Container(
                content=ft.ListView(
                    controls=[results_table],
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
        
        self.set_content(content)
    
    def show_profile(self):
        # Create profile form
        profile_form = ft.Column([
            ft.Text("Profile Information", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Row([
                ft.TextField(
                    label="Full Name",
                    value=self.user_data['full_name'],
                    read_only=True
                ),
                ft.TextField(
                    label="Username",
                    value=self.user_data['username'],
                    read_only=True
                )
            ], spacing=20),
            ft.Row([
                ft.TextField(
                    label="Email",
                    value=self.user_data['email'],
                    read_only=True
                ),
                ft.TextField(
                    label="Department",
                    value=self.user_data['department'] or "Not specified",
                    read_only=True
                )
            ], spacing=20),
            ft.Row([
                ft.TextField(
                    label="Unit",
                    value=self.user_data.get('unit') or "Not specified",
                    read_only=True
                ),
                ft.TextField(
                    label="Employee ID",
                    value=self.user_data.get('employee_id') or "Not specified",
                    read_only=True
                )
            ], spacing=20),
            ft.Container(height=20),
            ft.ElevatedButton(
                text="Change Password",
                icon=ft.icons.LOCK,
                on_click=self.show_change_password_dialog,
                style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
            )
        ], spacing=15)
        
        content = ft.Column([
            ft.Text("Profile", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
            ft.Divider(),
            ft.Container(
                content=profile_form,
                padding=ft.padding.all(20),
                bgcolor=COLORS['surface'],
                border_radius=8,
                shadow=ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=5,
                    color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
                )
            )
        ], spacing=10)
        
        self.set_content(content)
    
    def get_user_stats(self):
        # Get available exams count
        available_exams = len(self.get_available_exams())

        # Get total exams count (all active exams in the system)
        total = self.db.execute_single("""
            SELECT COUNT(*) as count FROM exams
            WHERE is_active = 1
        """)
        total_exams = total['count'] if total else 0

        # Get completed exams count
        completed = self.db.execute_single("""
            SELECT COUNT(*) as count FROM exam_sessions
            WHERE user_id = ? AND is_completed = 1
        """, (self.user_data['id'],))
        completed_exams = completed['count'] if completed else 0

        # Get average score (excluding exams with ungraded essay questions)
        average_score = self.calculate_average_score_excluding_pending()

        return {
            'total_exams': total_exams,
            'available_exams': available_exams,
            'completed_exams': completed_exams,
            'average_score': average_score
        }
    
    def get_available_exams(self):
        # Get assignments (not exams) user has permission to take
        return self.db.execute_query("""
            SELECT
                ea.id as assignment_id,
                ea.assignment_name as title,
                e.description,
                e.category,
                ea.duration_minutes,
                ea.passing_score,
                ea.max_attempts,
                ea.start_date,
                ea.end_date,
                ea.deadline,
                ea.exam_id,
                ea.randomize_questions,
                ea.show_results,
                ea.enable_fullscreen,
                ea.prevent_focus_loss,
                ea.enable_logging,
                ea.enable_pattern_analysis,
                ea.use_question_pool,
                ea.questions_to_select,
                ea.easy_questions_count,
                ea.medium_questions_count,
                ea.hard_questions_count
            FROM exam_assignments ea
            JOIN exams e ON ea.exam_id = e.id
            JOIN assignment_users au ON ea.id = au.assignment_id
            WHERE ea.is_active = 1
            AND au.user_id = ?
            AND au.is_active = 1
            ORDER BY ea.created_at DESC
        """, (self.user_data['id'],))
    
    def get_recent_exam_sessions(self):
        return self.db.execute_query("""
            SELECT es.*,
                   COALESCE(ea.assignment_name, e.title) as exam_title
            FROM exam_sessions es
            JOIN exams e ON es.exam_id = e.id
            LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
            WHERE es.user_id = ?
            ORDER BY es.start_time DESC
            LIMIT 10
        """, (self.user_data['id'],))
    
    def get_exam_score_display(self, exam):
        """Get appropriate score display text for dashboard, checking for ungraded questions"""
        try:
            if not exam['is_completed']:
                return f"Started: {exam['start_time'][:16]}" if exam['start_time'] else "Not started"
            
            if exam['score'] is None:
                return "Score not available"
            
            # Check if this exam session has ungraded essay/short_answer questions
            has_ungraded = False
            try:
                ungraded_count = self.db.execute_single("""
                    SELECT COUNT(*) as count
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    WHERE ua.session_id = ?
                    AND q.question_type IN ('essay', 'short_answer')
                    AND ua.points_earned IS NULL
                    AND ua.answer_text IS NOT NULL
                    AND ua.answer_text != ''
                """, (exam['id'],))
                
                has_ungraded = ungraded_count['count'] > 0 if ungraded_count else False
            except Exception as e:
                print(f"Error checking ungraded questions for exam {exam['id']}: {e}")
                has_ungraded = False
            
            if has_ungraded:
                return "Pending Grading"
            else:
                return f"Score: {exam['score']:.1f}%"
                
        except Exception as e:
            print(f"Error getting exam score display: {e}")
            return "Score not available"
    
    def calculate_average_score_excluding_pending(self):
        """Calculate average score excluding exams with ungraded essay questions"""
        try:
            # Get all completed exam sessions
            completed_sessions = self.db.execute_query("""
                SELECT id, score FROM exam_sessions 
                WHERE user_id = ? AND is_completed = 1 AND score IS NOT NULL
            """, (self.user_data['id'],))
            
            if not completed_sessions:
                return 0
            
            valid_scores = []
            for session in completed_sessions:
                # Check if this session has ungraded questions
                has_ungraded = False
                try:
                    ungraded_count = self.db.execute_single("""
                        SELECT COUNT(*) as count
                        FROM user_answers ua
                        JOIN questions q ON ua.question_id = q.id
                        WHERE ua.session_id = ?
                        AND q.question_type IN ('essay', 'short_answer')
                        AND ua.points_earned IS NULL
                        AND ua.answer_text IS NOT NULL
                        AND ua.answer_text != ''
                    """, (session['id'],))
                    
                    has_ungraded = ungraded_count['count'] > 0 if ungraded_count else False
                except Exception as e:
                    print(f"Error checking session {session['id']}: {e}")
                    has_ungraded = False
                
                # Only include scores from fully graded exams
                if not has_ungraded:
                    valid_scores.append(session['score'])
            
            return sum(valid_scores) / len(valid_scores) if valid_scores else 0
            
        except Exception as e:
            print(f"Error calculating average score: {e}")
            return 0
    
    def get_user_results(self):
        return self.db.execute_query("""
            SELECT es.*,
                   COALESCE(ea.assignment_name, e.title) as exam_title,
                   COALESCE(ea.passing_score, e.passing_score) as passing_score,
                   COALESCE(ea.show_results, e.show_results) as show_results
            FROM exam_sessions es
            JOIN exams e ON es.exam_id = e.id
            LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
            WHERE es.user_id = ? AND es.is_completed = 1
            ORDER BY es.start_time DESC
        """, (self.user_data['id'],))
    
    def start_exam(self, assignment_id):
        """Start taking an assignment"""
        try:
            # Get page reference - try multiple sources
            page_ref = None

            # First try the stored page reference from main.py
            if hasattr(self, '_page_ref') and self._page_ref:
                page_ref = self._page_ref
                print("Using stored page reference from main.py")
            # Then try the built-in page property
            elif self.page:
                page_ref = self.page
                print("Using built-in page property")
            else:
                print("Error: No page reference available. Dashboard may not be properly mounted.")
                print(f"Dashboard page reference: {self.page}")
                print(f"Stored page reference: {getattr(self, '_page_ref', 'Not set')}")
                self.show_error_dialog("Cannot start exam: Page context not available")
                return

            # Get assignment data with exam information
            assignment_data = self.db.execute_single("""
                SELECT
                    ea.*,
                    e.title,
                    e.description,
                    e.category,
                    e.passing_score
                FROM exam_assignments ea
                JOIN exams e ON ea.exam_id = e.id
                WHERE ea.id = ? AND ea.is_active = 1
            """, (assignment_id,))

            if not assignment_data:
                self.show_error_dialog("Assignment not found or inactive")
                return

            # Check if user has permission to take this assignment
            permission = self.db.execute_single("""
                SELECT * FROM assignment_users
                WHERE user_id = ? AND assignment_id = ? AND is_active = 1
            """, (self.user_data['id'], assignment_id))

            if not permission:
                self.show_error_dialog("You don't have permission to take this assignment")
                return

            # Check attempt limits
            attempts = self.db.execute_single("""
                SELECT COUNT(*) as count FROM exam_sessions
                WHERE user_id = ? AND assignment_id = ?
            """, (self.user_data['id'], assignment_id))

            attempt_count = attempts['count'] if attempts else 0
            if attempt_count >= assignment_data['max_attempts']:
                self.show_error_dialog(f"Maximum attempts ({assignment_data['max_attempts']}) reached for this assignment")
                return

            # Check assignment schedule
            now = datetime.now()
            if assignment_data['start_date']:
                start_date = datetime.fromisoformat(assignment_data['start_date'])
                if now < start_date:
                    self.show_error_dialog("This assignment is not yet available")
                    return

            if assignment_data['end_date']:
                end_date = datetime.fromisoformat(assignment_data['end_date'])
                if now > end_date:
                    self.show_error_dialog("This assignment has expired")
                    return

            if assignment_data['deadline']:
                deadline = datetime.fromisoformat(assignment_data['deadline'])
                if now > deadline:
                    self.show_error_dialog("This assignment deadline has passed")
                    return

            # Check if fullscreen mode is enabled for this assignment
            enable_fullscreen = bool(assignment_data.get('enable_fullscreen', 0))
            original_fullscreen_state = page_ref.window_full_screen if page_ref else False
            
            # Enable fullscreen if required
            if enable_fullscreen and page_ref:
                try:
                    page_ref.window_full_screen = True
                    page_ref.update()
                    print("Fullscreen mode enabled for exam")
                except Exception as e:
                    print(f"Warning: Could not enable fullscreen mode: {e}")
            
            # Import the new pure function exam interface
            from quiz_app.views.examinee.exam_interface import create_exam_interface
            
            # Create return callback that uses the stored page reference
            def return_callback():
                try:
                    # Restore original fullscreen state when exiting exam
                    if enable_fullscreen and page_ref:
                        try:
                            page_ref.window_full_screen = original_fullscreen_state
                            page_ref.update()
                            print("Fullscreen mode restored to original state")
                        except Exception as e:
                            print(f"Warning: Could not restore fullscreen state: {e}")
                    
                    if page_ref:
                        page_ref.controls.clear()
                        page_ref.add(self)
                        page_ref.update()
                        # Refresh the data to show updated results
                        self.show_dashboard()
                    else:
                        print("Error: No page reference available when returning from exam")
                except Exception as ex:
                    print(f"Error returning from exam: {ex}")
            
            # Create exam interface using pure function (no UserControl issues)
            # Pass both assignment data and exam_id for the exam interface
            exam_interface = create_exam_interface(
                exam_data=assignment_data,  # Contains all assignment settings
                user_data=self.user_data,
                return_callback=return_callback,
                exam_id=assignment_data['exam_id'],  # The actual exam template ID
                assignment_id=assignment_id  # The assignment instance ID
            )
            
            # Replace current content with exam interface
            if page_ref:
                page_ref.controls.clear()
                page_ref.add(exam_interface)
                page_ref.update()
                print("Successfully started exam interface")
            else:
                print("Error: No valid page reference available")
            
        except Exception as e:
            print(f"Error starting exam: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_dialog("Failed to start exam. Please try again.")


    def show_error_dialog(self, message):
        """Show error dialog"""
        # Get page reference - try multiple sources
        page_ref = None
        if hasattr(self, '_page_ref') and self._page_ref:
            page_ref = self._page_ref
        elif self.page:
            page_ref = self.page
        
        if not page_ref:
            print(f"Error (no page): {message}")
            return
            
        try:
            error_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row([
                    ft.Icon(ft.icons.ERROR, color=COLORS['error'], size=24),
                    ft.Text("Error", color=COLORS['error'], weight=ft.FontWeight.BOLD)
                ], spacing=8),
                content=ft.Text(message, size=16),
                actions=[
                    ft.ElevatedButton(
                        "OK",
                        on_click=lambda e: self.close_dialog(),
                        style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                    )
                ]
            )
            
            page_ref.dialog = error_dialog
            error_dialog.open = True
            page_ref.update()
        except Exception as e:
            print(f"Error showing dialog: {e}, Original message: {message}")

    def close_dialog(self):
        """Close the current dialog"""
        # Get page reference - try multiple sources
        page_ref = None
        if hasattr(self, '_page_ref') and self._page_ref:
            page_ref = self._page_ref
        elif self.page:
            page_ref = self.page
            
        if page_ref and page_ref.dialog:
            page_ref.dialog.open = False
            page_ref.update()
    
    def view_exam_details(self, session_id):
        """Show detailed exam review in a modal dialog"""
        try:
            print(f"Loading exam session {session_id} for review...")
            
            # Get exam session details
            session_data = self.get_exam_session_details(session_id)
            if not session_data:
                self.show_error_dialog("Exam session not found")
                return
            
            # Check if results are allowed to be shown to students
            if not session_data.get('show_results', 1):
                self.show_error_dialog("Results are not available for this exam")
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
            self.show_error_dialog("Failed to load exam details")
    
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
            # First check if this session has selected questions in session_questions table
            session_questions = self.db.execute_query("""
                SELECT q.*
                FROM questions q
                JOIN session_questions sq ON q.id = sq.question_id
                WHERE sq.session_id = ?
                ORDER BY sq.order_index, q.order_index, q.id
            """, (session_id,))
            
            if session_questions:
                # This session uses question pool - use selected questions
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
                
                # Get user's LATEST answer for this question (not the first one)
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
                    'points': question.get('points', 1.0),  # Total question points available
                    'options': options,
                    'user_answer': None,
                    'user_answer_text': None,
                    'is_correct': False,
                    'points_earned': None,  # Points awarded by instructor/auto-grading
                    'grading_status': 'not_answered'  # not_answered, pending, graded
                }
                
                # Process user answer based on question type
                if user_answer_data:
                    # Get points earned for all question types
                    points_earned = user_answer_data.get('points_earned')
                    question_review['points_earned'] = points_earned
                    
                    if question['question_type'] == 'single_choice':
                        question_review['user_answer'] = user_answer_data.get('selected_option_id')
                        # Get the text of selected option
                        if question_review['user_answer']:
                            selected_option = next((opt for opt in options if opt['id'] == question_review['user_answer']), None)
                            if selected_option:
                                question_review['user_answer_text'] = selected_option['option_text']
                                question_review['is_correct'] = selected_option['is_correct']
                                question_review['grading_status'] = 'graded'  # Auto-graded
                    
                    elif question['question_type'] == 'multiple_choice':
                        import json
                        selected_ids = user_answer_data.get('selected_option_ids')
                        
                        # Handle migrated data: if no selected_option_ids but has answer_text
                        if not selected_ids and user_answer_data.get('answer_text'):
                            # This was likely a migrated true/false question, show the answer_text
                            question_review['user_answer'] = []
                            question_review['user_answer_text'] = [user_answer_data.get('answer_text')]
                            question_review['is_correct'] = user_answer_data.get('is_correct', False)
                            question_review['grading_status'] = 'graded'
                            print(f"Multiple choice question {question['id']} using migrated answer_text: {user_answer_data.get('answer_text')}")
                        elif selected_ids:
                            try:
                                # Handle both string (from database) and list (from UI) formats
                                if isinstance(selected_ids, str):
                                    question_review['user_answer'] = json.loads(selected_ids)
                                else:
                                    question_review['user_answer'] = selected_ids
                                
                                # Get texts of selected options
                                selected_options = [opt for opt in options if opt['id'] in question_review['user_answer']]
                                question_review['user_answer_text'] = [opt['option_text'] for opt in selected_options]
                                
                                # Check if all correct options are selected and no incorrect ones
                                correct_ids = [opt['id'] for opt in options if opt['is_correct']]
                                question_review['is_correct'] = set(question_review['user_answer']) == set(correct_ids)
                                question_review['grading_status'] = 'graded'  # Auto-graded
                                
                                print(f"Multiple choice question {question['id']}: selected_ids={selected_ids}, user_answer_text={question_review['user_answer_text']}")
                            except (json.JSONDecodeError, TypeError) as e:
                                print(f"Error parsing multiple choice answer for question {question['id']}: {e}")
                                question_review['user_answer'] = []
                                question_review['user_answer_text'] = []
                                question_review['is_correct'] = False
                                question_review['grading_status'] = 'graded'  # Auto-graded with error
                        else:
                            # No answer provided
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
                            question_review['grading_status'] = 'graded'  # Auto-graded
                        else:
                            # For short answer and essay, use actual instructor grading results
                            points_earned = user_answer_data.get('points_earned')
                            if points_earned is not None:
                                # Has been graded by instructor
                                question_review['is_correct'] = points_earned > 0
                                question_review['points_earned'] = points_earned
                                question_review['grading_status'] = 'graded'
                            else:
                                # Not yet graded by instructor
                                question_review['is_correct'] = None  # Unknown until graded
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
                    # For True/False, show the correct answer as True or False
                    correct_answer = question.get('correct_answer', '') or ''
                    correct_answer = correct_answer.strip().lower()
                    if correct_answer in ['true', 'false']:
                        question_review['correct_answer_text'] = correct_answer.capitalize()
                    else:
                        question_review['correct_answer_text'] = 'N/A (Missing correct answer)'
                        print(f"Warning: True/False question {question['id']} has invalid correct_answer: '{question.get('correct_answer')}')")
                else:
                    # For short_answer and essay questions
                    question_review['correct_answer_text'] = question.get('correct_answer', 'N/A')
                
                review_data.append(question_review)
            
            return review_data
            
        except Exception as e:
            print(f"Error getting exam review data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_summary_stats_row(self, session_data, total_questions, correct_count, answered_count):
        """Create the summary statistics row with optional question pool information"""
        stats_containers = [
            # Score
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{session_data['score']:.1f}%", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text("Score", size=12, color=COLORS['text_secondary'])
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=ft.padding.all(12),
                bgcolor=COLORS['success'] if session_data['score'] >= session_data['passing_score'] else COLORS['error'],
                border_radius=8,
                opacity=0.9
            ),
            
            # Questions summary
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
            
            # Completion rate
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
            
            # Duration
            ft.Container(
                content=ft.Column([
                    ft.Text(f"{session_data['duration_seconds']//60}m", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Duration", size=12, color=COLORS['text_secondary'])
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=ft.padding.all(12),
                bgcolor=COLORS['surface'],
                border_radius=8,
                border=ft.border.all(1, COLORS['secondary'])
            )
        ]
        
        # Add question pool info if exam uses question pool
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
    
    def show_exam_review_dialog(self, session_data, review_data):
        """Show responsive exam review dialog"""
        try:
            # Get page reference for responsive sizing
            page_ref = None
            if hasattr(self, '_page_ref') and self._page_ref:
                page_ref = self._page_ref
            elif self.page:
                page_ref = self.page
            
            if not page_ref:
                print("No page reference available for dialog")
                return
            
            # Calculate responsive dialog dimensions
            # Default fallback sizes if window dimensions aren't available
            window_width = getattr(page_ref.window, 'width', 1200) or 1200
            window_height = getattr(page_ref.window, 'height', 800) or 800
            
            # Responsive sizing: 85% of window size with min/max constraints
            dialog_width = min(max(window_width * 0.85, 700), 1400)  # Min 700px, Max 1400px
            dialog_height = min(max(window_height * 0.8, 500), 900)   # Min 500px, Max 900px
            
            print(f"Window: {window_width}x{window_height}, Dialog: {dialog_width}x{dialog_height}")
            
            # Calculate summary stats
            total_questions = len(review_data)
            correct_count = sum(1 for q in review_data if q['is_correct'])
            answered_count = sum(1 for q in review_data if q['user_answer_text'] is not None)
            
            # Create dialog header with exam summary
            header_content = ft.Column([
                # Exam title and basic info
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
                
                # Summary stats row
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
                height=dialog_height - 250,  # Adjust height for header and footer
                padding=ft.padding.all(20)
            )
            
            # Create the responsive dialog
            review_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Container(
                    content=header_content,
                    padding=ft.padding.only(bottom=10)
                ),
                content=ft.Container(
                    content=content_area,
                    width=dialog_width - 100,  # Account for dialog padding
                    height=dialog_height - 200  # Account for title and actions
                ),
                actions=[
                    ft.Row([
                        ft.TextButton(
                            "Close",
                            on_click=lambda e: self.close_exam_review_dialog()
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER
            )
            
            # Show the dialog
            page_ref.dialog = review_dialog
            review_dialog.open = True
            page_ref.update()
            
            print("Exam review dialog opened successfully")
            
        except Exception as e:
            print(f"Error showing exam review dialog: {e}")
            import traceback
            traceback.print_exc()
            self.show_error_dialog("Failed to display exam review")
    
    def close_exam_review_dialog(self):
        """Close the exam review dialog"""
        try:
            # Get page reference
            page_ref = None
            if hasattr(self, '_page_ref') and self._page_ref:
                page_ref = self._page_ref
            elif self.page:
                page_ref = self.page
                
            if page_ref and page_ref.dialog:
                page_ref.dialog.open = False
                page_ref.update()
                print("Exam review dialog closed")
        except Exception as e:
            print(f"Error closing exam review dialog: {e}")
    
    def create_questions_review_content(self, review_data):
        """Create scrollable content showing all questions with user vs correct answers"""
        try:
            question_cards = []
            
            for i, question_data in enumerate(review_data, 1):
                # Determine status color and icon
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
                
                # Create question card
                question_card = ft.Container(
                    content=ft.Column([
                        # Question header with points display
                        ft.Row([
                            ft.Text(f"Question {i}", size=16, weight=ft.FontWeight.BOLD),
                            ft.Container(expand=True),
                            self.create_points_display(question_data),
                            ft.Container(width=15),  # Spacing between points and status
                            ft.Row([
                                ft.Icon(status_icon, color=status_color, size=20),
                                ft.Text(status_text, color=status_color, weight=ft.FontWeight.BOLD)
                            ], spacing=8)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        
                        ft.Container(height=10),
                        
                        # Question text
                        ft.Text(
                            question_data['question_text'],
                            size=14,
                            color=COLORS['text_primary'],
                            selectable=True
                        ),
                        
                        ft.Container(height=15),
                        
                        # Question type and answers section
                        self.create_answer_comparison_section(question_data),
                        
                        # Explanation if available
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
        """Create points display showing earned/total points based on grading status"""
        try:
            total_points = question_data.get('points', 1.0)
            points_earned = question_data.get('points_earned')
            grading_status = question_data.get('grading_status', 'not_answered')
            question_type = question_data.get('question_type', '')
            
            # For essay/short_answer questions, show instructor grading status
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
                # For auto-graded questions (multiple choice, etc.)
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
        """Create the user answer vs correct answer comparison section"""
        try:
            question_type = question_data['question_type']
            
            # Single choice questions
            if question_type == 'single_choice':
                return ft.Column([
                    ft.Text("Type: Single Choice", size=12, color=COLORS['text_secondary'], italic=True),
                    ft.Container(height=8),
                    
                    # Show all options with indicators
                    ft.Column([
                        self.create_option_display(option, question_data) 
                        for option in question_data['options']
                    ], spacing=6),
                    
                    ft.Container(height=10),
                    self.create_answer_summary(question_data)
                ], spacing=0)
            
            # Multiple choice questions  
            elif question_type == 'multiple_choice':
                return ft.Column([
                    ft.Text("Type: Multiple Choice (Select all that apply)", size=12, color=COLORS['text_secondary'], italic=True),
                    ft.Container(height=8),
                    
                    # Show all options with indicators
                    ft.Column([
                        self.create_option_display(option, question_data) 
                        for option in question_data['options']
                    ], spacing=6),
                    
                    ft.Container(height=10),
                    self.create_answer_summary(question_data)
                ], spacing=0)
            
            # True/False questions
            elif question_type == 'true_false':
                user_answer = question_data.get('user_answer_text', 'Not answered')
                correct_answer = question_data.get('correct_answer_text', 'N/A')
                
                return ft.Column([
                    ft.Text("Type: True/False", size=12, color=COLORS['text_secondary'], italic=True),
                    ft.Container(height=8),
                    self.create_text_answer_display(user_answer, correct_answer)
                ], spacing=0)
            
            # Short answer and essay questions
            elif question_type in ['short_answer', 'essay']:
                user_answer = question_data.get('user_answer_text', 'Not answered')
                correct_answer = question_data.get('correct_answer_text', 'Manual grading required')
                
                question_type_display = "Short Answer" if question_type == 'short_answer' else "Essay"
                
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
        """Create display for a single option showing user selection and correctness"""
        try:
            option_id = option['id']
            option_text = option['option_text']
            is_correct_option = option['is_correct']
            
            # Check if user selected this option
            user_selected = False
            if question_data['question_type'] == 'single_choice':
                user_selected = question_data.get('user_answer') == option_id
            elif question_data['question_type'] == 'multiple_choice':
                user_answers = question_data.get('user_answer', [])
                user_selected = option_id in user_answers if user_answers else False
            
            # Determine styling
            if is_correct_option and user_selected:
                # Correct and selected - green
                bg_color = ft.colors.with_opacity(0.1, COLORS['success'])
                border_color = COLORS['success']
                icon = ft.icons.CHECK_CIRCLE
                icon_color = COLORS['success']
            elif is_correct_option and not user_selected:
                # Correct but not selected - light green with dashed border
                bg_color = ft.colors.with_opacity(0.05, COLORS['success'])
                border_color = COLORS['success']
                icon = ft.icons.CHECK_CIRCLE_OUTLINE
                icon_color = COLORS['success']
            elif not is_correct_option and user_selected:
                # Incorrect but selected - red
                bg_color = ft.colors.with_opacity(0.1, COLORS['error'])
                border_color = COLORS['error']
                icon = ft.icons.CANCEL
                icon_color = COLORS['error']
            else:
                # Neither correct nor selected - neutral
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
        """Create display for text-based answers (true/false, short answer, essay)"""
        try:
            return ft.Column([
                # User's answer
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
                
                # Correct answer (if not manual grading)
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
                        "📝 This answer requires manual grading by your instructor",
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
        """Create a summary of the user's answer vs correct answer for choice questions"""
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
            
            return ft.Container()  # No summary for other question types
            
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
            
            return ft.Container()  # No explanation available
            
        except Exception as e:
            print(f"Error creating explanation section: {e}")
            return ft.Container()
    
    def show_change_password_dialog(self, e):
        """Show dialog to change password"""
        # Create password input fields
        current_password = ft.TextField(
            label="Current Password",
            password=True,
            can_reveal_password=True,
            width=400,
            autofocus=True
        )

        new_password = ft.TextField(
            label="New Password",
            password=True,
            can_reveal_password=True,
            width=400
        )

        confirm_password = ft.TextField(
            label="Confirm New Password",
            password=True,
            can_reveal_password=True,
            width=400
        )

        error_text = ft.Text("", color=COLORS['error'], size=14)
        success_text = ft.Text("", color=COLORS['success'], size=14)

        def validate_and_change_password(e):
            """Validate inputs and change password"""
            error_text.value = ""
            success_text.value = ""

            # Validation
            if not current_password.value or not new_password.value or not confirm_password.value:
                error_text.value = "All fields are required"
                dialog.update()
                return

            if new_password.value != confirm_password.value:
                error_text.value = "New passwords do not match"
                dialog.update()
                return

            if len(new_password.value) < 6:
                error_text.value = "New password must be at least 6 characters long"
                dialog.update()
                return

            # Verify current password
            import bcrypt
            user = self.db.execute_single(
                "SELECT password_hash FROM users WHERE id = ?",
                (self.user_data['id'],)
            )

            if not user or not bcrypt.checkpw(current_password.value.encode('utf-8'), user['password_hash'].encode('utf-8')):
                error_text.value = "Current password is incorrect"
                dialog.update()
                return

            # Update password
            new_password_hash = bcrypt.hashpw(new_password.value.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            try:
                self.db.execute_update(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (new_password_hash, self.user_data['id'])
                )

                success_text.value = "Password changed successfully!"
                error_text.value = ""
                current_password.value = ""
                new_password.value = ""
                confirm_password.value = ""
                dialog.update()

                # Close dialog after 1.5 seconds
                import time
                import threading
                def close_after_delay():
                    time.sleep(1.5)
                    if self.page:
                        dialog.open = False
                        self.page.update()

                threading.Thread(target=close_after_delay, daemon=True).start()

            except Exception as ex:
                error_text.value = f"Error changing password: {str(ex)}"
                dialog.update()

        # Create dialog
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Change Password"),
            content=ft.Container(
                content=ft.Column([
                    current_password,
                    ft.Container(height=10),
                    new_password,
                    ft.Container(height=10),
                    confirm_password,
                    ft.Container(height=10),
                    error_text,
                    success_text
                ], tight=True),
                width=450,
                padding=ft.padding.all(10)
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog()),
                ft.ElevatedButton(
                    "Change Password",
                    on_click=validate_and_change_password,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        # Show dialog
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def close_dialog(self):
        """Close the current dialog"""
        if self.page and self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def logout_clicked(self, e):
        self.logout_callback(self.page)