from typing import Optional, Dict
from datetime import datetime, timedelta
from quiz_app.config import SESSION_TIMEOUT

class SessionManager:
    def __init__(self):
        self.current_user = None
        self.session_data = {}
        self.login_time = None
        self.db = None  # Will be set externally if needed
        self.last_error = None  # Store last error for UI display

    def set_database(self, db):
        """Set database instance for language preference operations"""
        self.db = db

    def create_session(self, user_data: Dict) -> bool:
        """Create a new user session - BULLETPROOF VERSION"""
        # Store error for UI display
        self.last_error = None

        try:
            # Check if user_data is None or empty
            if not user_data:
                error_msg = "ERROR: user_data is None or empty"
                self.last_error = error_msg
                return False

            # Get critical fields with safe defaults
            user_id = user_data.get('id')
            username = user_data.get('username')
            role = user_data.get('role')
            full_name = user_data.get('full_name', '')

            # Validate only absolutely critical fields
            if not user_id:
                error_msg = f"ERROR: Missing user id. Keys: {list(user_data.keys())}"
                self.last_error = error_msg
                return False
            if not username:
                error_msg = f"ERROR: Missing username. Keys: {list(user_data.keys())}"
                self.last_error = error_msg
                return False
            if not role:
                error_msg = f"ERROR: Missing role. Keys: {list(user_data.keys())}"
                self.last_error = error_msg
                return False

            # Set session basics - these CANNOT fail
            self.current_user = user_data
            self.login_time = datetime.now()

            # Get language preference - completely optional, never fail
            language_pref = 'en'
            try:
                lang = user_data.get('language_preference')
                if lang and isinstance(lang, str) and lang in ['en', 'az']:
                    language_pref = lang
            except:
                pass

            # Create session data dictionary - use safe gets
            self.session_data = {
                'user_id': user_id,
                'username': username,
                'role': role,
                'full_name': full_name,
                'login_time': self.login_time,
                'language': language_pref
            }

            # Set language - do this AFTER session is fully created, non-critical
            try:
                from quiz_app.utils.localization import set_language
                set_language(language_pref)
            except Exception as e:
                # Don't fail session creation for this - session is already created
                pass

            return True

        except Exception as e:
            error_msg = f"CRITICAL ERROR: {type(e).__name__}: {str(e)}"
            import traceback
            tb = traceback.format_exc()
            self.last_error = f"{error_msg}\n{tb}"
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
        """Clear current session with complete cleanup"""
        # Clear all session data
        self.current_user = None
        self.session_data = {}
        self.login_time = None
        self.last_error = None

        # Clear any cached language preferences
        try:
            from quiz_app.utils.localization import set_language
            set_language('en')  # Reset to default
        except:
            pass
    
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
        try:
            from quiz_app.utils.localization import get_language
            return get_language()
        except:
            return 'en'

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
            from quiz_app.utils.localization import set_language
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