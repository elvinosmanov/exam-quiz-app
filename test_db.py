#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to initialize the database and verify the setup
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quiz_app.database.database import init_database, Database
from quiz_app.utils.auth import AuthManager

def test_database_setup():
    """Test database initialization and basic operations"""
    print("Testing database setup...")
    
    try:
        # Initialize database
        init_database()
        print("✓ Database initialized successfully")
        
        # Test database connection
        db = Database()
        users = db.execute_query("SELECT COUNT(*) as count FROM users")
        print(f"✓ Database connection works. Found {users[0]['count']} users")
        
        # Test authentication
        auth = AuthManager()
        user = auth.authenticate_user("admin", "admin123")
        if user:
            print(f"✓ Admin authentication works. User: {user['username']} ({user['role']})")
        else:
            print("✗ Admin authentication failed")
        
        # Test creating a new user
        new_user_id = auth.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            full_name="Test User",
            role="examinee",
            department="IT"
        )
        
        if new_user_id:
            print(f"✓ New user created successfully with ID: {new_user_id}")
            
            # Test new user authentication
            test_user = auth.authenticate_user("testuser", "testpass123")
            if test_user:
                print(f"✓ New user authentication works. User: {test_user['username']}")
            else:
                print("✗ New user authentication failed")
        else:
            print("✗ Failed to create new user")
        
        # Create a sample exam
        exam_id = db.execute_insert('''
            INSERT INTO exams (title, description, duration_minutes, passing_score, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', ("Sample Python Quiz", "A basic Python programming quiz", 30, 70.0, 1))
        
        if exam_id:
            print(f"✓ Sample exam created with ID: {exam_id}")
            
            # Create sample questions
            questions = [
                {
                    'text': 'What is the correct way to create a list in Python?',
                    'type': 'multiple_choice',
                    'options': [
                        ('my_list = []', True),
                        ('my_list = ()', False),
                        ('my_list = {}', False),
                        ('my_list = ""', False)
                    ]
                },
                {
                    'text': 'Python is an interpreted language.',
                    'type': 'true_false',
                    'options': [
                        ('True', True),
                        ('False', False)
                    ]
                },
                {
                    'text': 'What does the len() function do?',
                    'type': 'short_answer',
                    'correct_answer': 'Returns the length of an object'
                }
            ]
            
            for i, q in enumerate(questions):
                question_id = db.execute_insert('''
                    INSERT INTO questions (exam_id, question_text, question_type, correct_answer, points, order_index)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (exam_id, q['text'], q['type'], 
                      q.get('correct_answer', q['options'][0][0] if 'options' in q else ''), 
                      1.0, i))
                
                if question_id and 'options' in q:
                    for j, (option_text, is_correct) in enumerate(q['options']):
                        db.execute_insert('''
                            INSERT INTO question_options (question_id, option_text, is_correct, order_index)
                            VALUES (?, ?, ?, ?)
                        ''', (question_id, option_text, is_correct, j))
            
            print(f"✓ Sample questions created for exam")
        
        print("\n" + "="*50)
        print("DATABASE SETUP COMPLETE!")
        print("="*50)
        print("Default admin credentials:")
        print("Username: admin")
        print("Password: admin123")
        print("\nTest user credentials:")
        print("Username: testuser")
        print("Password: testpass123")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"✗ Error during database setup: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database_setup()
    if success:
        print("\nYou can now run the application with: python main.py")
    else:
        print("\nPlease fix the errors before running the application.")
        sys.exit(1)