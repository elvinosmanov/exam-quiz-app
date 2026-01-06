"""
Migration script to add grade editing audit trail functionality.

This migration adds:
1. grade_edit_history table to track all grade edits
2. Audit columns to exam_sessions table (last_edited_by, last_edited_at, edit_count)
"""

import sys
import os

# Add parent directory to path so we can import from quiz_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlcipher3 import dbapi2 as sqlite3
    ENCRYPTION_ENABLED = True
except ImportError:
    import sqlite3
    ENCRYPTION_ENABLED = False
    print("WARNING: sqlcipher3-wheels not installed. Database will NOT be encrypted!")

from config import DATABASE_PATH

# Database encryption key (must match the one in database.py)
DATABASE_ENCRYPTION_KEY = "QuizApp2025!AzErCoSmOs#SecureKey$Protected"

def get_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Apply encryption key if SQLCipher is enabled
    if ENCRYPTION_ENABLED:
        conn.execute(f"PRAGMA key='{DATABASE_ENCRYPTION_KEY}'")
        # Verify database is accessible
        try:
            conn.execute("SELECT count(*) FROM sqlite_master")
        except sqlite3.DatabaseError as e:
            print(f"Database encryption key validation failed: {e}")
            raise Exception("Unable to decrypt database. Encryption key may be incorrect.")

    return conn

def run_migration():
    """Run the migration to add grade editing functionality"""
    print("Starting grade editing migration...")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Create grade_edit_history table
        print("Creating grade_edit_history table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grade_edit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer_id INTEGER NOT NULL,
                old_points REAL NOT NULL,
                new_points REAL NOT NULL,
                old_total_score REAL,
                new_total_score REAL,
                edited_by INTEGER NOT NULL,
                edit_reason TEXT,
                edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES exam_sessions (id),
                FOREIGN KEY (question_id) REFERENCES questions (id),
                FOREIGN KEY (answer_id) REFERENCES user_answers (id),
                FOREIGN KEY (edited_by) REFERENCES users (id)
            )
        ''')

        # 2. Add audit columns to exam_sessions table
        print("Adding audit columns to exam_sessions table...")

        # Check if columns exist before adding
        cursor.execute("PRAGMA table_info(exam_sessions)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        if 'last_edited_by' not in existing_columns:
            cursor.execute('ALTER TABLE exam_sessions ADD COLUMN last_edited_by INTEGER')
            print("  - Added last_edited_by column")

        if 'last_edited_at' not in existing_columns:
            cursor.execute('ALTER TABLE exam_sessions ADD COLUMN last_edited_at TIMESTAMP')
            print("  - Added last_edited_at column")

        if 'edit_count' not in existing_columns:
            cursor.execute('ALTER TABLE exam_sessions ADD COLUMN edit_count INTEGER DEFAULT 0')
            print("  - Added edit_count column")

        # 3. Create indexes for better performance
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_grade_edit_history_session ON grade_edit_history(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_grade_edit_history_answer ON grade_edit_history(answer_id)')

        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        print("\nNew functionality:")
        print("  - Grades can now be edited after initial grading")
        print("  - Full audit trail of all grade changes")
        print("  - Edit history includes: who edited, when, old/new points, and reason")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
