"""
Migration to add email_sent boolean field to exam_sessions table
This allows tracking whether exam results have been emailed to examinees
"""

import sqlite3
from quiz_app.config import DATABASE_PATH

def migrate():
    """Add email_sent column to exam_sessions table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Add email_sent column to exam_sessions table
        cursor.execute('''
            ALTER TABLE exam_sessions ADD COLUMN email_sent BOOLEAN DEFAULT 0
        ''')

        conn.commit()
        print("✓ Migration successful: email_sent column added to exam_sessions table")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Migration skipped: email_sent column already exists")
        else:
            conn.rollback()
            print(f"✗ Migration failed: {e}")
            raise
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
