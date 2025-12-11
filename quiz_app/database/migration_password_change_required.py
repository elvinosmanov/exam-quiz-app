"""
Database Migration: Add Password Change Required Field
Adds flag to track if user needs to change password on first login
"""

import sqlite3
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from quiz_app.config import DATABASE_PATH
except ImportError:
    # Fallback if import fails
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'quiz_app.db')

def migrate():
    """
    Add password_change_required column to users table
    """
    print("[MIGRATION] Starting password change required migration...")

    if not os.path.exists(DATABASE_PATH):
        print(f"[ERROR] Database not found at {DATABASE_PATH}")
        return False

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'password_change_required' in columns:
            print("[MIGRATION] password_change_required column already exists. Skipping.")
            return True

        # Add new column
        print("[MIGRATION] Adding password_change_required column...")
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN password_change_required BOOLEAN DEFAULT 0
        """)

        conn.commit()
        print("[MIGRATION] password_change_required column added successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
