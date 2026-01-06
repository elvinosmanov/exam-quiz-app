# Quick User Reset Guide

## Option 1: Using the Reset Script (Recommended)

Run the interactive reset script:

```bash
cd exam-quiz-app
python3 reset_users.py
```

This will:
1. Show you all current users
2. Ask for confirmation
3. Delete all users and related data (sessions, answers, assignments)

**To confirm deletion, type:** `YES DELETE ALL`

---

## Option 2: Direct Database Command (Quick)

If you want to quickly reset without confirmation prompts:

```bash
cd exam-quiz-app
sqlite3 quiz_app.db << 'EOF'
DELETE FROM users;
DELETE FROM exam_sessions;
DELETE FROM user_answers;
DELETE FROM student_assignments;
SELECT 'Users deleted: ' || changes();
EOF
```

---

## Option 3: Using Python One-liner

```bash
cd exam-quiz-app
python3 -c "
import sys; sys.path.insert(0, 'quiz_app')
from database.database import Database
db = Database()
db.execute_update('DELETE FROM users')
db.execute_update('DELETE FROM exam_sessions')
db.execute_update('DELETE FROM user_answers')
db.execute_update('DELETE FROM student_assignments')
print('✅ All users and related data deleted!')
"
```

---

## What Gets Deleted

When you reset users, the following data is removed:

- ✅ **Users** - All user accounts
- ✅ **Exam Sessions** - All exam attempts
- ✅ **User Answers** - All submitted answers
- ✅ **Student Assignments** - All assignment submissions

**What is kept:**
- ✅ Questions
- ✅ Exams
- ✅ Exam Assignments
- ✅ Topics/Categories
- ✅ Question Options

---

## After Reset

After resetting, you'll need to create new users. The default admin account can be recreated using:

```bash
cd exam-quiz-app
python3 quiz_app/database/create_initial_users.py
```

Or create users manually through the admin interface (if you have an admin account).

---

## Verification

To check if users were deleted:

```bash
cd exam-quiz-app
sqlite3 quiz_app.db "SELECT COUNT(*) as user_count FROM users;"
```

Expected output: `0` (zero users)

---

## Safety Note

⚠️ **This action is IRREVERSIBLE**

- All user accounts will be permanently deleted
- All exam sessions and answers will be lost
- Make a backup first if you need to preserve any data

To backup the database:
```bash
cd exam-quiz-app
cp quiz_app.db quiz_app.db.backup
```

To restore from backup:
```bash
cd exam-quiz-app
cp quiz_app.db.backup quiz_app.db
```
