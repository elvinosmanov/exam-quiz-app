import bcrypt
from typing import Optional, Dict
from quiz_app.database.database import Database

class AuthManager:
    def __init__(self):
        self.db = Database()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username/email and password"""
        # Try username first, then email
        user = self.db.execute_single(
            "SELECT * FROM users WHERE (username = ? OR email = ?) AND is_active = 1",
            (username, username)
        )
        
        if not user:
            return None
        
        if self.verify_password(password, user['password_hash']):
            # Update last login
            self.db.execute_update(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user['id'],)
            )
            
            # Remove password hash from returned data
            user_data = dict(user)
            del user_data['password_hash']
            return user_data
        
        return None
    
    def create_user(self, username: str, email: str, password: str, 
                   full_name: str, role: str = 'examinee', 
                   department: str = None, employee_id: str = None) -> Optional[int]:
        """Create a new user"""
        try:
            # Check if username or email already exists
            existing = self.db.execute_single(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (username, email)
            )
            
            if existing:
                return None
            
            password_hash = self.hash_password(password)
            
            user_id = self.db.execute_insert('''
                INSERT INTO users (username, email, password_hash, full_name, role, department, employee_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, email, password_hash, full_name, role, department, employee_id))
            
            return user_id
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        user = self.db.execute_single(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        )
        
        if user:
            user_data = dict(user)
            del user_data['password_hash']
            return user_data
        
        return None
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """Update user password"""
        try:
            password_hash = self.hash_password(new_password)
            rows_affected = self.db.execute_update(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id)
            )
            return rows_affected > 0
        except Exception as e:
            print(f"Error updating password: {e}")
            return False
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account"""
        try:
            rows_affected = self.db.execute_update(
                "UPDATE users SET is_active = 0 WHERE id = ?",
                (user_id,)
            )
            return rows_affected > 0
        except Exception as e:
            print(f"Error deactivating user: {e}")
            return False