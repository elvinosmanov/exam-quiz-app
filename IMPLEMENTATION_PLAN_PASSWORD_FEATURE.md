# Implementation Plan: Auto-Password & Email Feature

## ✅ Completed So Far

1. ✅ Created `password_generator.py` utility
2. ✅ Added email configuration to `config.py`
3. ✅ Created database migration
4. ✅ Ran migration successfully - `password_change_required` column added

---

## 🚧 What I'm Implementing Now

### Phase 1: Update User Creation Dialog

**File**: `quiz_app/views/admin/user_management.py`

**Changes Needed**:

1. **Add imports**:
   ```python
   from quiz_app.utils.password_generator import generate_secure_password, send_password_email
   from quiz_app.config import (AUTO_GENERATE_PASSWORD, EMAIL_ENABLED, SMTP_SERVER,
                                  SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, APP_URL,
                                  GENERATED_PASSWORD_LENGTH)
   ```

2. **Add "Generate Password" button**:
   - Below password field
   - Clicking generates secure password and fills the field
   - Shows generated password in readable format

3. **Add "Copy Password" button**:
   - Next to password field
   - Copies password to clipboard
   - Shows "Copied!" tooltip

4. **Modify save_user function**:
   - When creating new user (not edit):
     - If password field is filled, use it
     - Set `password_change_required = 1`
   - Store generated password temporarily to send email

5. **After user created successfully**:
   - Show success dialog with:
     - Username
     - Generated password (with copy button)
     - "Send Email" button
     - "Close" button
   - If "Send Email" clicked:
     - Call `send_password_email()`
     - Show success/error message

---

### Phase 2: Force Password Change on First Login

**File**: `quiz_app/views/auth/login_view.py`

**Changes Needed**:

1. **After successful login**:
   - Check if `user_data['password_change_required'] == 1`
   - If yes, show password change dialog BEFORE going to dashboard
   - User CANNOT proceed without changing password

2. **Create password change dialog**:
   ```python
   def show_force_password_change_dialog(user_data):
       # Show dialog with:
       # - "You must change your password"
       # - New password field
       # - Confirm password field
       # - "Change Password" button
       # - Cannot close or skip
   ```

3. **Update password**:
   - Validate new password (minimum length, etc.)
   - Save new password hash
   - Set `password_change_required = 0`
   - Then proceed to dashboard

---

### Phase 3: Email Configuration UI (Optional - Later)

**File**: `quiz_app/views/admin/settings.py`

**Add email settings section**:
- SMTP server
- SMTP port
- Sender email
- Sender password (masked)
- Test email button
- Enable/disable email toggle

---

## 📝 Detailed Implementation

Let me implement each phase step by step. I'll start with Phase 1 now.

---

## ⏳ Status: Implementing Phase 1...
