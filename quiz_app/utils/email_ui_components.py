"""
Reusable Email UI Components
Email button and preview dialog for sending exam results
"""

import flet as ft
from quiz_app.config import COLORS
from quiz_app.utils.email_templates import EmailTemplateManager
from quiz_app.utils.email_handler import EmailHandler
from quiz_app.utils.permissions import UnitPermissionManager


def create_email_button(page, db, session_id: int, user_data: dict,
                       on_success=None, on_error=None, tooltip: str = "Email Results to Examinee"):
    """
    Create email button for exam session

    Args:
        page: Flet page instance
        db: Database instance
        session_id: Exam session ID
        user_data: Current user data (for permission checking)
        on_success: Callback function on successful email generation
        on_error: Callback function on error
        tooltip: Button tooltip text

    Returns:
        IconButton or None if user doesn't have permission
    """

    # Check if user has permission to send email for this session
    has_permission = can_send_email(db, session_id, user_data)
    print(f"[DEBUG] Email button for session {session_id}: permission={has_permission}, role={user_data.get('role')}")

    if not has_permission:
        print(f"[DEBUG] No permission to send email for session {session_id}")
        return None

    def show_email_preview(e):
        """Show email preview dialog"""
        dialog, update_callback = create_email_preview_dialog(
            page=page,
            db=db,
            session_id=session_id,
            user_data=user_data,
            on_success=on_success,
            on_error=on_error
        )

        page.dialog = dialog
        dialog.open = True
        page.update()

        # Update preview after dialog is shown
        update_callback()

    return ft.IconButton(
        icon=ft.icons.EMAIL_OUTLINED,
        icon_color=COLORS['primary'],
        tooltip=tooltip,
        on_click=show_email_preview
    )


def create_email_preview_dialog(page, db, session_id: int, user_data: dict,
                                on_success=None, on_error=None):
    """
    Create email preview dialog with language selector

    Args:
        page: Flet page instance
        db: Database instance
        session_id: Exam session ID
        user_data: Current user data
        on_success: Callback function on successful email generation
        on_error: Callback function on error

    Returns:
        AlertDialog with email preview
    """

    template_manager = EmailTemplateManager(db)
    email_handler = EmailHandler()

    # State variables
    selected_language = ft.Ref[ft.RadioGroup]()
    preview_container = ft.Ref[ft.Container]()
    email_data = {'recipient_email': None, 'subject': None, 'body': None, 'email_type': None}

    def update_preview(e=None):
        """Update email preview when language changes"""
        lang = selected_language.current.value if selected_language.current else 'en'

        # Generate email content
        recipient_email, subject, body = template_manager.generate_email(session_id, language=lang)

        if not recipient_email or not subject or not body:
            show_error("Failed to generate email. Please check if user has a valid email address.")
            return

        # Validate email
        if not email_handler.validate_email(recipient_email):
            show_error(f"Invalid email address: {recipient_email}")
            return

        # Determine email type for logging
        session_data = template_manager._get_session_data(session_id)
        email_type = template_manager._determine_email_type(session_data) if session_data else 'unknown'

        # Store for later use
        email_data['recipient_email'] = recipient_email
        email_data['subject'] = subject
        email_data['body'] = body
        email_data['email_type'] = email_type
        email_data['recipient_name'] = session_data.get('full_name', '') if session_data else ''

        # Update preview
        preview_container.current.content = ft.Column([
            # To field
            ft.Row([
                ft.Text("To:", weight=ft.FontWeight.BOLD, width=80),
                ft.Text(recipient_email, color=COLORS['text_secondary'])
            ]),

            ft.Divider(height=1),

            # Subject
            ft.Row([
                ft.Text("Subject:", weight=ft.FontWeight.BOLD, width=80),
                ft.Text(subject, color=COLORS['text_secondary'], expand=True)
            ]),

            ft.Divider(height=1),

            # Body
            ft.Container(
                content=ft.Column([
                    ft.Text("Message:", weight=ft.FontWeight.BOLD, size=12),
                    ft.Container(
                        content=ft.Text(
                            body,
                            color=COLORS['text_secondary'],
                            size=12,
                            selectable=True
                        ),
                        padding=10,
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                        border_radius=5
                    )
                ]),
                padding=ft.padding.only(top=10)
            )
        ], spacing=10, scroll=ft.ScrollMode.AUTO)

        preview_container.current.update()

    def show_error(message: str):
        """Show error in preview"""
        preview_container.current.content = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.ERROR_OUTLINE, color=COLORS['error']),
                ft.Text(message, color=COLORS['error'])
            ]),
            padding=20
        )
        preview_container.current.update()

    def open_in_email_client(e):
        """Open email draft in default email client"""
        if not email_data['recipient_email'] or not email_data['subject'] or not email_data['body']:
            show_snackbar(page, "Email data not ready", is_error=True)
            return

        # Open email client
        success = email_handler.open_email_draft(
            to_email=email_data['recipient_email'],
            subject=email_data['subject'],
            body=email_data['body']
        )

        if success:
            # Log email generation
            lang = selected_language.current.value if selected_language.current else 'en'
            email_handler.log_email_generation(
                db=db,
                session_id=session_id,
                recipient_email=email_data['recipient_email'],
                recipient_name=email_data['recipient_name'],
                sent_by_user_id=user_data['id'],
                email_type=email_data['email_type'],
                language=lang
            )

            # Close dialog
            page.dialog.open = False
            page.update()

            # Show success message
            show_snackbar(page, f"Email draft opened for {email_data['recipient_email']}")

            # Call success callback
            if on_success and callable(on_success):
                on_success()
        else:
            show_snackbar(page, "Failed to open email client", is_error=True)

            # Call error callback
            if on_error and callable(on_error):
                on_error()

    def close_dialog(e):
        """Close the dialog"""
        page.dialog.open = False
        page.update()

    # Language selector
    language_selector = ft.RadioGroup(
        ref=selected_language,
        value='en',
        on_change=update_preview,
        content=ft.Row([
            ft.Radio(value='en', label='English'),
            ft.Radio(value='az', label='Azərbaycan')
        ])
    )

    # Preview container
    preview = ft.Container(
        ref=preview_container,
        content=ft.ProgressRing(),  # Loading indicator
        padding=20,
        height=400,
        border=ft.border.all(1, ft.colors.OUTLINE),
        border_radius=10
    )

    # Dialog
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.icons.EMAIL, color=COLORS['primary']),
            ft.Text("Email Preview", weight=ft.FontWeight.BOLD)
        ]),
        content=ft.Container(
            content=ft.Column([
                # Language selector
                ft.Row([
                    ft.Text("Select Language:", weight=ft.FontWeight.BOLD),
                    language_selector
                ], spacing=20),

                ft.Divider(),

                # Preview
                preview
            ], spacing=10, tight=True),
            width=600
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.ElevatedButton(
                "Open in Outlook",
                icon=ft.icons.MAIL_OUTLINE,
                on_click=open_in_email_client,
                style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )

    # Don't call update_preview here - will be called after dialog is shown
    # Return both dialog and update function
    return dialog, update_preview


def can_send_email(db, session_id: int, user_data: dict) -> bool:
    """
    Check if user has permission to send email for this session

    Args:
        db: Database instance
        session_id: Exam session ID
        user_data: Current user data

    Returns:
        True if user can send email, False otherwise
    """
    try:
        user_role = user_data.get('role', 'unknown')
        print(f"[DEBUG can_send_email] Checking permission for session {session_id}, user role: {user_role}")

        # Admin and HR have full access
        if user_role in ['admin', 'hr']:
            print(f"[DEBUG can_send_email] User is {user_role} - GRANTED")
            return True

        # Expert role: Check unit permissions
        if user_role == 'expert':
            # Get session's assignment unit
            session_query = """
                SELECT ea.unit
                FROM exam_sessions es
                LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
                WHERE es.id = ?
            """
            session_result = db.execute_single(session_query, (session_id,))

            print(f"[DEBUG can_send_email] Expert checking unit access. Session unit: {session_result.get('unit') if session_result else 'None'}")

            if session_result and session_result.get('unit'):
                # Check if expert has access to this unit
                perm_manager = UnitPermissionManager(db)
                user_units = perm_manager.get_user_units(user_data['id'])
                has_access = session_result['unit'] in user_units
                print(f"[DEBUG can_send_email] Expert has access: {has_access}")
                return has_access

        print(f"[DEBUG can_send_email] Permission DENIED for role: {user_role}")
        return False

    except Exception as e:
        print(f"[EmailUIComponents] Error checking permission: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_snackbar(page, message: str, is_error: bool = False):
    """
    Show snackbar notification

    Args:
        page: Flet page instance
        message: Message to display
        is_error: If True, show as error (red), otherwise success (green)
    """
    page.snack_bar = ft.SnackBar(
        content=ft.Text(message, color=ft.colors.WHITE),
        bgcolor=COLORS['error'] if is_error else COLORS['success']
    )
    page.snack_bar.open = True
    page.update()


def create_bulk_email_button(page, db, session_ids: list, user_data: dict,
                             button_text: str = "Email Selected"):
    """
    Create button for bulk email generation

    Args:
        page: Flet page instance
        db: Database instance
        session_ids: List of session IDs
        user_data: Current user data
        button_text: Button text

    Returns:
        ElevatedButton for bulk email
    """

    def generate_bulk_emails(e):
        """Generate multiple email drafts"""
        if not session_ids:
            show_snackbar(page, "No sessions selected", is_error=True)
            return

        template_manager = EmailTemplateManager(db)
        email_handler = EmailHandler()

        success_count = 0
        error_count = 0

        # Filter sessions user has permission for
        allowed_sessions = [sid for sid in session_ids if can_send_email(db, sid, user_data)]

        if not allowed_sessions:
            show_snackbar(page, "You don't have permission to email these results", is_error=True)
            return

        # Generate emails for each session
        for session_id in allowed_sessions:
            recipient_email, subject, body = template_manager.generate_email(session_id)

            if recipient_email and subject and body:
                # Open email draft
                success = email_handler.open_email_draft(recipient_email, subject, body)

                if success:
                    # Log email generation
                    session_data = template_manager._get_session_data(session_id)
                    email_type = template_manager._determine_email_type(session_data) if session_data else 'unknown'

                    email_handler.log_email_generation(
                        db=db,
                        session_id=session_id,
                        recipient_email=recipient_email,
                        recipient_name=session_data.get('full_name', '') if session_data else '',
                        sent_by_user_id=user_data['id'],
                        email_type=email_type,
                        language='en'  # Default for bulk
                    )
                    success_count += 1
                else:
                    error_count += 1
            else:
                error_count += 1

        # Show result
        if success_count > 0:
            show_snackbar(page, f"Opened {success_count} email draft(s)")
        if error_count > 0:
            show_snackbar(page, f"Failed to generate {error_count} email(s)", is_error=True)

    return ft.ElevatedButton(
        f"{button_text} ({len(session_ids)})",
        icon=ft.icons.EMAIL,
        on_click=generate_bulk_emails,
        disabled=len(session_ids) == 0,
        style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
    )
