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
        # Mock data for now - replace with actual audit log queries
        return [
            {'description': 'New user registered: john.doe', 'timestamp': '2 minutes ago'},
            {'description': 'Exam "Python Basics" completed by user123', 'timestamp': '5 minutes ago'},
            {'description': 'Admin updated exam settings', 'timestamp': '10 minutes ago'},
            {'description': 'New question added to question bank', 'timestamp': '15 minutes ago'},
            {'description': 'User profile updated', 'timestamp': '20 minutes ago'}
        ]