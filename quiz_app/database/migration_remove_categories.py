#!/usr/bin/env python3
"""
Database Migration: Remove category column from questions table

This migration removes the category field from questions since categories
should be at the exam level, not the question level.
"""

import sqlite3
import os
import shutil
from datetime import datetime
from quiz_app.config import DATABASE_PATH

def backup_database():
    """Create a backup of the database before migration"""
    backup_path = f"{DATABASE_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(DATABASE_PATH, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path

def migrate_remove_question_category():
    """
    Remove category column from questions table
    
    Since SQLite doesn't support DROP COLUMN directly in older versions,
    we need to:
    1. Create a new table without the category column
    2. Copy all data except the category column
    3. Drop the old table
    4. Rename the new table
    """
    
    print("Starting migration: Remove category column from questions table")
    
    # Backup database first
    backup_path = backup_database()
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if category column exists
        cursor.execute("PRAGMA table_info(questions)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'category' not in column_names:
            print("Category column does not exist in questions table. Migration not needed.")
            return True
        
        print("Found category column in questions table. Proceeding with migration...")
        
        # Start transaction
        cursor.execute('BEGIN TRANSACTION')
        
        # Create new questions table without category column
        cursor.execute('''
            CREATE TABLE questions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                image_path TEXT,
                correct_answer TEXT,
                explanation TEXT,
                points REAL DEFAULT 1.0,
                difficulty_level TEXT DEFAULT 'medium',
                order_index INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            )
        ''')
        
        # Copy data from old table to new table (excluding category)
        cursor.execute('''
            INSERT INTO questions_new (
                id, exam_id, question_text, question_type, image_path,
                correct_answer, explanation, points, difficulty_level,
                order_index, is_active, created_at
            )
            SELECT 
                id, exam_id, question_text, question_type, image_path,
                correct_answer, explanation, points, difficulty_level,
                order_index, is_active, created_at
            FROM questions
        ''')
        
        # Get count of migrated records
        cursor.execute("SELECT COUNT(*) FROM questions_new")
        new_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM questions")
        old_count = cursor.fetchone()[0]
        
        if new_count != old_count:
            raise Exception(f"Data migration failed: old count {old_count}, new count {new_count}")
        
        # Drop old table
        cursor.execute('DROP TABLE questions')
        
        # Rename new table to original name
        cursor.execute('ALTER TABLE questions_new RENAME TO questions')
        
        # Recreate indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam_id)')
        
        # Commit transaction
        cursor.execute('COMMIT')
        
        print(f"Successfully migrated {new_count} questions")
        print("Category column removed from questions table")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        cursor.execute('ROLLBACK')
        print("Transaction rolled back")
        
        # Restore from backup
        print(f"Restoring database from backup: {backup_path}")
        shutil.copy2(backup_path, DATABASE_PATH)
        
        return False
        
    finally:
        conn.close()

def verify_migration():
    """Verify that the migration was successful"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(questions)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'category' in column_names:
            print("❌ Migration verification failed: category column still exists")
            return False
        
        # Check that we still have data
        cursor.execute("SELECT COUNT(*) FROM questions")
        count = cursor.fetchone()[0]
        
        print(f"✅ Migration verification successful:")
        print(f"   - Category column removed from questions table")
        print(f"   - {count} questions preserved")
        print(f"   - Columns in questions table: {', '.join(column_names)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False
        
    finally:
        conn.close()

def main():
    """Run the migration"""
    print("=" * 60)
    print("DATABASE MIGRATION: Remove Question Categories")
    print("=" * 60)
    
    if not os.path.exists(DATABASE_PATH):
        print(f"Error: Database not found at {DATABASE_PATH}")
        return False
    
    success = migrate_remove_question_category()
    
    if success:
        verify_migration()
        print("\n✅ Migration completed successfully!")
    else:
        print("\n❌ Migration failed!")
    
    return success

if __name__ == "__main__":
    main()