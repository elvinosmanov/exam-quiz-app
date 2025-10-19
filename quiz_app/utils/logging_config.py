import logging
import os
from datetime import datetime
from quiz_app.database.database import Database

class AuditLogger:
    def __init__(self):
        self.db = Database()
        
        # Setup file logging
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'quiz_app_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('quiz_app')
    
    def log_user_action(self, user_id: int, action: str, table_name: str = None, 
                       record_id: int = None, old_values: str = None, 
                       new_values: str = None, ip_address: str = None, 
                       user_agent: str = None):
        """Log user action to audit trail"""
        try:
            self.db.execute_insert('''
                INSERT INTO audit_log (user_id, action, table_name, record_id, 
                                     old_values, new_values, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, action, table_name, record_id, old_values, 
                  new_values, ip_address, user_agent))
            
            self.logger.info(f"User {user_id} performed action: {action}")
        
        except Exception as e:
            self.logger.error(f"Failed to log audit entry: {str(e)}")
    
    def log_exam_session(self, user_id: int, exam_id: int, action: str, details: str = None):
        """Log exam session events"""
        self.log_user_action(
            user_id=user_id,
            action=f"EXAM_{action}",
            table_name="exam_sessions",
            record_id=exam_id,
            new_values=details
        )
    
    def log_login(self, user_id: int, success: bool, ip_address: str = None):
        """Log login attempts"""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        self.log_user_action(
            user_id=user_id if success else None,
            action=action,
            ip_address=ip_address
        )
    
    def log_admin_action(self, admin_id: int, action: str, target_table: str, 
                        target_id: int, changes: str = None):
        """Log administrative actions"""
        self.log_user_action(
            user_id=admin_id,
            action=f"ADMIN_{action}",
            table_name=target_table,
            record_id=target_id,
            new_values=changes
        )

# Global logger instance
audit_logger = AuditLogger()