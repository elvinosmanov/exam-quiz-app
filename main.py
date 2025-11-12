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

    def setup_packaged_environment(self):
        """Setup environment for packaged executable"""
        import shutil
        from quiz_app.config import DATABASE_PATH, DATA_DIR, UPLOAD_FOLDER

        if getattr(sys, 'frozen', False):
            print("[SETUP] Running as packaged executable")

            # Get the bundle directory (_MEIPASS for PyInstaller)
            bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            print(f"[SETUP] Bundle directory (_MEIPASS): {bundle_dir}")

            # Check if database exists in the executable directory (writable location)
            if not os.path.exists(DATABASE_PATH):
                print(f"[SETUP] Database not found at {DATABASE_PATH}")

                # Try to find database in the bundle
                bundled_db = os.path.join(bundle_dir, 'quiz_app.db')
                print(f"[SETUP] Looking for bundled database at: {bundled_db}")

                if os.path.exists(bundled_db):
                    print(f"[SETUP] Found bundled database, copying to writable location")
                    shutil.copy2(bundled_db, DATABASE_PATH)
                    print(f"[SETUP] Database copied to: {DATABASE_PATH}")
                else:
                    print(f"[SETUP] No bundled database found. Will create new database.")
            else:
                print(f"[SETUP] Database found at: {DATABASE_PATH}")

            # Ensure assets directory exists in writable location
            if not os.path.exists(UPLOAD_FOLDER):
                print(f"[SETUP] Creating assets directory: {UPLOAD_FOLDER}")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Check if bundled assets exist and copy them
            bundle_assets = os.path.join(bundle_dir, 'assets', 'images')
            print(f"[SETUP] Looking for bundled assets at: {bundle_assets}")
            if os.path.exists(bundle_assets):
                print(f"[SETUP] Found bundled assets, copying to writable location")
                shutil.copytree(bundle_assets, UPLOAD_FOLDER, dirs_exist_ok=True)
                print(f"[SETUP] Assets copied to: {UPLOAD_FOLDER}")
            else:
                print(f"[SETUP] No bundled assets found at: {bundle_assets}")
                # List what's actually in the bundle
                if os.path.exists(bundle_dir):
                    print(f"[SETUP] Contents of bundle directory:")
                    for item in os.listdir(bundle_dir):
                        print(f"[SETUP]   - {item}")
        else:
            print("[SETUP] Running in development mode")

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

        # Check if running as packaged executable
        self.setup_packaged_environment()

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
    # Determine assets directory based on whether we're packaged or not
    if getattr(sys, 'frozen', False):
        # Running as packaged executable
        # Flet will use the bundled assets from _MEIPASS
        bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        assets_path = os.path.join(bundle_dir, 'assets')
        if os.path.exists(assets_path):
            print(f"[MAIN] Using bundled assets from: {assets_path}")
            ft.app(target=main, assets_dir=assets_path)
        else:
            print(f"[MAIN] No bundled assets found, using default")
            ft.app(target=main)
    else:
        # Running in development
        ft.app(target=main, assets_dir="quiz_app/assets")


 