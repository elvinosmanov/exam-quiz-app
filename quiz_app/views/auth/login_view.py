import flet as ft
from quiz_app.utils.auth import AuthManager
from quiz_app.config import COLORS
from quiz_app.utils.localization import t

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
            size=14,
            visible=False
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
                content=ft.Container(
                    content=ft.Column([
                        # Header with icon
                        ft.Icon(
                            ft.icons.QUIZ_ROUNDED,
                            size=70,
                            color=COLORS['primary']
                        ),
                        ft.Container(height=15),
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
                            height=20,
                            alignment=ft.alignment.center
                        ),

                        ft.Container(height=10),

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
                    # Turn off loading before page transition
                    self.show_loading(False)
                    # Proceed to dashboard
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