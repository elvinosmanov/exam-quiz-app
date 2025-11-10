"""
Email Handler
Handles opening email drafts in default email client
Supports mailto: protocol and .eml file generation
"""

import webbrowser
import urllib.parse
import platform
import os
import tempfile
import subprocess
from typing import Optional
from datetime import datetime


class EmailHandler:
    """Handles email draft generation and opening in email client"""

    # Maximum length for mailto: URLs (some email clients have limits)
    MAILTO_MAX_LENGTH = 2000

    @staticmethod
    def open_email_draft(to_email: str, subject: str, body: str, cc: Optional[str] = None,
                        bcc: Optional[str] = None) -> bool:
        """
        Open email draft in default email client

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            cc: CC email address (optional)
            bcc: BCC email address (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate email address
            if not to_email or '@' not in to_email:
                print(f"[EmailHandler] Invalid email address: {to_email}")
                return False

            # Try mailto: first (works on all platforms)
            mailto_success = EmailHandler._try_mailto(to_email, subject, body, cc, bcc)

            if mailto_success:
                return True

            # Fallback to .eml file for long emails or if mailto fails
            print("[EmailHandler] mailto: failed or too long, trying .eml file...")
            return EmailHandler._try_eml_file(to_email, subject, body, cc, bcc)

        except Exception as e:
            print(f"[EmailHandler] Error opening email draft: {e}")
            return False

    @staticmethod
    def _try_mailto(to_email: str, subject: str, body: str, cc: Optional[str] = None,
                   bcc: Optional[str] = None) -> bool:
        """
        Try to open email using mailto: protocol

        Returns:
            True if successful, False if URL too long or error
        """
        try:
            # Build mailto URL with URL encoding
            mailto_parts = [f"mailto:{urllib.parse.quote(to_email)}?"]

            params = []
            if subject:
                params.append(f"subject={urllib.parse.quote(subject)}")
            if body:
                params.append(f"body={urllib.parse.quote(body)}")
            if cc:
                params.append(f"cc={urllib.parse.quote(cc)}")
            if bcc:
                params.append(f"bcc={urllib.parse.quote(bcc)}")

            mailto_url = mailto_parts[0] + "&".join(params)

            # Check if URL is too long
            if len(mailto_url) > EmailHandler.MAILTO_MAX_LENGTH:
                print(f"[EmailHandler] mailto: URL too long ({len(mailto_url)} chars), falling back to .eml")
                return False

            # Open in default email client
            webbrowser.open(mailto_url)
            print(f"[EmailHandler] Opened mailto: link for {to_email}")
            return True

        except Exception as e:
            print(f"[EmailHandler] mailto: error: {e}")
            return False

    @staticmethod
    def _try_eml_file(to_email: str, subject: str, body: str, cc: Optional[str] = None,
                     bcc: Optional[str] = None) -> bool:
        """
        Create .eml file and open it (better for Outlook on Windows)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create .eml file content (RFC 822 format)
            eml_content = EmailHandler._create_eml_content(to_email, subject, body, cc, bcc)

            # Create temporary .eml file
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            eml_filename = f"exam_result_{timestamp}.eml"
            eml_path = os.path.join(temp_dir, eml_filename)

            # Write .eml file
            with open(eml_path, 'w', encoding='utf-8') as f:
                f.write(eml_content)

            # Open .eml file with default application
            EmailHandler._open_file(eml_path)

            print(f"[EmailHandler] Created and opened .eml file: {eml_path}")
            return True

        except Exception as e:
            print(f"[EmailHandler] .eml file error: {e}")
            return False

    @staticmethod
    def _create_eml_content(to_email: str, subject: str, body: str, cc: Optional[str] = None,
                           bcc: Optional[str] = None) -> str:
        """
        Create RFC 822 format email content for .eml file

        Returns:
            Email content as string
        """
        lines = []

        # Headers
        lines.append(f"To: {to_email}")
        if cc:
            lines.append(f"Cc: {cc}")
        if bcc:
            lines.append(f"Bcc: {bcc}")
        lines.append(f"Subject: {subject}")
        lines.append("Content-Type: text/plain; charset=UTF-8")
        lines.append("")  # Blank line separates headers from body

        # Body
        lines.append(body)

        return "\r\n".join(lines)

    @staticmethod
    def _open_file(filepath: str):
        """
        Open file with default application (platform-specific)

        Args:
            filepath: Path to file to open
        """
        system = platform.system()

        if system == 'Windows':
            os.startfile(filepath)
        elif system == 'Darwin':  # macOS
            subprocess.call(['open', filepath])
        else:  # Linux
            subprocess.call(['xdg-open', filepath])

    @staticmethod
    def log_email_generation(db, session_id: int, recipient_email: str, recipient_name: str,
                            sent_by_user_id: int, email_type: str, language: str) -> bool:
        """
        Log email generation in database

        Args:
            db: Database instance
            session_id: Exam session ID
            recipient_email: Email address of recipient
            recipient_name: Full name of recipient
            sent_by_user_id: User ID of HR/Expert who generated email
            email_type: Type of email ('passed', 'failed', 'pending')
            language: Language used ('en', 'az')

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            db.execute_insert(
                """INSERT INTO email_log
                   (session_id, recipient_email, recipient_name, sent_by, email_type, language)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, recipient_email, recipient_name, sent_by_user_id, email_type, language)
            )
            print(f"[EmailHandler] Logged email generation for session {session_id}")
            return True

        except Exception as e:
            print(f"[EmailHandler] Error logging email: {e}")
            return False

    @staticmethod
    def get_email_history(db, session_id: int) -> list:
        """
        Get email history for a specific exam session

        Args:
            db: Database instance
            session_id: Exam session ID

        Returns:
            List of email log dictionaries
        """
        try:
            return db.execute_query(
                """SELECT el.*, u.full_name as sent_by_name
                   FROM email_log el
                   JOIN users u ON el.sent_by = u.id
                   WHERE el.session_id = ?
                   ORDER BY el.sent_at DESC""",
                (session_id,)
            )
        except Exception as e:
            print(f"[EmailHandler] Error fetching email history: {e}")
            return []

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Basic email validation

        Args:
            email: Email address to validate

        Returns:
            True if valid format, False otherwise
        """
        if not email or '@' not in email:
            return False

        # Basic validation: has @ and at least one . after @
        parts = email.split('@')
        if len(parts) != 2:
            return False

        local, domain = parts
        if not local or not domain:
            return False

        if '.' not in domain:
            return False

        return True

    @staticmethod
    def get_platform_info() -> dict:
        """
        Get platform information for debugging

        Returns:
            Dictionary with platform details
        """
        return {
            'system': platform.system(),
            'platform': platform.platform(),
            'python_version': platform.python_version()
        }
