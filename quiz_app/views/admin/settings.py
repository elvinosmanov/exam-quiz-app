import flet as ft
from quiz_app.database.database import Database

# Define COLORS to match other admin pages
COLORS = {
    'primary': '#1976D2',
    'secondary': '#757575',
    'success': '#4CAF50',
    'error': '#F44336',
    'warning': '#FF9800',
    'text_primary': '#212121',
    'text_secondary': '#757575',
    'border': '#E0E0E0',
    'background': '#FAFAFA'
}

class Settings(ft.UserControl):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_settings = {}

        # Ensure settings table exists
        self.initialize_settings_table()

        # Load current settings
        self.load_settings()

    def initialize_settings_table(self):
        """Create settings table if it doesn't exist"""
        try:
            self.db.execute_update("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    setting_type TEXT DEFAULT 'string',
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert default settings if they don't exist
            default_settings = [
                ('passing_score', '70', 'number', 'Default passing score percentage'),
                ('default_exam_duration', '60', 'number', 'Default exam duration in minutes'),
                ('language', 'English', 'string', 'System language')
            ]

            for key, value, type_, desc in default_settings:
                # Check if setting exists
                existing = self.db.execute_query(
                    "SELECT * FROM system_settings WHERE setting_key = ?",
                    (key,)
                )
                if not existing:
                    self.db.execute_update(
                        """INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
                           VALUES (?, ?, ?, ?)""",
                        (key, value, type_, desc)
                    )

            print("[DEBUG] Settings table initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize settings table: {e}")

    def load_settings(self):
        """Load all settings from database"""
        try:
            settings = self.db.execute_query("SELECT setting_key, setting_value FROM system_settings")
            self.current_settings = {s['setting_key']: s['setting_value'] for s in settings}
            print(f"[DEBUG] Loaded settings: {self.current_settings}")
        except Exception as e:
            print(f"[ERROR] Failed to load settings: {e}")
            self.current_settings = {}

    def save_setting(self, key, value):
        """Save a single setting to database"""
        try:
            self.db.execute_update(
                """UPDATE system_settings
                   SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE setting_key = ?""",
                (str(value), key)
            )
            self.current_settings[key] = str(value)
            print(f"[DEBUG] Saved setting: {key} = {value}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save setting {key}: {e}")
            return False

    def show_success_message(self, message):
        """Show success snackbar"""
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=COLORS['success']
            )
            self.page.snack_bar.open = True
            self.page.update()

    def show_error_message(self, message):
        """Show error snackbar"""
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=COLORS['error']
            )
            self.page.snack_bar.open = True
            self.page.update()

    def build(self):
        # Get current values
        passing_score = self.current_settings.get('passing_score', '70')
        exam_duration = self.current_settings.get('default_exam_duration', '60')
        language = self.current_settings.get('language', 'English')

        # Passing Score TextField
        passing_score_field = ft.TextField(
            label="Passing Score (%)",
            value=passing_score,
            hint_text="Enter percentage (0-100)",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.icons.GRADE,
            helper_text="Students need this score to pass exams"
        )

        # Exam Duration TextField
        exam_duration_field = ft.TextField(
            label="Exam Duration (minutes)",
            value=exam_duration,
            hint_text="Enter duration in minutes",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.icons.TIMER,
            helper_text="Default time limit for exams"
        )

        # Language Dropdown
        language_dropdown = ft.Dropdown(
            label="System Language",
            value=language,
            width=300,
            options=[
                ft.dropdown.Option("English", "English"),
                ft.dropdown.Option("Azerbaijani", "Azərbaycan dili"),
            ],
            prefix_icon=ft.icons.LANGUAGE,
            hint_text="Select system language"
        )

        def save_passing_score(e):
            """Save passing score setting"""
            try:
                value = int(passing_score_field.value)
                if value < 0 or value > 100:
                    self.show_error_message("Passing score must be between 0 and 100")
                    return

                if self.save_setting('passing_score', value):
                    self.show_success_message(f"Passing score updated to {value}%")
                else:
                    self.show_error_message("Failed to save passing score")
            except ValueError:
                self.show_error_message("Please enter a valid number")

        def save_exam_duration(e):
            """Save exam duration setting"""
            try:
                value = int(exam_duration_field.value)
                if value <= 0:
                    self.show_error_message("Exam duration must be greater than 0")
                    return

                if self.save_setting('default_exam_duration', value):
                    self.show_success_message(f"Exam duration updated to {value} minutes")
                else:
                    self.show_error_message("Failed to save exam duration")
            except ValueError:
                self.show_error_message("Please enter a valid number")

        def save_language(e):
            """Save language setting"""
            value = language_dropdown.value
            if self.save_setting('language', value):
                self.show_success_message(f"Language changed to {value}")
            else:
                self.show_error_message("Failed to save language")

        # Setting Cards (bigger with icons)
        passing_score_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.SCHOOL, size=32, color=COLORS['primary']),
                    ft.Column([
                        ft.Text("Passing Score", size=18, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                        ft.Text("Set the minimum score required to pass exams", size=13, color=COLORS['text_secondary'])
                    ], spacing=2, expand=True)
                ], spacing=15),
                ft.Container(height=15),
                passing_score_field,
                ft.Container(height=10),
                ft.ElevatedButton(
                    text="Save Passing Score",
                    icon=ft.icons.SAVE,
                    on_click=save_passing_score,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS['primary'],
                        color=ft.colors.WHITE
                    )
                )
            ], spacing=5),
            padding=ft.padding.all(20),
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, COLORS['border'])
        )

        exam_duration_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.ACCESS_TIME, size=32, color=COLORS['warning']),
                    ft.Column([
                        ft.Text("Exam Duration", size=18, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                        ft.Text("Set the default time limit for exams", size=13, color=COLORS['text_secondary'])
                    ], spacing=2, expand=True)
                ], spacing=15),
                ft.Container(height=15),
                exam_duration_field,
                ft.Container(height=10),
                ft.ElevatedButton(
                    text="Save Exam Duration",
                    icon=ft.icons.SAVE,
                    on_click=save_exam_duration,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS['warning'],
                        color=ft.colors.WHITE
                    )
                )
            ], spacing=5),
            padding=ft.padding.all(20),
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, COLORS['border'])
        )

        language_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.TRANSLATE, size=32, color=COLORS['success']),
                    ft.Column([
                        ft.Text("System Language", size=18, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                        ft.Text("Change the language used throughout the system", size=13, color=COLORS['text_secondary'])
                    ], spacing=2, expand=True)
                ], spacing=15),
                ft.Container(height=15),
                language_dropdown,
                ft.Container(height=10),
                ft.ElevatedButton(
                    text="Save Language",
                    icon=ft.icons.SAVE,
                    on_click=save_language,
                    style=ft.ButtonStyle(
                        bgcolor=COLORS['success'],
                        color=ft.colors.WHITE
                    )
                )
            ], spacing=5),
            padding=ft.padding.all(20),
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, COLORS['border'])
        )

        # Main layout
        return ft.Column([
            # Header
            ft.Container(
                content=ft.Row([
                    ft.Text("System Settings", size=28, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                    ft.Container(expand=True),
                    ft.Icon(ft.icons.SETTINGS, size=32, color=COLORS['primary'])
                ]),
                padding=ft.padding.only(bottom=20)
            ),

            # Settings Cards
            ft.Column([
                passing_score_card,
                ft.Container(height=20),
                exam_duration_card,
                ft.Container(height=20),
                language_card
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)
