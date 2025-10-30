import flet as ft
import json
import os
import threading
import time
from datetime import datetime, timedelta
from quiz_app.database.database import Database
from quiz_app.utils.logging_config import get_audit_logger


class ExamInterfaceWrapper(ft.UserControl):
    """Wrapper UserControl to properly handle page lifecycle for fullscreen lock"""

    def __init__(self, exam_data, user_data, return_callback, exam_state, on_fullscreen_change):
        super().__init__()
        self.exam_data = exam_data
        self.user_data = user_data
        self.return_callback = return_callback
        self.exam_state = exam_state
        self.on_fullscreen_change = on_fullscreen_change
        self.content_container = None

    def build(self):
        # Return the main container that was created
        return self.exam_state['main_container']

    def did_mount(self):
        """Called when control is added to page - attach fullscreen lock listener here"""
        super().did_mount()

        # CRITICAL: Set page reference for all exam operations (timer, navigation, etc.)
        if self.page:
            self.exam_state['page_ref'] = self.page
            print(f"[PAGE] Page reference set successfully for exam interface")

            # Enable fullscreen lock if feature is enabled
            if self.exam_state.get('enable_fullscreen_lock'):
                try:
                    self.page.on_window_event = self.on_fullscreen_change
                    print(f"[FULLSCREEN] Fullscreen lock enabled for exam")
                except AttributeError as e:
                    print(f"[FULLSCREEN] Warning: Could not enable fullscreen lock: {e}")
                    # Fullscreen lock is optional, continue without it


def create_exam_interface(exam_data, user_data, return_callback, exam_id=None, assignment_id=None):
    """Create complete exam interface as pure function - no UserControl issues"""

    # Initialize data
    db = Database()

    # Generate session ID first
    session_id = int(datetime.now().timestamp())

    # Determine the actual exam_id for fetching questions
    # If exam_id is provided separately (new assignment-based approach), use it
    # Otherwise fall back to exam_data['id'] (old exam-based approach)
    actual_exam_id = exam_id if exam_id is not None else exam_data.get('id')

    # Use question selector to get questions (handles both regular and multi-template exams)
    from quiz_app.utils.question_selector import select_questions_for_exam_session
    # Pass a modified exam_data dict with the correct exam_id for question fetching
    exam_data_for_questions = {**exam_data, 'id': actual_exam_id}
    questions = select_questions_for_exam_session(exam_data_for_questions, session_id, assignment_id)

    if not questions:
        return ft.Container(
            content=ft.Text("No questions found for this exam", size=18),
            padding=ft.padding.all(50)
        )
    
    exam_state = {
        'current_question_index': 0,
        'user_answers': {},
        'marked_for_review': set(),  # Set of question IDs marked for review
        'time_remaining': exam_data['duration_minutes'] * 60,
        'start_time': datetime.now(),
        'timer_running': True,
        'timer_display': None,
        'main_container': None,
        'session_id': session_id,  # Use the session ID generated for question selection
        'question_start_times': {},  # Track when each question was first viewed
        'question_time_spent': {},  # Track cumulative time spent on each question
        'enable_fullscreen_lock': exam_data.get('enable_fullscreen', False),  # Fullscreen lock feature
        'fullscreen_lock_active': False,  # Is fullscreen currently locked?
        'page_ref': None  # Reference to page for fullscreen lock
    }
    
    # Colors
    EXAM_COLORS = {
        'primary': '#3182ce',
        'primary_light': '#63b3ed',
        'success': '#38a169',
        'error': '#e53e3e',
        'warning': '#d69e2e',
        'answered': '#38a169',
        'unanswered': '#e2e8f0',
        'current': '#3182ce',
        'marked': '#d69e2e',
        'surface': '#ffffff',
        'background': '#f7fafc',
        'border': '#e2e8f0',
        'text_primary': '#1a202c',
        'text_secondary': '#718096'
    }
    
    def get_question_options(question_id):
        """Get options for a question"""
        return db.execute_query("""
            SELECT * FROM question_options
            WHERE question_id = ?
            ORDER BY order_index, id
        """, (question_id,))

    def track_question_time(question_id):
        """Track time spent on current question before leaving it - DISABLED"""
        pass  # Disabled to fix page update issues
        # try:
        #     current_time = datetime.now()
        #     if question_id in exam_state['question_start_times']:
        #         start_time = exam_state['question_start_times'][question_id]
        #         time_spent = (current_time - start_time).total_seconds()
        #         if question_id in exam_state['question_time_spent']:
        #             exam_state['question_time_spent'][question_id] += time_spent
        #         else:
        #             exam_state['question_time_spent'][question_id] = time_spent
        # except Exception as e:
        #     print(f"Error tracking question time: {e}")

    def start_question_timer(question_id):
        """Start timing for a new question - DISABLED"""
        pass  # Disabled to fix page update issues
        # try:
        #     exam_state['question_start_times'][question_id] = datetime.now()
        # except Exception as e:
        #     print(f"Error starting question timer: {e}")
    
    def render_question_image(image_path):
        """Render question image if present - same logic as admin interface"""
        if not image_path:
            return ft.Container()
        
        # Convert relative path to absolute path - same as admin interface
        if not os.path.isabs(image_path):
            # Use exact same path construction as admin interface
            full_image_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                image_path
            )
        else:
            full_image_path = image_path
        
        return ft.Container(
            content=ft.Column([
                ft.Image(
                    src=full_image_path,
                    width=600,
                    height=300,
                    fit=ft.ImageFit.CONTAIN,
                    border_radius=8
                ),
                ft.Container(height=8),  # Small spacing between image and hint text
                ft.Text(
                    "Click image to view full size", 
                    size=12, 
                    color=EXAM_COLORS['text_secondary'], 
                    italic=True
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(vertical=20, horizontal=10),
            bgcolor=ft.colors.with_opacity(0.02, EXAM_COLORS['primary']),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, EXAM_COLORS['border'])),
            on_click=lambda e: show_image_fullscreen(full_image_path)
        )
    
    def show_image_fullscreen(image_path):
        """Show image in fullscreen dialog"""
        try:
            # Access page through main_container
            page = None
            if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                page = exam_state['main_container'].page

            if page:
                
                def close_image_dialog(e):
                    image_dialog.open = False
                    page.update()
                
                image_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Question Image", size=18, weight=ft.FontWeight.BOLD),
                    content=ft.Container(
                        content=ft.Image(
                            src=image_path,
                            width=800,
                            height=600,
                            fit=ft.ImageFit.CONTAIN
                        ),
                        width=800,
                        height=600,
                        alignment=ft.alignment.center
                    ),
                    actions=[
                        ft.TextButton(
                            "Close",
                            on_click=close_image_dialog,
                            style=ft.ButtonStyle(color=EXAM_COLORS['primary'])
                        )
                    ]
                )
                
                page.dialog = image_dialog
                image_dialog.open = True
                page.update()
            else:
                print(f"Cannot show fullscreen image: Page not available. Path: {image_path}")
        except Exception as e:
            print(f"Error showing fullscreen image: {e}")
    
    def get_user_answer_from_db(session_id, question_id):
        """Get user answer from database for scoring"""
        try:
            user_answer_data = db.execute_single("""
                SELECT * FROM user_answers 
                WHERE session_id = ? AND question_id = ?
                ORDER BY answered_at DESC
                LIMIT 1
            """, (session_id, question_id))
            
            if not user_answer_data:
                return None
                
            # Return answer data in the same format as exam_state['user_answers']
            if user_answer_data.get('selected_option_id'):
                return {'selected_option_id': user_answer_data['selected_option_id']}
            elif user_answer_data.get('selected_option_ids'):
                return {'selected_option_ids': user_answer_data['selected_option_ids']}
            elif user_answer_data.get('answer_text'):
                return {'answer_text': user_answer_data['answer_text']}
            else:
                return None
        except Exception as e:
            print(f"Error retrieving answer for question {question_id}: {e}")
            return None
    
    def save_answer(question_id, answer_data):
        """Save answer to database"""
        try:
            session_id = exam_state['session_id']  # Use consistent session ID

            # Get time spent on this question
            time_spent = int(exam_state['question_time_spent'].get(question_id, 0))

            # Get question type to determine scoring approach
            question = next((q for q in questions if q['id'] == question_id), None)
            question_type = question['question_type'] if question else 'unknown'

            if 'selected_option_id' in answer_data:
                # Single choice question - auto-grade immediately
                selected_option_id = answer_data['selected_option_id']

                # Auto-grade the single choice question
                points_earned = 0.0
                is_correct = 0
                if selected_option_id:
                    # Check if the selected option is correct
                    correct_option = db.execute_query("""
                        SELECT is_correct FROM question_options
                        WHERE id = ? AND question_id = ?
                    """, (selected_option_id, question_id))

                    if correct_option and correct_option[0]['is_correct']:
                        points_earned = question.get('points', 1.0)
                        is_correct = 1

                db.execute_update("""
                    INSERT OR REPLACE INTO user_answers (
                        session_id, question_id, selected_option_id, points_earned, is_correct, time_spent_seconds, answered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, question_id, selected_option_id, points_earned, is_correct, time_spent, datetime.now().isoformat()))
            elif 'selected_option_ids' in answer_data:
                # Multiple choice question - auto-grade immediately
                selected_ids_json = json.dumps(answer_data['selected_option_ids']) if answer_data['selected_option_ids'] else None
                
                # Auto-grade the multiple choice question
                points_earned = 0.0
                is_correct = 0
                if answer_data['selected_option_ids']:
                    # Get correct options for this question
                    correct_options = db.execute_query("""
                        SELECT id FROM question_options 
                        WHERE question_id = ? AND is_correct = 1
                    """, (question_id,))
                    
                    correct_ids = [opt['id'] for opt in correct_options]
                    selected_ids = answer_data['selected_option_ids']
                    
                    # Check if selected options match exactly with correct options
                    if set(selected_ids) == set(correct_ids) and len(selected_ids) > 0:
                        points_earned = question.get('points', 1.0)
                        is_correct = 1
                
                db.execute_update("""
                    INSERT OR REPLACE INTO user_answers (
                        session_id, question_id, selected_option_ids, points_earned, is_correct, time_spent_seconds, answered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (session_id, question_id, selected_ids_json, points_earned, is_correct, time_spent, datetime.now().isoformat()))
            elif 'answer_text' in answer_data:
                # Text-based questions - explicitly set points_earned based on question type
                if question_type in ['essay', 'short_answer']:
                    # Essay/short_answer questions need manual grading - set points_earned to NULL
                    db.execute_update("""
                        INSERT OR REPLACE INTO user_answers (
                            session_id, question_id, answer_text, points_earned, time_spent_seconds, answered_at
                        ) VALUES (?, ?, ?, NULL, ?, ?)
                    """, (session_id, question_id, answer_data['answer_text'], time_spent, datetime.now().isoformat()))
                else:
                    # True/false questions - auto-grade immediately
                    answer_text = answer_data['answer_text']

                    # Auto-grade the true/false question
                    points_earned = 0.0
                    is_correct = 0
                    if answer_text and answer_text.lower() in ['true', 'false']:
                        # Get the correct answer for this question
                        correct_option = db.execute_query("""
                            SELECT option_text FROM question_options
                            WHERE question_id = ? AND is_correct = 1
                        """, (question_id,))

                        if correct_option and correct_option[0]['option_text'].lower() == answer_text.lower():
                            points_earned = question.get('points', 1.0)
                            is_correct = 1

                    db.execute_update("""
                        INSERT OR REPLACE INTO user_answers (
                            session_id, question_id, answer_text, points_earned, is_correct, time_spent_seconds, answered_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (session_id, question_id, answer_text, points_earned, is_correct, time_spent, datetime.now().isoformat()))
            
            exam_state['user_answers'][question_id] = answer_data
            print(f"Answer saved for question {question_id} ({question_type}): {answer_data}")
            
            # Note: We removed aggressive UI refresh here to prevent TextField unfocus issues
            # Progress updates will happen on navigation instead
        except Exception as e:
            print(f"Error saving answer: {e}")
    
    def save_current_answer():
        """Save the current question's answer before navigation"""
        if not questions or exam_state['current_question_index'] >= len(questions):
            return
        
        current_question = questions[exam_state['current_question_index']]
        question_id = current_question['id']
        
        # Get answer from exam_state
        if question_id in exam_state['user_answers']:
            answer_data = exam_state['user_answers'][question_id]
            save_answer(question_id, answer_data)
            print(f"Saved answer on navigation for question {question_id}")
    
    def update_timer():
        """Update timer countdown with proper cleanup"""
        try:
            while exam_state['timer_running'] and exam_state['time_remaining'] > 0:
                time.sleep(1)

                # Check if timer is still running
                if not exam_state['timer_running']:
                    break

                exam_state['time_remaining'] -= 1

                # Update timer display
                if exam_state['timer_display']:
                    minutes = exam_state['time_remaining'] // 60
                    seconds = exam_state['time_remaining'] % 60
                    exam_state['timer_display'].value = f"{minutes:02d}:{seconds:02d}"

                    # Update page - try multiple methods to get page reference
                    try:
                        page = None
                        # Try to get page from main_container
                        if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                            page = exam_state['main_container'].page

                        if page:
                            page.update()
                    except Exception as e:
                        # Page closed or unavailable - stop timer gracefully
                        print(f"[TIMER] Page unavailable, stopping timer: {e}")
                        exam_state['timer_running'] = False
                        break

                # Time warnings
                if exam_state['time_remaining'] == 600:  # 10 minutes
                    print("Warning: 10 minutes remaining!")
                elif exam_state['time_remaining'] == 300:  # 5 minutes
                    print("Warning: 5 minutes remaining!")
                elif exam_state['time_remaining'] == 60:  # 1 minute
                    print("Warning: 1 minute remaining!")
                elif exam_state['time_remaining'] == 0:
                    print("Time's up! Auto-submitting exam...")
                    exam_state['timer_running'] = False
                    if return_callback:
                        try:
                            return_callback()
                        except:
                            pass
        except Exception as e:
            print(f"[TIMER] Timer thread error: {e}")
        finally:
            exam_state['timer_running'] = False
            print("[TIMER] Timer thread stopped cleanly")
    
    # Start timer thread
    timer_thread = threading.Thread(target=update_timer, daemon=True)
    timer_thread.start()

    # === Fullscreen Lock (Anti-Cheating) ===

    def on_fullscreen_change(e):
        """Detect and prevent fullscreen exit during exam"""
        if not exam_state['enable_fullscreen_lock'] or not exam_state['fullscreen_lock_active']:
            return  # Feature not enabled or lock not active

        try:
            print(f"[FULLSCREEN] Window event detected: {e.data}")

            # Check if page reference is available
            if not exam_state.get('page_ref'):
                return

            page = exam_state['page_ref']

            # Re-enable fullscreen if it was disabled
            # This runs on any window event to catch fullscreen exits
            if hasattr(page, 'window_full_screen'):
                if not page.window_full_screen:
                    print(f"[FULLSCREEN] Fullscreen exit detected - re-enabling lock")
                    page.window_full_screen = True
                    page.update()

        except Exception as ex:
            print(f"[FULLSCREEN] Error handling fullscreen change: {ex}")

    def show_fullscreen_lock_banner():
        """Create the fullscreen lock warning banner"""
        if not exam_state['enable_fullscreen_lock']:
            return None

        lock_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.LOCK, color=ft.colors.BLUE_700, size=20),
                ft.Text(
                    "🔒 Fullscreen mode locked - Submit exam to exit",
                    size=14,
                    color=ft.colors.BLUE_700,
                    weight=ft.FontWeight.W_500
                )
            ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=ft.colors.BLUE_50,
            padding=10,
            border_radius=8,
            border=ft.border.all(1, ft.colors.BLUE_400)
        )

        return lock_banner

    def create_question_content():
        """Create the current question display"""
        if not questions or exam_state['current_question_index'] >= len(questions):
            return ft.Text("Loading question...", size=16)
        
        current_question = questions[exam_state['current_question_index']]
        
        # Question text
        question_text = ft.Text(
            current_question['question_text'],
            size=18,
            color=EXAM_COLORS['text_primary'],
            selectable=True
        )
        
        # Question image (if present)
        question_image = render_question_image(current_question.get('image_path'))
        
        # Answer section based on question type
        if current_question['question_type'] == 'single_choice':
            options = get_question_options(current_question['id'])
            selected_answer = exam_state['user_answers'].get(current_question['id'], {}).get('selected_option_id')
            
            def on_radio_change(e):
                save_answer(current_question['id'], {'selected_option_id': e.control.value})
            
            radio_options = []
            for option in options:
                radio_options.append(
                    ft.Radio(
                        value=option['id'],
                        label=option['option_text']
                    )
                )
            
            answer_section = ft.RadioGroup(
                value=selected_answer,
                on_change=on_radio_change,
                content=ft.Column(radio_options, spacing=8)
            )
            
        elif current_question['question_type'] == 'true_false':
            selected_answer = exam_state['user_answers'].get(current_question['id'], {}).get('answer_text')
            
            def on_tf_change(e):
                save_answer(current_question['id'], {'answer_text': e.control.value})
            
            answer_section = ft.RadioGroup(
                value=selected_answer,
                on_change=on_tf_change,
                content=ft.Column([
                    ft.Radio(value="True", label="True"),
                    ft.Radio(value="False", label="False")
                ], spacing=8)
            )
            
        elif current_question['question_type'] == 'short_answer':
            selected_answer = exam_state['user_answers'].get(current_question['id'], {}).get('answer_text', '')
            
            def on_text_change(e):
                # Store in exam_state only, don't save to database on keystroke
                exam_state['user_answers'][current_question['id']] = {'answer_text': e.control.value}
            
            answer_section = ft.TextField(
                label="Your answer",
                value=selected_answer,
                on_change=on_text_change,
                multiline=False,
                max_lines=3
            )
            
        elif current_question['question_type'] == 'essay':
            selected_answer = exam_state['user_answers'].get(current_question['id'], {}).get('answer_text', '')
            
            def on_essay_change(e):
                # Store in exam_state only, don't save to database on keystroke
                exam_state['user_answers'][current_question['id']] = {'answer_text': e.control.value}
            
            answer_section = ft.TextField(
                label="Your essay response",
                value=selected_answer,
                on_change=on_essay_change,
                multiline=True,
                min_lines=6,
                max_lines=12
            )
            
        elif current_question['question_type'] == 'multiple_choice':
            options = get_question_options(current_question['id'])
            
            # Get previously selected options 
            saved_answer = exam_state['user_answers'].get(current_question['id'], {})
            selected_options = saved_answer.get('selected_option_ids', [])
            if isinstance(selected_options, str):
                selected_options = json.loads(selected_options) if selected_options else []
            elif selected_options is None:
                selected_options = []
            
            def on_checkbox_change(option_id, is_checked):
                # Create a fresh copy of selected options to avoid reference issues
                current_selected = exam_state['user_answers'].get(current_question['id'], {}).get('selected_option_ids', [])
                if isinstance(current_selected, str):
                    current_selected = json.loads(current_selected) if current_selected else []
                elif current_selected is None:
                    current_selected = []
                else:
                    current_selected = list(current_selected)  # Make a copy
                
                # Update the selection
                if is_checked and option_id not in current_selected:
                    current_selected.append(option_id)
                elif not is_checked and option_id in current_selected:
                    current_selected.remove(option_id)
                
                # Save the updated selection
                save_answer(current_question['id'], {'selected_option_ids': current_selected})
                
                # Note: Removed page.update() here to prevent unfocus issues
            
            checkbox_options = []
            for option in options:
                checkbox_options.append(
                    ft.Checkbox(
                        label=option['option_text'],
                        value=option['id'] in selected_options,
                        on_change=lambda e, opt_id=option['id']: on_checkbox_change(opt_id, e.control.value)
                    )
                )
            
            answer_section = ft.Column([
                ft.Text("Select all that apply:", size=14, color=EXAM_COLORS['text_secondary'], italic=True),
                ft.Container(height=8),
                ft.Column(checkbox_options, spacing=8)
            ], spacing=0)
            
        else:
            answer_section = ft.Text(f"Question type '{current_question['question_type']}' not yet implemented")
        
        # Mark for review checkbox
        def toggle_mark_for_review(e):
            question_id = current_question['id']
            if e.control.value:
                exam_state['marked_for_review'].add(question_id)
            else:
                exam_state['marked_for_review'].discard(question_id)
            
            # Update UI if page is available
            if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page') and exam_state['main_container'].page:
                exam_state['main_container'].page.update()
        
        mark_review_checkbox = ft.Checkbox(
            label="Mark for review",
            value=current_question['id'] in exam_state['marked_for_review'],
            on_change=toggle_mark_for_review
        )
        
        return ft.Column([
            question_text,
            ft.Container(height=15),  # Spacing after question text
            question_image,
            ft.Container(height=20),  # Spacing after image before answers
            answer_section,
            ft.Container(height=20),
            mark_review_checkbox
        ], spacing=0)
    
    def create_main_content():
        """Create main exam content"""
        # Progress header
        current_q = exam_state['current_question_index'] + 1
        total_q = len(questions)
        answered_count = len(exam_state['user_answers'])
        
        # Get current question points for display
        current_question = questions[exam_state['current_question_index']] if questions else None
        question_points = current_question['points'] if current_question and 'points' in current_question else 1.0
        
        progress_header = ft.Container(
            content=ft.Row([
                ft.Text(f"Question {current_q} of {total_q}", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text(f"Points: {question_points}", size=14, color=EXAM_COLORS['text_secondary'], weight=ft.FontWeight.W_500)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.only(bottom=20)
        )
        
        # Navigation buttons
        def go_previous(e):
            if exam_state['current_question_index'] > 0:
                # Save current answer before navigation
                save_current_answer()
                exam_state['current_question_index'] -= 1
                exam_state['main_container'].content = create_main_content()

                # Update page
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page') and exam_state['main_container'].page:
                    exam_state['main_container'].page.update()

        def go_next(e):
            if exam_state['current_question_index'] < len(questions) - 1:
                # Save current answer before navigation
                save_current_answer()
                exam_state['current_question_index'] += 1
                exam_state['main_container'].content = create_main_content()

                # Update page
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page') and exam_state['main_container'].page:
                    exam_state['main_container'].page.update()
        
        def navigate_to_question(index):
            if 0 <= index < len(questions):
                # Track time on current question before leaving
                current_q = questions[exam_state['current_question_index']]
                track_question_time(current_q['id'])

                # Save current answer before navigation
                save_current_answer()
                exam_state['current_question_index'] = index

                # Start timer for new question
                new_q = questions[index]
                start_question_timer(new_q['id'])

                # Update UI with new question content
                exam_state['main_container'].content = create_main_content()

                # Update page
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page') and exam_state['main_container'].page:
                    exam_state['main_container'].page.update()
                else:
                    print("[NAV] Warning: No page reference available for navigation update")
        
        def submit_exam(e):
            """Show confirmation dialog before submitting exam"""
            try:
                # Get page context for dialog
                page = None
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page
                
                if not page:
                    print("Warning: No page context available for exam submission dialog")
                    # Fallback to direct submission
                    submit_exam_final()
                    return
                
                # Count answered vs unanswered questions
                answered_count = len(exam_state['user_answers'])
                total_count = len(questions)
                unanswered_count = total_count - answered_count
                
                # Create confirmation message
                if unanswered_count > 0:
                    content_text = f"You have answered {answered_count} out of {total_count} questions.\n\n⚠️ {unanswered_count} questions remain unanswered.\n\nAre you sure you want to submit your exam?"
                    title_text = "Submit Exam - Unanswered Questions"
                    title_color = EXAM_COLORS['warning']
                    title_icon = ft.icons.WARNING
                else:
                    content_text = f"You have answered all {total_count} questions.\n\nAre you sure you want to submit your exam?"
                    title_text = "Submit Exam"
                    title_color = EXAM_COLORS['primary']
                    title_icon = ft.icons.SEND
                
                # Create confirmation dialog
                submit_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Row([
                        ft.Icon(title_icon, color=title_color, size=24),
                        ft.Text(title_text, color=title_color, weight=ft.FontWeight.BOLD)
                    ], spacing=8),
                    content=ft.Text(content_text, size=16),
                    actions=[
                        ft.TextButton(
                            "Cancel",
                            on_click=lambda e: close_submit_dialog()
                        ),
                        ft.ElevatedButton(
                            "Submit Exam",
                            on_click=lambda e: confirm_submit_exam(),
                            style=ft.ButtonStyle(
                                bgcolor=EXAM_COLORS['primary'],
                                color=ft.colors.WHITE
                            )
                        )
                    ]
                )
                
                # Show dialog
                page.dialog = submit_dialog
                submit_dialog.open = True
                page.update()
                
            except Exception as ex:
                print(f"Error showing submit confirmation: {ex}")
                # Fallback to direct submission
                submit_exam_final()
        
        def close_submit_dialog():
            """Close the submit confirmation dialog"""
            try:
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page
                    if page and page.dialog:
                        page.dialog.open = False
                        page.update()
            except Exception as ex:
                print(f"Error closing submit dialog: {ex}")
        
        def confirm_submit_exam():
            """Confirmed exam submission - close dialog and submit"""
            try:
                close_submit_dialog()
                submit_exam_final()
            except Exception as ex:
                print(f"Error confirming exam submission: {ex}")
                submit_exam_final()
        
        def submit_exam_final():
            """Final exam submission with proper processing"""
            try:
                # Track time for current question before submission
                if questions and exam_state['current_question_index'] < len(questions):
                    current_q = questions[exam_state['current_question_index']]
                    track_question_time(current_q['id'])

                # Save current answer before final submission
                save_current_answer()

                exam_state['timer_running'] = False  # Stop timer
                
                # Calculate exam duration
                exam_duration = datetime.now() - exam_state['start_time']
                duration_seconds = int(exam_duration.total_seconds())
                
                # Calculate exam results
                total_questions = len(questions)
                
                # Get the consistent session_id for database operations
                session_id = exam_state['session_id']
                
                # Count answered questions and calculate weighted scores
                answered_questions = 0
                correct_answers = 0
                total_points = 0
                earned_points = 0
                
                # CRITICAL FIX: Calculate total points for ALL questions first
                for question in questions:
                    question_points = question.get('points', 1.0)
                    total_points += question_points  # Always add to total, regardless of answer
                
                # Calculate score based on correct answers from database
                print(f"Starting score calculation for session {session_id} with {total_questions} questions")
                print(f"Total possible points: {total_points}")
                
                for question in questions:
                    question_id = question['id']
                    question_points = question.get('points', 1.0)  # Get question points
                    
                    # Get the latest answer from database instead of in-memory data
                    user_answer = get_user_answer_from_db(session_id, question_id)
                    if user_answer:
                        answered_questions += 1  # Count this as answered
                        print(f"Question {question_id} ({question['question_type']}) [{question_points}pts]: {user_answer}")
                        
                        # Check if answer is correct based on question type
                        if question['question_type'] in ['single_choice']:
                            # For single choice, check if selected option is correct
                            if 'selected_option_id' in user_answer:
                                correct_option = db.execute_single("""
                                    SELECT * FROM question_options 
                                    WHERE question_id = ? AND is_correct = 1
                                """, (question_id,))
                                
                                if correct_option and user_answer['selected_option_id'] == correct_option['id']:
                                    correct_answers += 1
                                    earned_points += question_points
                                    
                        elif question['question_type'] == 'multiple_choice':
                            # For multiple choice, check if all selected options are correct
                            if 'selected_option_ids' in user_answer and user_answer['selected_option_ids']:
                                # Handle both string (from database) and list (from UI) formats
                                if isinstance(user_answer['selected_option_ids'], str):
                                    selected_ids = json.loads(user_answer['selected_option_ids'])
                                else:
                                    selected_ids = user_answer['selected_option_ids']
                                correct_options = db.execute_query("""
                                    SELECT id FROM question_options 
                                    WHERE question_id = ? AND is_correct = 1
                                """, (question_id,))
                                
                                correct_ids = [opt['id'] for opt in correct_options]
                                
                                # Check if selected options match exactly with correct options
                                if set(selected_ids) == set(correct_ids) and len(selected_ids) > 0:
                                    correct_answers += 1
                                    earned_points += question_points
                                    
                        elif question['question_type'] == 'true_false':
                            # For true/false, check against correct_answer field
                            if 'answer_text' in user_answer:
                                correct_answer = question['correct_answer']
                                if correct_answer and user_answer['answer_text'].lower() == correct_answer.lower():
                                    correct_answers += 1
                                    earned_points += question_points
                                    
                        # For essay/short_answer questions, use instructor-awarded points if available
                        elif question['question_type'] in ['short_answer', 'essay']:
                            if 'answer_text' in user_answer and user_answer['answer_text'].strip():
                                # Get the latest points from database (instructor might have graded)
                                db_answer = db.execute_single("""
                                    SELECT points_earned, is_correct 
                                    FROM user_answers 
                                    WHERE session_id = ? AND question_id = ?
                                    ORDER BY answered_at DESC LIMIT 1
                                """, (session_id, question_id))
                                
                                if db_answer and db_answer['points_earned'] is not None:
                                    # Instructor has graded this question - only add to earned points
                                    earned_points += db_answer['points_earned']
                                    if db_answer['is_correct']:
                                        correct_answers += 1
                                # If not graded yet (points_earned is NULL), don't count in score calculation
                
                # Calculate percentage score based on weighted points
                score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
                
                print(f"📊 EXAM SUBMISSION SCORING SUMMARY:")
                print(f"   Total questions in exam: {total_questions}")
                print(f"   Questions answered: {answered_questions}")
                print(f"   Correct answers: {correct_answers}")
                print(f"   Points earned: {earned_points}/{total_points}")
                print(f"   Final score: {score_percentage:.1f}%")
                
                # Create exam session record with predetermined ID
                try:
                    db.execute_update("""
                        INSERT INTO exam_sessions (
                            id, user_id, exam_id, assignment_id, start_time, end_time, duration_seconds,
                            score, total_questions, correct_answers, status, attempt_number, is_completed, focus_loss_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        user_data['id'],
                        actual_exam_id,
                        assignment_id,
                        exam_state['start_time'].isoformat(),
                        datetime.now().isoformat(),
                        duration_seconds,
                        score_percentage,
                        total_questions,
                        correct_answers,
                        'completed',
                        1,  # TODO: Calculate actual attempt number
                        True,
                        0  # No longer tracking focus loss
                    ))
                except Exception as db_ex:
                    print(f"Database insert failed, trying without explicit ID: {db_ex}")
                    # Fallback to auto-generated ID
                    session_id = db.execute_insert("""
                        INSERT INTO exam_sessions (
                            user_id, exam_id, assignment_id, start_time, end_time, duration_seconds,
                            score, total_questions, correct_answers, status, attempt_number, is_completed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        user_data['id'],
                        actual_exam_id,
                        assignment_id,
                        exam_state['start_time'].isoformat(),
                        datetime.now().isoformat(),
                        duration_seconds,
                        score_percentage,
                        total_questions,
                        correct_answers,
                        'completed',
                        1,
                        True
                    ))
                
                print(f"Exam session created with consistent ID: {session_id}")
                print(f"Total answers saved: {len(exam_state['user_answers'])}")

                # Log exam submission
                try:
                    audit_logger = get_audit_logger()
                    audit_logger.log_exam_submit(
                        user_id=user_data['id'],
                        exam_id=exam_data['id'],
                        session_id=session_id,
                        score=score_percentage,
                        duration_seconds=duration_seconds
                    )
                except Exception as log_ex:
                    print(f"[AUDIT ERROR] Failed to log exam submission: {log_ex}")

                # Run pattern analysis if enabled
                if exam_data.get('enable_pattern_analysis', False):
                    try:
                        from quiz_app.utils.pattern_analyzer import get_pattern_analyzer
                        analyzer = get_pattern_analyzer()
                        analysis_result = analyzer.analyze_session(session_id)

                        if analysis_result['suspicion_score'] > 0:
                            print(f"[PATTERN] ⚠️  Suspicious activity detected! Score: {analysis_result['suspicion_score']}")
                            print(f"[PATTERN] Issues: {', '.join(analysis_result['issues_detected'])}")
                    except Exception as pattern_ex:
                        print(f"[PATTERN ERROR] Failed to analyze exam session: {pattern_ex}")

                # No need to update user_answers - they already have the correct session_id

                # Show results with calculated scores
                show_exam_results(
                    total_questions,
                    answered_questions,
                    correct_answers,
                    score_percentage,
                    exam_data['passing_score']
                )
                
            except Exception as ex:
                print(f"Error during final exam submission: {ex}")
                import traceback
                traceback.print_exc()
                # Try to calculate basic results even if database operations fail
                try:
                    total_questions = len(questions)
                    answered_questions = len(exam_state['user_answers'])
                    # Use a simple fallback calculation based on answered questions
                    fallback_score = (answered_questions / total_questions * 100) if total_questions > 0 else 0
                    show_exam_results(total_questions, answered_questions, answered_questions, fallback_score, exam_data.get('passing_score', 70))
                except:
                    # Last resort fallback
                    show_exam_results(len(questions), 0, 0, 0, 70)
        
        def show_simple_submission_confirmation():
            """Show simple exam submission confirmation when results are hidden"""
            try:
                page = None
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page

                if not page:
                    print("No page context for submission confirmation - returning to dashboard")
                    if return_callback and callable(return_callback):
                        return_callback()
                    return

                def close_dialog(e):
                    # Deactivate fullscreen lock before exiting
                    if exam_state['enable_fullscreen_lock']:
                        exam_state['fullscreen_lock_active'] = False
                        print("[FULLSCREEN] Fullscreen lock released after exam submission")

                    if page and page.dialog:
                        page.dialog.open = False
                        page.update()
                    if return_callback and callable(return_callback):
                        return_callback()
                
                # Create simple confirmation dialog
                confirmation_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Exam Submitted", size=20, weight=ft.FontWeight.BOLD),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.CHECK_CIRCLE, color=EXAM_COLORS['success'], size=48),
                            ft.Text("Your exam has been submitted successfully.", size=16, text_align=ft.TextAlign.CENTER),
                            ft.Text("Results will be available when released by your instructor.", size=14, color=EXAM_COLORS['text_secondary'], text_align=ft.TextAlign.CENTER)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                        padding=ft.padding.all(20),
                        width=400
                    ),
                    actions=[
                        ft.ElevatedButton(
                            "Return to Dashboard",
                            on_click=close_dialog,
                            style=ft.ButtonStyle(bgcolor=EXAM_COLORS['primary'], color=ft.colors.WHITE)
                        )
                    ],
                    actions_alignment=ft.MainAxisAlignment.CENTER
                )
                
                page.dialog = confirmation_dialog
                confirmation_dialog.open = True
                page.update()
                
            except Exception as e:
                print(f"Error showing submission confirmation: {e}")
                if return_callback and callable(return_callback):
                    return_callback()
        
        def show_pending_release_confirmation():
            """Show confirmation when exam is fully graded but results not released"""
            try:
                page = None
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page

                if not page:
                    print("No page context for pending release confirmation - returning to dashboard")
                    if return_callback and callable(return_callback):
                        return_callback()
                    return

                def close_dialog(e):
                    # Deactivate fullscreen lock before exiting
                    if exam_state['enable_fullscreen_lock']:
                        exam_state['fullscreen_lock_active'] = False
                        print("[FULLSCREEN] Fullscreen lock released after exam submission")

                    if page and page.dialog:
                        page.dialog.open = False
                        page.update()
                    if return_callback and callable(return_callback):
                        return_callback()
                
                # Create pending release dialog
                confirmation_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Exam Submitted", size=20, weight=ft.FontWeight.BOLD),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.SCHEDULE, color=EXAM_COLORS['warning'], size=48),
                            ft.Text("Your exam has been graded.", size=16, text_align=ft.TextAlign.CENTER),
                            ft.Text("Results are pending release by your instructor.", size=14, color=EXAM_COLORS['text_secondary'], text_align=ft.TextAlign.CENTER)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                        padding=ft.padding.all(20),
                        width=400
                    ),
                    actions=[
                        ft.ElevatedButton(
                            "Return to Dashboard",
                            on_click=close_dialog,
                            style=ft.ButtonStyle(bgcolor=EXAM_COLORS['primary'], color=ft.colors.WHITE)
                        )
                    ],
                    actions_alignment=ft.MainAxisAlignment.CENTER
                )
                
                page.dialog = confirmation_dialog
                confirmation_dialog.open = True
                page.update()
                
            except Exception as e:
                print(f"Error showing pending release confirmation: {e}")
                if return_callback and callable(return_callback):
                    return_callback()
        
        def show_exam_results(total_questions, answered_questions, correct_answers=0, score_percentage=0, passing_score=70):
            """Show comprehensive exam results dialog"""
            try:
                # Check if exam has essay/short_answer questions that need manual grading
                has_ungraded_manual_questions = False
                session_id = exam_state['session_id']
                
                try:
                    ungraded_manual = db.execute_query("""
                        SELECT COUNT(*) as count
                        FROM user_answers ua
                        JOIN questions q ON ua.question_id = q.id
                        WHERE ua.session_id = ?
                        AND q.question_type IN ('essay', 'short_answer')
                        AND ua.points_earned IS NULL
                        AND ua.answer_text IS NOT NULL
                        AND ua.answer_text != ''
                    """, (session_id,))
                    
                    has_ungraded_manual_questions = ungraded_manual[0]['count'] > 0 if ungraded_manual else False
                except Exception as e:
                    print(f"Error checking ungraded manual questions: {e}")
                    has_ungraded_manual_questions = False
                
                # If there are ungraded essay/short_answer questions, always show pending message
                if has_ungraded_manual_questions:
                    show_simple_submission_confirmation()
                    return
                
                # Check if results should be shown to students (for fully graded exams)
                if not exam_data.get('show_results', 1):
                    # All questions graded but results not released yet
                    show_pending_release_confirmation()
                    return
                
                page = None
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page
                
                if not page:
                    print("No page context for results dialog - returning to dashboard")
                    if return_callback and callable(return_callback):
                        return_callback()
                    return
                
                # Determine pass/fail status
                passed = score_percentage >= passing_score
                incorrect_answers = answered_questions - correct_answers
                unanswered_questions = total_questions - answered_questions
                
                # Calculate time taken
                exam_duration = datetime.now() - exam_state['start_time']
                time_taken_minutes = int(exam_duration.total_seconds() / 60)
                time_taken_seconds = int(exam_duration.total_seconds() % 60)
                
                # Choose colors and icons based on pass/fail
                if passed:
                    result_color = EXAM_COLORS['success']
                    result_icon = ft.icons.CHECK_CIRCLE
                    result_text = "Exam Passed!"
                else:
                    result_color = EXAM_COLORS['error']
                    result_icon = ft.icons.CANCEL
                    result_text = "Exam Failed"
                
                # Create detailed results content
                results_content = ft.Column([
                    # Main result message
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(result_icon, color=result_color, size=32),
                            ft.Text(result_text, size=20, weight=ft.FontWeight.BOLD, color=result_color)
                        ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
                        padding=ft.padding.only(bottom=20)
                    ),
                    
                    # Score display
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"{score_percentage:.1f}%", size=36, weight=ft.FontWeight.BOLD, color=result_color),
                            ft.Text(f"Passing Score: {passing_score}%", size=14, color=EXAM_COLORS['text_secondary'])
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.all(15),
                        bgcolor=ft.colors.with_opacity(0.1, result_color),
                        border_radius=8
                    ),
                    
                    # Detailed breakdown
                    ft.Container(height=10),
                    ft.Row([
                        ft.Icon(ft.icons.CHECK, color=EXAM_COLORS['success'], size=20),
                        ft.Text(f"Correct: {correct_answers}", size=16)
                    ], spacing=8),
                    ft.Row([
                        ft.Icon(ft.icons.CLOSE, color=EXAM_COLORS['error'], size=20),
                        ft.Text(f"Incorrect: {incorrect_answers}", size=16)
                    ], spacing=8),
                    ft.Row([
                        ft.Icon(ft.icons.HELP_OUTLINE, color=EXAM_COLORS['warning'], size=20),
                        ft.Text(f"Unanswered: {unanswered_questions}", size=16)
                    ], spacing=8),
                    ft.Row([
                        ft.Icon(ft.icons.TIMER, color=EXAM_COLORS['text_secondary'], size=20),
                        ft.Text(f"Time Taken: {time_taken_minutes}m {time_taken_seconds}s", size=16)
                    ], spacing=8),
                    
                    ft.Container(height=15),
                    ft.Divider(),
                    ft.Container(height=10),
                    
                    # Additional info
                    ft.Text(
                        "Your results have been saved and will be available in your dashboard.",
                        size=14,
                        color=EXAM_COLORS['text_secondary'],
                        italic=True,
                        text_align=ft.TextAlign.CENTER
                    )
                ], tight=True, spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                
                results_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Row([
                        ft.Icon(ft.icons.ASSESSMENT, color=EXAM_COLORS['primary'], size=24),
                        ft.Text("Exam Results", color=EXAM_COLORS['primary'], weight=ft.FontWeight.BOLD)
                    ], spacing=8),
                    content=ft.Container(
                        content=results_content,
                        width=400,
                        padding=ft.padding.all(10)
                    ),
                    actions=[
                        ft.ElevatedButton(
                            "Return to Dashboard",
                            on_click=lambda e: return_to_dashboard(),
                            style=ft.ButtonStyle(
                                bgcolor=EXAM_COLORS['primary'],
                                color=ft.colors.WHITE
                            )
                        )
                    ]
                )
                
                page.dialog = results_dialog
                results_dialog.open = True
                page.update()
                
            except Exception as ex:
                print(f"Error showing exam results: {ex}")
                # Fallback - just return to dashboard
                if return_callback and callable(return_callback):
                    return_callback()
        
        def return_to_dashboard():
            """Return to dashboard from results dialog"""
            try:
                # Deactivate fullscreen lock before exiting
                if exam_state['enable_fullscreen_lock']:
                    exam_state['fullscreen_lock_active'] = False
                    print("[FULLSCREEN] Fullscreen lock released after exam submission")

                # Close dialog first
                page = None
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page
                if page and page.dialog:
                    page.dialog.open = False
                    page.update()

                # Then return to dashboard (this will restore fullscreen state via callback)
                if return_callback and callable(return_callback):
                    return_callback()
                else:
                    print("Error: Invalid or missing return_callback for dashboard return")
                    
            except Exception as ex:
                print(f"Error returning to dashboard: {ex}")
                # Try to call return_callback anyway
                if return_callback and callable(return_callback):
                    try:
                        return_callback()
                    except Exception as callback_ex:
                        print(f"Error calling return_callback: {callback_ex}")
        
        navigation = ft.Row([
            ft.ElevatedButton(
                "← Previous",
                disabled=exam_state['current_question_index'] == 0,
                on_click=go_previous
            ),
            ft.Container(expand=True),
            ft.ElevatedButton(
                "Next →",
                disabled=exam_state['current_question_index'] >= len(questions) - 1,
                on_click=go_next
            )
        ])
        
        # Question content
        question_card = ft.Container(
            content=create_question_content(),
            padding=ft.padding.all(32),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=12
        )
        
        # Main content (70%) - Fixed navigation at bottom
        main_content = ft.Container(
            content=ft.Column([
                progress_header,
                ft.Container(
                    content=ft.Column([
                        question_card
                    ], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                    padding=ft.padding.symmetric(vertical=20)
                ),
                navigation  # Fixed at bottom, always visible
            ], spacing=0),
            expand=7,
            padding=ft.padding.only(right=10)
        )
        
        # Sidebar (30%)
        timer_display = ft.Text(
            f"{exam_state['time_remaining']//60:02d}:{exam_state['time_remaining']%60:02d}",
            size=24,
            weight=ft.FontWeight.BOLD
        )
        
        # Store timer display reference in exam_state
        exam_state['timer_display'] = timer_display
        
        timer_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.TIMER, size=24),
                    timer_display
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
                ft.Text("Time Remaining", size=12)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            padding=ft.padding.all(16),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=8
        )
        
        # Get exam template names for each question (for multi-template assignments)
        # Build a map of question_id -> exam_title
        question_to_exam_map = {}
        if assignment_id:
            # Multi-template assignment - get exam titles for each question
            exam_templates = db.execute_query("""
                SELECT DISTINCT e.id, e.title
                FROM assignment_exam_templates aet
                JOIN exams e ON aet.exam_id = e.id
                WHERE aet.assignment_id = ?
                ORDER BY aet.order_index
            """, (assignment_id,))

            # Map each question to its exam title
            for question in questions:
                for exam in exam_templates:
                    # Check if this question belongs to this exam
                    question_exam = db.execute_single("""
                        SELECT exam_id FROM questions WHERE id = ?
                    """, (question['id'],))

                    if question_exam and question_exam['exam_id'] == exam['id']:
                        question_to_exam_map[question['id']] = exam['title']
                        break
        else:
            # Single template - use exam title from exam_data
            exam_title = exam_data.get('title', 'Exam')
            for question in questions:
                question_to_exam_map[question['id']] = exam_title

        # Progress overview with per-exam breakdown
        # Group questions by exam template name for progress calculation
        topic_progress = {}
        for question in questions:
            exam_title = question_to_exam_map.get(question['id'], 'Unknown')
            if exam_title not in topic_progress:
                topic_progress[exam_title] = {'total': 0, 'answered': 0}
            topic_progress[exam_title]['total'] += 1
            if question['id'] in exam_state['user_answers']:
                topic_progress[exam_title]['answered'] += 1

        # Build progress display
        progress_items = [
            ft.Text("Progress Overview", size=14, weight=ft.FontWeight.BOLD),
            ft.Container(height=8),
            ft.Text(f"{answered_count} of {total_q} answered", size=16, weight=ft.FontWeight.W_500),
            ft.Container(height=8),
            ft.ProgressBar(
                value=answered_count/total_q if total_q > 0 else 0,
                height=8,
                color=EXAM_COLORS['primary'],
                bgcolor=EXAM_COLORS['unanswered']
            )
        ]

        # Add per-topic progress if multiple topics exist
        if len(topic_progress) > 1:
            progress_items.append(ft.Container(height=12))
            progress_items.append(ft.Divider(height=1, color=EXAM_COLORS['border']))
            progress_items.append(ft.Container(height=8))

            for topic in sorted(topic_progress.keys()):
                stats = topic_progress[topic]
                percentage = (stats['answered'] / stats['total'] * 100) if stats['total'] > 0 else 0

                progress_items.append(
                    ft.Row([
                        ft.Text(
                            f"{topic}:",
                            size=12,
                            color=EXAM_COLORS['text_secondary'],
                            weight=ft.FontWeight.W_500
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            f"{stats['answered']}/{stats['total']}",
                            size=12,
                            weight=ft.FontWeight.W_500
                        )
                    ], spacing=6)
                )

        progress_overview = ft.Container(
            content=ft.Column(progress_items, spacing=4),
            padding=ft.padding.all(16),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=8
        )
        
        # Question Navigator/Palette - Grouped by Exam Template Name
        # Group questions by their original exam template
        topic_groups = {}
        topic_question_indices = {}  # Map exam_title to list of question indices

        for i in range(len(questions)):
            exam_title = question_to_exam_map.get(questions[i]['id'], 'Unknown')
            if exam_title not in topic_groups:
                topic_groups[exam_title] = []
                topic_question_indices[exam_title] = []
            topic_groups[exam_title].append(questions[i])
            topic_question_indices[exam_title].append(i)

        # Build navigator with topic groups
        navigator_sections = []

        for topic in sorted(topic_groups.keys()):
            topic_questions = topic_groups[topic]
            topic_indices = topic_question_indices[topic]

            # Calculate topic progress
            topic_answered = sum(1 for q in topic_questions if q['id'] in exam_state['user_answers'])
            topic_total = len(topic_questions)

            # Topic header
            topic_header = ft.Container(
                content=ft.Row([
                    ft.Text(
                        f"{topic} ({topic_indices[0] + 1}-{topic_indices[-1] + 1})",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=EXAM_COLORS['text_primary']
                    ),
                    ft.Container(expand=True),
                    ft.Text(
                        f"{topic_answered}/{topic_total}",
                        size=11,
                        color=EXAM_COLORS['text_secondary']
                    )
                ], spacing=6),
                padding=ft.padding.only(top=8, bottom=4)
            )

            navigator_sections.append(topic_header)

            # Create question buttons for this topic
            topic_buttons = []
            for idx in topic_indices:
                question_id = questions[idx]['id']
                is_current = idx == exam_state['current_question_index']
                is_answered = question_id in exam_state['user_answers']
                is_marked = question_id in exam_state['marked_for_review']

                # Determine button color priority: current > marked > answered > unanswered
                if is_current:
                    bg_color = EXAM_COLORS['current']
                    text_color = ft.colors.WHITE
                elif is_marked:
                    bg_color = EXAM_COLORS['marked']
                    text_color = ft.colors.WHITE
                elif is_answered:
                    bg_color = EXAM_COLORS['answered']
                    text_color = ft.colors.WHITE
                else:
                    bg_color = EXAM_COLORS['unanswered']
                    text_color = EXAM_COLORS['text_primary']

                topic_buttons.append(
                    ft.Container(
                        content=ft.Text(
                            str(idx + 1),
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=text_color
                        ),
                        width=32,
                        height=32,
                        bgcolor=bg_color,
                        border_radius=4,
                        alignment=ft.alignment.center,
                        on_click=lambda e, i=idx: navigate_to_question(i)
                    )
                )

            # Create rows of 5 buttons each for this topic
            topic_rows = []
            for i in range(0, len(topic_buttons), 5):
                row_buttons = topic_buttons[i:i+5]
                topic_rows.append(ft.Row(row_buttons, spacing=4))

            # Add topic button grid
            navigator_sections.append(
                ft.Container(
                    content=ft.Column(topic_rows, spacing=6),
                    padding=ft.padding.only(bottom=8)
                )
            )

        question_navigator = ft.Container(
            content=ft.Column([
                ft.Text("Question Navigator", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column(navigator_sections, spacing=4, scroll=ft.ScrollMode.AUTO),
                    height=280
                )
            ]),
            padding=ft.padding.all(16),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=8
        )
        
        # Color Legend
        color_legend = ft.Container(
            content=ft.Column([
                ft.Text("Color Legend", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                ft.Column([
                    ft.Row([
                        ft.Container(
                            width=16, height=16, 
                            bgcolor=EXAM_COLORS['current'], 
                            border_radius=2
                        ),
                        ft.Text("Current Question", size=12)
                    ], spacing=8),
                    ft.Row([
                        ft.Container(
                            width=16, height=16, 
                            bgcolor=EXAM_COLORS['answered'], 
                            border_radius=2
                        ),
                        ft.Text("Answered", size=12)
                    ], spacing=8),
                    ft.Row([
                        ft.Container(
                            width=16, height=16, 
                            bgcolor=EXAM_COLORS['marked'], 
                            border_radius=2
                        ),
                        ft.Text("Marked for Review", size=12)
                    ], spacing=8),
                    ft.Row([
                        ft.Container(
                            width=16, height=16, 
                            bgcolor=EXAM_COLORS['unanswered'], 
                            border_radius=2
                        ),
                        ft.Text("Not Answered", size=12)
                    ], spacing=8)
                ], spacing=6)
            ]),
            padding=ft.padding.all(16),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=8
        )
        
        # Submit Exam button for sidebar
        submit_exam_button = ft.Container(
            content=ft.ElevatedButton(
                "Submit Exam",
                width=200,
                height=45,
                on_click=submit_exam,
                style=ft.ButtonStyle(
                    bgcolor=EXAM_COLORS['error'], 
                    color=ft.colors.WHITE,
                    text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD)
                )
            ),
            padding=ft.padding.all(16),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=8,
            alignment=ft.alignment.center
        )
        
        sidebar = ft.Container(
            content=ft.Column([
                timer_section,
                ft.Container(height=20),
                progress_overview,
                ft.Container(height=20),
                question_navigator,
                ft.Container(height=20),
                color_legend,
                ft.Container(height=20),
                submit_exam_button
            ], spacing=0),
            expand=3,
            padding=ft.padding.only(left=10)
        )
        
        # Create column controls list
        column_controls = [
            # Header
            ft.Container(
                content=ft.Row([
                    ft.Row([
                        ft.Icon(ft.icons.QUIZ, color=EXAM_COLORS['primary'], size=24),
                        ft.Text(exam_data['title'], size=20, weight=ft.FontWeight.BOLD)
                    ], spacing=8),
                    ft.Row([
                        ft.Icon(ft.icons.PERSON, color=EXAM_COLORS['text_secondary']),
                        ft.Text(user_data['full_name'], color=EXAM_COLORS['text_secondary']),
                        # ft.IconButton(
                        #     icon=ft.icons.HOME,
                        #     tooltip="Return to Dashboard",
                        #     on_click=lambda e: return_callback() if return_callback else None,
                        #     icon_color=EXAM_COLORS['text_secondary']
                        # )
                    ], spacing=8)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.symmetric(horizontal=24, vertical=16),
                bgcolor=EXAM_COLORS['surface'],
                border=ft.border.only(bottom=ft.BorderSide(1, EXAM_COLORS['border']))
            )
        ]

        # Fullscreen lock banner removed (feature temporarily disabled)

        # Add main content area
        column_controls.append(
            # Main content area
            ft.Container(
                content=ft.Row([
                    main_content,
                    ft.VerticalDivider(width=1, color=EXAM_COLORS['border']),
                    sidebar
                ], spacing=0),
                expand=True,
                padding=ft.padding.all(24),
                bgcolor=EXAM_COLORS['background']
            )
        )

        return ft.Column(column_controls, spacing=0)
    
    # Create the main container that will be returned
    main_container = ft.Container(
        content=create_main_content(),
        expand=True
    )

    # Store main container reference in exam_state
    exam_state['main_container'] = main_container

    # Note: Page reference and focus listener will be attached after container is added to page
    # This is handled in the did_mount equivalent when the container gets its page reference

    # Start timer for the first question
    if questions:
        first_question = questions[0]
        start_question_timer(first_question['id'])
        print(f"[TIME] Exam started - timer started for first question {first_question['id']}")

    # Log exam start
    try:
        audit_logger = get_audit_logger()
        audit_logger.log_exam_start(
            user_id=user_data['id'],
            exam_id=exam_data['id'],
            session_id=session_id,
            exam_title=exam_data['title']
        )
    except Exception as e:
        print(f"[AUDIT ERROR] Failed to log exam start: {e}")

    # Return the main container directly (no wrapper to avoid page reference issues)
    # Note: Fullscreen lock disabled for now due to technical limitations
    return main_container