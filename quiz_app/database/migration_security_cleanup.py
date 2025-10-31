"""
Database Migration: Security Settings Cleanup
Removes unused security features:
- prevent_focus_loss column from exam_assignments and exams
- enable_logging column from exam_assignments
- enable_pattern_analysis column from exam_assignments and exams
- audit_log table
- pattern_analysis table
"""

import sqlite3
import os

def migrate_database():
    """Remove unused security columns and tables from database"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'quiz_app.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.Connection(db_path)
    cursor = conn.cursor()

    try:
        print("Starting security cleanup migration...")

        # Step 1: Create new exam_assignments table without removed columns
        print("  - Creating new exam_assignments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_assignments_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                assignment_name TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                passing_score REAL NOT NULL,
                max_attempts INTEGER DEFAULT 1,
                start_date TEXT,
                end_date TEXT,
                deadline TEXT,
                randomize_questions BOOLEAN DEFAULT 0,
                show_results BOOLEAN DEFAULT 1,
                enable_fullscreen BOOLEAN DEFAULT 0,
                use_question_pool BOOLEAN DEFAULT 0,
                questions_to_select INTEGER DEFAULT 0,
                easy_questions_count INTEGER DEFAULT 0,
                medium_questions_count INTEGER DEFAULT 0,
                hard_questions_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY (exam_id) REFERENCES exams(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        # Step 2: Copy data from old table to new table
        print("  - Copying exam_assignments data...")
        cursor.execute("""
            INSERT INTO exam_assignments_new
            (id, exam_id, assignment_name, duration_minutes, passing_score, max_attempts,
             start_date, end_date, deadline, randomize_questions, show_results, enable_fullscreen,
             use_question_pool, questions_to_select, easy_questions_count, medium_questions_count,
             hard_questions_count, is_active, created_at, created_by)
            SELECT
                id, exam_id, assignment_name, duration_minutes, passing_score, max_attempts,
                start_date, end_date, deadline, randomize_questions, show_results, enable_fullscreen,
                use_question_pool, questions_to_select, easy_questions_count, medium_questions_count,
                hard_questions_count, is_active, created_at, created_by
            FROM exam_assignments
        """)

        # Step 3: Drop old table and rename new table
        print("  - Replacing exam_assignments table...")
        cursor.execute("DROP TABLE exam_assignments")
        cursor.execute("ALTER TABLE exam_assignments_new RENAME TO exam_assignments")

        # Step 4: Create new exams table without removed columns
        print("  - Creating new exams table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exams_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                duration_minutes INTEGER NOT NULL,
                passing_score REAL NOT NULL,
                max_attempts INTEGER DEFAULT 1,
                randomize_questions BOOLEAN DEFAULT 0,
                show_results BOOLEAN DEFAULT 1,
                enable_fullscreen BOOLEAN DEFAULT 0,
                created_by INTEGER,
                created_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        # Step 5: Copy data from old exams table
        print("  - Copying exams data...")
        cursor.execute("""
            INSERT INTO exams_new
            (id, title, description, category, duration_minutes, passing_score, max_attempts,
             randomize_questions, show_results, enable_fullscreen, created_by, created_at, is_active)
            SELECT
                id, title, description, category, duration_minutes, passing_score, max_attempts,
                randomize_questions, show_results, enable_fullscreen, created_by, created_at, is_active
            FROM exams
        """)

        # Step 6: Drop old table and rename new table
        print("  - Replacing exams table...")
        cursor.execute("DROP TABLE exams")
        cursor.execute("ALTER TABLE exams_new RENAME TO exams")

        # Step 7: Drop audit_log table if it exists
        print("  - Dropping audit_log table...")
        cursor.execute("DROP TABLE IF EXISTS audit_log")

        # Step 8: Drop pattern_analysis table if it exists
        print("  - Dropping pattern_analysis table...")
        cursor.execute("DROP TABLE IF EXISTS pattern_analysis")

        conn.commit()
        print("✓ Security cleanup migration completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\nMigration completed. Removed:")
        print("  - prevent_focus_loss column")
        print("  - enable_logging column")
        print("  - enable_pattern_analysis column")
        print("  - audit_log table")
        print("  - pattern_analysis table")
    else:
        print("\nMigration failed. Please check the errors above.")
