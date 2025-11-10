import flet as ft
from quiz_app.database.database import Database
from quiz_app.utils.email_templates import EmailTemplateManager
from quiz_app.utils.email_handler import EmailHandler

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
    def __init__(self, db, user_data=None):
        super().__init__()
        self.db = db
        self.user_data = user_data or {}
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

    def build_email_templates_card(self):
        """Build email templates editor card"""
        template_manager = EmailTemplateManager(self.db)

        # State variables
        template_type_dropdown = ft.Dropdown(
            label="Template Type",
            options=[
                ft.dropdown.Option("passed", "Passed Results"),
                ft.dropdown.Option("failed", "Failed Results"),
                ft.dropdown.Option("pending", "Pending Grading")
            ],
            value="passed",
            width=250
        )

        language_tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="English", icon=ft.icons.LANGUAGE),
                ft.Tab(text="Azərbaycan", icon=ft.icons.LANGUAGE)
            ]
        )

        # Load initial template for passed/en to populate fields
        initial_template = template_manager.get_template('passed', 'en')

        subject_field = ft.TextField(
            label="Email Subject",
            multiline=False,
            width=600,
            hint_text="e.g., 🎉 Exam Results - {{exam_name}}",
            value=initial_template['subject'] if initial_template else ""
        )

        body_field = ft.TextField(
            label="Email Body",
            multiline=True,
            min_lines=10,
            max_lines=20,
            width=600,
            hint_text="Enter email body with placeholders...",
            value=initial_template['body_template'] if initial_template else ""
        )

        placeholders_text = ft.Text(
            "Available Placeholders: " + ", ".join(template_manager.get_available_placeholders()),
            size=11,
            color=COLORS['text_secondary'],
            italic=True
        )

        def load_template(e=None):
            """Load selected template"""
            template_type = template_type_dropdown.value
            language = 'en' if language_tabs.selected_index == 0 else 'az'

            template = template_manager.get_template(template_type, language)

            if template:
                subject_field.value = template['subject']
                body_field.value = template['body_template']
            else:
                subject_field.value = ""
                body_field.value = ""

            # Only update if controls are already on page
            if self.page:
                try:
                    subject_field.update()
                    body_field.update()
                except:
                    pass  # Controls not added to page yet

        def save_template(e):
            """Save template to database"""
            template_type = template_type_dropdown.value
            language = 'en' if language_tabs.selected_index == 0 else 'az'

            if not subject_field.value or not body_field.value:
                self.show_error_message("Subject and body cannot be empty")
                return

            success = template_manager.save_template(
                template_type=template_type,
                language=language,
                subject=subject_field.value,
                body_template=body_field.value
            )

            if success:
                self.show_success_message(f"Template saved successfully ({template_type} - {language})")
            else:
                self.show_error_message("Failed to save template")

        def reset_to_default(e):
            """Reset template to default"""
            template_type = template_type_dropdown.value
            language = 'en' if language_tabs.selected_index == 0 else 'az'

            # Get default templates from migration
            from quiz_app.database.migration_email_system import get_default_templates
            defaults = get_default_templates()

            # Find matching default template
            default = next((t for t in defaults if t['template_type'] == template_type and t['language'] == language), None)

            if default:
                subject_field.value = default['subject']
                body_field.value = default['body_template']
                subject_field.update()
                body_field.update()
                self.show_success_message("Template reset to default")
            else:
                self.show_error_message("Default template not found")

        def test_email(e):
            """Generate test email with sample data"""
            from quiz_app.utils.email_handler import EmailHandler

            # Get current template values
            template_type = template_type_dropdown.value
            language = 'en' if language_tabs.selected_index == 0 else 'az'
            subject = subject_field.value
            body = body_field.value

            if not subject or not body:
                self.show_error_message("Please enter both subject and body before testing")
                return

            # Get current user's email
            current_user_email = self.user_data.get('email', 'admin@example.com')
            current_user_name = self.user_data.get('full_name', 'Test User')

            # Sample data for testing
            sample_data = {
                'full_name': current_user_name,
                'exam_name': 'Sample Exam - Test Assignment',
                'score': '85',
                'passing_score': '70',
                'status': 'PASSED' if template_type == 'passed' else 'NOT PASSED' if template_type == 'failed' else 'Pending',
                'correct': '17',
                'incorrect': '3',
                'unanswered': '0',
                'total_questions': '20'
            }

            # Replace placeholders with sample data
            test_subject = subject
            test_body = body
            for key, value in sample_data.items():
                placeholder = f"{{{{{key}}}}}"
                test_subject = test_subject.replace(placeholder, value)
                test_body = test_body.replace(placeholder, value)

            # Open email draft
            email_handler = EmailHandler()
            success = email_handler.open_email_draft(
                to_email=current_user_email,
                subject=test_subject,
                body=test_body
            )

            if success:
                self.show_success_message(f"Test email opened for {current_user_email}")
            else:
                self.show_error_message("Failed to open email client")

        # Hook up change events
        template_type_dropdown.on_change = load_template
        language_tabs.on_change = load_template

        # Load initial template (called directly, not as async task)
        load_template()

        return ft.Container(
            content=ft.Column([
                # Header
                ft.Row([
                    ft.Icon(ft.icons.EMAIL, size=32, color='#9C27B0'),
                    ft.Column([
                        ft.Text("Email Templates", size=18, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                        ft.Text("Customize email notifications for exam results", size=13, color=COLORS['text_secondary'])
                    ], spacing=2, expand=True)
                ], spacing=15),

                ft.Container(height=15),

                # Template selector
                ft.Row([
                    template_type_dropdown,
                    ft.Container(width=20),
                    language_tabs
                ], spacing=10),

                ft.Container(height=15),

                # Subject field
                subject_field,

                ft.Container(height=10),

                # Body field
                body_field,

                ft.Container(height=5),

                # Placeholders help
                placeholders_text,

                ft.Container(height=15),

                # Action buttons
                ft.Row([
                    ft.ElevatedButton(
                        text="Save Template",
                        icon=ft.icons.SAVE,
                        on_click=save_template,
                        style=ft.ButtonStyle(
                            bgcolor='#9C27B0',
                            color=ft.colors.WHITE
                        )
                    ),
                    ft.OutlinedButton(
                        text="Reset to Default",
                        icon=ft.icons.RESTORE,
                        on_click=reset_to_default
                    ),
                    ft.Container(expand=True),
                    ft.TextButton(
                        text="Test Email",
                        icon=ft.icons.SEND,
                        on_click=test_email
                    )
                ], spacing=10)
            ], spacing=5),
            padding=ft.padding.all(20),
            bgcolor=ft.colors.WHITE,
            border_radius=12,
            border=ft.border.all(1, COLORS['border'])
        )

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

        # Email Templates Card
        email_templates_card = self.build_email_templates_card()

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
                language_card,
                ft.Container(height=20),
                email_templates_card
            ], scroll=ft.ScrollMode.AUTO, expand=True)
        ], expand=True)
