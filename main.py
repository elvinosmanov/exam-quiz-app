import flet as ft
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))



from quiz_app.database.database import init_database, Database
from quiz_app.views.auth.login_view import LoginView
from quiz_app.utils.session import SessionManager
from quiz_app.utils.localization import set_language

class QuizApp:
    def __init__(self):
        self.session_manager = SessionManager()
        self.db = None  # Will be initialized in main()
        self.current_view = None
        self.expert_view_mode = 'expert'  # 'expert' or 'examinee' for expert users
        self.current_user_data = None  # Store current user for view switching

    def load_system_language(self):
        """Load system-wide language setting from database"""
        try:
            # Query system settings for language
            result = self.db.execute_single(
                "SELECT setting_value FROM system_settings WHERE setting_key = 'language'"
            )

            if result:
                language_value = result['setting_value']
                # Map from display name to language code
                language_code = 'en' if language_value == 'English' else 'az'
                set_language(language_code)
                print(f"[DEBUG] System language loaded: {language_code} ({language_value})")
            else:
                # Default to English if no setting found
                set_language('en')
                print("[DEBUG] No system language setting found, defaulting to English")
        except Exception as e:
            print(f"[WARNING] Failed to load system language: {e}")
            # Default to English on error
            set_language('en')

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

        # Create database instance and connect it to session manager
        self.db = Database()
        self.session_manager.set_database(self.db)

        # Load system language setting from database
        self.load_system_language()
        
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
        """Handle successful login and route to appropriate dashboard"""
        # Store current user for view switching
        self.current_user_data = user_data

        # Reset expert view mode to default
        if user_data['role'] == 'expert':
            self.expert_view_mode = 'expert'

        # Show appropriate dashboard
        self.show_dashboard(page)

    def show_dashboard(self, page: ft.Page):
        """Show appropriate dashboard based on user role and view mode"""
        from quiz_app.views.admin.admin_dashboard import AdminDashboard
        from quiz_app.views.examinee.examinee_dashboard import ExamineeDashboard
        from quiz_app.utils.view_switcher import create_view_switcher

        page.clean()

        user_data = self.current_user_data
        role = user_data['role']

        # Determine which dashboard to show
        if role == 'admin':
            # Admin always sees admin dashboard
            dashboard = AdminDashboard(self.session_manager, user_data, self.logout)

        elif role == 'expert':
            # Expert can switch between expert and examinee views
            if self.expert_view_mode == 'examinee':
                # Show examinee dashboard with view switcher
                dashboard = ExamineeDashboard(
                    self.session_manager,
                    user_data,
                    self.logout,
                    view_switcher=create_view_switcher(
                        'examinee',
                        'expert',
                        self.switch_expert_view
                    )
                )
            else:
                # Show admin dashboard (expert mode) with view switcher
                dashboard = AdminDashboard(
                    self.session_manager,
                    user_data,
                    self.logout,
                    view_switcher=create_view_switcher(
                        'expert',
                        'expert',
                        self.switch_expert_view
                    )
                )

        else:  # examinee
            # Regular examinee sees examinee dashboard
            dashboard = ExamineeDashboard(self.session_manager, user_data, self.logout)

        # Store page reference and current view
        dashboard._page_ref = page
        self.current_view = dashboard

        page.add(dashboard)
        page.update()

    def switch_expert_view(self, new_view):
        """Switch expert between expert and examinee views"""
        print(f"[DEBUG] switch_expert_view called with new_view: {new_view}")
        if self.current_user_data and self.current_user_data['role'] == 'expert':
            print(f"[DEBUG] Switching from {self.expert_view_mode} to {new_view}")
            self.expert_view_mode = new_view
            # Re-render dashboard with new view
            if self.current_view and hasattr(self.current_view, '_page_ref'):
                print(f"[DEBUG] Calling show_dashboard with page reference")
                self.show_dashboard(self.current_view._page_ref)
            else:
                print(f"[ERROR] No page reference found")
        
    def logout(self, page: ft.Page):
        """Logout and return to login screen with proper cleanup"""
        try:
            print("[LOGOUT] Starting logout process...")

            # Clear session
            self.session_manager.clear_session()

            # Reset state
            self.current_user_data = None
            self.expert_view_mode = 'expert'

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


 