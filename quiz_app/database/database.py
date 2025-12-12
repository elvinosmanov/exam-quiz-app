import sqlite3
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from quiz_app.config import DATABASE_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_PATH
        
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

    @staticmethod
    def _validate_identifier(name: str):
        if not name or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
                           for ch in name):
            raise ValueError(f"Invalid identifier: {name}")

    def _column_exists(self, table: str, column: str) -> bool:
        self._validate_identifier(table)
        self._validate_identifier(column)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            return any(row[1] == column for row in cursor.fetchall())

    def ensure_column_exists(self, table: str, column: str, definition: str) -> bool:
        """
        Guarantee that a column exists on a table, adding it if missing.

        Returns:
            bool: True if the column was added, False if it already existed.
        """
        if self._column_exists(table, column):
            return False

        if not definition or not definition.strip():
            raise ValueError("Column definition must be provided")

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                conn.commit()
            logger.info("Added missing column %s.%s", table, column)
            return True
        except sqlite3.OperationalError as exc:
            logger.error("Failed to add column %s.%s: %s", table, column, exc)
            raise

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
                section TEXT,
                unit TEXT,
                employee_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                password_change_required BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Add section and unit columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN section TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN unit TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN language_preference TEXT DEFAULT "en"')
        except sqlite3.OperationalError:
            # Column already exists
            pass

        # Set default language preference for existing users who don't have it
        try:
            cursor.execute('UPDATE users SET language_preference = "en" WHERE language_preference IS NULL')
            conn.commit()
        except:
            pass

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
                assignment_id INTEGER,
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
                is_active BOOLEAN DEFAULT 1,
                email_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (exam_id) REFERENCES exams (id),
                FOREIGN KEY (assignment_id) REFERENCES exam_assignments (id) ON DELETE CASCADE
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

        # Exam observers table (experts allowed to view specific topics)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_observers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                observer_id INTEGER NOT NULL,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_id) REFERENCES exams (id),
                FOREIGN KEY (observer_id) REFERENCES users (id),
                FOREIGN KEY (granted_by) REFERENCES users (id),
                UNIQUE(exam_id, observer_id)
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

        # Email templates table (for customizable email notifications)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_type TEXT NOT NULL,
                language TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_template TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(template_type, language)
            )
        ''')

        # Email log table (for tracking email notifications)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT,
                sent_by INTEGER NOT NULL,
                email_type TEXT NOT NULL,
                language TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES exam_sessions (id),
                FOREIGN KEY (sent_by) REFERENCES users (id)
            )
        ''')

        # Exam Preset Templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_preset_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by_user_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id)
            )
        ''')

        # Add is_active column to exam_preset_templates if it doesn't exist
        db.ensure_column_exists('exam_preset_templates', 'is_active', 'BOOLEAN DEFAULT 1')

        # Junction table for preset templates and exam topics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preset_template_exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                easy_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                hard_count INTEGER DEFAULT 0,
                FOREIGN KEY (template_id) REFERENCES exam_preset_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
                UNIQUE(template_id, exam_id)
            )
        ''')

        # Preset Observers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preset_observers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preset_id INTEGER NOT NULL,
                observer_id INTEGER NOT NULL,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (preset_id) REFERENCES exam_preset_templates (id) ON DELETE CASCADE,
                FOREIGN KEY (observer_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (granted_by) REFERENCES users (id),
                UNIQUE(preset_id, observer_id)
            )
        ''')

        # Exam Assignments table (allows same exam to be assigned multiple times with different settings)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                assignment_name TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                passing_score REAL NOT NULL,
                max_attempts INTEGER DEFAULT 1,
                randomize_questions BOOLEAN DEFAULT 0,
                show_results BOOLEAN DEFAULT 1,
                enable_fullscreen BOOLEAN DEFAULT 0,
                prevent_focus_loss BOOLEAN DEFAULT 0,
                enable_logging BOOLEAN DEFAULT 0,
                enable_pattern_analysis BOOLEAN DEFAULT 0,
                use_question_pool BOOLEAN DEFAULT 0,
                questions_to_select INTEGER DEFAULT 0,
                easy_questions_count INTEGER DEFAULT 0,
                medium_questions_count INTEGER DEFAULT 0,
                hard_questions_count INTEGER DEFAULT 0,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                deadline TIMESTAMP,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_archived BOOLEAN DEFAULT 0,
                pdf_variant_count INTEGER DEFAULT 1,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')

        # Assignment Users junction table (tracks which users have access to which assignments)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignment_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (assignment_id) REFERENCES exam_assignments (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (granted_by) REFERENCES users (id),
                UNIQUE(assignment_id, user_id)
            )
        ''')

        # Assignment Exam Templates junction table (supports multiple exam templates per assignment)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignment_exam_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                exam_id INTEGER NOT NULL,
                order_index INTEGER DEFAULT 0,
                easy_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                hard_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assignment_id) REFERENCES exam_assignments (id) ON DELETE CASCADE,
                FOREIGN KEY (exam_id) REFERENCES exams (id) ON DELETE CASCADE,
                UNIQUE(assignment_id, exam_id)
            )
        ''')

        # System Settings table (for application-wide settings)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Insert default language setting if not exists
        cursor.execute('''
            INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description)
            VALUES ('language', 'English', 'System-wide language setting')
        ''')

        # Organizational Structure table (departments, sections, units)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS organizational_structure (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('department', 'section', 'unit')),
                name_az TEXT NOT NULL,
                name_en TEXT NOT NULL,
                abbr_az TEXT NOT NULL,
                abbr_en TEXT NOT NULL,
                parent_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_key) REFERENCES organizational_structure(key) ON DELETE CASCADE
            )
        ''')

        # Pattern Analysis table (stub for backward compatibility - feature deprecated)
        # This table is no longer actively used but kept for backward compatibility with legacy code
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                suspicion_score INTEGER DEFAULT 0,
                details TEXT,
                issues_detected TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES exam_sessions (id)
            )
        ''')

        # Add language_preference column to users table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN language_preference TEXT DEFAULT 'en'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_sessions_user_exam ON exam_sessions(user_id, exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_sessions_assignment ON exam_sessions(assignment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_answers_session ON user_answers(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_question_options_question ON question_options(question_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_questions_session ON session_questions(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_exports_exam ON pdf_exports(exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdf_exports_variant ON pdf_exports(exam_id, variant_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_templates_type_lang ON email_templates(template_type, language)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_log_session ON email_log(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_log_sent_by ON email_log(sent_by)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_observers_exam ON exam_observers(exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_observers_observer ON exam_observers(observer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_assignments_exam ON exam_assignments(exam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignment_users_assignment ON assignment_users(assignment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignment_users_user ON assignment_users(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignment_exam_templates_assignment ON assignment_exam_templates(assignment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(setting_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_organizational_structure_key ON organizational_structure(key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_organizational_structure_type ON organizational_structure(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_organizational_structure_parent ON organizational_structure(parent_key)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_analysis_session ON pattern_analysis(session_id)')

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

    # Run organizational structure migration
    try:
        from quiz_app.database.migration_organizational_structure import run_migration
        db = Database()
        run_migration(db)
    except Exception as e:
        print(f"Warning: Organizational structure migration failed: {e}")

    print(f"Database initialized at: {DATABASE_PATH}")

if __name__ == "__main__":
    init_database()
