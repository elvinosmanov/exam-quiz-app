"""
Audit Logging System for Quiz Examination System

Tracks all user actions, exam activities, and administrative operations
for security monitoring and compliance.
"""

import logging
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from quiz_app.database.database import Database


class AuditLogger:
    """Centralized audit logging system"""

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
        print(f"[AUDIT] Audit logger initialized. Log file: {log_file}")

    def log_user_action(self, user_id: Optional[int], action: str, table_name: Optional[str] = None,
                       record_id: Optional[int] = None, old_values: Optional[str] = None,
                       new_values: Optional[str] = None, ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None):
        """
        Log user action to audit trail database

        Args:
            user_id: ID of user performing action (None for system/anonymous)
            action: Action description (e.g., 'LOGIN_SUCCESS', 'EXAM_START')
            table_name: Database table affected
            record_id: Record ID affected
            old_values: JSON string of old values (for updates)
            new_values: JSON string of new values or details
            ip_address: IP address of user
            user_agent: User agent string
        """
        try:
            self.db.execute_insert('''
                INSERT INTO audit_log (user_id, action, table_name, record_id,
                                     old_values, new_values, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, action, table_name, record_id, old_values,
                  new_values, ip_address, user_agent))

            log_msg = f"[AUDIT] User:{user_id} Action:{action}"
            if table_name:
                log_msg += f" Table:{table_name}"
            if record_id:
                log_msg += f" RecordID:{record_id}"

            self.logger.info(log_msg)
            print(log_msg)  # Also print to console for visibility

        except Exception as e:
            self.logger.error(f"[AUDIT ERROR] Failed to log audit entry: {str(e)}")
            print(f"[AUDIT ERROR] Failed to log audit entry: {str(e)}")

    # === Authentication Logging ===

    def log_login(self, username: str, user_id: Optional[int], success: bool,
                  ip_address: Optional[str] = None, reason: Optional[str] = None):
        """Log login attempts"""
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        details = {"username": username}
        if reason:
            details["reason"] = reason

        self.log_user_action(
            user_id=user_id if success else None,
            action=action,
            new_values=json.dumps(details),
            ip_address=ip_address
        )

    def log_logout(self, user_id: int, username: str):
        """Log logout actions"""
        self.log_user_action(
            user_id=user_id,
            action="LOGOUT",
            new_values=json.dumps({"username": username})
        )

    # === Exam Session Logging ===

    def log_exam_start(self, user_id: int, exam_id: int, session_id: int, exam_title: str):
        """Log exam start event"""
        self.log_user_action(
            user_id=user_id,
            action="EXAM_START",
            table_name="exam_sessions",
            record_id=session_id,
            new_values=json.dumps({
                "exam_id": exam_id,
                "exam_title": exam_title,
                "session_id": session_id
            })
        )

    def log_exam_submit(self, user_id: int, exam_id: int, session_id: int,
                       score: float, duration_seconds: int):
        """Log exam submission"""
        self.log_user_action(
            user_id=user_id,
            action="EXAM_SUBMIT",
            table_name="exam_sessions",
            record_id=session_id,
            new_values=json.dumps({
                "exam_id": exam_id,
                "session_id": session_id,
                "score": score,
                "duration_seconds": duration_seconds
            })
        )

    def log_answer_save(self, user_id: int, session_id: int, question_id: int,
                       question_type: str):
        """Log answer submissions (called per question)"""
        self.log_user_action(
            user_id=user_id,
            action="ANSWER_SAVE",
            table_name="user_answers",
            record_id=question_id,
            new_values=json.dumps({
                "session_id": session_id,
                "question_id": question_id,
                "question_type": question_type
            })
        )

    # === Admin Action Logging ===

    def log_admin_action(self, admin_id: int, action: str, target_table: str,
                        target_id: Optional[int] = None, changes: Optional[Dict[str, Any]] = None):
        """
        Log administrative actions

        Args:
            admin_id: ID of admin user
            action: Action type (CREATE, UPDATE, DELETE, etc.)
            target_table: Table being modified
            target_id: ID of record being modified
            changes: Dict of changes made
        """
        self.log_user_action(
            user_id=admin_id,
            action=f"ADMIN_{action}",
            table_name=target_table,
            record_id=target_id,
            new_values=json.dumps(changes) if changes else None
        )

    def log_user_create(self, admin_id: int, new_user_id: int, username: str, role: str):
        """Log user creation"""
        self.log_admin_action(
            admin_id=admin_id,
            action="CREATE_USER",
            target_table="users",
            target_id=new_user_id,
            changes={"username": username, "role": role}
        )

    def log_user_update(self, admin_id: int, target_user_id: int, changes: Dict[str, Any]):
        """Log user updates"""
        self.log_admin_action(
            admin_id=admin_id,
            action="UPDATE_USER",
            target_table="users",
            target_id=target_user_id,
            changes=changes
        )

    def log_user_delete(self, admin_id: int, target_user_id: int, username: str):
        """Log user deletion/deactivation"""
        self.log_admin_action(
            admin_id=admin_id,
            action="DELETE_USER",
            target_table="users",
            target_id=target_user_id,
            changes={"username": username}
        )

    def log_exam_create(self, admin_id: int, exam_id: int, title: str):
        """Log exam creation"""
        self.log_admin_action(
            admin_id=admin_id,
            action="CREATE_EXAM",
            target_table="exams",
            target_id=exam_id,
            changes={"title": title}
        )

    def log_exam_update(self, admin_id: int, exam_id: int, changes: Dict[str, Any]):
        """Log exam updates"""
        self.log_admin_action(
            admin_id=admin_id,
            action="UPDATE_EXAM",
            target_table="exams",
            target_id=exam_id,
            changes=changes
        )

    def log_exam_delete(self, admin_id: int, exam_id: int, title: str):
        """Log exam deletion"""
        self.log_admin_action(
            admin_id=admin_id,
            action="DELETE_EXAM",
            target_table="exams",
            target_id=exam_id,
            changes={"title": title}
        )

    def log_question_create(self, admin_id: int, question_id: int, question_type: str):
        """Log question creation"""
        self.log_admin_action(
            admin_id=admin_id,
            action="CREATE_QUESTION",
            target_table="questions",
            target_id=question_id,
            changes={"question_type": question_type}
        )

    # === Security Event Logging ===

    def log_focus_loss(self, user_id: int, session_id: int, focus_loss_count: int):
        """Log focus loss during exam (anti-cheating)"""
        self.log_user_action(
            user_id=user_id,
            action="EXAM_FOCUS_LOSS",
            table_name="exam_sessions",
            record_id=session_id,
            new_values=json.dumps({"focus_loss_count": focus_loss_count})
        )

    def log_suspicious_activity(self, user_id: int, activity_type: str, details: Dict[str, Any]):
        """Log suspicious activities detected"""
        self.log_user_action(
            user_id=user_id,
            action=f"SUSPICIOUS_{activity_type}",
            new_values=json.dumps(details)
        )


# Global logger instance - singleton pattern
_audit_logger_instance = None

def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance"""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger()
    return _audit_logger_instance

# For backward compatibility
audit_logger = get_audit_logger()