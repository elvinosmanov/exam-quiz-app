import pandas as pd
import os
from typing import List, Dict, Optional, Tuple
from quiz_app.database.database import Database

class BulkImporter:
    def __init__(self, db=None):
        self.db = db if db else Database()
        self.supported_formats = ['.csv', '.xlsx', '.xls']
    
    def safe_str_strip(self, value, default=''):
        """Safely convert value to string and strip, handling None and numeric types"""
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
        
    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """Validate if file exists and has supported format"""
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in self.supported_formats:
            return False, f"Unsupported file format. Supported: {', '.join(self.supported_formats)}"
        
        return True, "Valid file"
    
    def read_file(self, file_path: str) -> Tuple[Optional[pd.DataFrame], str]:
        """Read data from Excel or CSV file"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                return None, "Unsupported file format"
            
            return df, "Success"
        
        except Exception as e:
            return None, f"Error reading file: {str(e)}"
    
    def validate_questions_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate the structure and content of questions data"""
        errors = []
        
        # Required columns
        required_columns = ['question_text', 'question_type', 'correct_answer']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check for empty rows
        empty_rows = df[df['question_text'].isna() | (df['question_text'] == '')].index.tolist()
        if empty_rows:
            errors.append(f"Empty question text in rows: {empty_rows}")
        
        # Validate question types
        valid_types = ['single_choice', 'multiple_choice', 'true_false', 'short_answer', 'essay']
        invalid_types = df[~df['question_type'].isin(valid_types)]['question_type'].unique().tolist()
        if invalid_types:
            errors.append(f"Invalid question types: {invalid_types}. Valid types: {valid_types}")
        
        # Validate choice questions have options
        choice_questions = df[df['question_type'].isin(['single_choice', 'multiple_choice'])]
        for idx, row in choice_questions.iterrows():
            options = [row.get(f'option_{i}', '') for i in range(1, 7)]  # Check up to 6 options
            valid_options = [self.safe_str_strip(opt) for opt in options if pd.notna(opt) and self.safe_str_strip(opt)]
            if len(valid_options) < 2:
                errors.append(f"Choice question in row {idx} needs at least 2 options")
        
        return len(errors) == 0, errors
    
    def import_questions(self, file_path: str, exam_id: int) -> Dict:
        """Import questions from file to specified exam"""
        # Validate file
        is_valid, message = self.validate_file(file_path)
        if not is_valid:
            return {'success': False, 'error': message, 'imported_count': 0, 'skipped_count': 0}
        
        # Read file
        df, read_message = self.read_file(file_path)
        if df is None:
            return {'success': False, 'error': read_message, 'imported_count': 0, 'skipped_count': 0}
        
        # Validate data structure
        is_valid_data, validation_errors = self.validate_questions_data(df)
        if not is_valid_data:
            return {'success': False, 'error': "\n".join(validation_errors), 'imported_count': 0, 'skipped_count': 0}
        
        # Process and import questions
        try:
            imported_count = 0
            skipped_count = 0
            error_count = 0
            
            for idx, row in df.iterrows():
                try:
                    # Prepare question data
                    question_data = {
                        'exam_id': exam_id,
                        'question_text': self.safe_str_strip(row['question_text']),
                        'question_type': self.safe_str_strip(row['question_type']),
                        'difficulty_level': self.safe_str_strip(row.get('difficulty_level', 'medium'), 'medium'),
                        'points': float(row.get('points', 1.0)) if pd.notna(row.get('points')) else 1.0,
                        'explanation': self.safe_str_strip(row.get('explanation', '')) if pd.notna(row.get('explanation')) else None,
                        'correct_answer': self.safe_str_strip(row['correct_answer'])
                    }
                    
                    # Insert question
                    question_id = self.db.execute_insert('''
                        INSERT INTO questions (exam_id, question_text, question_type, difficulty_level, 
                                             points, explanation, correct_answer)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        question_data['exam_id'],
                        question_data['question_text'],
                        question_data['question_type'],
                        question_data['difficulty_level'],
                        question_data['points'],
                        question_data['explanation'],
                        question_data['correct_answer']
                    ))
                    
                    # Handle options for choice-based questions
                    if question_data['question_type'] in ['single_choice', 'multiple_choice']:
                        options_added = 0
                        correct_answers = []
                        
                        # Parse correct answers (can be comma-separated for multiple choice)
                        if question_data['question_type'] == 'multiple_choice':
                            correct_answers = [ans.strip() for ans in question_data['correct_answer'].split(',')]
                        else:
                            correct_answers = [question_data['correct_answer']]
                        
                        for i in range(1, 7):  # Support up to 6 options
                            option_text = row.get(f'option_{i}')
                            if pd.notna(option_text):
                                option_text_clean = self.safe_str_strip(option_text)
                                if option_text_clean:  # Only process non-empty options
                                    is_correct = option_text_clean in correct_answers
                                    
                                    self.db.execute_insert('''
                                        INSERT INTO question_options (question_id, option_text, is_correct, order_index)
                                        VALUES (?, ?, ?, ?)
                                    ''', (question_id, option_text_clean, is_correct, i))
                                    
                                    options_added += 1
                        
                        if options_added < 2:
                            # Not enough options, skip this question
                            self.db.execute_update("DELETE FROM questions WHERE id = ?", (question_id,))
                            skipped_count += 1
                            continue
                    
                    elif question_data['question_type'] == 'true_false':
                        # Add True/False options
                        is_true_correct = question_data['correct_answer'].lower() in ['true', 't', 'yes', '1']
                        
                        self.db.execute_insert('''
                            INSERT INTO question_options (question_id, option_text, is_correct, order_index)
                            VALUES (?, ?, ?, ?)
                        ''', (question_id, 'True', is_true_correct, 1))
                        
                        self.db.execute_insert('''
                            INSERT INTO question_options (question_id, option_text, is_correct, order_index)
                            VALUES (?, ?, ?, ?)
                        ''', (question_id, 'False', not is_true_correct, 2))
                    
                    imported_count += 1
                
                except Exception as e:
                    error_count += 1
                    print(f"Error importing question at row {idx}: {str(e)}")
            
            if imported_count > 0:
                return {
                    'success': True, 
                    'imported_count': imported_count, 
                    'skipped_count': skipped_count,
                    'error_count': error_count,
                    'total': len(df)
                }
            else:
                return {
                    'success': False, 
                    'error': "No questions were imported", 
                    'imported_count': 0, 
                    'skipped_count': skipped_count
                }
        
        except Exception as e:
            return {
                'success': False, 
                'error': f"Error during import: {str(e)}", 
                'imported_count': 0, 
                'skipped_count': 0
            }
    
    def get_sample_template(self) -> pd.DataFrame:
        """Generate a sample template for question import"""
        sample_data = {
            'question_text': [
                'What is the capital of France?',
                'Which of the following are programming languages? (Select all that apply)',
                'Python is a programming language.',
                'What does HTML stand for?',
                'Explain the difference between a list and a tuple in Python.'
            ],
            'question_type': [
                'single_choice',
                'multiple_choice', 
                'true_false',
                'short_answer',
                'essay'
            ],
            'difficulty_level': [
                'easy',
                'medium',
                'easy',
                'medium',
                'hard'
            ],
            'points': [1.0, 2.0, 1.0, 2.0, 5.0],
            'correct_answer': [
                'Paris', 
                'Python, Java, JavaScript',  # Multiple correct answers separated by comma
                'True', 
                'HyperText Markup Language',
                'Lists are mutable, tuples are immutable'  # Sample answer for grading reference
            ],
            'option_1': ['Paris', 'Python', 'True', '', ''],
            'option_2': ['London', 'Java', 'False', '', ''],
            'option_3': ['Berlin', 'JavaScript', '', '', ''],
            'option_4': ['Madrid', 'HTML', '', '', ''],
            'option_5': ['', 'CSS', '', '', ''],
            'option_6': ['', '', '', '', ''],
            'explanation': [
                'Paris is the capital and largest city of France.',
                'Python, Java, and JavaScript are all programming languages. HTML and CSS are markup/styling languages.',
                'Python is indeed a high-level programming language.',
                'HTML stands for HyperText Markup Language and is used to create web pages.',
                'This question tests understanding of Python data structures.'
            ]
        }
        
        return pd.DataFrame(sample_data)
    
    def export_sample_template(self, file_path: str) -> bool:
        """Export a sample template to file"""
        try:
            df = self.get_sample_template()
            
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.csv':
                df.to_csv(file_path, index=False)
            elif file_ext in ['.xlsx', '.xls']:
                df.to_excel(file_path, index=False)
            else:
                return False
            
            return True
        
        except Exception as e:
            print(f"Error exporting template: {str(e)}")
            return False
    
    def create_template(self, file_path=None) -> str:
        """Create a template file and return the path"""
        import tempfile
        from datetime import datetime
        
        if file_path is None:
            # Create in downloads or temp directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"questions_template_{timestamp}.xlsx"
            
            # Try to use Downloads folder, fallback to temp
            try:
                import os
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                if os.path.exists(downloads_path):
                    file_path = os.path.join(downloads_path, file_name)
                else:
                    file_path = os.path.join(tempfile.gettempdir(), file_name)
            except:
                file_path = os.path.join(tempfile.gettempdir(), file_name)
        
        success = self.export_sample_template(file_path)
        if success:
            return file_path
        else:
            raise Exception("Failed to create template file")