"""
Database Migration: Add Role Validation
Security Fix: Add CHECK constraint to validate user roles
"""

import sqlite3
import os
from quiz_app.config import DATABASE_PATH

def migrate():
    """
    Add role validation to users table

    NOTE: SQLite doesn't support adding CHECK constraints to existing tables,
    so we need to recreate the table with the constraint.
    """
    print("[MIGRATION] Starting role validation migration...")

    if not os.path.exists(DATABASE_PATH):
        print(f"[ERROR] Database not found at {DATABASE_PATH}")
        return False

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if migration already applied
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
        result = cursor.fetchone()
        if result and "CHECK" in result[0] and "role IN" in result[0]:
            print("[MIGRATION] Role validation constraint already exists. Skipping.")
            return True

        # Start transaction
        cursor.execute("BEGIN TRANSACTION")

        # Step 1: Create new users table with CHECK constraint
        print("[MIGRATION] Creating new users table with role validation...")
        cursor.execute('''
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'examinee' CHECK(role IN ('admin', 'expert', 'examinee')),
                department TEXT,
                section TEXT,
                unit TEXT,
                employee_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                language_preference TEXT DEFAULT "en"
            )
        ''')

        # Step 2: Copy data from old table to new table
        print("[MIGRATION] Copying data to new table...")
        cursor.execute('''
            INSERT INTO users_new
            SELECT id, username, email, password_hash, full_name,
                   LOWER(role), department, section, unit, employee_id,
                   is_active, created_at, last_login, language_preference
            FROM users
        ''')

        # Step 3: Drop old table
        print("[MIGRATION] Dropping old users table...")
        cursor.execute("DROP TABLE users")

        # Step 4: Rename new table to original name
        print("[MIGRATION] Renaming new table...")
        cursor.execute("ALTER TABLE users_new RENAME TO users")

        # Commit transaction
        conn.commit()
        print("[MIGRATION] Role validation migration completed successfully!")
        return True

    except Exception as e:
        # Rollback on error
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
