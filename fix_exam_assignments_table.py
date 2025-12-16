#!/usr/bin/env python3
"""
Fix exam_assignments table structure
=====================================

This script fixes the exam_assignments table which lost its PRIMARY KEY constraint,
causing all new assignments to have NULL id values.

IMPORTANT: This will:
1. Backup the current table data
2. Drop the corrupted table
3. Recreate it with proper PRIMARY KEY
4. Restore the data with new IDs
"""

import os
import sys
from datetime import datetime

from quiz_app.database.database import Database
from quiz_app.config import DATABASE_PATH

def fix_exam_assignments_table():
    """Fix the exam_assignments table structure"""

    print("=" * 70)
    print("FIX EXAM_ASSIGNMENTS TABLE")
    print("=" * 70)
    print(f"Database: {DATABASE_PATH}")
    print()

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Step 1: Check current state
    print("[1/6] Checking current table structure...")
    cursor.execute("PRAGMA table_info(exam_assignments)")
    columns = cursor.fetchall()
    id_col = [dict(c) for c in columns if c[1] == 'id'][0]

    if id_col['pk'] == 0:
        print("✗ Table is corrupted - 'id' is not a primary key!")
    else:
        print("✓ Table structure is correct")
        print("\nNo fix needed. Exiting.")
        return

    # Step 2: Backup existing data
    print("\n[2/6] Backing up existing data...")
    cursor.execute("SELECT * FROM exam_assignments")
    backup_data = [dict(row) for row in cursor.fetchall()]

    # Filter out rows with NULL id
    valid_data = [row for row in backup_data if row['id'] is not None]
    corrupted_data = [row for row in backup_data if row['id'] is None]

    print(f"  Total rows: {len(backup_data)}")
    print(f"  Valid rows (with ID): {len(valid_data)}")
    print(f"  Corrupted rows (NULL ID): {len(corrupted_data)}")

    if corrupted_data:
        print("\n  Corrupted assignments that will be DELETED:")
        for row in corrupted_data:
            print(f"    - {row['assignment_name']} (created: {row['created_at']})")

    # Step 3: Backup related tables
    print("\n[3/6] Backing up related data...")

    # Backup assignment_users (only for valid assignments)
    valid_ids = [row['id'] for row in valid_data]
    if valid_ids:
        placeholders = ','.join('?' * len(valid_ids))
        cursor.execute(f"SELECT * FROM assignment_users WHERE assignment_id IN ({placeholders})", valid_ids)
        assignment_users_backup = [dict(row) for row in cursor.fetchall()]
    else:
        assignment_users_backup = []

    # Backup assignment_exam_templates
    if valid_ids:
        cursor.execute(f"SELECT * FROM assignment_exam_templates WHERE assignment_id IN ({placeholders})", valid_ids)
        assignment_templates_backup = [dict(row) for row in cursor.fetchall()]
    else:
        assignment_templates_backup = []

    print(f"  Backed up {len(assignment_users_backup)} user assignments")
    print(f"  Backed up {len(assignment_templates_backup)} template assignments")

    # Step 4: Drop and recreate table
    print("\n[4/6] Recreating table with correct structure...")
    cursor.execute("DROP TABLE IF EXISTS exam_assignments")

    # Create with proper PRIMARY KEY
    cursor.execute('''
        CREATE TABLE exam_assignments (
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
            delivery_method TEXT DEFAULT 'online',
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
            is_archived BOOLEAN DEFAULT 0,
            pdf_variant_count INTEGER DEFAULT 1,
            FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    print("✓ Table recreated with proper PRIMARY KEY")

    # Step 5: Restore data
    print("\n[5/6] Restoring data...")

    # Create mapping from old IDs to new IDs
    id_mapping = {}

    for row in valid_data:
        old_id = row['id']

        # Insert without id (let AUTOINCREMENT generate it)
        cursor.execute('''
            INSERT INTO exam_assignments (
                exam_id, assignment_name, duration_minutes, passing_score, max_attempts,
                randomize_questions, show_results, enable_fullscreen,
                delivery_method, use_question_pool, questions_to_select,
                easy_questions_count, medium_questions_count, hard_questions_count,
                start_date, end_date, deadline,
                created_by, created_at, is_active, is_archived, pdf_variant_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['exam_id'], row['assignment_name'], row['duration_minutes'], row['passing_score'],
            row['max_attempts'], row['randomize_questions'], row['show_results'], row['enable_fullscreen'],
            row['delivery_method'], row['use_question_pool'], row['questions_to_select'],
            row['easy_questions_count'], row['medium_questions_count'], row['hard_questions_count'],
            row['start_date'], row['end_date'], row['deadline'],
            row['created_by'], row['created_at'], row['is_active'], row['is_archived'], row['pdf_variant_count']
        ))

        new_id = cursor.lastrowid
        id_mapping[old_id] = new_id
        print(f"  Restored: {row['assignment_name']} (old ID: {old_id} -> new ID: {new_id})")

    # Step 6: Restore related tables with new IDs
    print("\n[6/6] Restoring related data with new IDs...")

    for user_assignment in assignment_users_backup:
        old_assignment_id = user_assignment['assignment_id']
        if old_assignment_id in id_mapping:
            new_assignment_id = id_mapping[old_assignment_id]
            cursor.execute('''
                INSERT INTO assignment_users (assignment_id, user_id, granted_by, granted_at, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                new_assignment_id, user_assignment['user_id'], user_assignment['granted_by'],
                user_assignment['granted_at'], user_assignment['is_active']
            ))

    for template_assignment in assignment_templates_backup:
        old_assignment_id = template_assignment['assignment_id']
        if old_assignment_id in id_mapping:
            new_assignment_id = id_mapping[old_assignment_id]
            cursor.execute('''
                INSERT INTO assignment_exam_templates (
                    assignment_id, exam_id, order_index,
                    easy_count, medium_count, hard_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                new_assignment_id, template_assignment['exam_id'], template_assignment['order_index'],
                template_assignment.get('easy_count'), template_assignment.get('medium_count'),
                template_assignment.get('hard_count')
            ))

    conn.commit()

    print(f"\n✓ Restored {len(assignment_users_backup)} user assignments")
    print(f"✓ Restored {len(assignment_templates_backup)} template assignments")

    # Verify
    cursor.execute("SELECT COUNT(*) as count FROM exam_assignments")
    count = cursor.fetchone()[0]

    print("\n" + "=" * 70)
    print("FIX COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"✓ Table structure fixed (id is now PRIMARY KEY AUTOINCREMENT)")
    print(f"✓ Restored {len(valid_data)} valid assignments")
    print(f"✓ Deleted {len(corrupted_data)} corrupted assignments")
    print(f"✓ Total assignments in database: {count}")
    print("\nYou can now create new assignments and they will have proper IDs!")
    print("=" * 70)

if __name__ == "__main__":
    print("\n" + "⚠️  " * 15)
    print("WARNING: This script will fix the exam_assignments table structure.")
    print("Corrupted assignments (with NULL id) will be permanently deleted.")
    print("Valid assignments will be restored with new IDs.")
    print("⚠️  " * 15 + "\n")

    response = input("Do you want to continue? (yes/no): ")
    if response.lower() == 'yes':
        fix_exam_assignments_table()
    else:
        print("Operation cancelled.")
