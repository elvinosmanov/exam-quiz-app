import sqlite3
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from quiz_app.config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_single(self, query: str, params: tuple = ()) -> Optional[Dict]:
        result = self.execute_query(query, params)
        return result[0] if result else None
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount

# Database schema creation
def create_tables():
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'examinee',
                department TEXT,
                employee_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Exams table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                duration_minutes INTEGER NOT NULL DEFAULT 60,
                passing_score REAL NOT NULL DEFAULT 70.0,
                max_attempts INTEGER DEFAULT 1,
                randomize_questions BOOLEAN DEFAULT 0,
                show_results BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Add category column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN category TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Add security settings columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN enable_fullscreen BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN prevent_focus_loss BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN enable_logging BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN enable_pattern_analysis BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        # Add question pool columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN use_question_pool BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN total_questions_in_pool INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN questions_to_select INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN easy_questions_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN medium_questions_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute('ALTER TABLE exams ADD COLUMN hard_questions_count INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        # Ensure PDF variant count column exists on exam assignments
        try:
            cursor.execute('ALTER TABLE exam_assignments ADD COLUMN pdf_variant_count INTEGER DEFAULT 1')
        except sqlite3.OperationalError:
            pass
        
        # Questions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                image_path TEXT,
                correct_answer TEXT,
                explanation TEXT,
                points REAL DEFAULT 1.0,
                difficulty_level TEXT DEFAULT 'medium',
                order_index INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            )
        ''')
        
        # Question options table (for multiple choice questions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                option_text TEXT NOT NULL,
                is_correct BOOLEAN DEFAULT 0,
                order_index INTEGER,
                FOREIGN KEY (question_id) REFERENCES questions (id)
            )
        ''')
        
        # Exam sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration_seconds INTEGER,
                score REAL,
                total_questions INTEGER,
                correct_answers INTEGER,
                status TEXT DEFAULT 'in_progress',
                attempt_number INTEGER DEFAULT 1,
                ip_address TEXT,
                user_agent TEXT,
                is_completed BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            )
        ''')
        
        # User answers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                answer_text TEXT,
                selected_option_id INTEGER,
                selected_option_ids TEXT,
                is_correct BOOLEAN,
                points_earned REAL DEFAULT 0,
                time_spent_seconds INTEGER,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES exam_sessions (id),
                FOREIGN KEY (question_id) REFERENCES questions (id),
                FOREIGN KEY (selected_option_id) REFERENCES question_options (id)
            )
        ''')
        
        # Add selected_option_ids column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE user_answers ADD COLUMN selected_option_ids TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Session questions table (tracks which questions were selected for each exam session)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                difficulty_level TEXT NOT NULL,
                order_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES exam_sessions (id),
                FOREIGN KEY (question_id) REFERENCES questions (id),
                UNIQUE(session_id, question_id)
            )
        ''')
        
        # Exam permissions table (for user-specific exam access)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (exam_id) REFERENCES exams (id),
                FOREIGN KEY (granted_by) REFERENCES users (id),
                UNIQUE(user_id, exam_id)
            )
        ''')
        
        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # PDF exports table (for tracking variant exports)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pdf_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                variant_number INTEGER NOT NULL,
                question_snapshot TEXT NOT NULL,
                exported_by INTEGER NOT NULL,
                exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                notes TEXT,
                FOREIGN KEY (exam_id) REFERENCES exams (id),
                FOREIGN KEY (exported_by) REFERENCES users (id),
                UNIQUE(exam_id, variant_number)
            )
        ''')

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_sessions_user_exam ON exam_sessions(user_id, exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_answers_session ON user_answers(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_question_options_question ON question_options(question_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_questions_session ON session_questions(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_exports_exam ON pdf_exports(exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_exports_variant ON pdf_exports(exam_id, variant_number)')

        conn.commit()

def create_default_admin():
    """Create default admin user if none exists"""
    import bcrypt
    
    db = Database()
    
    # Check if admin exists
    admin = db.execute_single("SELECT id FROM users WHERE role = 'admin'")
    
    if not admin:
        # Create default admin
        password = "admin123"  # Change this in production
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        db.execute_insert('''
            INSERT INTO users (username, email, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin', 'admin@example.com', password_hash, 'System Administrator', 'admin', 1))
        
        print("Default admin user created:")
        print("Username: admin")
        print("Password: admin123")
        print("Please change the password after first login!")

def init_database():
    """Initialize the database with tables and default data"""
    create_tables()
    create_default_admin()
    print(f"Database initialized at: {DATABASE_PATH}")

if __name__ == "__main__":
    init_database()
