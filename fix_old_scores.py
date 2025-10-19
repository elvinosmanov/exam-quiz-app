#!/usr/bin/env python3
"""
Migration script to fix scores for existing exam sessions
Run this to recalculate all scores using the corrected logic
"""

import sys
import os
sys.path.append('.')

from quiz_app.database.database import Database

def fix_exam_session_scores():
    """Recalculate scores for all existing exam sessions"""
    print("🔧 Starting score recalculation for all existing exam sessions...")
    
    db = Database()
    
    # Get all completed exam sessions
    sessions = db.execute_query("""
        SELECT id, user_id, exam_id, score as old_score
        FROM exam_sessions 
        WHERE is_completed = 1
        ORDER BY id
    """)
    
    if not sessions:
        print("✅ No completed exam sessions found - nothing to fix")
        return
    
    print(f"📋 Found {len(sessions)} completed exam sessions to recalculate")
    
    fixed_count = 0
    unchanged_count = 0
    error_count = 0
    
    for session in sessions:
        session_id = session['id']
        old_score = session['old_score']
        
        try:
            print(f"\n🔄 Processing session {session_id} (old score: {old_score:.1f}%)")
            
            # Get questions for this session (handles both regular exams and question pool exams)
            # First check if this session has selected questions in session_questions table
            session_questions = db.execute_query("""
                SELECT q.id, q.points, q.question_type
                FROM questions q
                JOIN session_questions sq ON q.id = sq.question_id
                WHERE sq.session_id = ?
                ORDER BY sq.order_index, q.order_index, q.id
            """, (session_id,))
            
            if session_questions:
                # This session uses question pool - use selected questions
                exam_questions = session_questions
                print(f"   Using question pool: {len(exam_questions)} selected questions")
            else:
                # Regular exam - get all questions from the exam
                exam_questions = db.execute_query("""
                    SELECT q.id, q.points, q.question_type
                    FROM questions q
                    JOIN exam_sessions es ON es.id = ?
                    JOIN exams e ON e.id = es.exam_id AND e.id = q.exam_id
                    ORDER BY q.order_index, q.id
                """, (session_id,))
                print(f"   Using regular exam: {len(exam_questions)} total questions")
            
            if not exam_questions:
                print(f"   ⚠️  No questions found for session {session_id}")
                error_count += 1
                continue
            
            # Calculate total points for ALL questions
            total_points = sum(q['points'] for q in exam_questions)
            earned_points = 0
            correct_answers = 0
            answered_questions = 0
            
            # Get user answers for each question (avoid duplicates)
            for question in exam_questions:
                question_id = question['id']
                
                # Get the latest answer for this question (avoid duplicates)
                answer = db.execute_single("""
                    SELECT points_earned, is_correct
                    FROM user_answers 
                    WHERE session_id = ? AND question_id = ?
                    ORDER BY answered_at DESC
                    LIMIT 1
                """, (session_id, question_id))
                
                if answer and answer['points_earned'] is not None:
                    answered_questions += 1
                    earned_points += answer['points_earned']
                    
                    if answer['is_correct']:
                        correct_answers += 1
            
            # Calculate percentage score
            new_score = (earned_points / total_points * 100) if total_points > 0 else 0
            
            print(f"   📊 Questions: {len(exam_questions)} total, {answered_questions} answered, {correct_answers} correct")
            print(f"   📊 Points: {earned_points}/{total_points} = {new_score:.1f}%")
            
            # Update the exam session with new score
            db.execute_update("""
                UPDATE exam_sessions 
                SET score = ?, correct_answers = ?, total_questions = ?
                WHERE id = ?
            """, (new_score, correct_answers, len(exam_questions), session_id))
            
            if abs(new_score - old_score) > 0.1:  # Score changed significantly
                print(f"   ✅ FIXED: {old_score:.1f}% → {new_score:.1f}%")
                fixed_count += 1
            else:
                print(f"   ✓ Unchanged: {new_score:.1f}%")
                unchanged_count += 1
                
        except Exception as e:
            print(f"   ❌ Error processing session {session_id}: {e}")
            error_count += 1
    
    print(f"\n🎯 MIGRATION COMPLETE:")
    print(f"   ✅ Fixed scores: {fixed_count}")
    print(f"   ✓ Unchanged: {unchanged_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📊 Total processed: {len(sessions)}")
    
    if fixed_count > 0:
        print(f"\n🚀 Successfully fixed {fixed_count} exam session scores!")
    else:
        print(f"\n✅ All scores were already correct!")

if __name__ == "__main__":
    try:
        fix_exam_session_scores()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)