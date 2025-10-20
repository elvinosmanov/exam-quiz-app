"""
Answer Pattern Analysis System for Quiz Examination System

Detects suspicious patterns in exam behavior including:
- Rapid answers (too fast to be legitimate)
- Excessive answer changes (unusual indecision)
- Cross-student similarity (potential collaboration)
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from quiz_app.database.database import Database


class PatternAnalyzer:
    """Analyzes exam answer patterns for suspicious activity"""

    # Detection thresholds
    RAPID_ANSWER_THRESHOLD = 10  # Seconds - answers faster than this are suspicious
    EXCESSIVE_CHANGES_THRESHOLD = 3  # Answer changes - more than this is suspicious
    SIMILARITY_THRESHOLD = 0.85  # 85% similarity between students is suspicious

    def __init__(self):
        self.db = Database()

    def analyze_session(self, session_id: int) -> Dict[str, Any]:
        """
        Analyze a completed exam session for suspicious patterns

        Args:
            session_id: The exam session to analyze

        Returns:
            Dict with analysis results and detected issues
        """
        analysis_result = {
            'session_id': session_id,
            'analyzed_at': datetime.now().isoformat(),
            'issues_detected': [],
            'suspicion_score': 0,
            'details': {}
        }

        try:
            # Get session info
            session = self.db.execute_single("""
                SELECT * FROM exam_sessions WHERE id = ?
            """, (session_id,))

            if not session:
                return analysis_result

            analysis_result['user_id'] = session['user_id']
            analysis_result['exam_id'] = session['exam_id']

            # Run all detection algorithms
            rapid_answers = self._detect_rapid_answers(session_id)
            excessive_changes = self._detect_excessive_changes(session_id)
            similarity_issues = self._detect_answer_similarity(
                session['user_id'],
                session['exam_id'],
                session_id
            )

            # Compile results
            if rapid_answers:
                analysis_result['issues_detected'].append('RAPID_ANSWERS')
                analysis_result['details']['rapid_answers'] = rapid_answers
                analysis_result['suspicion_score'] += len(rapid_answers) * 10

            if excessive_changes:
                analysis_result['issues_detected'].append('EXCESSIVE_CHANGES')
                analysis_result['details']['excessive_changes'] = excessive_changes
                analysis_result['suspicion_score'] += len(excessive_changes) * 5

            if similarity_issues:
                analysis_result['issues_detected'].append('ANSWER_SIMILARITY')
                analysis_result['details']['similarity'] = similarity_issues
                analysis_result['suspicion_score'] += 50  # High weight for similarity

            # Cap suspicion score at 100
            analysis_result['suspicion_score'] = min(analysis_result['suspicion_score'], 100)

            # Save analysis to database
            self._save_analysis(analysis_result)

            print(f"[PATTERN] Analyzed session {session_id}: Score={analysis_result['suspicion_score']}, Issues={analysis_result['issues_detected']}")

        except Exception as e:
            print(f"[PATTERN ERROR] Failed to analyze session {session_id}: {e}")

        return analysis_result

    def _detect_rapid_answers(self, session_id: int) -> List[Dict[str, Any]]:
        """Detect questions answered too quickly"""
        rapid_answers = []

        try:
            # Get all answers with time spent
            answers = self.db.execute_query("""
                SELECT question_id, time_spent_seconds
                FROM user_answers
                WHERE session_id = ? AND time_spent_seconds IS NOT NULL
                ORDER BY answered_at
            """, (session_id,))

            for answer in answers:
                if answer['time_spent_seconds'] < self.RAPID_ANSWER_THRESHOLD:
                    rapid_answers.append({
                        'question_id': answer['question_id'],
                        'time_spent': answer['time_spent_seconds'],
                        'threshold': self.RAPID_ANSWER_THRESHOLD
                    })

        except Exception as e:
            print(f"[PATTERN ERROR] Rapid answer detection failed: {e}")

        return rapid_answers

    def _detect_excessive_changes(self, session_id: int) -> List[Dict[str, Any]]:
        """Detect questions with too many answer changes"""
        excessive_changes = []

        try:
            # Count answer submissions per question
            change_counts = self.db.execute_query("""
                SELECT question_id, COUNT(*) as change_count
                FROM user_answers
                WHERE session_id = ?
                GROUP BY question_id
                HAVING change_count > ?
            """, (session_id, self.EXCESSIVE_CHANGES_THRESHOLD))

            for item in change_counts:
                excessive_changes.append({
                    'question_id': item['question_id'],
                    'changes': item['change_count'],
                    'threshold': self.EXCESSIVE_CHANGES_THRESHOLD
                })

        except Exception as e:
            print(f"[PATTERN ERROR] Excessive changes detection failed: {e}")

        return excessive_changes

    def _detect_answer_similarity(self, user_id: int, exam_id: int, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Detect high similarity with other students' answers on the same exam

        This checks for potential collaboration by comparing answer patterns
        """
        try:
            # Get this user's answers
            user_answers = self._get_session_answers(session_id)

            if not user_answers:
                return None

            # Get other completed sessions for the same exam
            other_sessions = self.db.execute_query("""
                SELECT id, user_id FROM exam_sessions
                WHERE exam_id = ? AND user_id != ? AND status = 'completed'
                AND id != ?
            """, (exam_id, user_id, session_id))

            highest_similarity = 0
            similar_user = None

            for other_session in other_sessions:
                other_answers = self._get_session_answers(other_session['id'])

                if not other_answers:
                    continue

                # Calculate similarity percentage
                similarity = self._calculate_similarity(user_answers, other_answers)

                if similarity > highest_similarity:
                    highest_similarity = similarity
                    similar_user = other_session['user_id']

            # Report if similarity exceeds threshold
            if highest_similarity >= self.SIMILARITY_THRESHOLD:
                return {
                    'similar_user_id': similar_user,
                    'similarity_percentage': round(highest_similarity * 100, 2),
                    'threshold': self.SIMILARITY_THRESHOLD * 100
                }

        except Exception as e:
            print(f"[PATTERN ERROR] Similarity detection failed: {e}")

        return None

    def _get_session_answers(self, session_id: int) -> Dict[int, Any]:
        """Get all answers for a session as a dict keyed by question_id"""
        answers_dict = {}

        try:
            answers = self.db.execute_query("""
                SELECT question_id, selected_option_id, answer_text, is_true
                FROM user_answers
                WHERE session_id = ?
                ORDER BY question_id, answered_at DESC
            """, (session_id,))

            # Keep only the latest answer per question
            for answer in answers:
                qid = answer['question_id']
                if qid not in answers_dict:
                    answers_dict[qid] = {
                        'selected_option_id': answer.get('selected_option_id'),
                        'answer_text': answer.get('answer_text'),
                        'is_true': answer.get('is_true')
                    }

        except Exception as e:
            print(f"[PATTERN ERROR] Failed to get session answers: {e}")

        return answers_dict

    def _calculate_similarity(self, answers1: Dict, answers2: Dict) -> float:
        """
        Calculate similarity between two sets of answers

        Returns: Float between 0.0 and 1.0
        """
        if not answers1 or not answers2:
            return 0.0

        # Find common questions
        common_questions = set(answers1.keys()) & set(answers2.keys())

        if not common_questions:
            return 0.0

        matching_answers = 0

        for qid in common_questions:
            ans1 = answers1[qid]
            ans2 = answers2[qid]

            # Compare based on answer type
            if ans1['selected_option_id'] is not None:
                # Multiple choice or True/False
                if ans1['selected_option_id'] == ans2['selected_option_id']:
                    matching_answers += 1
            elif ans1['is_true'] is not None:
                # True/False
                if ans1['is_true'] == ans2['is_true']:
                    matching_answers += 1
            elif ans1['answer_text'] and ans2['answer_text']:
                # Text answers - use simple similarity check
                if self._text_similarity(ans1['answer_text'], ans2['answer_text']) > 0.8:
                    matching_answers += 1

        return matching_answers / len(common_questions)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity based on word overlap"""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _save_analysis(self, analysis: Dict[str, Any]):
        """Save pattern analysis results to database"""
        try:
            self.db.execute_insert("""
                INSERT INTO pattern_analysis (
                    session_id, user_id, exam_id, analyzed_at,
                    suspicion_score, issues_detected, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis['session_id'],
                analysis.get('user_id'),
                analysis.get('exam_id'),
                analysis['analyzed_at'],
                analysis['suspicion_score'],
                json.dumps(analysis['issues_detected']),
                json.dumps(analysis['details'])
            ))
        except Exception as e:
            print(f"[PATTERN ERROR] Failed to save analysis: {e}")

    def get_suspicious_sessions(self, min_score: int = 30) -> List[Dict[str, Any]]:
        """Get all sessions with suspicion score above threshold"""
        try:
            sessions = self.db.execute_query("""
                SELECT pa.*, es.score as exam_score, u.username, u.full_name, e.title as exam_title
                FROM pattern_analysis pa
                JOIN exam_sessions es ON pa.session_id = es.id
                JOIN users u ON pa.user_id = u.id
                JOIN exams e ON pa.exam_id = e.id
                WHERE pa.suspicion_score >= ?
                ORDER BY pa.suspicion_score DESC, pa.analyzed_at DESC
            """, (min_score,))

            return sessions
        except Exception as e:
            print(f"[PATTERN ERROR] Failed to get suspicious sessions: {e}")
            return []


# Global analyzer instance - singleton pattern
_pattern_analyzer_instance = None

def get_pattern_analyzer() -> PatternAnalyzer:
    """Get or create the global pattern analyzer instance"""
    global _pattern_analyzer_instance
    if _pattern_analyzer_instance is None:
        _pattern_analyzer_instance = PatternAnalyzer()
    return _pattern_analyzer_instance
