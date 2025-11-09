import flet as ft
from quiz_app.config import COLORS

class BaseAdminLayout(ft.UserControl):
    def __init__(self, session_manager, user_data, logout_callback, view_switcher=None):
        super().__init__()
        self.session_manager = session_manager
        self.user_data = user_data
        self.logout_callback = logout_callback
        self.view_switcher = view_switcher  # For expert role switching
        self.selected_nav_index = 0
        self.db = None  # Will be set by subclass

        # Dynamic height properties
        self.dynamic_height = 700  # Default fallback height
        self.TOP_BAR_HEIGHT = 65   # Top bar height (padding + font size + border)
        self.BUFFER = 20           # Buffer for margins/padding
        self.MIN_HEIGHT = 600      # Minimum height for small windows
        
        # Navigation items (no filtering - experts can now see User Management)
        self.nav_items = [
            {"title": "Dashboard", "icon": ft.icons.DASHBOARD, "route": "dashboard"},
            {"title": "User Management", "icon": ft.icons.PEOPLE, "route": "users"},
            {"title": "Exam Assignments", "icon": ft.icons.QUIZ, "route": "exams"},
            {"title": "Question Bank", "icon": ft.icons.HELP, "route": "questions"},
            {"title": "Grading", "icon": ft.icons.GRADING, "route": "grading"},
            {"title": "Reports", "icon": ft.icons.ANALYTICS, "route": "reports"},
            {"title": "Settings", "icon": ft.icons.SETTINGS, "route": "settings"}
        ]

        # Grading badge indicator (blue circle)
        self.grading_badge = ft.Container(
            content=ft.Container(
                width=8,
                height=8,
                border_radius=4,
                bgcolor=ft.colors.BLUE,
            ),
            visible=False,  # Hidden by default
        )

        # Create navigation rail WITHOUT expand - let parent container handle constraints
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Stack([
                        ft.Icon(item["icon"]),
                        ft.Container(
                            content=self.grading_badge if item["route"] == "grading" else None,
                            alignment=ft.alignment.top_right,
                            offset=ft.Offset(0.3, -0.3),
                        ) if item["route"] == "grading" else ft.Icon(item["icon"])
                    ]) if item["route"] == "grading" else item["icon"],
                    label=item["title"]
                ) for item in self.nav_items
            ],
            on_change=self.nav_changed,
            bgcolor=COLORS['surface']
        )
        
        # Main content area
        self.content_area = ft.Container(
            expand=True,
            padding=ft.padding.all(20),
            bgcolor=COLORS['background']
        )
        
        # Top bar
        self.top_bar = self.create_top_bar()
        
        # Main container (will be set in build method)
        self.main_container = None
    
    def create_top_bar(self):
        # Title - change for expert
        if self.user_data['role'] == 'expert':
            title = "Quiz Expert System"
        else:
            title = "Quiz Administration System"

        # Right side controls
        right_controls = []

        # Add view switcher for experts (if provided)
        if self.view_switcher:
            right_controls.append(self.view_switcher)

        # User info and logout
        right_controls.extend([
            ft.Icon(ft.icons.PERSON, color=COLORS['text_secondary']),
            ft.Text(
                f"Welcome, {self.user_data['full_name']}",
                color=COLORS['text_secondary']
            ),
            ft.IconButton(
                icon=ft.icons.LOGOUT,
                tooltip="Logout",
                on_click=self.logout_clicked,
                icon_color=COLORS['error']
            )
        ])

        return ft.Container(
            content=ft.Row([
                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=COLORS['text_primary']
                ),
                ft.Row(right_controls, spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            bgcolor=COLORS['surface'],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS['secondary']))
        )
    
    def calculate_dynamic_height(self):
        """Calculate dynamic height based on current window size"""
        if self.page and hasattr(self.page, 'window') and self.page.window.height:
            available_height = self.page.window.height - self.TOP_BAR_HEIGHT - self.BUFFER
            return max(available_height, self.MIN_HEIGHT)
        return self.dynamic_height  # Return current height if page not available
    
    def update_height(self):
        """Update the dynamic height and refresh the layout"""
        new_height = self.calculate_dynamic_height()
        if new_height != self.dynamic_height:
            self.dynamic_height = new_height
            if self.main_container:
                self.main_container.height = self.dynamic_height
                if self.page:  # Only update if control is added to page
                    self.update()
    
    def page_resized(self, e):
        """Handle window resize events"""
        self.update_height()
    
    def did_mount(self):
        """Called after the control is added to the page"""
        super().did_mount()
        if self.page:
            # Set up resize event handler
            self.page.on_resized = self.page_resized
            # Calculate initial height
            self.update_height()
    
    def build(self):
        # Create main container with dynamic height
        self.main_container = ft.Container(
            content=ft.Row([
                self.nav_rail,
                ft.VerticalDivider(width=1),
                self.content_area
            ], spacing=0),
            expand=True,
            height=self.dynamic_height  # Dynamic height to bound NavigationRail
        )
        
        return ft.Column([
            self.top_bar,
            self.main_container
        ], spacing=0)
    
    def nav_changed(self, e):
        self.selected_nav_index = e.control.selected_index
        route = self.nav_items[self.selected_nav_index]["route"]
        self.on_route_changed(route)
    
    def on_route_changed(self, route):
        # Override in subclasses
        pass
    
    def set_content(self, content):
        self.content_area.content = content
        if self.page:  # Only update if control is added to page
            self.update()
    
    def logout_clicked(self, e):
        self.logout_callback(self.page)

    def check_ungraded_items(self):
        """Check if there are any ungraded essay/short answer questions"""
        if not self.db:
            return 0

        try:
            ungraded = self.db.execute_query("""
                SELECT COUNT(DISTINCT es.id) as count
                FROM exam_sessions es
                JOIN user_answers ua ON ua.session_id = es.id
                JOIN questions q ON ua.question_id = q.id
                WHERE q.question_type IN ('essay', 'short_answer')
                AND ua.points_earned IS NULL
                AND ua.answer_text IS NOT NULL
                AND ua.answer_text != ''
                AND es.is_completed = 1
            """)

            count = ungraded[0]['count'] if ungraded else 0
            return count
        except Exception as e:
            print(f"Error checking ungraded items: {e}")
            return 0

    def update_grading_badge(self):
        """Update the grading badge visibility based on ungraded items"""
        try:
            ungraded_count = self.check_ungraded_items()
            self.grading_badge.visible = ungraded_count > 0

            if self.page:
                self.update()
        except Exception as e:
            print(f"Error updating grading badge: {e}")