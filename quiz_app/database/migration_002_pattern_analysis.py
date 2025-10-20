"""
Database migration: Add pattern_analysis table for detecting suspicious exam behavior
"""

import sqlite3

def migrate(conn: sqlite3.Connection):
    """Add pattern_analysis table"""
    cursor = conn.cursor()

    # Create pattern_analysis table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pattern_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            analyzed_at TEXT NOT NULL,
            suspicion_score INTEGER DEFAULT 0,
            issues_detected TEXT,
            details TEXT,
            reviewed_by INTEGER,
            reviewed_at TEXT,
            review_notes TEXT,
            FOREIGN KEY (session_id) REFERENCES exam_sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id)
        )
    """)

    print("[MIGRATION] Created pattern_analysis table")
    conn.commit()

if __name__ == "__main__":
    # Test migration
    conn = sqlite3.connect("../../quiz_app.db")
    migrate(conn)
    conn.close()
    print("[MIGRATION] Pattern analysis migration completed successfully")
