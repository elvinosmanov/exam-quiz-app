"""
Migration to add is_archived field to exam_assignments table
"""

import sqlite3
import os
from quiz_app.config import DATABASE_PATH

def migrate():
    """Add is_archived field to exam_assignments table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Add is_archived column to exam_assignments table
        cursor.execute('''
            ALTER TABLE exam_assignments ADD COLUMN is_archived BOOLEAN DEFAULT 0
        ''')

        conn.commit()
        print("✓ Migration successful: is_archived field added to exam_assignments table")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Column is_archived already exists")
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
