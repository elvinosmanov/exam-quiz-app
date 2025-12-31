#!/usr/bin/env python3
"""
Cleanup script to remove duplicate user_answers from the database.

This script identifies and removes duplicate answer entries for the same
question in the same exam session, keeping only the latest answer.

CRITICAL FIX: Resolves the grading interface duplication issue where
5 questions would show up as 25+ entries due to duplicate user_answers.
"""

import sys
sys.path.insert(0, 'quiz_app')

from database.database import Database
from datetime import datetime

def main():
    print("="*80)
    print("DUPLICATE ANSWERS CLEANUP SCRIPT")
    print("="*80)
    print()

    db = Database()

    # Step 1: Find all duplicate answers
    print("Step 1: Identifying duplicate answers...")
    duplicates = db.execute_query("""
        SELECT
            session_id,
            question_id,
            COUNT(*) as answer_count,
            GROUP_CONCAT(id ORDER BY answered_at DESC, id DESC) as answer_ids
        FROM user_answers
        GROUP BY session_id, question_id
        HAVING COUNT(*) > 1
        ORDER BY answer_count DESC
    """)

    if not duplicates:
        print("✅ No duplicate answers found! Database is clean.")
        return

    print(f"Found {len(duplicates)} question-session pairs with duplicates:")
    print()

    total_duplicates = sum(d['answer_count'] - 1 for d in duplicates)
    total_to_keep = len(duplicates)

    print(f"  Total duplicate entries to remove: {total_duplicates}")
    print(f"  Latest answers to keep: {total_to_keep}")
    print()

    # Show details
    for i, dup in enumerate(duplicates[:10], 1):
        session = db.execute_single(
            "SELECT id, user_id FROM exam_sessions WHERE id = ?",
            (dup['session_id'],)
        )
        user = db.execute_single(
            "SELECT full_name FROM users WHERE id = ?",
            (session['user_id'],)
        ) if session else None

        answer_ids = dup['answer_ids'].split(',')
        keep_id = answer_ids[0]  # First one (latest by ORDER BY)
        remove_ids = answer_ids[1:]

        print(f"  {i}. Session {dup['session_id']} - {user['full_name'] if user else 'Unknown'}")
        print(f"     Question {dup['question_id']}: {dup['answer_count']} answers")
        print(f"     Keep: {keep_id}, Remove: {', '.join(remove_ids)}")

    if len(duplicates) > 10:
        print(f"     ... and {len(duplicates) - 10} more")

    print()
    print("="*80)

    # Ask for confirmation
    response = input("⚠️  Proceed with cleanup? This will DELETE duplicate answers! (yes/no): ").strip().lower()

    if response != 'yes':
        print("❌ Cleanup cancelled.")
        return

    print()
    print("Step 2: Removing duplicate answers...")

    removed_count = 0
    errors = 0

    for dup in duplicates:
        try:
            # Get all answer IDs for this session-question pair
            answer_ids = dup['answer_ids'].split(',')

            # Keep the first one (latest), remove the rest
            keep_id = answer_ids[0]
            remove_ids = answer_ids[1:]

            # Delete the duplicates
            for remove_id in remove_ids:
                db.execute_update(
                    "DELETE FROM user_answers WHERE id = ?",
                    (int(remove_id),)
                )
                removed_count += 1

            # Verify only one answer remains
            remaining = db.execute_single("""
                SELECT COUNT(*) as count
                FROM user_answers
                WHERE session_id = ? AND question_id = ?
            """, (dup['session_id'], dup['question_id']))

            if remaining['count'] != 1:
                print(f"⚠️  Warning: Session {dup['session_id']}, Question {dup['question_id']} has {remaining['count']} answers (expected 1)")
                errors += 1

        except Exception as e:
            print(f"❌ Error processing session {dup['session_id']}, question {dup['question_id']}: {e}")
            errors += 1

    print()
    print("="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print(f"✅ Removed {removed_count} duplicate answers")
    if errors > 0:
        print(f"⚠️  {errors} errors encountered")
    else:
        print("✅ No errors!")
    print()

    # Verify cleanup
    print("Verification: Checking for remaining duplicates...")
    remaining_duplicates = db.execute_query("""
        SELECT
            COUNT(*) as count
        FROM (
            SELECT session_id, question_id
            FROM user_answers
            GROUP BY session_id, question_id
            HAVING COUNT(*) > 1
        )
    """)

    if remaining_duplicates and remaining_duplicates[0]['count'] > 0:
        print(f"⚠️  Warning: {remaining_duplicates[0]['count']} duplicates still remain!")
    else:
        print("✅ Database is now clean - no duplicate answers found!")

    print()
    print(f"Cleanup completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == '__main__':
    main()
