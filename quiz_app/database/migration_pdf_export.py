"""
Migration: Add PDF Export Support
Adds delivery method to exams table and creates pdf_exports table for tracking variants
"""

import sqlite3
from quiz_app.config import DATABASE_PATH

def migrate():
    """Run the migration"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Add delivery_method column to exams table
        print("Adding delivery_method column to exams table...")
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN delivery_method TEXT DEFAULT "online"')
            print("✓ Added delivery_method column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("✓ delivery_method column already exists")
            else:
                raise

        # Create pdf_exports table
        print("Creating pdf_exports table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pdf_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                variant_number INTEGER NOT NULL,
                question_snapshot TEXT NOT NULL,
                exported_by INTEGER NOT NULL,
                exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                notes TEXT,
                FOREIGN KEY (exam_id) REFERENCES exams (id),
                FOREIGN KEY (exported_by) REFERENCES users (id),
                UNIQUE(exam_id, variant_number)
            )
        ''')
        print("✓ Created pdf_exports table")

        # Create indexes for better performance
        print("Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_exports_exam ON pdf_exports(exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_exports_variant ON pdf_exports(exam_id, variant_number)')
        print("✓ Created indexes")

        conn.commit()
        print("\n✓ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

def rollback():
    """Rollback the migration"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        print("Rolling back migration...")

        # Drop pdf_exports table
        cursor.execute('DROP TABLE IF EXISTS pdf_exports')
        print("✓ Dropped pdf_exports table")

        # Note: Cannot remove column from SQLite easily, would need to recreate table
        print("⚠ Note: delivery_method column remains in exams table (SQLite limitation)")

        conn.commit()
        print("\n✓ Rollback completed!")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Rollback failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
