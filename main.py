import flet as ft
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))



from quiz_app.database.database import init_database
from quiz_app.views.auth.login_view import LoginView
from quiz_app.utils.session import SessionManager
from quiz_app.utils.logging_config import get_audit_logger

class QuizApp:
    def __init__(self):
        self.session_manager = SessionManager()
        self.current_view = None
        
    def main(self, page: ft.Page):
        page.title = "Quiz Examination System"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window.width = 1200
        page.window.height = 800
        page.window.min_width = 800
        page.window.min_height = 600
        page.padding = 0  # Remove default padding for full height containers
        page.spacing = 0  # Remove default spacing for full height containers
        
        # Initialize database
        init_database()
        
        # Set up theme
        page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
            use_material3=True
            
        )
        

        # Initialize with login view
        self.show_login(page)
        
    def show_login(self, page: ft.Page):
        page.clean()
        login_view = LoginView(self.session_manager, self.on_login_success)
        page.add(login_view)
        page.update()
        
    def on_login_success(self, page: ft.Page, user_data):
        from quiz_app.views.admin.admin_dashboard import AdminDashboard
        from quiz_app.views.examinee.examinee_dashboard import ExamineeDashboard
        
        page.clean()
        
        if user_data['role'] == 'admin':
            dashboard = AdminDashboard(self.session_manager, user_data, self.logout)
        else:
            dashboard = ExamineeDashboard(self.session_manager, user_data, self.logout)
        
        # Store page reference in dashboard before adding to page
        dashboard._page_ref = page
            
        page.add(dashboard)
        page.update()
        
    def logout(self, page: ft.Page):
        """Logout and return to login screen with proper cleanup"""
        try:
            print("[LOGOUT] Starting logout process...")

            # Get current user data before clearing session
            current_user = self.session_manager.get_current_user()

            # Log logout action
            if current_user:
                audit_logger = get_audit_logger()
                audit_logger.log_logout(
                    user_id=current_user['id'],
                    username=current_user['username']
                )

            # Clear session
            self.session_manager.clear_session()

            # Small delay to allow background threads to detect page changes
            import time
            time.sleep(0.1)

            # Show login
            self.show_login(page)

            print("[LOGOUT] Logout completed successfully")
        except Exception as e:
            print(f"[LOGOUT] Error during logout: {e}")
            # Force show login anyway
            try:
                self.show_login(page)
            except:
                pass

def main(page: ft.Page):
    app = QuizApp()
    app.main(page)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="quiz_app/assets")