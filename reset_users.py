#!/usr/bin/env python3
"""
Database Users Reset Script

This script allows you to safely delete all users from the database.
Use with caution - this will remove ALL user accounts!
"""

import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'quiz_app'))

from database.database import Database

def main():
    db = Database()

    print("="*80)
    print("DATABASE USERS RESET")
    print("="*80)
    print()

    # Get current user count
    current_users = db.execute_query("SELECT COUNT(*) as count FROM users")
    user_count = current_users[0]['count']

    print(f"Current users in database: {user_count}")

    if user_count == 0:
        print("✅ Database is already empty - no users to delete.")
        return

    print()

    # Show all current users
    all_users = db.execute_query("""
        SELECT id, username, full_name, role, email
        FROM users
        ORDER BY id
    """)

    print("Current users:")
    print("-" * 80)
    print(f"{'ID':<5} {'Username':<20} {'Full Name':<25} {'Role':<15} {'Email':<30}")
    print("-" * 80)
    for user in all_users:
        print(f"{user['id']:<5} {user['username']:<20} {user['full_name']:<25} {user['role']:<15} {user.get('email', 'N/A'):<30}")
    print("-" * 80)

    print()
    print("⚠️  WARNING: This will DELETE ALL USERS from the database!")
    print("⚠️  This action CANNOT be undone!")
    print()

    response = input("Do you want to DELETE ALL USERS? (type 'YES DELETE ALL' to confirm): ")

    if response == "YES DELETE ALL":
        print()
        print("Deleting users...")

        try:
            # Delete all users
            db.execute_update("DELETE FROM users")
            print("✅ All users deleted successfully!")

            # Verify
            remaining = db.execute_query("SELECT COUNT(*) as count FROM users")
            print(f"✅ Remaining users: {remaining[0]['count']}")

            # Also clean up related data
            print()
            print("Cleaning up related data...")

            # Delete exam sessions
            db.execute_update("DELETE FROM exam_sessions")
            print("✅ Deleted all exam sessions")

            # Delete user answers
            db.execute_update("DELETE FROM user_answers")
            print("✅ Deleted all user answers")

            # Delete student assignments
            db.execute_update("DELETE FROM student_assignments")
            print("✅ Deleted all student assignments")

            print()
            print("✅ Database reset complete!")

        except Exception as e:
            print(f"❌ Error during deletion: {e}")
            import traceback
            traceback.print_exc()
    else:
        print()
        print("❌ User deletion cancelled.")
        print(f"   You entered: '{response}'")
        print("   Required: 'YES DELETE ALL'")

    print("="*80)

if __name__ == '__main__':
    main()
