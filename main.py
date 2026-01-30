import flet as ft
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))



from quiz_app.database.database import init_database, Database
from quiz_app.views.auth.login_view import LoginView
from quiz_app.utils.session import SessionManager
from quiz_app.utils.localization import set_language
from quiz_app.config import ROLE_ADMIN, ROLE_EXPERT, ROLE_EXAMINEE, VALID_ROLES

# Pre-import dashboard views for faster loading (Fix: Performance Issue #3)
from quiz_app.views.admin.admin_dashboard import AdminDashboard
from quiz_app.views.examinee.examinee_dashboard import ExamineeDashboard
from quiz_app.utils.view_switcher import create_view_switcher

class QuizApp:
    def __init__(self):
        self.session_manager = SessionManager()
        self.db = None  # Will be initialized in main()
        self.current_view = None
        self.expert_view_mode = 'expert'  # 'expert' or 'examinee' for expert users
        self.current_user_data = None  # Store current user for view switching

    def setup_packaged_environment(self):
        """Setup environment for packaged executable - Optimized (Performance Fix #5)"""
        import shutil
        from quiz_app.config import DATABASE_PATH, DATA_DIR, UPLOAD_FOLDER

        if getattr(sys, 'frozen', False):
            # Get the bundle directory (_MEIPASS for PyInstaller)
            bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))

            # Only copy database if it doesn't exist (one-time operation)
            if not os.path.exists(DATABASE_PATH):
                bundled_db = os.path.join(bundle_dir, 'quiz_app.db')
                if os.path.exists(bundled_db):
                    shutil.copy2(bundled_db, DATABASE_PATH)

            # Ensure assets directory exists (lightweight operation)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Only copy assets if directory is empty (one-time operation)
            bundle_assets = os.path.join(bundle_dir, 'assets', 'images')
            if os.path.exists(bundle_assets) and not os.listdir(UPLOAD_FOLDER):
                shutil.copytree(bundle_assets, UPLOAD_FOLDER, dirs_exist_ok=True)

    def load_system_language(self):
        """Load system-wide language setting from database - Optimized (Performance Fix #5)"""
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
            else:
                # Default to English if no setting found
                set_language('en')
        except Exception:
            # Default to English on error (silent fail for performance)
            set_language('en')

    def main(self, page: ft.Page):
        # Set custom window icon - use relative path from assets_dir
        if getattr(sys, 'frozen', False):
            # Running as packaged executable
            base_path = os.path.dirname(sys.executable)
            icon_path = os.path.join(base_path, "icon.png")
        else:
            # Running in development - use relative path to assets folder
            icon_path = "icon.png"

        try:
            page.window.icon = icon_path
            print(f"[MAIN] Setting window icon: {icon_path}")
            page.update()
        except Exception as e:
            print(f"[MAIN] Failed to set icon: {e}")

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
        """Show login view with complete cleanup"""
        # Force close all dialogs and overlays
        if hasattr(page, 'overlay') and page.overlay:
            page.overlay.clear()

        if page.dialog:
            page.dialog.open = False
            page.dialog = None

        if page.banner:
            page.banner.open = False
            page.banner = None

        if page.snack_bar:
            page.snack_bar.open = False
            page.snack_bar = None

        # Clean page completely
        page.clean()

        # Force garbage collection hint (optional but helps)
        import gc
        gc.collect()

        # Create fresh login view
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
        # Imports moved to top for performance

        # CRITICAL: Complete cleanup before loading dashboard
        if hasattr(page, 'overlay') and page.overlay:
            page.overlay.clear()

        if page.dialog:
            page.dialog.open = False
            page.dialog = None

        if page.banner:
            page.banner.open = False
            page.banner = None

        if page.snack_bar:
            page.snack_bar.open = False
            page.snack_bar = None

        page.clean()

        # Show loading indicator while dashboard builds (Performance Fix #4)
        loading_overlay = ft.Container(
            content=ft.Column([
                ft.ProgressRing(),
                ft.Container(height=20),
                ft.Text(
                    "Loading dashboard...",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.BLUE_700
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.colors.WHITE
        )

        page.add(loading_overlay)
        page.update()

        user_data = self.current_user_data
        role = user_data.get('role', '').lower()

        # Validate role - must be one of: admin, expert, examinee (SECURITY FIX)
        if role not in VALID_ROLES:
            # Invalid role - log out and show error
            print(f"[SECURITY] Invalid role detected: {role} for user {user_data.get('username')}")
            page.clean()
            page.add(ft.Container(
                content=ft.Text(
                    "Invalid user role. Please contact administrator.",
                    color=ft.colors.RED,
                    size=16
                ),
                padding=20
            ))
            page.update()
            self.logout()
            return

        # Determine which dashboard to show
        if role == ROLE_ADMIN:
            # Admin always sees admin dashboard
            dashboard = AdminDashboard(self.session_manager, user_data, self.logout)

        elif role == ROLE_EXPERT:
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

        # Replace loading overlay with actual dashboard (Performance Fix #4)
        page.clean()
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
        """Logout and return to login screen with aggressive cleanup"""
        try:
            print("[LOGOUT] Starting logout process...")

            # STEP 1: Clear all UI elements first (prevents visual glitches)
            if hasattr(page, 'overlay') and page.overlay:
                page.overlay.clear()

            if page.dialog:
                page.dialog.open = False
                page.dialog = None

            if page.banner:
                page.banner.open = False
                page.banner = None

            if page.snack_bar:
                page.snack_bar.open = False
                page.snack_bar = None

            # STEP 2: Clear current view reference
            if self.current_view:
                # Remove page reference to break circular references
                if hasattr(self.current_view, '_page_ref'):
                    delattr(self.current_view, '_page_ref')
                self.current_view = None

            # STEP 3: Clear session and state
            self.session_manager.clear_session()
            self.current_user_data = None
            self.expert_view_mode = 'expert'

            # STEP 4: Force garbage collection
            import gc
            gc.collect()

            # STEP 5: Small delay for cleanup to complete
            import time
            time.sleep(0.15)

            # STEP 6: Show clean login screen
            self.show_login(page)

            print("[LOGOUT] Logout completed successfully")
        except Exception as e:
            print(f"[LOGOUT] Error during logout: {e}")
            import traceback
            traceback.print_exc()

            # Force show login anyway with full cleanup
            try:
                page.clean()
                import gc
                gc.collect()
                self.show_login(page)
            except Exception as e2:
                print(f"[LOGOUT] Critical error in fallback: {e2}")

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


 