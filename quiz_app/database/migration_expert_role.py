"""
Migration: Add Expert Role Support
- Adds 'expert' to role validation
- Ensures department and unit fields exist
- Creates indexes for performance
- Handles existing expert users (if any)
"""

import sqlite3
import os
from quiz_app.config import DATABASE_PATH

def migrate():
    """Run the migration"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        print("[MIGRATION] Starting expert role migration...")

        # 1. Ensure department field exists
        print("[MIGRATION] Checking department field...")
        try:
            cursor.execute("SELECT department FROM users LIMIT 1")
            print("✓ department field exists")
        except sqlite3.OperationalError:
            print("[MIGRATION] Adding department field...")
            cursor.execute('ALTER TABLE users ADD COLUMN department TEXT DEFAULT NULL')
            print("✓ department field added")

        # 2. Ensure unit field exists
        print("[MIGRATION] Checking unit field...")
        try:
            cursor.execute("SELECT unit FROM users LIMIT 1")
            print("✓ unit field exists")
        except sqlite3.OperationalError:
            print("[MIGRATION] Adding unit field...")
            cursor.execute('ALTER TABLE users ADD COLUMN unit TEXT DEFAULT NULL')
            print("✓ unit field added")

        # 3. Update role validation (SQLite doesn't have enum, using check constraint)
        # Note: SQLite doesn't easily support modifying constraints,
        # so we'll handle validation in application layer
        print("[MIGRATION] Role validation will be handled in application layer")
        print("✓ Roles supported: admin, expert, examinee")

        # 4. Create indexes for performance
        print("[MIGRATION] Creating indexes...")

        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_department ON users(department)')
            print("✓ Created index on users.department")
        except sqlite3.OperationalError as e:
            print(f"⚠ Index on department may already exist: {e}")

        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_unit ON users(unit)')
            print("✓ Created index on users.unit")
        except sqlite3.OperationalError as e:
            print(f"⚠ Index on unit may already exist: {e}")

        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_dept_unit ON users(department, unit)')
            print("✓ Created composite index on users(department, unit)")
        except sqlite3.OperationalError as e:
            print(f"⚠ Composite index may already exist: {e}")

        # 5. Check for existing expert users
        print("[MIGRATION] Checking for existing expert users...")
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE role = 'expert'")
        expert_count = cursor.fetchone()[0]

        if expert_count > 0:
            print(f"⚠ Found {expert_count} existing expert user(s)")
            print("⚠ These users may need department/unit assignment")
            print("⚠ You can update them via User Management interface")

            # List existing experts
            cursor.execute("SELECT id, username, full_name, department, unit FROM users WHERE role = 'expert'")
            experts = cursor.fetchall()
            for expert in experts:
                dept_status = expert[3] if expert[3] else "NOT SET"
                unit_status = expert[4] if expert[4] else "NOT SET"
                print(f"  - {expert[2]} (username: {expert[1]}) - Dept: {dept_status}, Unit: {unit_status}")
        else:
            print("✓ No existing expert users found")

        # 6. Commit changes
        conn.commit()
        print("\n✅ Expert role migration completed successfully!")
        print("\nNext steps:")
        print("1. Create expert users via User Management")
        print("2. Assign department and unit to each expert")
        print("3. Experts will see content from their unit only")

        return True

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        conn.close()

def rollback():
    """Rollback the migration"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        print("[ROLLBACK] Starting rollback of expert role migration...")

        # Drop indexes
        print("[ROLLBACK] Dropping indexes...")
        cursor.execute('DROP INDEX IF EXISTS idx_users_department')
        cursor.execute('DROP INDEX IF EXISTS idx_users_unit')
        cursor.execute('DROP INDEX IF EXISTS idx_users_dept_unit')
        print("✓ Indexes dropped")

        # Note: Cannot easily remove columns in SQLite
        print("⚠ Note: department and unit columns will remain (SQLite limitation)")
        print("⚠ They will simply not be used")

        conn.commit()
        print("\n✅ Rollback completed!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Rollback failed: {e}")
        raise

    finally:
        conn.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback()
    else:
        migrate()
