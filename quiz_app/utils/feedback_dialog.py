"""
Feedback Dialog Component
Allows users to send feedback/issues via email with optional screenshot attachment
"""

import flet as ft
from datetime import datetime
import platform
from quiz_app.config import COLORS
from quiz_app.utils.localization import t
from quiz_app.utils.email_handler import EmailHandler


class FeedbackDialog(ft.UserControl):
    """Dialog component for sending feedback/issues to support"""

    # Support email address
    SUPPORT_EMAIL = "elvin.osmanov@azercosmos.az"

    def __init__(self, user_data=None, current_page=None, close_callback=None):
        """
        Initialize feedback dialog

        Args:
            user_data: Dictionary with user information (optional, None for non-logged-in users)
            current_page: String indicating current page/view (optional)
            close_callback: Function to call when dialog is closed
        """
        super().__init__()
        self.user_data = user_data
        self.current_page = current_page or "Unknown"
        self.close_callback = close_callback

        # File picker for screenshot attachment
        self.file_picker = ft.FilePicker(on_result=self.file_picker_result)
        self.selected_file = None
        self.selected_file_text = ft.Text("", size=12, color=COLORS['text_secondary'])

        # Form fields
        self.feedback_type = ft.Dropdown(
            label="Feedback Type",
            width=500,
            options=[
                ft.dropdown.Option("bug", "🐛 Bug Report"),
                ft.dropdown.Option("feature", "💡 Feature Request"),
                ft.dropdown.Option("question", "❓ Question"),
                ft.dropdown.Option("other", "📝 Other"),
            ],
            value="bug",
            border_radius=8,
        )

        self.subject_field = ft.TextField(
            label="Subject",
            width=500,
            border_radius=8,
            hint_text="Brief description of your issue/feedback",
        )

        self.message_field = ft.TextField(
            label="Message",
            width=500,
            height=200,
            multiline=True,
            min_lines=8,
            max_lines=15,
            border_radius=8,
            hint_text="Please describe your issue or feedback in detail...",
        )

        self.contact_email_field = ft.TextField(
            label="Your Email (for follow-up)",
            width=500,
            border_radius=8,
            hint_text="your.email@example.com (optional)",
        )

        # Pre-fill user email if available
        if user_data and user_data.get('email'):
            self.contact_email_field.value = user_data['email']

        # Buttons
        self.send_button = ft.ElevatedButton(
            text="Send Feedback",
            icon=ft.icons.SEND,
            style=ft.ButtonStyle(
                bgcolor=COLORS['primary'],
                color=ft.colors.WHITE,
            ),
            on_click=self.send_feedback,
        )

        self.cancel_button = ft.TextButton(
            text="Cancel",
            on_click=self.close_dialog,
        )

        self.attach_button = ft.OutlinedButton(
            text="Attach Screenshot",
            icon=ft.icons.ATTACH_FILE,
            on_click=lambda _: self.file_picker.pick_files(
                allowed_extensions=["png", "jpg", "jpeg", "gif"],
                dialog_title="Select Screenshot"
            ),
        )

        # Status text
        self.status_text = ft.Text("", size=12, visible=False)

        # Alert dialog
        self.dialog = None

    def build(self):
        """Build the feedback dialog UI"""
        # Create overlay for file picker
        if self.page:
            self.page.overlay.append(self.file_picker)

        return ft.Container()  # Empty container, actual dialog shown via show()

    def file_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle file picker result"""
        if e.files:
            self.selected_file = e.files[0]
            self.selected_file_text.value = f"📎 {self.selected_file.name}"
            self.selected_file_text.color = COLORS['success']
        else:
            self.selected_file = None
            self.selected_file_text.value = ""

        if self.page:
            self.page.update()

    def get_system_info(self) -> str:
        """Get system information for debugging"""
        info_lines = [
            "\n\n--- System Information ---",
            f"Platform: {platform.system()} {platform.release()}",
            f"Python: {platform.python_version()}",
            f"Page: {self.current_page}",
        ]

        if self.user_data:
            info_lines.extend([
                f"User: {self.user_data.get('username', 'Unknown')} ({self.user_data.get('full_name', 'Unknown')})",
                f"Role: {self.user_data.get('role', 'Unknown')}",
                f"User ID: {self.user_data.get('id', 'Unknown')}",
            ])
            if self.user_data.get('department'):
                info_lines.append(f"Department: {self.user_data.get('department', 'N/A')}")
        else:
            info_lines.append("User: Not logged in")

        info_lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(info_lines)

    def build_email_body(self) -> str:
        """Build email body with all information"""
        feedback_type_labels = {
            "bug": "Bug Report",
            "feature": "Feature Request",
            "question": "Question",
            "other": "Other",
        }

        body_parts = [
            f"Feedback Type: {feedback_type_labels.get(self.feedback_type.value, 'Unknown')}",
            "",
            "Message:",
            "-" * 50,
            self.message_field.value or "(No message provided)",
            "-" * 50,
        ]

        # Add contact email if provided
        if self.contact_email_field.value and self.contact_email_field.value.strip():
            body_parts.extend([
                "",
                f"Contact Email: {self.contact_email_field.value.strip()}",
            ])

        # Add screenshot note if attached
        if self.selected_file:
            body_parts.extend([
                "",
                f"📎 Screenshot Attached: {self.selected_file.name}",
                f"   Path: {self.selected_file.path}",
                "",
                "NOTE: Please manually attach the screenshot from the path above.",
            ])

        # Add system information
        body_parts.append(self.get_system_info())

        return "\n".join(body_parts)

    def send_feedback(self, e):
        """Send feedback via email"""
        # Validate required fields
        if not self.subject_field.value or not self.subject_field.value.strip():
            self.show_error("Please enter a subject")
            return

        if not self.message_field.value or not self.message_field.value.strip():
            self.show_error("Please enter your feedback message")
            return

        # Validate email if provided
        if self.contact_email_field.value and self.contact_email_field.value.strip():
            if not EmailHandler.validate_email(self.contact_email_field.value.strip()):
                self.show_error("Please enter a valid email address")
                return

        # Build email subject and body
        subject = f"[Exam Quiz App Feedback] {self.subject_field.value}"
        body = self.build_email_body()

        # Open email draft
        success = EmailHandler.open_email_draft(
            to_email=self.SUPPORT_EMAIL,
            subject=subject,
            body=body
        )

        if success:
            self.show_success("Email draft opened! Please review and send it.")
            # Close dialog after showing success message
            self.close_dialog(None)
        else:
            self.show_error("Failed to open email client. Please check your email configuration.")

    def show_error(self, message: str):
        """Show error message"""
        self.status_text.value = f"❌ {message}"
        self.status_text.color = COLORS['error']
        self.status_text.visible = True
        if self.page:
            self.page.update()

    def show_success(self, message: str):
        """Show success message"""
        self.status_text.value = f"✅ {message}"
        self.status_text.color = COLORS['success']
        self.status_text.visible = True
        if self.page:
            self.page.update()

    def close_dialog(self, e):
        """Close the dialog"""
        if self.dialog:
            self.dialog.open = False
            if self.page:
                self.page.update()

        if self.close_callback:
            self.close_callback()

    def show(self, page):
        """Show the feedback dialog"""
        self.page = page

        # Add file picker to overlay if not already added
        if self.file_picker not in page.overlay:
            page.overlay.append(self.file_picker)

        # Create dialog content
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.FEEDBACK, color=COLORS['primary']),
                ft.Text("Send Feedback / Report Issue", weight=ft.FontWeight.BOLD),
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Help us improve! Report bugs, request features, or ask questions.",
                        size=13,
                        color=COLORS['text_secondary'],
                    ),
                    ft.Divider(),
                    self.feedback_type,
                    self.subject_field,
                    self.message_field,
                    self.contact_email_field,
                    ft.Row([
                        self.attach_button,
                        self.selected_file_text,
                    ], spacing=10),
                    ft.Container(height=5),
                    self.status_text,
                ], spacing=15, tight=True),
                width=550,
            ),
            actions=[
                self.cancel_button,
                self.send_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(self.dialog)
        self.dialog.open = True
        page.update()


def create_feedback_button(user_data=None, current_page=None, is_icon_only=True):
    """
    Create a feedback button that can be added to any view

    Args:
        user_data: User information dictionary (optional)
        current_page: Current page/view name (optional)
        is_icon_only: If True, shows only icon; if False, shows icon + text

    Returns:
        ft.Container with styled button
    """
    def show_feedback_dialog(e):
        """Show feedback dialog"""
        print(f"[FEEDBACK] Button clicked! Opening feedback dialog for page: {current_page}")
        try:
            page = e.page
            if not page:
                print("[FEEDBACK ERROR] No page reference available!")
                return

            feedback = FeedbackDialog(
                user_data=user_data,
                current_page=current_page,
            )
            feedback.show(page)
            print("[FEEDBACK] Dialog shown successfully")
        except Exception as ex:
            print(f"[FEEDBACK ERROR] Failed to show dialog: {ex}")
            import traceback
            traceback.print_exc()

    if is_icon_only:
        # Small icon-only button for minimal footprint - subtle gray color
        button = ft.IconButton(
            icon=ft.icons.BUG_REPORT,
            icon_color=ft.colors.GREY_600,
            bgcolor=ft.colors.GREY_200,
            tooltip="Report bugs or send feedback",
            on_click=show_feedback_dialog,
            icon_size=18,
        )
        return button
    else:
        return ft.OutlinedButton(
            text="Feedback",
            icon=ft.icons.FEEDBACK_OUTLINED,
            tooltip="Send Feedback / Report Issue",
            on_click=show_feedback_dialog,
        )
