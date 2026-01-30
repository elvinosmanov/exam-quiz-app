"""
Database Cleanup Script - Remove Duplicate User Answers
This script fixes the issue where graded exams still appear in the grading section
because old duplicate answer records exist with NULL points_earned.

WHAT THIS SCRIPT DOES:
1. Finds all duplicate user_answers records (same session_id + question_id)
2. Keeps ONLY the LATEST answer (based on answered_at timestamp)
3. Deletes old duplicate answers that are causing the grading issue

SAFE TO RUN: This script only deletes old duplicates, not the current answers!
"""

# Use SQLCipher for encrypted database (same as main app)
try:
    from sqlcipher3 import dbapi2 as sqlite3
    ENCRYPTION_ENABLED = True
except ImportError:
    import sqlite3
    ENCRYPTION_ENABLED = False
    print("WARNING: sqlcipher3-wheels not installed. Database encryption disabled!")

import sys
import os

# Database encryption key (must match database.py)
DATABASE_ENCRYPTION_KEY = "QuizApp2025!AzErCoSmOs#SecureKey$Protected"

# Get the correct database path
def get_database_path():
    """Get the database path - same logic as config.py"""
    if getattr(sys, 'frozen', False):
        # Running as packaged executable
        data_dir = os.path.dirname(sys.executable)
    else:
        # Development mode
        data_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(data_dir, 'quiz_app.db')

def cleanup_duplicate_answers():
    """Remove duplicate user answers, keeping only the latest one"""

    db_path = get_database_path()
    print(f"Database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")

    if not os.path.exists(db_path):
        print("ERROR: Database file not found!")
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Apply encryption key if SQLCipher is enabled
        if ENCRYPTION_ENABLED:
            conn.execute(f"PRAGMA key='{DATABASE_ENCRYPTION_KEY}'")
            # Verify database is accessible
            try:
                conn.execute("SELECT count(*) FROM sqlite_master")
                print("✅ Database decrypted successfully")
            except sqlite3.DatabaseError as e:
                print(f"❌ ERROR: Unable to decrypt database: {e}")
                print("The encryption key may be incorrect.")
                conn.close()
                return False

        cursor = conn.cursor()

        print("\n" + "="*80)
        print("STEP 1: Finding duplicate user_answers records...")
        print("="*80)

        # Find all duplicates (same session_id + question_id)
        cursor.execute("""
            SELECT session_id, question_id, COUNT(*) as count
            FROM user_answers
            GROUP BY session_id, question_id
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        """)

        duplicates = cursor.fetchall()

        if not duplicates:
            print("✅ No duplicate answers found! Database is clean.")
            conn.close()
            return True

        print(f"\n⚠️  Found {len(duplicates)} question(s) with duplicate answers:")
        print(f"{'Session ID':<12} {'Question ID':<12} {'Count':<8}")
        print("-" * 35)
        for dup in duplicates[:20]:  # Show first 20
            print(f"{dup['session_id']:<12} {dup['question_id']:<12} {dup['count']:<8}")

        if len(duplicates) > 20:
            print(f"... and {len(duplicates) - 20} more")

        print("\n" + "="*80)
        print("STEP 2: Analyzing which answers to keep vs delete...")
        print("="*80)

        total_to_delete = 0

        # For each duplicate, find which records to delete (keep only the latest)
        for dup in duplicates:
            session_id = dup['session_id']
            question_id = dup['question_id']

            # Get all answers for this session + question
            cursor.execute("""
                SELECT id, answered_at, points_earned, is_correct
                FROM user_answers
                WHERE session_id = ? AND question_id = ?
                ORDER BY answered_at DESC, id DESC
            """, (session_id, question_id))

            answers = cursor.fetchall()

            if len(answers) > 1:
                # Keep the first one (latest), delete the rest
                keep_answer = answers[0]
                delete_answers = answers[1:]

                print(f"\nSession {session_id}, Question {question_id}:")
                print(f"  ✅ KEEP: ID={keep_answer['id']}, Date={keep_answer['answered_at']}, Points={keep_answer['points_earned']}")

                for ans in delete_answers:
                    print(f"  ❌ DELETE: ID={ans['id']}, Date={ans['answered_at']}, Points={ans['points_earned']}")
                    total_to_delete += 1

        print("\n" + "="*80)
        print(f"STEP 3: Ready to delete {total_to_delete} old duplicate answers")
        print("="*80)

        # Ask for confirmation
        print(f"\n⚠️  This will delete {total_to_delete} old duplicate answer records.")
        print("The LATEST answer for each question will be kept.")

        response = input("\nDo you want to proceed? (yes/no): ").strip().lower()

        if response != 'yes':
            print("\n❌ Cleanup cancelled. No changes made.")
            conn.close()
            return False

        # Perform the cleanup
        deleted_count = 0

        for dup in duplicates:
            session_id = dup['session_id']
            question_id = dup['question_id']

            # Delete all but the latest answer
            cursor.execute("""
                DELETE FROM user_answers
                WHERE session_id = ? AND question_id = ?
                AND id NOT IN (
                    SELECT id FROM user_answers
                    WHERE session_id = ? AND question_id = ?
                    ORDER BY answered_at DESC, id DESC
                    LIMIT 1
                )
            """, (session_id, question_id, session_id, question_id))

            deleted_count += cursor.rowcount

        # Commit the changes
        conn.commit()

        print("\n" + "="*80)
        print("CLEANUP COMPLETED!")
        print("="*80)
        print(f"✅ Deleted {deleted_count} duplicate answer records")
        print(f"✅ Kept the latest answer for each question")
        print("\n🎉 Database is now clean!")
        print("\n💡 Restart your application to see the changes.")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ ERROR during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*80)
    print("DATABASE CLEANUP TOOL - Remove Duplicate User Answers")
    print("="*80)
    print("\nThis will fix the issue where graded exams still appear in grading section.")
    print("\n⚠️  IMPORTANT: Close your application before running this script!")

    response = input("\nIs your application closed? (yes/no): ").strip().lower()

    if response != 'yes':
        print("\n❌ Please close your application first, then run this script again.")
        sys.exit(1)

    success = cleanup_duplicate_answers()

    if success:
        print("\n✅ SUCCESS! You can now restart your application.")
        print("\nThe graded exams should now appear in the 'Completed' section.")
    else:
        print("\n❌ Cleanup failed. Please check the errors above.")

    input("\nPress Enter to exit...")
