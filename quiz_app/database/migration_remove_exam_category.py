"""
Migration to remove category column from exams table
Category field is not used anywhere in the application logic
"""

import sqlite3
from quiz_app.config import DATABASE_PATH

def migrate():
    """Remove category column from exams table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Check if category column exists
        cursor.execute("PRAGMA table_info(exams)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'category' not in column_names:
            print("✓ Category column does not exist in exams table. Migration not needed.")
            return

        print("Removing category column from exams table...")

        # SQLite doesn't support DROP COLUMN directly in older versions
        # So we need to recreate the table

        # Start transaction
        cursor.execute('BEGIN TRANSACTION')

        # Create new exams table without category column
        cursor.execute('''
            CREATE TABLE exams_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                passing_score REAL NOT NULL DEFAULT 70.0,
                max_attempts INTEGER DEFAULT 1,
                randomize_questions BOOLEAN DEFAULT 0,
                show_results BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                enable_fullscreen BOOLEAN DEFAULT 0,
                prevent_focus_loss BOOLEAN DEFAULT 0,
                enable_logging BOOLEAN DEFAULT 0,
                enable_pattern_analysis BOOLEAN DEFAULT 0,
                use_question_pool BOOLEAN DEFAULT 0,
                total_questions_in_pool INTEGER DEFAULT 0,
                questions_to_select INTEGER DEFAULT 0,
                easy_questions_count INTEGER DEFAULT 0,
                medium_questions_count INTEGER DEFAULT 0,
                hard_questions_count INTEGER DEFAULT 0,
                access_mode TEXT DEFAULT 'open',
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')

        # Copy data from old table to new table (excluding category)
        cursor.execute('''
            INSERT INTO exams_new (
                id, title, description, duration_minutes, passing_score, max_attempts,
                randomize_questions, show_results, is_active, start_date, end_date,
                created_by, created_at, enable_fullscreen, prevent_focus_loss,
                enable_logging, enable_pattern_analysis, use_question_pool,
                total_questions_in_pool, questions_to_select, easy_questions_count,
                medium_questions_count, hard_questions_count, access_mode
            )
            SELECT
                id, title, description, duration_minutes, passing_score, max_attempts,
                randomize_questions, show_results, is_active, start_date, end_date,
                created_by, created_at, enable_fullscreen, prevent_focus_loss,
                enable_logging, enable_pattern_analysis, use_question_pool,
                total_questions_in_pool, questions_to_select, easy_questions_count,
                medium_questions_count, hard_questions_count, access_mode
            FROM exams
        ''')

        # Drop old table
        cursor.execute('DROP TABLE exams')

        # Rename new table to original name
        cursor.execute('ALTER TABLE exams_new RENAME TO exams')

        # Commit transaction
        conn.commit()
        print("✓ Migration successful: category column removed from exams table")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
