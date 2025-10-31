import flet as ft
from quiz_app.views.admin.base_admin_layout import BaseAdminLayout
from quiz_app.views.admin.user_management import UserManagement
from quiz_app.views.admin.quiz_management import QuizManagement
from quiz_app.views.admin.question_management import QuestionManagement
from quiz_app.views.admin.grading import Grading
from quiz_app.views.admin.reports import Reports
from quiz_app.database.database import Database
from quiz_app.config import COLORS

class AdminDashboard(BaseAdminLayout):
    def __init__(self, session_manager, user_data, logout_callback):
        super().__init__(session_manager, user_data, logout_callback)
        self.db = Database()
        
        # Don't initialize dashboard view here - wait until added to page
    
    def did_mount(self):
        """Called after the control is added to the page"""
        super().did_mount()
        self.show_dashboard()
    
    def on_route_changed(self, route):
        print(f"[DEBUG] on_route_changed called with route: {route}")
        if route == "dashboard":
            self.show_dashboard()
        elif route == "users":
            self.show_user_management()
        elif route == "exams":
            self.show_exam_management()
        elif route == "questions":
            self.show_question_management()
        elif route == "grading":
            self.show_grading()
        elif route == "reports":
            self.show_reports()
        elif route == "settings":
            self.show_settings()
        else:
            print(f"[DEBUG] Unknown route: {route}")
    
    def show_dashboard(self):
        # Get statistics
        stats = self.get_dashboard_stats()
        
        # Create dashboard cards
        cards = ft.Row([
            self.create_stat_card("Total Users", str(stats['total_users']), ft.icons.PEOPLE, COLORS['primary']),
            self.create_stat_card("Total Exams", str(stats['total_exams']), ft.icons.QUIZ, COLORS['success']),
            self.create_stat_card("Active Sessions", str(stats['active_sessions']), ft.icons.TIMER, COLORS['warning']),
            self.create_stat_card("Completed Exams", str(stats['completed_exams']), ft.icons.CHECK_CIRCLE, COLORS['success'])
        ], spacing=20, wrap=True)
        
        # Recent activity
        recent_activity = self.get_recent_activity()
        activity_list = ft.Column([
            ft.Text("Recent Activity", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            *[ft.ListTile(
                leading=ft.Icon(ft.icons.CIRCLE, size=8, color=COLORS['primary']),
                title=ft.Text(activity['description']),
                subtitle=ft.Text(activity['timestamp'])
            ) for activity in recent_activity[:10]]
        ], spacing=5)
        
        content = ft.Column([
            ft.Text("Dashboard Overview", size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
            ft.Divider(),
            cards,
            ft.Container(height=20),
            ft.Container(
                content=activity_list,
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
    
    def show_user_management(self):
        print("[DEBUG] show_user_management called")
        try:
            user_mgmt = UserManagement(self.db)
            self.set_content(user_mgmt)
            print("[DEBUG] UserManagement component set as content")
        except Exception as e:
            print(f"[ERROR] Exception in show_user_management: {e}")
    
    def show_exam_management(self):
        print("[DEBUG] show_exam_management called")
        try:
            exam_mgmt = QuizManagement(self.db, self.user_data)
            exam_mgmt.parent_dashboard = self  # Pass parent reference
            self.set_content(exam_mgmt)
            print("[DEBUG] QuizManagement component set as content")
        except Exception as e:
            print(f"[ERROR] Exception in show_exam_management: {e}")
    
    def show_question_management(self):
        question_mgmt = QuestionManagement(self.db)
        self.set_content(question_mgmt)
    
    def show_question_management_with_exam(self, exam_id):
        """Show question management with pre-selected exam"""
        question_mgmt = QuestionManagement(self.db)
        # Pre-select the exam
        question_mgmt.preselect_exam(exam_id)
        self.set_content(question_mgmt)
    
    def show_grading(self):
        grading = Grading(self.db)
        self.set_content(grading)
    
    def show_reports(self):
        reports = Reports(self.db)
        self.set_content(reports)
    
    def show_settings(self):
        content = ft.Column([
            ft.Text("System Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Coming soon...", size=16, color=COLORS['text_secondary'])
        ])
        self.set_content(content)
    
    def get_dashboard_stats(self):
        total_users = self.db.execute_single("SELECT COUNT(*) as count FROM users WHERE is_active = 1")['count']
        total_exams = self.db.execute_single("SELECT COUNT(*) as count FROM exams WHERE is_active = 1")['count']
        active_sessions = self.db.execute_single("SELECT COUNT(*) as count FROM exam_sessions WHERE status = 'in_progress'")['count']
        completed_exams = self.db.execute_single("SELECT COUNT(*) as count FROM exam_sessions WHERE is_completed = 1")['count']
        
        return {
            'total_users': total_users,
            'total_exams': total_exams,
            'active_sessions': active_sessions,
            'completed_exams': completed_exams
        }
    
    def get_recent_activity(self):
        """Get recent exam activity - latest completions and pending grading"""
        from datetime import datetime, timedelta

        activity_list = []

        # Get latest exam completions (last 20)
        recent_completions = self.db.execute_query("""
            SELECT
                u.full_name,
                COALESCE(ea.assignment_name, e.title) as exam_title,
                es.score,
                es.end_time,
                CASE WHEN es.score >= COALESCE(ea.passing_score, e.passing_score) THEN 'PASS' ELSE 'FAIL' END as status
            FROM exam_sessions es
            JOIN users u ON es.user_id = u.id
            JOIN exams e ON es.exam_id = e.id
            LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
            WHERE es.is_completed = 1 AND es.end_time IS NOT NULL
            ORDER BY es.end_time DESC
            LIMIT 20
        """)

        for completion in recent_completions:
            status_emoji = "✅" if completion['status'] == 'PASS' else "❌"
            activity_list.append({
                'description': f"{status_emoji} {completion['full_name']} completed '{completion['exam_title']}' - Score: {completion['score']:.1f}%",
                'timestamp': completion['end_time'][:16] if completion['end_time'] else 'N/A'
            })

        # Get exams needing manual grading (essay/short answer questions)
        pending_grading = self.db.execute_query("""
            SELECT DISTINCT
                u.full_name,
                COALESCE(ea.assignment_name, e.title) as exam_title,
                es.end_time,
                COUNT(ua.id) as pending_count
            FROM exam_sessions es
            JOIN users u ON es.user_id = u.id
            JOIN exams e ON es.exam_id = e.id
            LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
            JOIN user_answers ua ON es.id = ua.session_id
            JOIN questions q ON ua.question_id = q.id
            WHERE es.is_completed = 1
              AND q.question_type IN ('short_answer', 'essay')
              AND (ua.is_correct IS NULL OR ua.is_correct = 0)
            GROUP BY es.id
            ORDER BY es.end_time DESC
            LIMIT 10
        """)

        for grading in pending_grading:
            activity_list.append({
                'description': f"📝 {grading['full_name']} - '{grading['exam_title']}' has {grading['pending_count']} answer(s) pending manual grading",
                'timestamp': grading['end_time'][:16] if grading['end_time'] else 'N/A'
            })

        # Sort all activity by timestamp (newest first)
        activity_list.sort(key=lambda x: x['timestamp'], reverse=True)

        return activity_list[:15]  # Return top 15 most recent activities