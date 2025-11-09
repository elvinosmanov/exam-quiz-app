"""
View Switcher for Expert Role

Experts can switch between two views:
1. Expert View (Creator mode) - Create/manage exams, questions, assignments
2. Examinee View (Participant mode) - Take exams assigned to them

This module provides UI components and utilities for view switching.
"""

import flet as ft
from quiz_app.config import COLORS


def create_view_switcher(current_view, user_role, on_switch_callback):
    """
    Create a view switcher component for expert users

    Shows only the button to switch to the OTHER mode (not current mode)

    Args:
        current_view (str): Current active view ('expert' or 'examinee')
        user_role (str): User's role (only shows for 'expert')
        on_switch_callback (callable): Function to call when view is switched
                                       Receives one arg: new_view ('expert' or 'examinee')

    Returns:
        ft.ElevatedButton or None: View switcher button, or None if not applicable

    Example:
        switcher = create_view_switcher(
            current_view='expert',
            user_role='expert',
            on_switch_callback=lambda view: switch_view(view)
        )
    """
    # Only show for expert role
    if user_role != 'expert':
        return None

    # Show button for the OTHER mode (not current)
    if current_view == 'expert':
        # Currently in expert mode, show button to switch to examinee
        return ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.icons.SCHOOL, size=18),
                ft.Text("Switch to Examinee Mode", size=14, weight=ft.FontWeight.BOLD)
            ], spacing=8, tight=True),
            on_click=lambda e: on_switch_callback('examinee'),
            style=ft.ButtonStyle(
                bgcolor=COLORS['success'],
                color=ft.colors.WHITE,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=8)
            )
        )
    else:
        # Currently in examinee mode, show button to switch to expert
        return ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.icons.WORKSPACE_PREMIUM, size=18),
                ft.Text("Switch to Expert Mode", size=14, weight=ft.FontWeight.BOLD)
            ], spacing=8, tight=True),
            on_click=lambda e: on_switch_callback('expert'),
            style=ft.ButtonStyle(
                bgcolor=COLORS['primary'],
                color=ft.colors.WHITE,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=8)
            )
        )


def create_view_mode_indicator(current_view, user_role):
    """
    Create a small indicator showing current view mode

    Useful for header/navigation to show which mode user is in

    Args:
        current_view (str): Current view ('expert' or 'examinee')
        user_role (str): User's role

    Returns:
        ft.Container or None: Mode indicator, or None if not applicable
    """
    if user_role != 'expert':
        return None

    is_expert_mode = (current_view == 'expert')

    return ft.Container(
        content=ft.Row([
            ft.Icon(
                ft.icons.WORKSPACE_PREMIUM if is_expert_mode else ft.icons.SCHOOL,
                size=16,
                color=ft.colors.WHITE
            ),
            ft.Text(
                "Expert Mode" if is_expert_mode else "Examinee Mode",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=ft.colors.WHITE
            )
        ], spacing=5),
        bgcolor=COLORS['primary'] if is_expert_mode else COLORS['success'],
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border_radius=20
    )


def can_switch_views(user_role):
    """
    Check if user can switch between views

    Args:
        user_role (str): User's role

    Returns:
        bool: True if user can switch views
    """
    return user_role == 'expert'


def get_available_views_for_user(user_role):
    """
    Get list of available views for a user

    Args:
        user_role (str): User's role

    Returns:
        list: List of dicts with 'id', 'name', 'icon' keys

    Example:
        [
            {'id': 'expert', 'name': 'Expert Mode', 'icon': ft.icons.WORKSPACE_PREMIUM},
            {'id': 'examinee', 'name': 'Examinee Mode', 'icon': ft.icons.SCHOOL}
        ]
    """
    if user_role == 'expert':
        return [
            {
                'id': 'expert',
                'name': 'Expert Mode',
                'icon': ft.icons.WORKSPACE_PREMIUM,
                'description': 'Create and manage exams, questions, and assignments'
            },
            {
                'id': 'examinee',
                'name': 'Examinee Mode',
                'icon': ft.icons.SCHOOL,
                'description': 'Take exams assigned to you'
            }
        ]
    elif user_role == 'admin':
        # Admin only has one view (could add examinee later if needed)
        return [
            {
                'id': 'admin',
                'name': 'Admin Mode',
                'icon': ft.icons.ADMIN_PANEL_SETTINGS,
                'description': 'Full system administration'
            }
        ]
    else:  # examinee
        return [
            {
                'id': 'examinee',
                'name': 'Examinee Mode',
                'icon': ft.icons.SCHOOL,
                'description': 'Take exams'
            }
        ]
