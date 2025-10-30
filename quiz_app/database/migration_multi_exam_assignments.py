"""
Migration to support multiple exam templates in a single assignment
Adds assignment_exam_templates junction table
"""

import sqlite3
import os
from quiz_app.config import DATABASE_PATH

def migrate():
    """Add support for multiple exam templates per assignment"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Create assignment_exam_templates junction table
        # This allows one assignment to include multiple exam templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignment_exam_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES exam_assignments (id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
                UNIQUE(assignment_id, exam_id)
            )
        ''')

        # Add index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_assignment_exam_templates_assignment
            ON assignment_exam_templates(assignment_id)
        ''')

        conn.commit()
        print("✓ Migration successful: assignment_exam_templates table created")
        print("  Assignments can now include multiple exam templates!")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
