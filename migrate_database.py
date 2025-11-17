"""
Database Migration Script
Adds 'section' and 'unit' columns to users table if they don't exist
"""

import sqlite3
import os

# Path to database
DB_PATH = 'quiz_app.db'

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_database():
    """Add missing columns to users table"""
    if not os.path.exists(DB_PATH):
        print(f"Database file not found: {DB_PATH}")
        print("Please run the application first to create the database.")
        return False

    print(f"Migrating database: {DB_PATH}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check and add 'section' column
        if not check_column_exists(cursor, 'users', 'section'):
            print("Adding 'section' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN section TEXT")
            print("✓ Added 'section' column")
        else:
            print("✓ 'section' column already exists")

        # Check and add 'unit' column
        if not check_column_exists(cursor, 'users', 'unit'):
            print("Adding 'unit' column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN unit TEXT")
            print("✓ Added 'unit' column")
        else:
            print("✓ 'unit' column already exists")

        conn.commit()
        conn.close()

        print("\n✓ Database migration completed successfully!")
        return True

    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Database Migration Tool")
    print("=" * 50)
    print()

    success = migrate_database()

    print()
    input("Press Enter to exit...")
