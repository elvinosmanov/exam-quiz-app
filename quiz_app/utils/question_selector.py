"""
Question Selection Utility for Question Pool Feature

This module handles the random selection of questions from a question pool
based on difficulty distribution and exam configuration.
"""

import random
from typing import List, Dict, Tuple
from quiz_app.database.database import Database


class QuestionSelector:
    """Handles question selection logic for exams with question pools"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def select_questions_for_session(self, exam_data: Dict, session_id: int) -> List[Dict]:
        """
        Select questions for an exam session based on exam configuration.
        
        Args:
            exam_data: Exam configuration data
            session_id: Exam session ID to store selected questions
            
        Returns:
            List of selected questions for the exam session
        """
        # Check if this exam uses question pool
        if not exam_data.get('use_question_pool', False):
            # Standard behavior: get all questions
            return self._get_all_exam_questions(exam_data['id'])
        
        # Check if questions already selected for this session
        existing_selection = self.db.execute_query("""
            SELECT q.* FROM questions q
            JOIN session_questions sq ON q.id = sq.question_id
            WHERE sq.session_id = ?
            ORDER BY sq.order_index, q.order_index, q.id
        """, (session_id,))
        
        if existing_selection:
            print(f"Using existing question selection for session {session_id}")
            return existing_selection
        
        # Perform new question selection
        print(f"Selecting new questions for session {session_id}")
        return self._select_random_questions(exam_data, session_id)
    
    def _get_all_exam_questions(self, exam_id: int) -> List[Dict]:
        """Get all questions for an exam (standard behavior)"""
        return self.db.execute_query("""
            SELECT * FROM questions 
            WHERE exam_id = ? AND is_active = 1 
            ORDER BY order_index, id
        """, (exam_id,))
    
    def _select_random_questions(self, exam_data: Dict, session_id: int) -> List[Dict]:
        """
        Select random questions based on difficulty distribution.
        
        Args:
            exam_data: Exam configuration including difficulty counts
            session_id: Session ID to store the selection
            
        Returns:
            List of selected questions
        """
        exam_id = exam_data['id']
        easy_count = exam_data.get('easy_questions_count', 0)
        medium_count = exam_data.get('medium_questions_count', 0)
        hard_count = exam_data.get('hard_questions_count', 0)
        
        print(f"Question selection for exam {exam_id}:")
        print(f"  Requested: {easy_count} easy, {medium_count} medium, {hard_count} hard")
        
        selected_questions = []
        order_index = 1
        
        # Select questions by difficulty level
        for difficulty, count in [('easy', easy_count), ('medium', medium_count), ('hard', hard_count)]:
            if count > 0:
                difficulty_questions = self._select_questions_by_difficulty(
                    exam_id, difficulty, count, session_id, order_index
                )
                selected_questions.extend(difficulty_questions)
                order_index += len(difficulty_questions)
        
        # Shuffle the final list for randomization (optional)
        if exam_data.get('randomize_questions', False):
            random.shuffle(selected_questions)
            # Re-assign order indices after shuffling
            for i, question in enumerate(selected_questions):
                self.db.execute_update("""
                    UPDATE session_questions 
                    SET order_index = ? 
                    WHERE session_id = ? AND question_id = ?
                """, (i + 1, session_id, question['id']))
        
        print(f"Selected {len(selected_questions)} questions total")
        return selected_questions
    
    def _select_questions_by_difficulty(self, exam_id: int, difficulty: str, count: int, 
                                      session_id: int, start_order_index: int) -> List[Dict]:
        """
        Select random questions of a specific difficulty level.
        
        Args:
            exam_id: Exam ID
            difficulty: Difficulty level ('easy', 'medium', 'hard')
            count: Number of questions to select
            session_id: Session ID for storing selection
            start_order_index: Starting order index for selected questions
            
        Returns:
            List of selected questions of the specified difficulty
        """
        # Get all available questions of this difficulty
        available_questions = self.db.execute_query("""
            SELECT * FROM questions 
            WHERE exam_id = ? AND difficulty_level = ? AND is_active = 1
            ORDER BY order_index, id
        """, (exam_id, difficulty))
        
        available_count = len(available_questions)
        print(f"  {difficulty.capitalize()}: {available_count} available, {count} requested")
        
        # Handle insufficient questions
        if available_count == 0:
            print(f"  Warning: No {difficulty} questions available")
            return []
        
        if available_count < count:
            print(f"  Warning: Only {available_count} {difficulty} questions available, but {count} requested")
            count = available_count
        
        # Randomly select questions
        selected = random.sample(available_questions, count)
        
        # Store the selection in session_questions table
        for i, question in enumerate(selected):
            self.db.execute_insert("""
                INSERT INTO session_questions (session_id, question_id, difficulty_level, order_index)
                VALUES (?, ?, ?, ?)
            """, (session_id, question['id'], difficulty, start_order_index + i))
        
        print(f"  Selected {len(selected)} {difficulty} questions")
        return selected
    
    def get_question_pool_stats(self, exam_id: int) -> Dict:
        """
        Get statistics about the question pool for an exam.
        
        Args:
            exam_id: Exam ID
            
        Returns:
            Dictionary with question counts by difficulty level
        """
        stats = {}
        
        # Get total questions
        total = self.db.execute_single("""
            SELECT COUNT(*) as count FROM questions 
            WHERE exam_id = ? AND is_active = 1
        """, (exam_id,))
        stats['total'] = total['count'] if total else 0
        
        # Get counts by difficulty
        for difficulty in ['easy', 'medium', 'hard']:
            count = self.db.execute_single("""
                SELECT COUNT(*) as count FROM questions 
                WHERE exam_id = ? AND difficulty_level = ? AND is_active = 1
            """, (exam_id, difficulty))
            stats[difficulty] = count['count'] if count else 0
        
        return stats
    
    def validate_question_pool_config(self, exam_data: Dict) -> Tuple[bool, str]:
        """
        Validate that an exam's question pool configuration is feasible.
        
        Args:
            exam_data: Exam configuration data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not exam_data.get('use_question_pool', False):
            return True, ""
        
        exam_id = exam_data['id']
        easy_requested = exam_data.get('easy_questions_count', 0)
        medium_requested = exam_data.get('medium_questions_count', 0)
        hard_requested = exam_data.get('hard_questions_count', 0)
        
        # Get available questions by difficulty
        stats = self.get_question_pool_stats(exam_id)
        
        # Check if we have enough questions of each difficulty
        errors = []
        
        if easy_requested > stats['easy']:
            errors.append(f"Requested {easy_requested} easy questions but only {stats['easy']} available")
        
        if medium_requested > stats['medium']:
            errors.append(f"Requested {medium_requested} medium questions but only {stats['medium']} available")
        
        if hard_requested > stats['hard']:
            errors.append(f"Requested {hard_requested} hard questions but only {stats['hard']} available")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, ""


def select_questions_for_exam_session(exam_data: Dict, session_id: int) -> List[Dict]:
    """
    Convenience function to select questions for an exam session.
    
    Args:
        exam_data: Exam configuration data
        session_id: Exam session ID
        
    Returns:
        List of selected questions for the exam session
    """
    db = Database()
    selector = QuestionSelector(db)
    return selector.select_questions_for_session(exam_data, session_id)