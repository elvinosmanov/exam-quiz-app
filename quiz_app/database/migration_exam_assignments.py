"""
Migration to add exam_assignments and assignment_users tables
This allows the same exam to be assigned multiple times with different settings
"""

import sqlite3
import os
from quiz_app.config import DATABASE_PATH

def migrate():
    """Add exam_assignments and assignment_users tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Create exam_assignments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                assignment_name TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                passing_score REAL NOT NULL,
                max_attempts INTEGER DEFAULT 1,
                randomize_questions BOOLEAN DEFAULT 0,
                show_results BOOLEAN DEFAULT 1,
                enable_fullscreen BOOLEAN DEFAULT 0,
                prevent_focus_loss BOOLEAN DEFAULT 0,
                enable_logging BOOLEAN DEFAULT 0,
                enable_pattern_analysis BOOLEAN DEFAULT 0,
                use_question_pool BOOLEAN DEFAULT 0,
                questions_to_select INTEGER DEFAULT 0,
                easy_questions_count INTEGER DEFAULT 0,
                medium_questions_count INTEGER DEFAULT 0,
                hard_questions_count INTEGER DEFAULT 0,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                deadline TIMESTAMP,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')

        # Create assignment_users junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignment_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (assignment_id) REFERENCES exam_assignments (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (granted_by) REFERENCES users (id),
                UNIQUE(assignment_id, user_id)
            )
        ''')

        conn.commit()
        print("✓ Migration successful: exam_assignments and assignment_users tables created")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
