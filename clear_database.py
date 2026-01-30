#!/usr/bin/env python3
"""
Script to clear all database data except the admin user.
Keeps only: admin user (username: admin)
Deletes: All other data from all tables
"""

try:
    from sqlcipher3 import dbapi2 as sqlite3
    ENCRYPTION_ENABLED = True
except ImportError:
    import sqlite3
    ENCRYPTION_ENABLED = False

from quiz_app.config import DATABASE_PATH

# Database encryption key (same as in database.py)
DATABASE_ENCRYPTION_KEY = "QuizApp2025!AzErCoSmOs#SecureKey$Protected"

def clear_database():
    """Clear all data except admin user"""

    print("=" * 60)
    print("DATABASE CLEANUP - Keeping only admin user")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)

    # Apply encryption key if SQLCipher is enabled
    if ENCRYPTION_ENABLED:
        conn.execute(f"PRAGMA key='{DATABASE_ENCRYPTION_KEY}'")
        try:
            conn.execute("SELECT count(*) FROM sqlite_master")
        except sqlite3.DatabaseError as e:
            print(f"ERROR: Database encryption key validation failed: {e}")
            return

    cursor = conn.cursor()

    # Disable foreign key constraints temporarily
    cursor.execute("PRAGMA foreign_keys = OFF")

    try:
        # Get admin user ID before deletion
        cursor.execute("SELECT id, username, full_name FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()

        if not admin_user:
            print("ERROR: Admin user not found! Cannot proceed.")
            return

        admin_id, admin_username, admin_fullname = admin_user
        print(f"\nFound admin user: {admin_username} (ID: {admin_id}, Name: {admin_fullname})")
        print("\nDeleting data from all tables...\n")

        # List of tables to clear completely
        tables_to_clear = [
            'grade_edit_history',
            'pattern_analysis',
            'email_log',
            'pdf_exports',
            'preset_observers',
            'preset_template_exams',
            'exam_preset_templates',
            'assignment_exam_templates',
            'assignment_users',
            'exam_assignments',
            'exam_observers',
            'exam_permissions',
            'session_questions',
            'user_answers',
            'exam_sessions',
            'question_options',
            'questions',
            'exams',
        ]

        # Delete from tables (in order to respect foreign keys)
        for table in tables_to_clear:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]

                cursor.execute(f"DELETE FROM {table}")
                conn.commit()

                print(f"  ✓ {table:30s} - Deleted {count_before} rows")
            except sqlite3.OperationalError as e:
                print(f"  ⚠ {table:30s} - Error: {e}")

        # Delete all users EXCEPT admin
        cursor.execute("SELECT COUNT(*) FROM users WHERE username != 'admin'")
        users_to_delete = cursor.fetchone()[0]

        cursor.execute("DELETE FROM users WHERE username != 'admin'")
        conn.commit()
        print(f"  ✓ {'users':30s} - Deleted {users_to_delete} users (kept admin)")

        # Clear system tables but keep structure
        system_tables = [
            'organizational_structure',
        ]

        for table in system_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count_before = cursor.fetchone()[0]

                cursor.execute(f"DELETE FROM {table}")
                conn.commit()

                print(f"  ✓ {table:30s} - Deleted {count_before} rows")
            except sqlite3.OperationalError as e:
                print(f"  ⚠ {table:30s} - Error: {e}")

        # Keep email_templates and system_settings (they contain app configuration)
        print(f"\n  ℹ  Keeping: email_templates, system_settings (app configuration)")

        print("\n" + "=" * 60)
        print("DATABASE CLEANUP COMPLETED")
        print("=" * 60)
        print(f"\nRemaining data:")
        print(f"  • Admin user: {admin_username}")
        print(f"  • Email templates: {cursor.execute('SELECT COUNT(*) FROM email_templates').fetchone()[0]} templates")
        print(f"  • System settings: {cursor.execute('SELECT COUNT(*) FROM system_settings').fetchone()[0]} settings")
        print(f"\nAll exam/question/session/assignment data has been deleted.")
        print(f"\nYou can now log in with:")
        print(f"  Username: admin")
        print(f"  Password: admin123")

    except Exception as e:
        print(f"\nERROR during cleanup: {e}")
        conn.rollback()
    finally:
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.close()

if __name__ == "__main__":
    import sys

    # Check for --confirm flag
    if "--confirm" in sys.argv:
        clear_database()
    else:
        # Ask for confirmation
        print("\n⚠️  WARNING: This will delete ALL data except the admin user!")
        print("This action cannot be undone.\n")
        print("Run with --confirm flag to execute:")
        print("  python3 clear_database.py --confirm")
        print("\nOr type 'DELETE ALL' to confirm: ", end="")

        try:
            confirmation = input()
            if confirmation == "DELETE ALL":
                clear_database()
            else:
                print("\nOperation cancelled.")
        except EOFError:
            print("\nOperation cancelled (non-interactive mode).")
