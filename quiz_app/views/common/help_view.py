"""
Help View Component for Quiz Examination System
Provides comprehensive, role-based help documentation with search functionality
"""

import flet as ft
from quiz_app.config import COLORS
from quiz_app.utils.localization import t
from quiz_app.data.help_content import HELP_CONTENT


class HelpView(ft.UserControl):
    def __init__(self, user_role='examinee'):
        super().__init__()
        self.expand = True  # Fix for UserControl expand issue
        self.user_role = user_role  # 'admin', 'expert', or 'examinee'
        self.search_query = ""
        self.selected_category = None
        self.selected_topic = None

        # Get role-specific content
        self.all_topics = {}
        self.categories = []
        self._load_role_content()

        # UI Components (will be created in build)
        self.search_field = None
        self.category_sidebar = None
        self.topics_list_container = None
        self.content_area_container = None

    def _load_role_content(self):
        """Load categories and topics based on user role"""
        # Treat 'expert' as 'admin' for help content
        role = 'admin' if self.user_role in ['admin', 'expert'] else 'examinee'

        role_content = HELP_CONTENT.get(role, {})
        common_content = HELP_CONTENT.get('common', {})

        # Merge categories
        self.categories = []
        self.categories.extend(role_content.get('categories', []))
        self.categories.extend(common_content.get('categories', []))

        # Merge topics
        self.all_topics = {}
        self.all_topics.update(role_content.get('topics', {}))
        self.all_topics.update(common_content.get('topics', {}))

    def build(self):
        """Build the help view UI"""
        # Search bar
        self.search_field = ft.TextField(
            hint_text=t('search_help'),
            prefix_icon=ft.icons.SEARCH,
            on_change=self.on_search_changed,
            border_radius=8,
            border_color=COLORS['secondary'],
            focused_border_color=COLORS['primary'],
            expand=True
        )

        # Build initial UI components
        self.category_sidebar = self.build_category_sidebar()
        self.topics_list_container = self.build_topics_list()
        self.content_area_container = self.build_content_area()

        # Store the main content row so we can update it later
        self.main_row = ft.Row([
            # Left: Categories
            self.category_sidebar,

            # Divider
            ft.VerticalDivider(width=1, color=COLORS['secondary']),

            # Middle: Topics list
            self.topics_list_container,

            # Divider
            ft.VerticalDivider(width=1, color=COLORS['secondary']),

            # Right: Content
            self.content_area_container
        ], expand=True, spacing=0)

        return ft.Column([
            # Header with search
            ft.Container(
                content=ft.Row([
                    ft.Text(
                        t('help_center'),
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS['text_primary']
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        content=self.search_field,
                        width=400
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.all(20),
                bgcolor=COLORS['surface'],
                border=ft.border.only(bottom=ft.border.BorderSide(1, COLORS['secondary']))
            ),

            # Main content area
            ft.Container(
                content=self.main_row,
                expand=True,
                bgcolor=COLORS['background']
            )
        ], spacing=0, expand=True)

    def build_category_sidebar(self):
        """Build the category sidebar"""
        category_items = []

        for category in self.categories:
            is_selected = self.selected_category == category['id']

            category_item = ft.Container(
                content=ft.Row([
                    ft.Icon(
                        category['icon'],
                        size=18,
                        color=COLORS['surface'] if is_selected else COLORS['primary']
                    ),
                    ft.Text(
                        t(category['title_key']),
                        size=14,
                        weight=ft.FontWeight.W_500 if is_selected else ft.FontWeight.NORMAL,
                        color=COLORS['surface'] if is_selected else COLORS['text_primary']
                    )
                ], spacing=10),
                padding=ft.padding.all(12),
                border_radius=6,
                bgcolor=COLORS['primary'] if is_selected else ft.colors.TRANSPARENT,
                on_click=lambda e, cat=category: self.select_category(cat),
                ink=True
            )
            category_items.append(category_item)

        return ft.Container(
            content=ft.Column(
                category_items,
                spacing=5,
                scroll=ft.ScrollMode.AUTO
            ),
            width=220,
            padding=ft.padding.all(15),
            bgcolor=COLORS['surface']
        )

    def build_topics_list(self):
        """Build the topics list (middle column)"""
        if not self.selected_category and not self.search_query:
            # Show welcome message
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.TOUCH_APP, size=48, color=COLORS['secondary']),
                    ft.Text(
                        t('help_select_topic'),
                        size=14,
                        color=COLORS['text_secondary'],
                        text_align=ft.TextAlign.CENTER
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER),
                width=280,
                padding=ft.padding.all(20)
            )

        # Get topics to display
        topics_to_show = self.get_filtered_topics()

        if not topics_to_show:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.SEARCH_OFF, size=48, color=COLORS['secondary']),
                    ft.Text(
                        t('no_results'),
                        size=14,
                        color=COLORS['text_secondary'],
                        text_align=ft.TextAlign.CENTER
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER),
                width=280,
                padding=ft.padding.all(20)
            )

        # Build topic items
        topic_items = []
        for topic_id in topics_to_show:
            if topic_id not in self.all_topics:
                continue

            topic = self.all_topics[topic_id]
            is_selected = self.selected_topic == topic_id

            topic_item = ft.Container(
                content=ft.Text(
                    t(topic['title_key']),
                    size=13,
                    color=COLORS['primary'] if is_selected else COLORS['text_primary'],
                    weight=ft.FontWeight.W_500 if is_selected else ft.FontWeight.NORMAL
                ),
                padding=ft.padding.all(10),
                border_radius=4,
                bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']) if is_selected
                        else ft.colors.TRANSPARENT,
                border=ft.border.all(1, COLORS['primary']) if is_selected
                       else ft.border.all(1, ft.colors.TRANSPARENT),
                on_click=lambda e, tid=topic_id: self.select_topic(tid),
                ink=True
            )
            topic_items.append(topic_item)

        return ft.Container(
            content=ft.Column(
                topic_items,
                spacing=3,
                scroll=ft.ScrollMode.AUTO
            ),
            width=280,
            padding=ft.padding.all(10)
        )

    def build_content_area(self):
        """Build the content display area (right column)"""
        if not self.selected_topic:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.HELP_OUTLINE, size=64, color=COLORS['secondary']),
                    ft.Container(height=10),
                    ft.Text(
                        t('help_select_topic'),
                        size=16,
                        color=COLORS['text_secondary'],
                        text_align=ft.TextAlign.CENTER
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER),
                expand=True
            )

        topic = self.all_topics.get(self.selected_topic)
        if not topic:
            return ft.Container(expand=True)

        content_sections = [
            # Title
            ft.Text(
                t(topic['title_key']),
                size=28,
                weight=ft.FontWeight.BOLD,
                color=COLORS['text_primary']
            ),
            ft.Divider(color=COLORS['secondary']),
            ft.Container(height=5),

            # Description
            ft.Text(
                t(topic['content_key']),
                size=15,
                color=COLORS['text_secondary']
            ),
            ft.Container(height=25),
        ]

        # Steps (if available)
        if 'steps' in topic and topic['steps']:
            content_sections.append(self.build_steps_section(topic['steps']))
            content_sections.append(ft.Container(height=20))

        # Tips (if available)
        if 'tips' in topic and topic['tips']:
            content_sections.append(self.build_tips_section(topic['tips']))
            content_sections.append(ft.Container(height=20))

        # Related topics (if available)
        if 'related' in topic and topic['related']:
            content_sections.append(self.build_related_section(topic['related']))

        return ft.Container(
            content=ft.Column(
                content_sections,
                spacing=10,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=ft.padding.all(25),
            expand=True
        )

    def build_steps_section(self, steps):
        """Build the steps section with numbered items"""
        step_items = []
        for i, step_key in enumerate(steps, 1):
            step_items.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(
                            str(i),
                            size=14,
                            color=COLORS['surface'],
                            weight=ft.FontWeight.BOLD
                        ),
                        bgcolor=COLORS['primary'],
                        border_radius=16,
                        width=32,
                        height=32,
                        alignment=ft.alignment.center
                    ),
                    ft.Container(
                        content=ft.Text(
                            t(step_key),
                            size=14,
                            color=COLORS['text_primary']
                        ),
                        expand=True
                    )
                ], spacing=12)
            )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.FORMAT_LIST_NUMBERED, size=20, color=COLORS['primary']),
                    ft.Text(
                        'Steps',
                        size=18,
                        weight=ft.FontWeight.W_600,
                        color=COLORS['text_primary']
                    )
                ], spacing=10),
                ft.Container(height=12),
                ft.Column(step_items, spacing=12)
            ]),
            padding=ft.padding.all(18),
            bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, COLORS['primary']))
        )

    def build_tips_section(self, tips):
        """Build the tips section with bullet points"""
        tip_items = []
        for tip_key in tips:
            tip_items.append(
                ft.Row([
                    ft.Icon(
                        ft.icons.CHECK_CIRCLE_OUTLINE,
                        size=18,
                        color=COLORS['success']
                    ),
                    ft.Container(
                        content=ft.Text(
                            t(tip_key),
                            size=14,
                            color=COLORS['text_primary']
                        ),
                        expand=True
                    )
                ], spacing=10)
            )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.LIGHTBULB_OUTLINE, size=20, color=COLORS['warning']),
                    ft.Text(
                        'Tips',
                        size=18,
                        weight=ft.FontWeight.W_600,
                        color=COLORS['text_primary']
                    )
                ], spacing=10),
                ft.Container(height=12),
                ft.Column(tip_items, spacing=10)
            ]),
            padding=ft.padding.all(18),
            bgcolor=ft.colors.with_opacity(0.05, COLORS['warning']),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, COLORS['warning']))
        )

    def build_related_section(self, related_ids):
        """Build the related topics section"""
        related_items = []
        for topic_id in related_ids:
            if topic_id not in self.all_topics:
                continue

            topic = self.all_topics[topic_id]
            related_items.append(
                ft.TextButton(
                    text=t(topic['title_key']),
                    icon=ft.icons.ARROW_FORWARD,
                    on_click=lambda e, tid=topic_id: self.select_topic(tid),
                    style=ft.ButtonStyle(
                        color=COLORS['primary']
                    )
                )
            )

        if not related_items:
            return ft.Container()

        return ft.Column([
            ft.Divider(color=COLORS['secondary']),
            ft.Text(
                t('related_topics'),
                size=18,
                weight=ft.FontWeight.W_600,
                color=COLORS['text_primary']
            ),
            ft.Container(height=5),
            ft.Column(related_items, spacing=2)
        ])

    def get_filtered_topics(self):
        """Get list of topic IDs based on current filters (category or search)"""
        if self.search_query:
            # Search mode
            return self.search_topics(self.search_query)
        elif self.selected_category:
            # Category mode
            for category in self.categories:
                if category['id'] == self.selected_category:
                    return category.get('topics', [])

        return []

    def search_topics(self, query):
        """Search topics by query string"""
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        matching_topics = []
        for topic_id, topic_data in self.all_topics.items():
            # Search in title
            title = t(topic_data['title_key']).lower()
            if query_lower in title:
                matching_topics.append(topic_id)
                continue

            # Search in description
            desc = t(topic_data['content_key']).lower()
            if query_lower in desc:
                matching_topics.append(topic_id)
                continue

            # Search in steps
            if 'steps' in topic_data:
                for step_key in topic_data['steps']:
                    if query_lower in t(step_key).lower():
                        matching_topics.append(topic_id)
                        break

        return matching_topics

    def select_category(self, category):
        """Handle category selection"""
        self.selected_category = category['id']
        self.selected_topic = None
        self.search_query = ""
        if self.search_field:
            self.search_field.value = ""

        # Rebuild UI components
        self.category_sidebar = self.build_category_sidebar()
        self.topics_list_container = self.build_topics_list()
        self.content_area_container = self.build_content_area()

        # Update the main row's controls
        self.main_row.controls = [
            self.category_sidebar,
            ft.VerticalDivider(width=1, color=COLORS['secondary']),
            self.topics_list_container,
            ft.VerticalDivider(width=1, color=COLORS['secondary']),
            self.content_area_container
        ]

        self.update()

    def select_topic(self, topic_id):
        """Handle topic selection"""
        self.selected_topic = topic_id

        # Rebuild content area and topics list (to show selected state)
        self.topics_list_container = self.build_topics_list()
        self.content_area_container = self.build_content_area()

        # Update the main row's controls
        self.main_row.controls = [
            self.category_sidebar,
            ft.VerticalDivider(width=1, color=COLORS['secondary']),
            self.topics_list_container,
            ft.VerticalDivider(width=1, color=COLORS['secondary']),
            self.content_area_container
        ]

        self.update()

    def on_search_changed(self, e):
        """Handle search input changes"""
        self.search_query = e.control.value

        # Clear category selection when searching
        if self.search_query:
            self.selected_category = None
            self.selected_topic = None

        # Rebuild UI components
        self.category_sidebar = self.build_category_sidebar()
        self.topics_list_container = self.build_topics_list()
        self.content_area_container = self.build_content_area()

        # Update the main row's controls
        self.main_row.controls = [
            self.category_sidebar,
            ft.VerticalDivider(width=1, color=COLORS['secondary']),
            self.topics_list_container,
            ft.VerticalDivider(width=1, color=COLORS['secondary']),
            self.content_area_container
        ]

        self.update()
