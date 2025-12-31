#!/usr/bin/env python3
"""
ROOT CAUSE FIX: Add UNIQUE constraint to user_answers table to PREVENT duplicates

This script fixes the fundamental issue causing duplicate user_answers:
- The user_answers table was missing a UNIQUE constraint on (session_id, question_id)
- INSERT OR REPLACE only works with UNIQUE constraints or PRIMARY KEY matches
- Without the constraint, every save creates a NEW record instead of replacing

This script:
1. Removes any existing duplicate answers (keeping the latest)
2. Adds a UNIQUE index on (session_id, question_id)
3. Prevents future duplicates from being created

**This is the REAL fix - not just hiding duplicates in queries!**
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'quiz_app'))

from database.database import Database
from datetime import datetime

def main():
    print("="*80)
    print("ROOT CAUSE FIX: Add UNIQUE Constraint to user_answers")
    print("="*80)
    print()
    print("This will:")
    print("  1. Remove duplicate user_answers (keeping latest per session+question)")
    print("  2. Add UNIQUE constraint on (session_id, question_id)")
    print("  3. PREVENT future duplicates from being created")
    print()
    print("="*80)
    print()

    db = Database()

    # Step 1: Check if UNIQUE constraint already exists
    print("Step 1: Checking current database schema...")

    schema = db.execute_query("""
        SELECT sql FROM sqlite_master
        WHERE type='table' AND name='user_answers'
    """)

    if schema:
        table_sql = schema[0]['sql']
        print(f"Current schema:\n{table_sql}\n")

        if 'UNIQUE(session_id, question_id)' in table_sql or 'UNIQUE (session_id, question_id)' in table_sql:
            print("✅ UNIQUE constraint already exists on (session_id, question_id)")

            # Check for index as well
            index_check = db.execute_query("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='user_answers'
                AND sql LIKE '%session_id%question_id%'
            """)

            if index_check:
                print(f"✅ UNIQUE index also exists: {index_check[0]['name']}")
                print()
                print("No migration needed - constraint is already in place!")
                return
        else:
            print("❌ UNIQUE constraint is MISSING - this is why duplicates are created!")

    print()

    # Step 2: Find and remove duplicates
    print("Step 2: Cleaning duplicate answers...")

    duplicates = db.execute_query("""
        SELECT
            session_id,
            question_id,
            COUNT(*) as answer_count,
            GROUP_CONCAT(id ORDER BY answered_at DESC, id DESC) as answer_ids
        FROM user_answers
        GROUP BY session_id, question_id
        HAVING COUNT(*) > 1
    """)

    if duplicates:
        print(f"Found {len(duplicates)} duplicate pairs")
        total_dupes = sum(d['answer_count'] - 1 for d in duplicates)
        print(f"Total duplicate records to remove: {total_dupes}\n")

        removed_count = 0
        for dup in duplicates:
            # Keep the first ID (latest), remove the rest
            answer_ids = dup['answer_ids'].split(',')
            keep_id = answer_ids[0]
            remove_ids = answer_ids[1:]

            for remove_id in remove_ids:
                db.execute_update("DELETE FROM user_answers WHERE id = ?", (int(remove_id),))
                removed_count += 1

        print(f"✅ Removed {removed_count} duplicate answers")
    else:
        print("✅ No duplicates found - database is clean")

    print()

    # Step 3: Add UNIQUE constraint
    print("Step 3: Adding UNIQUE constraint to prevent future duplicates...")

    try:
        # SQLite doesn't support ALTER TABLE ADD CONSTRAINT directly
        # We need to create a UNIQUE INDEX instead
        db.execute_update("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_user_answers_session_question
            ON user_answers(session_id, question_id)
        """)

        print("✅ UNIQUE index created successfully!")
        print()

        # Verify the index was created
        verification = db.execute_query("""
            SELECT name, sql FROM sqlite_master
            WHERE type='index' AND tbl_name='user_answers'
            AND name='idx_user_answers_session_question'
        """)

        if verification:
            print("Verification:")
            print(f"  Index name: {verification[0]['name']}")
            print(f"  Index SQL: {verification[0]['sql']}")

    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            print("❌ Error: Still have duplicate records!")
            print("   Re-run this script to clean them up first.")
        else:
            print(f"❌ Error creating index: {e}")
        return

    print()
    print("="*80)
    print("✅ ROOT CAUSE FIX COMPLETE")
    print("="*80)
    print()
    print("What was fixed:")
    print("  ❌ BEFORE: user_answers had NO unique constraint")
    print("     → INSERT OR REPLACE always created new records")
    print("     → Every answer save = new database row = DUPLICATES")
    print()
    print("  ✅ AFTER: UNIQUE index on (session_id, question_id)")
    print("     → INSERT OR REPLACE replaces existing record")
    print("     → Every answer save = update same row = NO DUPLICATES")
    print()
    print("Future duplicates will now be PREVENTED at the database level!")
    print(f"Migration completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == '__main__':
    main()
