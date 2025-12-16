#!/usr/bin/env python3
"""
Fix assignment_users table structure
======================================

This script fixes the assignment_users table which lost its PRIMARY KEY constraint.
"""

from quiz_app.database.database import Database

def fix_assignment_users():
    """Fix the assignment_users table structure"""

    print("=" * 70)
    print("FIX ASSIGNMENT_USERS TABLE")
    print("=" * 70)

    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Step 1: Backup data
    print("[1/4] Backing up data...")
    cursor.execute("SELECT * FROM assignment_users")
    backup_data = [dict(row) for row in cursor.fetchall()]
    print(f"  Backed up {len(backup_data)} records")

    # Step 2: Drop and recreate table
    print("\n[2/4] Recreating table with correct structure...")
    cursor.execute("DROP TABLE IF EXISTS assignment_users")
    cursor.execute('''
        CREATE TABLE assignment_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            granted_by INTEGER,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            UNIQUE(assignment_id, user_id),
            FOREIGN KEY (assignment_id) REFERENCES exam_assignments (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (granted_by) REFERENCES users (id)
        )
    ''')
    print("  ✓ Table recreated")

    # Step 3: Restore data
    print("\n[3/4] Restoring data...")
    restored = 0
    skipped = 0
    for row in backup_data:
        # Skip records with NULL assignment_id or user_id
        if row.get('assignment_id') is None or row.get('user_id') is None:
            skipped += 1
            continue

        try:
            cursor.execute('''
                INSERT INTO assignment_users (assignment_id, user_id, granted_by, granted_at, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                row['assignment_id'],
                row['user_id'],
                row.get('granted_by'),
                row.get('granted_at'),
                1  # Default is_active to 1
            ))
            restored += 1
        except Exception as e:
            print(f"  Skipped record: {e}")
            skipped += 1

    conn.commit()
    print(f"  ✓ Restored {restored} valid records")
    print(f"  ⚠ Skipped {skipped} invalid records")

    # Step 4: Verify
    print("\n[4/4] Verifying...")
    cursor.execute("PRAGMA table_info(assignment_users)")
    columns = cursor.fetchall()
    id_col = [dict(c) for c in columns if c[1] == 'id'][0]

    if id_col['pk'] == 1:
        print("  ✓ 'id' is now a PRIMARY KEY")
    else:
        print("  ✗ ERROR: 'id' is still not a PRIMARY KEY")

    cursor.execute("SELECT COUNT(*) as count FROM assignment_users")
    count = cursor.fetchone()[0]

    print("\n" + "=" * 70)
    print("FIX COMPLETED!")
    print("=" * 70)
    print(f"✓ Table structure fixed")
    print(f"✓ {count} records in table")
    print("=" * 70)

if __name__ == "__main__":
    fix_assignment_users()
