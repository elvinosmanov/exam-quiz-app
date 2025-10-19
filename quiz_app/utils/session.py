from typing import Optional, Dict
from datetime import datetime, timedelta
from quiz_app.config import SESSION_TIMEOUT

class SessionManager:
    def __init__(self):
        self.current_user = None
        self.session_data = {}
        self.login_time = None
    
    def create_session(self, user_data: Dict) -> bool:
        """Create a new user session"""
        try:
            self.current_user = user_data
            self.login_time = datetime.now()
            self.session_data = {
                'user_id': user_data['id'],
                'username': user_data['username'],
                'role': user_data['role'],
                'full_name': user_data['full_name'],
                'login_time': self.login_time
            }
            return True
        except Exception as e:
            print(f"Error creating session: {e}")
            return False
    
    def is_valid_session(self) -> bool:
        """Check if current session is valid"""
        if not self.current_user or not self.login_time:
            return False
        
        # Check session timeout
        elapsed_time = datetime.now() - self.login_time
        if elapsed_time.total_seconds() > SESSION_TIMEOUT:
            self.clear_session()
            return False
        
        return True
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current user data if session is valid"""
        if self.is_valid_session():
            return self.current_user
        return None
    
    def get_user_role(self) -> Optional[str]:
        """Get current user's role"""
        user = self.get_current_user()
        return user['role'] if user else None
    
    def is_admin(self) -> bool:
        """Check if current user is admin"""
        return self.get_user_role() == 'admin'
    
    def clear_session(self):
        """Clear current session"""
        self.current_user = None
        self.session_data = {}
        self.login_time = None
    
    def extend_session(self):
        """Extend session timeout"""
        if self.is_valid_session():
            self.login_time = datetime.now()
    
    def get_session_remaining_time(self) -> int:
        """Get remaining session time in seconds"""
        if not self.is_valid_session():
            return 0
        
        elapsed_time = datetime.now() - self.login_time
        remaining = SESSION_TIMEOUT - elapsed_time.total_seconds()
        return max(0, int(remaining))