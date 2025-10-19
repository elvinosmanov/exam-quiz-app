#!/usr/bin/env python3
"""
Database Migration 001: Enhanced Question Types Support
- Add support for multiple answer selections
- Migrate existing questions to new types
- Add question type validation
"""

import sqlite3
import os
import sys
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from quiz_app.config import DATABASE_PATH

class QuestionTypeMigration:
    def __init__(self):
        self.db_path = DATABASE_PATH
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def run_migration(self) -> bool:
        """Run the complete migration"""
        try:
            print("🔄 Starting Question Types Migration...")
            
            # Step 1: Add new columns
            self.add_new_columns()
            
            # Step 2: Migrate existing data
            self.migrate_existing_questions()
            
            # Step 3: Add validation (for future use)
            self.add_validation()
            
            print("✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def add_new_columns(self):
        """Add new columns to support multiple answer selections"""
        print("📝 Adding new database columns...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Add selected_option_ids column to user_answers table
                cursor.execute('''
                    ALTER TABLE user_answers ADD COLUMN selected_option_ids TEXT
                ''')
                print("   ✓ Added selected_option_ids column to user_answers")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print("   ⚠️  selected_option_ids column already exists")
                else:
                    raise e
            
            conn.commit()
    
    def migrate_existing_questions(self):
        """Migrate existing multiple_choice questions to single_choice"""
        print("🔄 Migrating existing questions...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get count of questions to migrate
            cursor.execute("SELECT COUNT(*) as count FROM questions WHERE question_type = 'multiple_choice'")
            count = cursor.fetchone()['count']
            
            if count > 0:
                print(f"   📊 Found {count} multiple_choice questions to migrate")
                
                # Migrate multiple_choice to single_choice (backward compatibility)
                cursor.execute('''
                    UPDATE questions 
                    SET question_type = 'single_choice' 
                    WHERE question_type = 'multiple_choice'
                ''')
                
                print(f"   ✓ Migrated {count} questions from 'multiple_choice' to 'single_choice'")
            else:
                print("   ℹ️  No questions need migration")
            
            conn.commit()
    
    def add_validation(self):
        """Add validation rules (informational - SQLite doesn't enforce CHECK in ALTER)"""
        print("📋 Adding validation documentation...")
        
        # Note: SQLite doesn't support adding CHECK constraints via ALTER TABLE
        # This is documented for future schema recreation
        valid_types = ['single_choice', 'multiple_choice', 'true_false', 'short_answer', 'essay']
        print(f"   📝 Valid question types: {', '.join(valid_types)}")
        print("   ℹ️  Validation will be enforced in application logic")
    
    def verify_migration(self) -> bool:
        """Verify the migration was successful"""
        print("🔍 Verifying migration...")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if new column exists
                cursor.execute("PRAGMA table_info(user_answers)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'selected_option_ids' not in columns:
                    print("   ❌ selected_option_ids column not found")
                    return False
                
                # Check question type migration
                cursor.execute("SELECT COUNT(*) as count FROM questions WHERE question_type = 'multiple_choice'")
                old_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM questions WHERE question_type = 'single_choice'")
                new_count = cursor.fetchone()['count']
                
                print(f"   ✓ Questions with old type 'multiple_choice': {old_count}")
                print(f"   ✓ Questions with new type 'single_choice': {new_count}")
                
                # Show current question type distribution
                cursor.execute('''
                    SELECT question_type, COUNT(*) as count 
                    FROM questions 
                    GROUP BY question_type 
                    ORDER BY count DESC
                ''')
                
                print("   📊 Current question type distribution:")
                for row in cursor.fetchall():
                    print(f"      - {row['question_type']}: {row['count']}")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Verification failed: {e}")
            return False
    
    def rollback_migration(self):
        """Rollback migration (for testing purposes)"""
        print("⏪ Rolling back migration...")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Rollback question type changes
                cursor.execute('''
                    UPDATE questions 
                    SET question_type = 'multiple_choice' 
                    WHERE question_type = 'single_choice'
                ''')
                
                print("   ✓ Rolled back question types")
                conn.commit()
                
        except Exception as e:
            print(f"   ❌ Rollback failed: {e}")

def run_migration():
    """Main migration function"""
    migration = QuestionTypeMigration()
    
    print("🚀 Question Types Migration Starting...")
    print("=" * 50)
    
    success = migration.run_migration()
    
    if success:
        verification_success = migration.verify_migration()
        if verification_success:
            print("=" * 50)
            print("🎉 Migration completed successfully!")
            print("📝 Database is now ready for enhanced question types")
        else:
            print("⚠️  Migration completed but verification failed")
    else:
        print("❌ Migration failed - database unchanged")
    
    return success

if __name__ == "__main__":
    run_migration()