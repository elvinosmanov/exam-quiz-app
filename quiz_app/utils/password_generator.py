"""
Password Generation and Email Utilities
Generates secure passwords and sends them to users via email
"""

import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple

def generate_secure_password(length: int = 12) -> str:
    """
    Generate a secure random password

    Args:
        length: Password length (default: 12)

    Returns:
        str: Random password with uppercase, lowercase, digits, and special characters

    Password Rules:
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 2 digits
        - At least 1 special character
        - Total length: 12 characters (default)
    """
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special_chars = "!@#$%&*"

    # Ensure password has required characters
    password_chars = [
        random.choice(uppercase),      # At least 1 uppercase
        random.choice(uppercase),      # Another uppercase
        random.choice(lowercase),      # At least 1 lowercase
        random.choice(lowercase),      # Another lowercase
        random.choice(digits),         # At least 1 digit
        random.choice(digits),         # Another digit
        random.choice(special_chars),  # At least 1 special char
    ]

    # Fill the rest with random characters from all sets
    all_chars = uppercase + lowercase + digits + special_chars
    remaining_length = length - len(password_chars)
    password_chars.extend(random.choice(all_chars) for _ in range(remaining_length))

    # Shuffle to avoid predictable patterns
    random.shuffle(password_chars)

    return ''.join(password_chars)


def send_password_email(
    recipient_email: str,
    recipient_name: str,
    username: str,
    password: str,
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    app_url: str = "http://localhost"
) -> Tuple[bool, Optional[str]]:
    """
    Send password to user via email

    Args:
        recipient_email: User's email address
        recipient_name: User's full name
        username: User's username for login
        password: Generated password
        smtp_server: SMTP server address (e.g., 'smtp.gmail.com')
        smtp_port: SMTP port (e.g., 587 for TLS)
        sender_email: Email address to send from
        sender_password: Password for sender email
        app_url: URL of the application

    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
            - (True, None) if email sent successfully
            - (False, error_message) if failed
    """
    try:
        # Create email message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Your New Account Credentials - Quiz Examination System"
        message["From"] = sender_email
        message["To"] = recipient_email

        # Create HTML email body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        Welcome to Quiz Examination System
                    </h2>

                    <p>Dear <strong>{recipient_name}</strong>,</p>

                    <p>Your account has been created successfully. Below are your login credentials:</p>

                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>Username:</strong> {username}</p>
                        <p style="margin: 5px 0;"><strong>Temporary Password:</strong> <code style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px;">{password}</code></p>
                        <p style="margin: 5px 0;"><strong>Login URL:</strong> <a href="{app_url}">{app_url}</a></p>
                    </div>

                    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>⚠️ Important Security Notice:</strong></p>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>This is a temporary password</li>
                            <li>You <strong>must change your password</strong> after your first login</li>
                            <li>Do not share your credentials with anyone</li>
                            <li>Keep your password secure</li>
                        </ul>
                    </div>

                    <h3 style="color: #2c3e50; margin-top: 30px;">How to Login:</h3>
                    <ol>
                        <li>Open the Quiz Examination System</li>
                        <li>Enter your username and temporary password</li>
                        <li>You will be prompted to change your password</li>
                        <li>Create a strong, unique password</li>
                    </ol>

                    <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
                        If you did not request this account or have any questions, please contact your system administrator immediately.
                    </p>

                    <p style="color: #666; font-size: 14px;">
                        Best regards,<br>
                        <strong>Quiz Examination System</strong>
                    </p>
                </div>
            </body>
        </html>
        """

        # Create plain text version (fallback)
        text_body = f"""
        Welcome to Quiz Examination System

        Dear {recipient_name},

        Your account has been created successfully. Below are your login credentials:

        Username: {username}
        Temporary Password: {password}
        Login URL: {app_url}

        IMPORTANT SECURITY NOTICE:
        - This is a temporary password
        - You MUST change your password after your first login
        - Do not share your credentials with anyone
        - Keep your password secure

        How to Login:
        1. Open the Quiz Examination System
        2. Enter your username and temporary password
        3. You will be prompted to change your password
        4. Create a strong, unique password

        If you did not request this account or have any questions, please contact your system administrator immediately.

        Best regards,
        Quiz Examination System
        """

        # Attach both versions
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        message.attach(part1)
        message.attach(part2)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Enable TLS encryption
            server.login(sender_email, sender_password)
            server.send_message(message)

        return True, None

    except smtplib.SMTPAuthenticationError:
        return False, "Email authentication failed. Please check sender email credentials."
    except smtplib.SMTPException as e:
        return False, f"Failed to send email: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error sending email: {str(e)}"


# Example usage and testing
if __name__ == "__main__":
    # Test password generation
    print("Testing password generation:")
    for i in range(5):
        password = generate_secure_password()
        print(f"  Password {i+1}: {password}")

    print("\nPassword meets requirements:")
    test_pwd = generate_secure_password()
    print(f"  Length: {len(test_pwd)}")
    print(f"  Has uppercase: {any(c.isupper() for c in test_pwd)}")
    print(f"  Has lowercase: {any(c.islower() for c in test_pwd)}")
    print(f"  Has digits: {any(c.isdigit() for c in test_pwd)}")
    print(f"  Has special chars: {any(c in '!@#$%&*' for c in test_pwd)}")
