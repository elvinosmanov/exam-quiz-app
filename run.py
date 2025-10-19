#!/usr/bin/env python3
"""
Simple startup script for the Quiz Examination System
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Check if database exists, if not initialize it
    db_path = os.path.join(os.path.dirname(__file__), 'quiz_app.db')
    if not os.path.exists(db_path):
        print("Database not found. Initializing...")
        from quiz_app.database.database import init_database
        init_database()
        print("Database initialized successfully!")
    
    # Import and run the main application
    from main import main
    import flet as ft
    
    print("Starting Quiz Examination System...")
    print("Default admin: admin / admin123")
    print("Test user: testuser / testpass123")
    print("Note: Some deprecation warnings are expected and can be ignored.")
    
    ft.app(target=main)
    
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)