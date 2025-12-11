# Security Fixes - Testing Guide

This document explains how to test all the critical security fixes that were implemented.

## ✅ Fixes Implemented

### 1. **Dashboard Statistics Filtering for Experts** ✅
- **File**: `quiz_app/views/admin/admin_dashboard.py`
- **Lines**: 218-313
- **What was fixed**: Experts now see only their department/unit statistics instead of system-wide data

### 2. **Recent Activity Filtering for Experts** ✅
- **File**: `quiz_app/views/admin/admin_dashboard.py`
- **Lines**: 315-405
- **What was fixed**: Recent activity now filtered by department/unit for experts

### 3. **Role Validation at Login** ✅
- **File**: `main.py`
- **Lines**: 147-165
- **What was fixed**: System now validates that role is 'admin', 'expert', or 'examinee' at login

### 4. **Server-Side Role Validation in User Management** ✅
- **File**: `quiz_app/views/admin/user_management.py`
- **Lines**: 634-640
- **What was fixed**: Role value is validated server-side before saving to database

### 5. **Role Constants Created** ✅
- **File**: `quiz_app/config.py`
- **Lines**: 40-44
- **What was added**: `ROLE_ADMIN`, `ROLE_EXPERT`, `ROLE_EXAMINEE`, `VALID_ROLES`

### 6. **Database CHECK Constraint** ✅
- **File**: `quiz_app/database/migration_role_validation.py`
- **What was added**: Database migration to add CHECK constraint for roles

---

## 🧪 How to Test Each Fix

### **Test #1: Dashboard Statistics Filtering**

**Objective**: Verify that expert users only see statistics for their department/unit, not the entire system.

**Prerequisites**:
- You need at least 2 departments in your system (e.g., "IT Department" and "HR Department")
- Create users in different departments
- Create exams and sessions from different departments

**Steps**:

1. **Login as Admin**:
   ```
   Username: admin
   Password: admin123
   ```
   - Look at dashboard statistics
   - Note down: Total Users, Total Exams, Active Sessions, Completed Exams
   - These should show ALL system data

2. **Create an Expert User** (if you don't have one):
   - Go to User Management
   - Click "Add User"
   - Create user with:
     - Role: Expert
     - Department: IT Department (or your test department)
     - Unit: Software Development (or your test unit)
   - Save and note the username/password

3. **Login as Expert**:
   - Logout from admin
   - Login with the expert credentials
   - Look at dashboard statistics

4. **Verify**:
   - [ ] Total Users shows only users in IT Department + Software Development unit
   - [ ] Total Exams shows only exams created by users in that unit
   - [ ] Active Sessions shows only sessions from users in that unit
   - [ ] Completed Exams shows only completions from users in that unit
   - [ ] Numbers should be SMALLER than what admin sees

**Expected Result**: Expert sees ONLY their unit's data, NOT system-wide data.

---

### **Test #2: Recent Activity Filtering**

**Objective**: Verify that experts only see activity from their department/unit.

**Steps**:

1. **As Admin**:
   - Complete some exams as different users from different departments
   - Note the activity in "Recent Activity" section

2. **As Expert (IT Department, Software Unit)**:
   - Login as expert
   - Check "Recent Activity" section

3. **Verify**:
   - [ ] Only shows exam completions from users in IT Department + Software Unit
   - [ ] Does NOT show activity from other departments (like HR)
   - [ ] Pending grading only shows items from their unit

**Expected Result**: Expert sees only activity from their own unit.

---

### **Test #3: Role Validation at Login**

**Objective**: Verify system rejects users with invalid roles.

**Steps**:

1. **Manually corrupt a user's role in database**:
   ```bash
   # Open database
   sqlite3 quiz_app.db

   # Check current roles
   SELECT id, username, role FROM users;

   # Change a test user's role to invalid value
   UPDATE users SET role = 'hacker' WHERE username = 'testuser';

   # Verify change
   SELECT id, username, role FROM users WHERE username = 'testuser';

   # Exit
   .quit
   ```

2. **Try to login with that user**:
   - Username: testuser
   - Password: testpass123

3. **Verify**:
   - [ ] System shows error: "Invalid user role. Please contact administrator."
   - [ ] User is automatically logged out
   - [ ] Cannot access any dashboard

4. **Fix the database**:
   ```bash
   sqlite3 quiz_app.db
   UPDATE users SET role = 'examinee' WHERE username = 'testuser';
   .quit
   ```

**Expected Result**: System rejects invalid roles and shows error message.

---

### **Test #4: Server-Side Role Validation**

**Objective**: Verify that role field is validated when creating/editing users.

**Steps**:

1. **Login as Admin**

2. **Try to create user with manual role manipulation** (requires developer tools):
   - Open User Management
   - Click "Add User"
   - Fill in user details
   - BEFORE clicking Save, open browser DevTools (F12)
   - In Console, type:
     ```javascript
     // This simulates an attacker trying to inject invalid role
     // Note: Since this is a desktop app, direct manipulation is harder
     // but the validation still protects against any programmatic attacks
     ```

3. **Alternative test - Check validation code**:
   - Open `quiz_app/views/admin/user_management.py`
   - Find line 634-640
   - Verify this code exists:
     ```python
     # Server-side role validation (SECURITY FIX)
     valid_roles = ['admin', 'expert', 'examinee']
     if role_dropdown.value not in valid_roles:
         error_text.value = f"Invalid role: {role_dropdown.value}. Must be admin, expert, or examinee."
         error_text.visible = True
         self.user_dialog.update()
         return
     ```

**Expected Result**: Role validation code exists and prevents invalid role values.

---

### **Test #5: Role Constants Usage**

**Objective**: Verify role constants are properly defined and used.

**Steps**:

1. **Check config file**:
   ```bash
   cat quiz_app/config.py | grep -A 5 "User role constants"
   ```

2. **Verify output shows**:
   ```python
   # User role constants (SECURITY FIX)
   ROLE_ADMIN = 'admin'
   ROLE_EXPERT = 'expert'
   ROLE_EXAMINEE = 'examinee'
   VALID_ROLES = [ROLE_ADMIN, ROLE_EXPERT, ROLE_EXAMINEE]
   ```

3. **Check main.py uses constants**:
   ```bash
   grep "ROLE_ADMIN\|ROLE_EXPERT" main.py
   ```

**Expected Result**: Constants are defined and used in main.py.

---

### **Test #6: Database CHECK Constraint**

**Objective**: Verify database prevents invalid roles.

**Steps**:

1. **Run the migration**:
   ```bash
   python3 quiz_app/database/migration_role_validation.py
   ```

2. **Verify output**:
   ```
   [MIGRATION] Starting role validation migration...
   [MIGRATION] Creating new users table with role validation...
   [MIGRATION] Copying data to new table...
   [MIGRATION] Dropping old users table...
   [MIGRATION] Renaming new table...
   [MIGRATION] Role validation migration completed successfully!
   ```

3. **Test constraint works**:
   ```bash
   sqlite3 quiz_app.db

   # Try to insert user with invalid role
   INSERT INTO users (username, email, password_hash, full_name, role)
   VALUES ('baduser', 'bad@test.com', 'hash', 'Bad User', 'hacker');

   # Should see error: CHECK constraint failed: role IN ('admin', 'expert', 'examinee')
   ```

**Expected Result**: Database rejects invalid role values with CHECK constraint error.

---

## 📊 Testing Checklist

Use this checklist to track your testing progress:

- [ ] Test #1: Dashboard Statistics Filtering - Expert sees only their unit
- [ ] Test #2: Recent Activity Filtering - Expert sees only their unit's activity
- [ ] Test #3: Role Validation at Login - Invalid roles are rejected
- [ ] Test #4: Server-Side Role Validation - Code validates role on save
- [ ] Test #5: Role Constants - Constants are defined and used
- [ ] Test #6: Database CHECK Constraint - Database enforces valid roles

---

## 🔍 Quick Verification Commands

Run these commands to quickly verify the fixes are in place:

```bash
# 1. Check dashboard filtering code exists
grep -n "perm_manager = UnitPermissionManager" quiz_app/views/admin/admin_dashboard.py

# 2. Check role validation exists
grep -n "VALID_ROLES" main.py

# 3. Check server-side validation exists
grep -n "Server-side role validation" quiz_app/views/admin/user_management.py

# 4. Check role constants exist
grep -n "ROLE_ADMIN\|ROLE_EXPERT\|ROLE_EXAMINEE" quiz_app/config.py

# 5. Check database schema has CHECK constraint
sqlite3 quiz_app.db "SELECT sql FROM sqlite_master WHERE name='users';"
```

---

## 🚀 What to Look For

### **BEFORE the fixes** (if you revert changes):
- Expert users can see ALL users, exams, sessions from entire system
- Expert users see activity from other departments
- No validation when user has invalid role
- Roles are hardcoded as strings everywhere

### **AFTER the fixes** (current state):
- Expert users see ONLY their department/unit data
- Expert users see ONLY their department/unit activity
- Invalid roles are caught and rejected at login
- Server validates roles before saving
- Role constants used consistently
- Database enforces valid roles with CHECK constraint

---

## ⚠️ Important Notes

1. **Testing with Real Data**: Create test users in different departments to properly test filtering
2. **Department/Unit Structure**: Make sure your expert users have department AND unit assigned
3. **Migration**: Run the database migration BEFORE testing constraint
4. **Backup**: Always backup your database before running migrations

---

## 📝 Reporting Issues

If you find any issues during testing:

1. Note which test failed
2. Capture what you expected vs. what you saw
3. Check the console output for any error messages
4. Verify the code changes are present in the files

---

## ✅ All Tests Passed?

If all tests pass, the security vulnerabilities have been successfully fixed! 🎉

The system now:
- ✅ Filters dashboard data by department/unit for experts
- ✅ Filters activity logs by department/unit for experts
- ✅ Validates roles at login
- ✅ Validates roles server-side on user creation/edit
- ✅ Uses consistent role constants
- ✅ Enforces valid roles at database level
