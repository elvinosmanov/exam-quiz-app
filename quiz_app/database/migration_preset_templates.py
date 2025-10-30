"""
Migration: Add preset templates tables
Creates tables for managing exam preset templates with topic/difficulty configuration
"""

import sqlite3
from quiz_app.config import DATABASE_PATH

def run_migration():
    """Add preset templates tables to database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Create exam_preset_templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_preset_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id)
            )
        ''')

        # Create preset_template_exams table (configuration per exam/topic)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preset_template_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                easy_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                hard_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES exam_preset_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE
            )
        ''')

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_preset_templates_creator ON exam_preset_templates(created_by_user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_preset_template_exams_template ON preset_template_exams(template_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_preset_template_exams_exam ON preset_template_exams(exam_id)')

        conn.commit()
        print("✓ Migration completed: Preset templates tables created successfully")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
