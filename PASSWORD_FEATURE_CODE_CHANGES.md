# Exact Code Changes for Password Feature

This document shows the EXACT changes I'll make to implement the auto-password feature.

---

## File 1: user_management.py - Add Imports (Top of file)

**Add these imports**:
```python
from quiz_app.utils.password_generator import generate_secure_password, send_password_email
from quiz_app.config import (
    AUTO_GENERATE_PASSWORD, EMAIL_ENABLED, SMTP_SERVER, SMTP_PORT,
    SENDER_EMAIL, SENDER_PASSWORD, APP_URL, GENERATED_PASSWORD_LENGTH
)
import pyperclip  # For copy to clipboard (need to add to requirements.txt)
```

---

## File 2: user_management.py - Modify show_user_dialog()

**Find this section** (around line 307-311):
```python
password_field = ft.TextField(
    label=t('password') if not is_edit else t('new_password'),
    password=True,
    can_reveal_password=True
)
```

**Replace with**:
```python
# Password field with auto-generate option
password_field = ft.TextField(
    label=t('password') if not is_edit else t('new_password'),
    password=True,
    can_reveal_password=True,
    hint_text="Leave empty to auto-generate" if not is_edit else None
)

# Generate password button (only for new users)
def generate_password_clicked(e):
    new_password = generate_secure_password(GENERATED_PASSWORD_LENGTH)
    password_field.value = new_password
    password_field.update()
    # Show success snackbar
    if self.page:
        self.page.show_snack_bar(ft.SnackBar(
            content=ft.Text("Password generated! You can edit it if needed."),
            bgcolor=ft.colors.GREEN
        ))

generate_btn = None
if not is_edit:
    generate_btn = ft.ElevatedButton(
        "Generate Secure Password",
        icon=ft.icons.KEY,
        on_click=generate_password_clicked
    )
```

**Then, find where the dialog content is built** and add the generate button after password_field.

---

## File 3: user_management.py - Modify save_user function

**Find the section where new user is created** (around line 678-693):
```python
else:
    # Create new user
    user_id = self.auth_manager.create_user(
        username_field.value.strip(),
        email_field.value.strip(),
        password_field.value,  # ← We'll modify this
        full_name_field.value.strip(),
        role_dropdown.value,
        dept_value or None,
        section_value or None,
        unit_value or None
    )
```

**Replace with**:
```python
else:
    # Create new user
    # Auto-generate password if empty
    generated_password = None
    if not password_field.value or password_field.value.strip() == "":
        generated_password = generate_secure_password(GENERATED_PASSWORD_LENGTH)
        user_password = generated_password
    else:
        user_password = password_field.value

    user_id = self.auth_manager.create_user(
        username_field.value.strip(),
        email_field.value.strip(),
        user_password,
        full_name_field.value.strip(),
        role_dropdown.value,
        dept_value or None,
        section_value or None,
        unit_value or None
    )

    if not user_id:
        error_text.value = t('user_already_exists')
        error_text.visible = True
        self.user_dialog.update()
        return

    # Set password_change_required flag
    self.db.execute_update(
        "UPDATE users SET password_change_required = 1 WHERE id = ?",
        (user_id,)
    )

    # Show success dialog with password
    if generated_password:
        self.show_password_success_dialog(
            username_field.value.strip(),
            generated_password,
            email_field.value.strip(),
            full_name_field.value.strip()
        )
```

---

## File 4: user_management.py - Add New Method

**Add this NEW method to UserManagement class**:

```python
def show_password_success_dialog(self, username, password, email, full_name):
    """
    Show dialog with generated password and option to send email
    """
    # Password display (copyable)
    password_display = ft.TextField(
        value=password,
        read_only=True,
        can_reveal_password=True,
        password=False,
        border_color=ft.colors.GREEN,
        width=300
    )

    def copy_password(e):
        try:
            # Copy to clipboard
            import pyperclip
            pyperclip.copy(password)
            copy_btn.text = "Copied!"
            copy_btn.icon = ft.icons.CHECK
            copy_btn.update()
            # Reset after 2 seconds
            import time
            time.sleep(2)
            copy_btn.text = "Copy"
            copy_btn.icon = ft.icons.COPY
            copy_btn.update()
        except:
            self.page.show_snack_bar(ft.SnackBar(
                content=ft.Text("Failed to copy to clipboard"),
                bgcolor=ft.colors.RED
            ))

    copy_btn = ft.IconButton(
        icon=ft.icons.COPY,
        tooltip="Copy password",
        on_click=copy_password
    )

    def send_email_clicked(e):
        send_email_btn.disabled = True
        send_email_btn.text = "Sending..."
        send_email_btn.update()

        success, error_msg = send_password_email(
            recipient_email=email,
            recipient_name=full_name,
            username=username,
            password=password,
            smtp_server=SMTP_SERVER,
            smtp_port=SMTP_PORT,
            sender_email=SENDER_EMAIL,
            sender_password=SENDER_PASSWORD,
            app_url=APP_URL
        )

        if success:
            self.page.show_snack_bar(ft.SnackBar(
                content=ft.Text(f"Email sent successfully to {email}"),
                bgcolor=ft.colors.GREEN
            ))
            send_email_btn.text = "Email Sent ✓"
        else:
            self.page.show_snack_bar(ft.SnackBar(
                content=ft.Text(f"Failed to send email: {error_msg}"),
                bgcolor=ft.colors.RED
            ))
            send_email_btn.text = "Send Email"
            send_email_btn.disabled = False

        send_email_btn.update()

    send_email_btn = ft.ElevatedButton(
        "Send Password Email",
        icon=ft.icons.EMAIL,
        on_click=send_email_clicked
    ) if EMAIL_ENABLED else None

    def close_dialog(e):
        success_dialog.open = False
        self.user_dialog.open = False
        if self.page:
            self.page.update()
        self.load_users()
        self.update()

    success_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("User Created Successfully!"),
        content=ft.Container(
            content=ft.Column([
                ft.Text("User account has been created. Please share these credentials:", size=14),
                ft.Divider(),
                ft.Text(f"Username: {username}", weight=ft.FontWeight.BOLD),
                ft.Row([
                    password_display,
                    copy_btn
                ]),
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.WARNING, color=ft.colors.ORANGE, size=20),
                        ft.Text(
                            "⚠️ User must change password on first login",
                            size=12,
                            color=ft.colors.ORANGE
                        )
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=ft.colors.ORANGE_50,
                    padding=10,
                    border_radius=8,
                    margin=ft.margin.only(top=10, bottom=10)
                ),
            ], tight=True, spacing=10),
            width=400
        ),
        actions=[
            send_email_btn if send_email_btn else None,
            ft.TextButton("Close", on_click=close_dialog)
        ]
    )

    self.page.dialog = success_dialog
    success_dialog.open = True
    self.page.update()
```

---

## File 5: requirements.txt - Add New Dependency

**Add this line**:
```
pyperclip==1.8.2
```

---

## Summary of Changes

1. ✅ Added imports for password generation and email
2. ✅ Modified password field to allow auto-generation
3. ✅ Added "Generate Password" button
4. ✅ Modified save function to auto-generate if empty
5. ✅ Set `password_change_required = 1` for new users
6. ✅ Created success dialog showing password with copy button
7. ✅ Added "Send Email" button (if enabled)
8. ✅ Added pyperclip dependency

---

## What's NOT Included (Will Do Next)

- Force password change on first login (login_view.py changes)
- Email configuration UI in Settings

---

## Do You Want Me To Apply These Changes?

**Option 1**: Yes, apply all changes now ✅
**Option 2**: Let me review first, I might want modifications
**Option 3**: Apply Phase 1 only (user creation), test, then do Phase 2

What would you like me to do?
