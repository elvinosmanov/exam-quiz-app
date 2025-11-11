from typing import Optional, Dict
from datetime import datetime, timedelta
from quiz_app.config import SESSION_TIMEOUT
from quiz_app.utils.localization import set_language, get_language

class SessionManager:
    def __init__(self):
        self.current_user = None
        self.session_data = {}
        self.login_time = None
        self.db = None  # Will be set externally if needed

    def set_database(self, db):
        """Set database instance for language preference operations"""
        self.db = db

    def create_session(self, user_data: Dict) -> bool:
        """Create a new user session"""
        try:
            self.current_user = user_data
            self.login_time = datetime.now()

            # Get user language preference
            language_pref = user_data.get('language_preference', 'en')

            # If no preference in user data, try to load from database
            if not language_pref or language_pref == 'en':
                if self.db:
                    try:
                        user_info = self.db.execute_single(
                            "SELECT language_preference FROM users WHERE id = ?",
                            (user_data['id'],)
                        )
                        if user_info and user_info.get('language_preference'):
                            language_pref = user_info['language_preference']
                    except Exception as e:
                        print(f"[WARNING] Could not load language preference: {e}")

            # Set the application language
            set_language(language_pref)

            self.session_data = {
                'user_id': user_data['id'],
                'username': user_data['username'],
                'role': user_data['role'],
                'full_name': user_data['full_name'],
                'login_time': self.login_time,
                'language': language_pref
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

    def get_language(self) -> str:
        """Get current user's language preference"""
        if self.session_data:
            return self.session_data.get('language', 'en')
        return get_language()

    def set_user_language(self, language_code: str) -> bool:
        """
        Update user's language preference in session and database

        Args:
            language_code: Language code ('en' or 'az')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update in session
            if self.session_data:
                self.session_data['language'] = language_code

            # Update application language
            set_language(language_code)

            # Update in database if available
            if self.db and self.current_user:
                self.db.execute_update(
                    "UPDATE users SET language_preference = ? WHERE id = ?",
                    (language_code, self.current_user['id'])
                )

            return True
        except Exception as e:
            print(f"[ERROR] Failed to update language preference: {e}")
            return False