import flet as ft
from quiz_app.utils.auth import AuthManager
from quiz_app.config import COLORS
from quiz_app.utils.localization import t
from quiz_app.utils.feedback_dialog import create_feedback_button

class LoginView(ft.UserControl):
    def __init__(self, session_manager, on_login_success):
        super().__init__()
        self.expand = True  # Fix for UserControl expand issue
        self.session_manager = session_manager
        self.on_login_success = on_login_success
        self.auth_manager = AuthManager()

        # Form controls
        self.username_field = ft.TextField(
            label=t('username_or_email'),
            prefix_icon=ft.icons.PERSON,
            border_radius=8,
            filled=True,
            width=300,
            text_align=ft.TextAlign.LEFT,
            on_submit=self.login_clicked
        )

        self.password_field = ft.TextField(
            label=t('password'),
            prefix_icon=ft.icons.LOCK,
            password=True,
            can_reveal_password=True,
            border_radius=8,
            filled=True,
            width=300,
            text_align=ft.TextAlign.LEFT,
            on_submit=self.login_clicked
        )

        self.login_button = ft.ElevatedButton(
            text=t('login'),
            width=300,
            height=45,
            style=ft.ButtonStyle(
                bgcolor=COLORS['primary'],
                color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
                alignment=ft.alignment.center
            ),
            on_click=self.login_clicked
        )

        self.error_text = ft.Text(
            "",
            color=COLORS['error'],
            size=12,
            visible=False,
            width=300,
            max_lines=3,
            overflow=ft.TextOverflow.ELLIPSIS,
            text_align=ft.TextAlign.CENTER
        )

        self.loading_ring = ft.ProgressRing(
            width=16,
            height=16,
            visible=False
        )
    
    def build(self):
        return ft.Stack([
            # Background
            ft.Container(
                image_src="images/background.png",
                image_fit=ft.ImageFit.COVER,
                image_opacity=0.9,
                bgcolor=COLORS['background'],
                expand=True
            ),
            # Centered login card
            ft.Container(
                content=ft.Stack([
                    # Main login card content
                    ft.Container(
                        content=ft.Column([
                            # Azercosmos Logo
                            ft.Image(
                                src="images/azercosmos-logo.png",
                                width=200,
                                fit=ft.ImageFit.CONTAIN
                            ),
                            ft.Container(height=20),
                            ft.Text(
                                t('app_name'),
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS['text_primary'],
                                text_align=ft.TextAlign.CENTER
                            ),
                            ft.Container(height=5),
                            ft.Text(
                                t('please_sign_in'),
                                size=14,
                                color=COLORS['text_secondary'],
                                text_align=ft.TextAlign.CENTER
                            ),
                            ft.Container(height=30),

                            # Login form fields
                            self.username_field,
                            ft.Container(height=5),
                            self.password_field,

                            # Error message
                            ft.Container(
                                content=self.error_text,
                                width=300,
                                alignment=ft.alignment.center
                            ),

                            ft.Container(height=15),

                            # Login button with loading indicator
                            ft.Row([
                                self.login_button,
                                self.loading_ring
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, tight=True),
                        width=420,
                        padding=ft.padding.all(35),
                        bgcolor=ft.colors.with_opacity(0.97, ft.colors.WHITE),
                        border_radius=16,
                        shadow=ft.BoxShadow(
                            spread_radius=1,
                            blur_radius=30,
                            color=ft.colors.with_opacity(0.2, ft.colors.BLACK),
                            offset=ft.Offset(0, 10)
                        ),
                        border=ft.border.all(1, ft.colors.with_opacity(0.1, ft.colors.WHITE))
                    ),
                    # Feedback button - positioned at top-right of login card
                    ft.Container(
                        content=create_feedback_button(
                            user_data=None,
                            current_page="Login Page",
                            is_icon_only=True
                        ),
                        right=10,
                        top=10
                    )
                ]),
                alignment=ft.alignment.center,
                expand=True
            )
        ], expand=True)
    
    def login_clicked(self, e):
        self.show_loading(True)
        self.hide_error()

        username = self.username_field.value.strip()
        password = self.password_field.value

        if not username or not password:
            self.show_error(t('enter_credentials'))
            self.show_loading(False)
            return

        try:
            # Authenticate user
            user_data = self.auth_manager.authenticate_user(username, password)

            if user_data:
                # Create session
                if self.session_manager.create_session(user_data):
                    # Check if password change is required
                    if user_data.get('password_change_required') == 1:
                        # Show password change dialog BEFORE proceeding to dashboard
                        self.show_loading(False)
                        self.show_force_password_change_dialog(user_data)
                    else:
                        # Update loading message - keep loading indicator visible
                        self.login_button.text = t('loading_dashboard')
                        self.update()

                        # Proceed to dashboard - loading will be turned off by dashboard
                        self.on_login_success(self.page, user_data)
                else:
                    # Show detailed error from session manager
                    error_detail = getattr(self.session_manager, 'last_error', None)
                    if error_detail:
                        self.show_error(f"Session failed: {error_detail}")
                    else:
                        self.show_error(t('session_failed'))
                    self.show_loading(False)
            else:
                self.show_error(t('invalid_credentials'))
                self.show_loading(False)
        except Exception as ex:
            print(f"[ERROR] Login error: {ex}")
            import traceback
            tb = traceback.format_exc()
            print(tb)
            # Show the actual exception in UI
            self.show_error(f"Login error: {type(ex).__name__}: {str(ex)}")
            self.show_loading(False)

    def show_error(self, message: str):
        self.error_text.value = message
        self.error_text.visible = True
        self.update()

        # Also show in dialog for long errors
        if len(message) > 50 or '\n' in message:
            def close_dialog(e):
                dialog.open = False
                self.page.dialog = None  # Clear dialog reference

                # Clear overlays too
                if hasattr(self.page, 'overlay') and self.page.overlay:
                    self.page.overlay.clear()

                self.page.update()

            dialog = ft.AlertDialog(
                title=ft.Text("Error Details"),
                content=ft.Container(
                    content=ft.Text(
                        message,
                        selectable=True,
                        size=12
                    ),
                    width=500,
                    padding=10
                ),
                actions=[
                    ft.TextButton("Close", on_click=close_dialog)
                ]
            )

            # Clear any existing dialogs first
            if self.page.dialog:
                self.page.dialog.open = False
                self.page.dialog = None

            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def hide_error(self):
        self.error_text.visible = False
        self.update()

    def show_loading(self, show: bool):
        self.loading_ring.visible = show
        self.login_button.disabled = show
        if show:
            self.login_button.text = t('signing_in')
        else:
            self.login_button.text = t('login')
        self.update()

    def show_force_password_change_dialog(self, user_data):
        """
        Show mandatory password change dialog for first-time login
        User cannot skip or close this dialog - must change password
        """
        from quiz_app.database.database import Database
        from quiz_app.config import COLORS

        db = Database()
        new_password_field = ft.TextField(
            label="New Password",
            password=True,
            can_reveal_password=True,
            autofocus=True,
            hint_text="Enter a strong password"
        )

        confirm_password_field = ft.TextField(
            label="Confirm New Password",
            password=True,
            can_reveal_password=True,
            hint_text="Re-enter your password"
        )

        error_text = ft.Text(
            "",
            color=COLORS['error'],
            size=14,
            visible=False
        )

        def change_password(e):
            # Validate inputs
            if not new_password_field.value or len(new_password_field.value) < 6:
                error_text.value = "Password must be at least 6 characters"
                error_text.visible = True
                self.page.update()
                return

            if new_password_field.value != confirm_password_field.value:
                error_text.value = "Passwords do not match"
                error_text.visible = True
                self.page.update()
                return

            # Update password
            try:
                self.auth_manager.update_password(user_data['id'], new_password_field.value)

                # Clear password_change_required flag
                db.execute_update(
                    "UPDATE users SET password_change_required = 0 WHERE id = ?",
                    (user_data['id'],)
                )

                # Update user_data to reflect the change
                user_data['password_change_required'] = 0

                # CRITICAL: Close dialog completely before loading dashboard
                change_dialog.open = False
                self.page.dialog = None

                # Clear any overlays too
                if hasattr(self.page, 'overlay') and self.page.overlay:
                    self.page.overlay.clear()

                self.page.update()

                # Small delay to ensure dialog closes before dashboard loads
                import time
                time.sleep(0.15)

                # Now proceed to dashboard
                self.login_button.text = t('loading_dashboard')
                self.update()
                self.on_login_success(self.page, user_data)

            except Exception as ex:
                error_text.value = f"Failed to update password: {str(ex)}"
                error_text.visible = True
                self.page.update()

        change_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.LOCK_RESET, color=COLORS['warning'], size=28),
                ft.Text("Password Change Required", weight=ft.FontWeight.BOLD)
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "You must change your temporary password before continuing.",
                        size=14,
                        color=COLORS['text_primary']
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text(
                            "⚠️ This is your first login. For security reasons, please create a new strong password.",
                            size=12,
                            color=COLORS['warning'],
                            weight=ft.FontWeight.W_500
                        ),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                        padding=10,
                        border_radius=8,
                        border=ft.border.all(1, COLORS['warning'])
                    ),
                    ft.Container(height=15),
                    new_password_field,
                    confirm_password_field,
                    ft.Container(height=5),
                    error_text
                ], spacing=10, tight=True),
                width=450
            ),
            actions=[
                ft.ElevatedButton(
                    "Change Password",
                    icon=ft.icons.CHECK,
                    on_click=change_password,
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.page.dialog = change_dialog
        change_dialog.open = True
        self.page.update()
