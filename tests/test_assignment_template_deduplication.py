"""
Test and fix assignment template deduplication issues.

This script:
1. Identifies duplicate assignment_exam_templates entries
2. Removes duplicates, keeping only the most recent entry
3. Verifies the fix by showing before/after counts
"""

from sqlcipher3 import dbapi2 as sqlite3

DATABASE_PATH = "quiz_app.db"
DATABASE_ENCRYPTION_KEY = "QuizApp2025!AzErCoSmOs#SecureKey$Protected"


def get_db_connection():
    """Get an encrypted database connection."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.execute(f"PRAGMA key='{DATABASE_ENCRYPTION_KEY}'")
    conn.row_factory = sqlite3.Row
    return conn


def find_duplicates():
    """Find duplicate assignment_exam_templates entries."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT assignment_id, exam_id, COUNT(*) as count
            FROM assignment_exam_templates
            GROUP BY assignment_id, exam_id
            HAVING COUNT(*) > 1
            ORDER BY assignment_id, exam_id
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def get_assignment_details(assignment_id):
    """Get assignment details."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT id, assignment_name, created_at
            FROM exam_assignments
            WHERE id = ?
        """, (assignment_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def remove_duplicates():
    """Remove duplicate entries, keeping only the most recent (highest ID)."""
    conn = get_db_connection()
    try:
        duplicates = find_duplicates()
        
        if not duplicates:
            print("No duplicates found!")
            return 0
        
        total_removed = 0
        for dup in duplicates:
            assignment_id = dup['assignment_id']
            exam_id = dup['exam_id']
            count = dup['count']
            
            # Delete all but the most recent entry
            cursor = conn.execute("""
                DELETE FROM assignment_exam_templates
                WHERE assignment_id = ? AND exam_id = ?
                AND id NOT IN (
                    SELECT MAX(id)
                    FROM assignment_exam_templates
                    WHERE assignment_id = ? AND exam_id = ?
                )
            """, (assignment_id, exam_id, assignment_id, exam_id))
            
            removed = cursor.rowcount
            total_removed += removed

            assignment = get_assignment_details(assignment_id)
            assignment_name = assignment['assignment_name'] if assignment else '(deleted)'
            print(f"  Assignment #{assignment_id}: '{assignment_name}'")
            print(f"    Exam ID {exam_id}: Removed {removed} duplicate(s) (kept 1 of {count})")
        
        conn.commit()
        return total_removed
        
    finally:
        conn.close()


def verify_counts(assignment_ids):
    """Verify template counts after deduplication."""
    conn = get_db_connection()
    try:
        for assignment_id in assignment_ids:
            cursor = conn.execute("""
                WITH template_counts AS (
                    SELECT
                        assignment_id,
                        COUNT(*) as num_templates,
                        COUNT(DISTINCT exam_id) as num_unique_exams,
                        SUM(COALESCE(easy_count, 0)) AS total_easy,
                        SUM(COALESCE(medium_count, 0)) AS total_medium,
                        SUM(COALESCE(hard_count, 0)) AS total_hard,
                        SUM(COALESCE(easy_count, 0) + COALESCE(medium_count, 0) + COALESCE(hard_count, 0)) AS total_selected
                    FROM assignment_exam_templates
                    WHERE assignment_id = ?
                )
                SELECT
                    ea.id,
                    ea.assignment_name,
                    tc.num_templates,
                    tc.num_unique_exams,
                    tc.total_easy,
                    tc.total_medium,
                    tc.total_hard,
                    tc.total_selected
                FROM exam_assignments ea
                LEFT JOIN template_counts tc ON tc.assignment_id = ea.id
                WHERE ea.id = ?
            """, (assignment_id, assignment_id))
            
            row = cursor.fetchone()
            if row:
                print(f"\n  Assignment #{row['id']}: {row['assignment_name']}")
                print(f"    Templates: {row['num_templates'] or 0} (Unique exams: {row['num_unique_exams'] or 0})")
                print(f"    Questions: E:{row['total_easy'] or 0} + M:{row['total_medium'] or 0} + H:{row['total_hard'] or 0} = {row['total_selected'] or 0}")
    finally:
        conn.close()


def main():
    print("=" * 70)
    print("Assignment Template Deduplication Tool")
    print("=" * 70)
    print()
    
    # Step 1: Find duplicates
    print("Step 1: Checking for duplicates...")
    duplicates = find_duplicates()
    
    if not duplicates:
        print("✓ No duplicates found - database is clean!")
        return
    
    print(f"✗ Found {len(duplicates)} duplicate assignment-exam combinations\n")
    
    # Get unique assignment IDs
    affected_assignments = list(set([d['assignment_id'] for d in duplicates]))
    
    print(f"Affected assignments: {affected_assignments}")
    print()
    
    # Step 2: Remove duplicates
    print("Step 2: Removing duplicates...")
    total_removed = remove_duplicates()
    print(f"\n✓ Removed {total_removed} duplicate entries")
    print()
    
    # Step 3: Verify
    print("Step 3: Verifying counts after cleanup...")
    verify_counts(affected_assignments)
    
    print()
    print("=" * 70)
    print("✓ Deduplication complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
