"""
Password Email Utility
Generates mailto: links to open Outlook with new user credentials
"""

import urllib.parse
import webbrowser

def create_new_user_email_body(username: str, password: str, full_name: str) -> str:
    """
    Create email body for new user credentials

    Args:
        username: User's username
        password: Generated password
        full_name: User's full name

    Returns:
        str: Email body text
    """
    body = f"""Dear {full_name},

Your account has been created successfully in the Quiz Examination System.

Login Credentials:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Username: {username}
Temporary Password: {password}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ IMPORTANT SECURITY NOTICE:
• This is a TEMPORARY password
• You MUST change your password immediately upon your first login
• Do not share your credentials with anyone
• Keep your password secure

How to Login:
1. Open the Quiz Examination System
2. Enter your username and temporary password
3. You will be automatically prompted to change your password
4. Create a strong, unique password

If you did not request this account or have any questions, please contact your system administrator immediately.

Best regards,
Quiz Examination System
"""
    return body


def open_email_draft(recipient_email: str, username: str, password: str, full_name: str) -> bool:
    """
    Open email client with pre-filled credentials email

    Args:
        recipient_email: User's email address
        username: User's username
        password: Generated password
        full_name: User's full name

    Returns:
        bool: True if email client opened successfully
    """
    try:
        subject = "Your New Account Credentials - Quiz Examination System"
        body = create_new_user_email_body(username, password, full_name)

        # Create mailto URL
        mailto_url = f"mailto:{recipient_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"

        # Open in default email client
        webbrowser.open(mailto_url)
        return True

    except Exception as e:
        print(f"[ERROR] Failed to open email client: {e}")
        return False
