import flet as ft
from quiz_app.utils.auth import AuthManager
from quiz_app.config import COLORS

class LoginView(ft.UserControl):
    def __init__(self, session_manager, on_login_success):
        super().__init__()
        self.expand = True  # Fix for UserControl expand issue
        self.session_manager = session_manager
        self.on_login_success = on_login_success
        self.auth_manager = AuthManager()
        
        # Form controls
        self.username_field = ft.TextField(
            label="Username or Email",
            prefix_icon=ft.icons.PERSON,
            border_radius=8,
            filled=True,
            width=300
        )
        
        self.password_field = ft.TextField(
            label="Password",
            prefix_icon=ft.icons.LOCK,
            password=True,
            can_reveal_password=True,
            border_radius=8,
            filled=True,
            width=300
        )
        
        self.login_button = ft.ElevatedButton(
            text="Login",
            width=300,
            height=45,
            style=ft.ButtonStyle(
                bgcolor=COLORS['primary'],
                color=ft.colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8)
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
        return ft.Container(
            content=ft.Column([
                # Login Form with fixed width (includes header inside)
                ft.Container(
                    content=ft.Column([
                        # Header inside login container
                        ft.Icon(
                            ft.icons.QUIZ,
                            size=64,
                            color=COLORS['primary']
                        ),
                        ft.Text(
                            "Quiz Examination System",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS['text_primary']
                        ),
                        ft.Text(
                            "Please sign in to continue",
                            size=16,
                            color=COLORS['text_secondary']
                        ),
                        ft.Container(height=30),  # Spacing between header and form
                        
                        # Login form fields
                        self.username_field,
                        self.password_field,
                        self.error_text,
                        
                        ft.Row([
                            self.login_button,
                            self.loading_ring
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        
                        # Default credentials info
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(height=20),
                                ft.Text(
                                    "Default Admin Credentials:",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=COLORS['text_secondary']
                                ),
                                ft.Text(
                                    "Username: admin",
                                    size=12,
                                    color=COLORS['text_secondary']
                                ),
                                ft.Text(
                                    "Password: admin123",
                                    size=12,
                                    color=COLORS['text_secondary']
                                )
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            margin=ft.margin.only(top=20),
                            padding=ft.padding.all(15),
                            bgcolor=ft.colors.BLUE_50,
                            border_radius=8
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                    width=450,  # Fixed width for login container
                    padding=ft.padding.all(30),
                    bgcolor=ft.colors.with_opacity(0.95, COLORS['surface']),
                    border_radius=12,
                    shadow=ft.BoxShadow(
                        spread_radius=2,
                        blur_radius=20,
                        color=ft.colors.with_opacity(0.15, ft.colors.BLACK),
                        offset=ft.Offset(0, 8)
                    )
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.center,
            padding=ft.padding.all(20),
            # Background image with fallback
            image_src="images/background.jpg",
            image_fit=ft.ImageFit.COVER,
            image_opacity=0.9,
            bgcolor=COLORS['background'],  # Fallback color if image fails
            expand=True,  # Full screen expansion
        )
    
    def login_clicked(self, e):
        self.show_loading(True)
        self.hide_error()
        
        username = self.username_field.value.strip()
        password = self.password_field.value
        
        if not username or not password:
            self.show_error("Please enter both username and password")
            self.show_loading(False)
            return
        
        # Authenticate user
        user_data = self.auth_manager.authenticate_user(username, password)
        
        if user_data:
            # Create session
            if self.session_manager.create_session(user_data):
                self.on_login_success(self.page, user_data)
            else:
                self.show_error("Failed to create session")
                self.show_loading(False)
        else:
            self.show_error("Invalid username or password")
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
            self.login_button.text = "Signing in..."
        else:
            self.login_button.text = "Login"
        self.update()