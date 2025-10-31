import sqlite3
import os

def delete_topics():
    db_path = os.path.join(os.path.dirname(__file__), 'quiz_app.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Topics to delete
    topic_names = ['Fizika', 'Astronomiya', 'Programlaşdırma', 'Məntiq', 'Peyk mühəndisliyi', 'Telekomunikasiya']

    # Get exam IDs
    placeholders = ','.join(['?' for _ in topic_names])
    cursor.execute(f"SELECT id, title FROM exams WHERE title IN ({placeholders})", topic_names)
    exams_to_delete = cursor.fetchall()

    if not exams_to_delete:
        print("No exams found to delete!")
        conn.close()
        return

    print("Found the following exams to delete:")
    for exam_id, title in exams_to_delete:
        print(f"  - {title} (ID: {exam_id})")

    exam_ids = [exam[0] for exam in exams_to_delete]
    exam_placeholders = ','.join(['?' for _ in exam_ids])

    # Delete question_options first (foreign key constraint)
    cursor.execute(f"""
        DELETE FROM question_options
        WHERE question_id IN (
            SELECT id FROM questions WHERE exam_id IN ({exam_placeholders})
        )
    """, exam_ids)
    deleted_options = cursor.rowcount

    # Delete questions
    cursor.execute(f"DELETE FROM questions WHERE exam_id IN ({exam_placeholders})", exam_ids)
    deleted_questions = cursor.rowcount

    # Delete exams
    cursor.execute(f"DELETE FROM exams WHERE id IN ({exam_placeholders})", exam_ids)
    deleted_exams = cursor.rowcount

    conn.commit()

    print("\n" + "="*60)
    print("DELETION COMPLETE!")
    print("="*60)
    print(f"Deleted {deleted_exams} exams")
    print(f"Deleted {deleted_questions} questions")
    print(f"Deleted {deleted_options} question options")
    print("="*60)

    conn.close()

if __name__ == "__main__":
    delete_topics()
