"""
Email Template Manager
Handles email template loading, generation, and placeholder replacement
"""

from typing import Dict, Tuple, Optional, List
from datetime import datetime


class EmailTemplateManager:
    """Manages email templates for exam result notifications"""

    def __init__(self, db):
        self.db = db
        self._template_cache = {}  # Cache templates in memory for performance

    def get_template(self, template_type: str, language: str = 'en') -> Optional[Dict]:
        """
        Get email template from database

        Args:
            template_type: Type of template ('passed', 'failed', 'pending')
            language: Language code ('en', 'az')

        Returns:
            Dictionary with 'subject' and 'body_template' or None if not found
        """
        # Check cache first
        cache_key = f"{template_type}_{language}"
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        # Load from database
        try:
            result = self.db.execute_single(
                "SELECT subject, body_template FROM email_templates WHERE template_type = ? AND language = ?",
                (template_type, language)
            )

            if result:
                template = {
                    'subject': result['subject'],
                    'body_template': result['body_template']
                }
                # Cache for future use
                self._template_cache[cache_key] = template
                return template

            # Fallback to English if requested language not found
            if language != 'en':
                print(f"[EmailTemplateManager] Template not found for {template_type} ({language}), falling back to English")
                return self.get_template(template_type, 'en')

            return None

        except Exception as e:
            print(f"[EmailTemplateManager] Error loading template: {e}")
            return None

    def generate_email(self, session_id: int, language: str = 'en', user_language: str = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Generate complete email for an exam session

        Args:
            session_id: Exam session ID
            language: Preferred language ('en', 'az')
            user_language: User's preferred language from profile (optional)

        Returns:
            Tuple of (recipient_email, subject, body) or (None, None, None) if error
        """
        try:
            # Use user's preferred language if available
            if user_language:
                language = user_language

            # Fetch session data with all necessary information
            session_data = self._get_session_data(session_id)
            if not session_data:
                print(f"[EmailTemplateManager] Session {session_id} not found")
                return None, None, None

            # Determine email type (passed/failed/pending)
            email_type = self._determine_email_type(session_data)

            # Get appropriate template
            template = self.get_template(email_type, language)
            if not template:
                print(f"[EmailTemplateManager] Template not found for {email_type} ({language})")
                return None, None, None

            # Prepare placeholder values
            placeholders = self._prepare_placeholders(session_data)

            # Replace placeholders in subject and body
            subject = self._replace_placeholders(template['subject'], placeholders)
            body = self._replace_placeholders(template['body_template'], placeholders)

            recipient_email = session_data.get('email', '')

            return recipient_email, subject, body

        except Exception as e:
            print(f"[EmailTemplateManager] Error generating email: {e}")
            return None, None, None

    def _get_session_data(self, session_id: int) -> Optional[Dict]:
        """Fetch all necessary data for email generation (assignment-based)"""
        try:
            query = """
                SELECT
                    es.id as session_id,
                    es.score,
                    es.total_questions,
                    es.correct_answers,
                    es.status,
                    es.assignment_id,
                    u.email,
                    u.full_name,
                    u.language_preference,
                    e.title as topic_name,
                    ea.assignment_name,
                    COALESCE(ea.passing_score, e.passing_score) as passing_score,
                    COALESCE(ea.show_results, e.show_results) as show_results
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
                LEFT JOIN exams e ON COALESCE(ea.exam_id, es.exam_id) = e.id
                WHERE es.id = ?
            """

            result = self.db.execute_single(query, (session_id,))

            if result:
                # Calculate additional fields
                total_questions = result['total_questions'] or 0
                correct_answers = result['correct_answers'] or 0
                incorrect_answers = total_questions - correct_answers if total_questions > 0 else 0

                # For unanswered, we need to check user_answers table
                answered_count_query = """
                    SELECT COUNT(*) as answered
                    FROM user_answers
                    WHERE session_id = ? AND (answer_text IS NOT NULL AND answer_text != '' OR selected_option_id IS NOT NULL)
                """
                answered_result = self.db.execute_single(answered_count_query, (session_id,))
                answered_count = answered_result['answered'] if answered_result else 0
                unanswered = total_questions - answered_count if total_questions > 0 else 0

                # Check for ungraded manual questions
                ungraded_query = """
                    SELECT COUNT(*) as count
                    FROM user_answers ua
                    JOIN questions q ON ua.question_id = q.id
                    WHERE ua.session_id = ?
                    AND q.question_type IN ('essay', 'short_answer')
                    AND ua.points_earned IS NULL
                    AND ua.answer_text IS NOT NULL
                    AND ua.answer_text != ''
                """
                ungraded_result = self.db.execute_single(ungraded_query, (session_id,))
                has_ungraded = (ungraded_result['count'] > 0) if ungraded_result else False

                # Use assignment_name if available, fallback to topic_name
                exam_display_name = result.get('assignment_name') or result.get('topic_name', 'Exam')

                return {
                    'session_id': result['session_id'],
                    'email': result['email'],
                    'full_name': result['full_name'],
                    'language_preference': result['language_preference'] or 'en',
                    'exam_name': exam_display_name,  # Assignment name (or topic as fallback)
                    'topic_name': result.get('topic_name', ''),  # Original topic name
                    'assignment_name': result.get('assignment_name', ''),
                    'score': round(result['score'], 1) if result['score'] is not None else 0,
                    'passing_score': result['passing_score'],
                    'show_results': result['show_results'],
                    'correct': correct_answers,
                    'incorrect': incorrect_answers,
                    'unanswered': unanswered,
                    'total_questions': total_questions,
                    'has_ungraded_manual': has_ungraded,
                    'status': result['status']
                }

            return None

        except Exception as e:
            print(f"[EmailTemplateManager] Error fetching session data: {e}")
            return None

    def _determine_email_type(self, session_data: Dict) -> str:
        """
        Determine which email template to use based on session status

        Logic:
        1. If has ungraded essay/short_answer questions → 'pending'
        2. If show_results is disabled → 'pending'
        3. If score >= passing_score → 'passed'
        4. Otherwise → 'failed'
        """
        # Check for ungraded manual questions
        if session_data.get('has_ungraded_manual', False):
            return 'pending'

        # Check if results are hidden
        if not session_data.get('show_results', 1):
            return 'pending'

        # Check pass/fail status
        score = session_data.get('score', 0)
        passing_score = session_data.get('passing_score', 70)

        if score >= passing_score:
            return 'passed'
        else:
            return 'failed'

    def _prepare_placeholders(self, session_data: Dict) -> Dict[str, str]:
        """Prepare placeholder values for template replacement"""
        return {
            'full_name': session_data.get('full_name', ''),
            'exam_name': session_data.get('exam_name', ''),
            'score': str(session_data.get('score', 0)),
            'passing_score': str(session_data.get('passing_score', 70)),
            'status': 'PASSED' if session_data.get('score', 0) >= session_data.get('passing_score', 70) else 'NOT PASSED',
            'correct': str(session_data.get('correct', 0)),
            'incorrect': str(session_data.get('incorrect', 0)),
            'unanswered': str(session_data.get('unanswered', 0)),
            'total_questions': str(session_data.get('total_questions', 0))
        }

    def _replace_placeholders(self, text: str, placeholders: Dict[str, str]) -> str:
        """Replace {{placeholder}} with actual values"""
        result = text
        for key, value in placeholders.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            result = result.replace(placeholder, value)
        return result

    def save_template(self, template_type: str, language: str, subject: str, body_template: str) -> bool:
        """
        Save or update email template

        Args:
            template_type: Type of template ('passed', 'failed', 'pending')
            language: Language code ('en', 'az')
            subject: Email subject with placeholders
            body_template: Email body with placeholders

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if template exists
            existing = self.db.execute_single(
                "SELECT id FROM email_templates WHERE template_type = ? AND language = ?",
                (template_type, language)
            )

            if existing:
                # Update existing template
                self.db.execute_update(
                    """UPDATE email_templates
                       SET subject = ?, body_template = ?, updated_at = CURRENT_TIMESTAMP
                       WHERE template_type = ? AND language = ?""",
                    (subject, body_template, template_type, language)
                )
            else:
                # Insert new template
                self.db.execute_insert(
                    """INSERT INTO email_templates (template_type, language, subject, body_template)
                       VALUES (?, ?, ?, ?)""",
                    (template_type, language, subject, body_template)
                )

            # Clear cache for this template
            cache_key = f"{template_type}_{language}"
            if cache_key in self._template_cache:
                del self._template_cache[cache_key]

            return True

        except Exception as e:
            print(f"[EmailTemplateManager] Error saving template: {e}")
            return False

    def get_available_placeholders(self) -> List[str]:
        """Return list of available placeholders for templates"""
        return [
            '{{full_name}}',
            '{{exam_name}}',
            '{{score}}',
            '{{passing_score}}',
            '{{status}}',
            '{{correct}}',
            '{{incorrect}}',
            '{{unanswered}}',
            '{{total_questions}}'
        ]

    def clear_cache(self):
        """Clear template cache (useful after bulk updates)"""
        self._template_cache = {}
