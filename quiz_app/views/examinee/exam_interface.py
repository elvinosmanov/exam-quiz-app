import flet as ft
import json
import os
import base64
import threading
import time
from datetime import datetime, timedelta
from quiz_app.database.database import Database
from quiz_app.utils.localization import t


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

    def will_unmount(self):
        """Clean up when exam interface is unmounted - CRITICAL for allowing window close"""
        try:
            print("[DEBUG] ExamInterfaceWrapper will_unmount called - starting cleanup")

            # Mark exam as finished to prevent further timer updates
            self.exam_state['exam_finished'] = True
            self.exam_state['timer_running'] = False

            # Force restore window_prevent_close as primary failsafe
            if self.page and hasattr(self.page, 'window_prevent_close'):
                try:
                    self.page.window_prevent_close = False
                    print("[DEBUG] Forced window_prevent_close to False")
                except Exception as e:
                    print(f"[ERROR] Failed to restore window_prevent_close: {e}")

            # Restore all original page event handlers
            try:
                # Restore keyboard handler
                if self.exam_state.get('keyboard_hooked'):
                    original_handler = self.exam_state.get('original_keyboard_handler')
                    if self.page:
                        self.page.on_keyboard_event = original_handler
                        print("[DEBUG] Restored original keyboard handler")

                # Restore window event handler
                if self.exam_state.get('window_event_hooked'):
                    original_handler = self.exam_state.get('original_window_event')
                    if self.page:
                        self.page.on_window_event = original_handler
                        print("[DEBUG] Restored original window event handler")

                # Mark handlers as restored
                self.exam_state['handlers_restored'] = True

            except Exception as e:
                print(f"[ERROR] Failed to restore page handlers: {e}")

            # Release fullscreen lock
            if self.exam_state.get('enable_fullscreen_lock'):
                self.exam_state['fullscreen_lock_active'] = False
                print("[DEBUG] Released fullscreen lock")

            # Clean up any open dialogs
            try:
                if self.page and hasattr(self.page, 'dialog') and self.page.dialog:
                    self.page.dialog.open = False
                    self.page.dialog = None
                    print("[DEBUG] Closed any open dialogs")
            except Exception as e:
                print(f"[ERROR] Failed to close dialogs: {e}")

            print("[DEBUG] ExamInterfaceWrapper cleanup completed successfully")

        except Exception as ex:
            print(f"[CRITICAL ERROR] ExamInterfaceWrapper cleanup failed: {ex}")
            import traceback
            traceback.print_exc()

            # Last resort failsafe - force window_prevent_close to False no matter what
            try:
                if self.page and hasattr(self.page, 'window_prevent_close'):
                    self.page.window_prevent_close = False
                    print("[FAILSAFE] Force-disabled window_prevent_close in exception handler")
            except:
                pass
        finally:
            super().will_unmount()


class SubmitTrigger(ft.UserControl):
    """
    An invisible control that triggers a callback when mounted to the page.
    This is used to safely marshal a call from a background thread to the main UI thread.
    """
    def __init__(self, submit_callback, page_ref):
        super().__init__()
        self.submit_callback = submit_callback
        self.page_ref = page_ref

    def did_mount(self):
        """Called when control is added to the page - guaranteed to run on the UI thread."""
        try:
            if callable(self.submit_callback):
                print("[THREAD] SubmitTrigger mounted, invoking callback on main thread.")
                self.submit_callback()
        except Exception as e:
            print(f"[THREAD] Error executing submit callback from trigger: {e}")
        finally:
            # Clean up: remove self from overlay
            if self.page_ref and self.page_ref.overlay and self in self.page_ref.overlay:
                self.page_ref.overlay.remove(self)
                try:
                    self.page_ref.update()
                except Exception as update_err:
                    print(f"[THREAD] Error updating page after trigger cleanup: {update_err}")

    def build(self):
        # This control is invisible
        return ft.Container()


def create_exam_interface(exam_data, user_data, return_callback, exam_id=None, assignment_id=None, page=None):
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
            content=ft.Text(t('no_questions_found'), size=18),
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
        'page_ref': page,  # Reference to page for fullscreen/close handling
        'randomize_questions': exam_data.get('randomize_questions', False),  # Randomize answer options
        'shuffled_options_cache': {},  # Cache shuffled options for consistency during exam
        'original_window_event': None,
        'original_window_prevent_close': None,
        'original_keyboard_handler': None,
        'exam_finished': False,
        'exit_prompt_open': False,
        'handlers_restored': False,
        'keyboard_hooked': False,
        'window_event_hooked': False,
        'beforeunload_registered': False,
        'navigator_scroll_offset': 0  # Track navigation sidebar scroll position
    }
    
    def cleanup_page_handlers():
        """Restore original page event handlers and allow closing the window."""
        if exam_state.get('handlers_restored'):
            print("[CLEANUP] Handlers already restored. Skipping.")
            return

        print("[CLEANUP] Starting cleanup of page handlers...")
        page_ref = exam_state.get('page_ref')
        if not page_ref and exam_state.get('main_container') and hasattr(exam_state['main_container'], 'page'):
            page_ref = exam_state['main_container'].page

        try:
            if page_ref:
                print("[CLEANUP] Page reference found. Restoring handlers.")
                # Restore keyboard handler
                if exam_state.get('keyboard_hooked'):
                    page_ref.on_keyboard_event = exam_state.get('original_keyboard_handler')
                    print("[CLEANUP] Restored keyboard handler.")

                # Restore window event handler
                if exam_state.get('window_event_hooked'):
                    page_ref.on_window_event = exam_state.get('original_window_event')
                    print("[CLEANUP] Restored window event handler.")

                # CRITICAL: Force window_prevent_close to False to ensure exit is possible
                try:
                    if hasattr(page_ref, 'window_prevent_close'):
                        print(f"[CLEANUP] Current window_prevent_close: {page_ref.window_prevent_close}. Forcing to False.")
                        page_ref.window_prevent_close = False
                    else:
                        print("[CLEANUP] window_prevent_close attribute not found.")
                except Exception as e:
                    print(f"[CLEANUP] CRITICAL ERROR: Failed to set window_prevent_close to False: {e}")

                # Update the page to apply changes
                page_ref.update()
                print("[CLEANUP] Page updated.")

            else:
                print("[CLEANUP] WARNING: No page reference found during cleanup.")

        except Exception as handler_error:
            print(f"[CLEANUP] Error during handler restoration: {handler_error}")
        finally:
            if page_ref and exam_state.get('beforeunload_registered') and hasattr(page_ref, "run_javascript"):
                try:
                    page_ref.run_javascript("""
                        if (window.__examBeforeUnloadHandler) {
                            window.removeEventListener('beforeunload', window.__examBeforeUnloadHandler);
                            delete window.__examBeforeUnloadHandler;
                        }
                    """)
                    print("[CLEANUP] Removed 'beforeunload' browser handler.")
                except Exception as js_err:
                    print(f"[CLEANUP] Error removing 'beforeunload' handler: {js_err}")

            exam_state['handlers_restored'] = True
            exam_state['exam_finished'] = True
            print("[CLEANUP] Cleanup process finished.")

    def return_to_dashboard():
        """Return to dashboard safely, ensuring fullscreen and handlers are reset."""
        try:
            # Release fullscreen lock tracking
            if exam_state['enable_fullscreen_lock']:
                exam_state['fullscreen_lock_active'] = False
                print("[FULLSCREEN] Fullscreen lock released on exit")

            # Close any open dialog
            page_ref = None
            if exam_state.get('main_container') and hasattr(exam_state['main_container'], 'page'):
                page_ref = exam_state['main_container'].page
            if page_ref and page_ref.dialog:
                page_ref.dialog.open = False
                page_ref.update()

            cleanup_page_handlers()

            if return_callback and callable(return_callback):
                return_callback()
            else:
                print("Error: Invalid or missing return_callback for dashboard return")
        except Exception as ex:
            print(f"Error returning to dashboard: {ex}")
            if return_callback and callable(return_callback):
                try:
                    return_callback()
                except Exception as callback_ex:
                    print(f"Error calling return_callback: {callback_ex}")

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

    # Track if a text field is currently focused
    exam_state['text_field_focused'] = False

    # Keyboard shortcut handler
    def handle_keyboard_event(e):
        """Handle keyboard shortcuts: Arrow Left (previous), Arrow Right (next), M (mark for review)"""
        print(f"[KEYBOARD] Key pressed: {e.key}, text_field_focused: {exam_state.get('text_field_focused', False)}")

        # Skip shortcuts if user is typing in a text field
        if exam_state.get('text_field_focused', False):
            print(f"[KEYBOARD] Ignoring shortcut - user is typing in TextField")
            return

        if e.key == "Arrow Right" or e.key == "ArrowRight":
            # Next question
            if exam_state['current_question_index'] < len(questions) - 1:
                save_current_answer()
                exam_state['current_question_index'] += 1
                exam_state['main_container'].content = create_main_content()
                if exam_state['main_container'].page:
                    exam_state['main_container'].page.update()
                print(f"[KEYBOARD] Navigated to question {exam_state['current_question_index'] + 1}")

        elif e.key == "Arrow Left" or e.key == "ArrowLeft":
            # Previous question
            if exam_state['current_question_index'] > 0:
                save_current_answer()
                exam_state['current_question_index'] -= 1
                exam_state['main_container'].content = create_main_content()
                if exam_state['main_container'].page:
                    exam_state['main_container'].page.update()
                print(f"[KEYBOARD] Navigated to question {exam_state['current_question_index'] + 1}")

        elif e.key == "m" or e.key == "M":
            # Toggle mark for review
            current_question = questions[exam_state['current_question_index']]
            question_id = current_question['id']
            if question_id in exam_state['marked_for_review']:
                exam_state['marked_for_review'].discard(question_id)
                print(f"[KEYBOARD] Unmarked question {question_id}")
            else:
                exam_state['marked_for_review'].add(question_id)
                print(f"[KEYBOARD] Marked question {question_id}")
            exam_state['main_container'].content = create_main_content()
            if exam_state['main_container'].page:
                exam_state['main_container'].page.update()

    def register_beforeunload_handler():
        """Register browser beforeunload handler to warn users when closing tab."""
        if exam_state.get('beforeunload_registered'):
            return

        page_ref = exam_state.get('page_ref')
        if not page_ref or not hasattr(page_ref, "run_javascript"):
            return

        script = """
            if (!window.__examBeforeUnloadHandler) {
                window.__examBeforeUnloadHandler = function (event) {
                    event.preventDefault();
                    event.returnValue = "Exiting now will submit and finish your exam.";
                    return event.returnValue;
                };
                window.addEventListener("beforeunload", window.__examBeforeUnloadHandler);
            }
        """
        try:
            page_ref.run_javascript(script)
            exam_state['beforeunload_registered'] = True
            print("[EXIT] Browser beforeunload confirmation enabled")
        except Exception as js_error:
            print(f"[EXIT] Warning: Could not register beforeunload handler: {js_error}")

    def show_exit_confirmation():
        """Prompt the user before closing the window during an active exam."""
        if exam_state.get('exit_prompt_open'):
            return

        page_ref = exam_state.get('page_ref')
        if not page_ref and exam_state.get('main_container') and hasattr(exam_state['main_container'], 'page'):
            page_ref = exam_state['main_container'].page

        if not page_ref:
            print("[EXIT] No page reference available for exit confirmation. Submitting exam.")
            submit_exam_final()
            return

        def close_dialog(_=None):
            if page_ref.dialog:
                page_ref.dialog.open = False
                page_ref.update()
            exam_state['exit_prompt_open'] = False

        def confirm_exit(_=None):
            close_dialog()
            submit_exam_final()

        exit_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.WARNING, color=EXAM_COLORS['error'], size=24),
                ft.Text(t('confirm_submit'), color=EXAM_COLORS['error'], weight=ft.FontWeight.BOLD)
            ], spacing=8),
            content=ft.Text(
                t('confirm_submit_message'),
                size=15
            ),
            actions=[
                ft.TextButton(t('cancel'), on_click=close_dialog),
                ft.ElevatedButton(
                    t('submit_exam'),
                    on_click=confirm_exit,
                    style=ft.ButtonStyle(bgcolor=EXAM_COLORS['error'], color=ft.colors.WHITE)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        page_ref.dialog = exit_dialog
        exit_dialog.open = True
        page_ref.update()
        exam_state['exit_prompt_open'] = True

    def handle_window_event(e):
        """Handle global window events (close, fullscreen changes)."""
        if e.data == "close":
            if exam_state.get('exam_finished'):
                cleanup_page_handlers()
            else:
                show_exit_confirmation()
            return

        # Forward other events to fullscreen handler
        on_fullscreen_change(e)

    # Attach keyboard and window handlers if page is provided
    if page:
        exam_state['page_ref'] = page

        # Hook keyboard events
        try:
            exam_state['original_keyboard_handler'] = getattr(page, 'on_keyboard_event', None)
        except Exception as keyboard_get_error:
            print(f"[KEYBOARD] Could not read existing handler: {keyboard_get_error}")
            exam_state['original_keyboard_handler'] = None

        try:
            page.on_keyboard_event = handle_keyboard_event
            exam_state['keyboard_hooked'] = True
            print("[KEYBOARD] Keyboard shortcuts enabled: ← (previous), → (next), M (mark for review)")
        except Exception as keyboard_hook_error:
            exam_state['keyboard_hooked'] = False
            print(f"[KEYBOARD] Warning: Could not attach keyboard handler: {keyboard_hook_error}")

        window_obj = getattr(page, "_Page__window", None)
        window_control_available = window_obj is not None

        if window_control_available:
            try:
                exam_state['original_window_event'] = getattr(page, 'on_window_event', None)
            except Exception as window_get_error:
                print(f"[EXIT] Could not read existing window handler: {window_get_error}")
                exam_state['original_window_event'] = None

            if hasattr(page, 'window_prevent_close'):
                try:
                    exam_state['original_window_prevent_close'] = page.window_prevent_close
                    page.window_prevent_close = True
                except Exception as prevent_error:
                    print(f"[EXIT] Warning: Could not set window_prevent_close: {prevent_error}")
                    exam_state['original_window_prevent_close'] = None
            else:
                exam_state['original_window_prevent_close'] = None

            try:
                page.on_window_event = handle_window_event
                exam_state['window_event_hooked'] = True
                print("[EXIT] Native window close confirmation enabled during exam session")
            except Exception as window_hook_error:
                exam_state['window_event_hooked'] = False
                print(f"[EXIT] Warning: Window events not available ({window_hook_error})")
        else:
            exam_state['original_window_event'] = None
            exam_state['original_window_prevent_close'] = None
            exam_state['window_event_hooked'] = False
            register_beforeunload_handler()

    def get_question_options(question_id):
        """Get options for a question, with optional shuffling"""
        # Check if we've already shuffled this question's options
        if question_id in exam_state['shuffled_options_cache']:
            return exam_state['shuffled_options_cache'][question_id]

        # Get options from database
        options = db.execute_query("""
            SELECT * FROM question_options
            WHERE question_id = ?
            ORDER BY order_index, id
        """, (question_id,))

        # Shuffle options if randomization is enabled
        if exam_state['randomize_questions'] and options:
            # Check question type - don't shuffle true/false questions
            current_question = next((q for q in questions if q['id'] == question_id), None)
            if current_question and current_question['question_type'] != 'true_false':
                # Shuffle the options list
                import random
                options = list(options)  # Convert to list if needed
                random.shuffle(options)

        # Cache the shuffled (or original) options for consistency
        exam_state['shuffled_options_cache'][question_id] = options
        return options

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
    
    def render_question_image(question_id):
        """Render question image if present - loads from encrypted database"""
        if not question_id:
            return ft.Container()

        # Load image from encrypted database
        db = Database()
        image_data_dict = db.get_question_image(question_id)

        if not image_data_dict:
            return ft.Container()

        print(f"[IMAGE] Loading encrypted image from database for question {question_id}")

        # Convert binary data to base64 for display
        image_base64 = base64.b64encode(image_data_dict['data']).decode('utf-8')

        return ft.Container(
            content=ft.Column([
                ft.Image(
                    src_base64=image_base64,
                    width=600,
                    height=300,
                    fit=ft.ImageFit.CONTAIN,
                    border_radius=8,
                    error_content=ft.Text("Failed to load image", color=EXAM_COLORS['error'])
                ),
                ft.Container(height=8),
                ft.Text(
                    t('click_to_view'),
                    size=12,
                    color=EXAM_COLORS['text_secondary'],
                    italic=True
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(vertical=20, horizontal=10),
            bgcolor=ft.colors.with_opacity(0.02, EXAM_COLORS['primary']),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, EXAM_COLORS['border'])),
            on_click=lambda e, img=image_base64: show_image_fullscreen(img)
        )
    
    def show_image_fullscreen(image_base64):
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
                    title=ft.Text(t('question_image'), size=18, weight=ft.FontWeight.BOLD),
                    content=ft.Container(
                        content=ft.Image(
                            src_base64=image_base64,
                            width=800,
                            height=600,
                            fit=ft.ImageFit.CONTAIN,
                            error_content=ft.Text("Failed to load image", color=EXAM_COLORS['error'])
                        ),
                        width=800,
                        height=600,
                        alignment=ft.alignment.center
                    ),
                    actions=[
                        ft.TextButton(
                            t('close'),
                            on_click=close_image_dialog,
                            style=ft.ButtonStyle(color=EXAM_COLORS['primary'])
                        )
                    ]
                )

                page.dialog = image_dialog
                image_dialog.open = True
                page.update()
            else:
                print(f"Cannot show fullscreen image: Page not available")
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
                    # Check if answer is empty after trimming
                    trimmed_answer = (answer_data['answer_text'] or '').strip()
                    if not trimmed_answer:
                        # DELETE the old answer from database if user cleared the text
                        db.execute_update("""
                            DELETE FROM user_answers
                            WHERE session_id = ? AND question_id = ?
                        """, (session_id, question_id))

                        # Remove from exam_state if it exists
                        if question_id in exam_state['user_answers']:
                            del exam_state['user_answers'][question_id]

                        print(f"Deleted empty essay/short_answer for question {question_id}")
                        return

                    # Essay/short_answer questions need manual grading - set points_earned to NULL
                    db.execute_update("""
                        INSERT OR REPLACE INTO user_answers (
                            session_id, question_id, answer_text, points_earned, time_spent_seconds, answered_at
                        ) VALUES (?, ?, ?, NULL, ?, ?)
                    """, (session_id, question_id, trimmed_answer, time_spent, datetime.now().isoformat()))
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

            # This runs when time_remaining reaches 0 OR timer is manually stopped
            if exam_state['time_remaining'] <= 0 and exam_state['timer_running']:
                print("⏰ Time's up! Auto-submitting exam...")
                exam_state['timer_running'] = False

                page_ref = exam_state.get('page_ref')
                submit_callback = exam_state.get('submit_exam_final')

                if page_ref and callable(submit_callback) and hasattr(page_ref, 'overlay'):
                    # Use a trigger control to safely marshal the call to the main UI thread
                    print("[TIMER] Scheduling exam submission on main thread.")
                    submit_trigger = SubmitTrigger(submit_callback, page_ref)
                    page_ref.overlay.append(submit_trigger)
                    page_ref.update()
                elif callable(submit_callback):
                    # Fallback if page_ref is not available for some reason
                    print("[TIMER] WARNING: Page reference not found, calling submit directly (may be unsafe)")
                    submit_callback()
                else:
                    print("[TIMER] ERROR: submit_exam_final function not found in exam_state")
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
        
        # Question image (if present) - loaded from encrypted database
        question_image = render_question_image(current_question.get('id'))
        
        # Answer section based on question type
        if current_question['question_type'] == 'single_choice':
            options = get_question_options(current_question['id'])
            selected_answer = exam_state['user_answers'].get(current_question['id'], {}).get('selected_option_id')
            
            def on_radio_change(e):
                save_answer(current_question['id'], {'selected_option_id': e.control.value})
                # Update UI immediately to reflect answer selection
                print("[UI] Answer selected, updating UI...")
                try:
                    if exam_state['main_container'] and exam_state['main_container'].page:
                        exam_state['main_container'].content = create_main_content()
                        exam_state['main_container'].page.update()
                        print("[UI] UI updated successfully")
                    else:
                        print("[UI] WARNING: No page reference available")
                except Exception as ex:
                    print(f"[UI] ERROR updating UI: {ex}")
            
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
                # Update UI immediately to reflect answer selection
                exam_state['main_container'].content = create_main_content()
                exam_state['main_container'].page.update()
            
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

            def on_text_focus(e):
                exam_state['text_field_focused'] = True
                print("[KEYBOARD] TextField focused - shortcuts disabled")

            def on_text_blur(e):
                exam_state['text_field_focused'] = False
                print("[KEYBOARD] TextField blurred - shortcuts enabled")

            answer_section = ft.TextField(
                label=t('your_answer'),
                value=selected_answer,
                on_change=on_text_change,
                on_focus=on_text_focus,
                on_blur=on_text_blur,
                multiline=False,
                max_lines=3
            )
            
        elif current_question['question_type'] == 'essay':
            selected_answer = exam_state['user_answers'].get(current_question['id'], {}).get('answer_text', '')

            def on_essay_change(e):
                # Store in exam_state only, don't save to database on keystroke
                exam_state['user_answers'][current_question['id']] = {'answer_text': e.control.value}

            def on_essay_focus(e):
                exam_state['text_field_focused'] = True
                print("[KEYBOARD] TextField focused - shortcuts disabled")

            def on_essay_blur(e):
                exam_state['text_field_focused'] = False
                print("[KEYBOARD] TextField blurred - shortcuts enabled")

            answer_section = ft.TextField(
                label=t('your_answer'),
                value=selected_answer,
                on_change=on_essay_change,
                on_focus=on_essay_focus,
                on_blur=on_essay_blur,
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

                # Update UI immediately to reflect answer selection
                print("[UI] Checkbox answer selected, updating UI...")
                try:
                    if exam_state['main_container'] and exam_state['main_container'].page:
                        exam_state['main_container'].content = create_main_content()
                        exam_state['main_container'].page.update()
                        print("[UI] UI updated successfully")
                    else:
                        print("[UI] WARNING: No page reference available")
                except Exception as ex:
                    print(f"[UI] ERROR updating UI: {ex}")
            
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
                ft.Text(t('select_answer'), size=14, color=EXAM_COLORS['text_secondary'], italic=True),
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

            # Update UI immediately to reflect mark change
            exam_state['main_container'].content = create_main_content()
            exam_state['main_container'].page.update()
        
        mark_review_checkbox = ft.Checkbox(
            label=t('mark_for_review'),
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
                ft.Text(f"{t('question')} {current_q} {t('of')} {total_q}", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Text(f"{t('points')}: {question_points}", size=14, color=EXAM_COLORS['text_secondary'], weight=ft.FontWeight.W_500)
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
                            t('cancel'),
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

        def check_and_archive_assignment(assignment_id):
            """Check if all users completed the assignment and archive if so"""
            try:
                # Get total assigned users count
                total_stats = db.execute_single("""
                    SELECT COUNT(DISTINCT user_id) as total_assigned
                    FROM assignment_users
                    WHERE assignment_id = ? AND is_active = 1
                """, (assignment_id,))

                # Get assignment max_attempts to check if users exhausted all attempts
                assignment_info = db.execute_single("""
                    SELECT max_attempts
                    FROM exam_assignments
                    WHERE id = ?
                """, (assignment_id,))

                if total_stats and assignment_info:
                    total_assigned = total_stats['total_assigned']
                    max_attempts = assignment_info['max_attempts']

                    # Count how many users have used ALL their attempts
                    users_at_max = db.execute_query("""
                        SELECT au.user_id, COUNT(es.id) as attempt_count
                        FROM assignment_users au
                        LEFT JOIN exam_sessions es ON au.user_id = es.user_id
                            AND es.assignment_id = au.assignment_id
                        WHERE au.assignment_id = ? AND au.is_active = 1
                        GROUP BY au.user_id
                        HAVING attempt_count >= ?
                    """, (assignment_id, max_attempts))

                    users_at_max_count = len(users_at_max)

                    print(f"📋 Assignment {assignment_id}: {users_at_max_count}/{total_assigned} users used all {max_attempts} attempts")

                    # Only archive if ALL users have exhausted ALL their attempts
                    if total_assigned > 0 and users_at_max_count == total_assigned:
                        db.execute_update("""
                            UPDATE exam_assignments
                            SET is_archived = 1
                            WHERE id = ? AND is_deleted = 0
                        """, (assignment_id,))
                        print(f"✅ Assignment {assignment_id} auto-archived - all users exhausted all {max_attempts} attempts!")

            except Exception as e:
                print(f"Error checking assignment completion for auto-archive: {e}")
                import traceback
                traceback.print_exc()

        def submit_exam_final():
            """Final exam submission with proper processing"""
            try:
                # Prevent multiple simultaneous submissions
                if exam_state.get('exam_finished'):
                    print("[SUBMIT] Exam already submitted, ignoring duplicate submission")
                    return

                exam_state['exam_finished'] = True  # Mark as finished immediately
                cleanup_page_handlers()

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

                # No need to update user_answers - they already have the correct session_id

                # Check if assignment should be auto-archived
                if assignment_id:
                    check_and_archive_assignment(assignment_id)

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

        # Store submit_exam_final in exam_state so timer thread can access it
        exam_state['submit_exam_final'] = submit_exam_final

        def show_simple_submission_confirmation():
            """Show simple exam submission confirmation when results are hidden"""
            try:
                page = None
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page

                if not page:
                    print("No page context for submission confirmation - returning to dashboard")
                    return_to_dashboard()
                    return

                def close_dialog(e):
                    return_to_dashboard()
                
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
                return_to_dashboard()
        
        def show_pending_release_confirmation():
            """Show confirmation when exam is fully graded but results not released"""
            try:
                page = None
                if exam_state['main_container'] and hasattr(exam_state['main_container'], 'page'):
                    page = exam_state['main_container'].page

                if not page:
                    print("No page context for pending release confirmation - returning to dashboard")
                    return_to_dashboard()
                    return

                def close_dialog(e):
                    return_to_dashboard()
                
                # Create pending release dialog
                confirmation_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Exam Completed Successfully", size=20, weight=ft.FontWeight.BOLD),
                    content=ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.SCHEDULE, color=EXAM_COLORS['warning'], size=48),
                            ft.Text("Your exam has been submitted and completed.", size=16, text_align=ft.TextAlign.CENTER),
                            ft.Text("Results will be released by your instructor at a later time.", size=14, color=EXAM_COLORS['text_secondary'], text_align=ft.TextAlign.CENTER)
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
                return_to_dashboard()
        
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
                        AND TRIM(ua.answer_text) != ''
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
                    return_to_dashboard()
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
                return_to_dashboard()
        
        navigation = ft.Row([
            ft.ElevatedButton(
                f"← {t('previous')}",
                disabled=exam_state['current_question_index'] == 0,
                on_click=go_previous
            ),
            ft.Container(expand=True),
            ft.ElevatedButton(
                f"{t('next')} →",
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
        # Store question card container reference to update only its content
        if 'main_content_container' not in exam_state or exam_state['main_content_container'] is None:
            # First time - create containers
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
            exam_state['main_content_container'] = main_content
        else:
            # Reuse existing container and update its column content
            main_content = exam_state['main_content_container']
            main_content.content.controls = [
                progress_header,
                ft.Container(
                    content=ft.Column([
                        question_card
                    ], scroll=ft.ScrollMode.AUTO),
                    expand=True,
                    padding=ft.padding.symmetric(vertical=20)
                ),
                navigation
            ]
        
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
                ft.Text(t('time_remaining'), size=12)
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

        # Build progress display with timer in top right
        progress_items = [
            # Header row with Progress Overview title and Timer
            ft.Row([
                ft.Text(t('overview'), size=14, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.Row([
                    ft.Icon(ft.icons.TIMER, size=18, color=EXAM_COLORS['primary']),
                    timer_display
                ], spacing=6)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=8),
            ft.Text(f"{answered_count} {t('of')} {total_q} {t('answered')}", size=16, weight=ft.FontWeight.W_500),
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

        # Preserve the order topics first appear in the randomized question list
        ordered_topics = sorted(topic_groups.keys(), key=lambda t: topic_question_indices[t][0])

        for topic in ordered_topics:
            topic_questions = topic_groups[topic]
            topic_indices = topic_question_indices[topic]

            # Calculate topic progress
            topic_answered = sum(1 for q in topic_questions if q['id'] in exam_state['user_answers'])
            topic_total = len(topic_questions)
            if topic_total == 0:
                continue  # No questions to render for this topic

            # Calculate range of question numbers for this topic (sequential order)
            topic_start_number = min(topic_indices) + 1
            topic_end_number = max(topic_indices) + 1

            # Topic header
            topic_header = ft.Container(
                content=ft.Row([
                    ft.Text(
                        f"{topic} ({topic_start_number}-{topic_end_number})" if topic_total > 1 else f"{topic} ({topic_start_number})",
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
            # CRITICAL FIX: Sort indices so buttons appear in sequential navigation order
            for idx in sorted(topic_indices):
                # CRITICAL FIX: Use actual array index + 1 for display number (sequential order)
                display_number = idx + 1
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
                            str(display_number),
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

            # Add topic button grid with responsive wrap
            navigator_sections.append(
                ft.Container(
                    content=ft.Row(
                        topic_buttons,
                        wrap=True,
                        spacing=4,
                        run_spacing=6
                    ),
                    padding=ft.padding.only(bottom=8)
                )
            )

        # Simple Column with scroll - no fancy preservation attempts
        # User can manually scroll as needed
        question_navigator = ft.Container(
            content=ft.Column([
                ft.Text(t('navigation'), size=14, weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column(
                        navigator_sections,
                        spacing=4,
                        scroll=ft.ScrollMode.AUTO
                    ),
                    height=280
                )
            ]),
            padding=ft.padding.all(16),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=8
        )
        
        # Color Legend and Keyboard Shortcuts in 2 columns
        color_legend_and_shortcuts = ft.Container(
            content=ft.Row([
                # Color Legend Column
                ft.Container(
                    content=ft.Column([
                        ft.Text(t('status'), size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(height=8),
                        ft.Column([
                            ft.Row([
                                ft.Container(width=14, height=14, bgcolor=EXAM_COLORS['current'], border_radius=2),
                                ft.Text(t('active'), size=11)
                            ], spacing=6),
                            ft.Row([
                                ft.Container(width=14, height=14, bgcolor=EXAM_COLORS['answered'], border_radius=2),
                                ft.Text(t('answered'), size=11)
                            ], spacing=6),
                            ft.Row([
                                ft.Container(width=14, height=14, bgcolor=EXAM_COLORS['marked'], border_radius=2),
                                ft.Text(t('marked_for_review'), size=11)
                            ], spacing=6),
                            ft.Row([
                                ft.Container(width=14, height=14, bgcolor=EXAM_COLORS['unanswered'], border_radius=2),
                                ft.Text(t('unanswered'), size=11)
                            ], spacing=6)
                        ], spacing=5)
                    ]),
                    expand=1
                ),
                # Vertical divider
                ft.Container(width=1, bgcolor=EXAM_COLORS['border']),
                # Keyboard Shortcuts Column
                ft.Container(
                    content=ft.Column([
                        ft.Text("Shortcuts", size=13, weight=ft.FontWeight.BOLD),
                        ft.Container(height=8),
                        ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.KEYBOARD_ARROW_LEFT, size=14, color=EXAM_COLORS['text_secondary']),
                                ft.Text("← Prev", size=11)
                            ], spacing=6),
                            ft.Row([
                                ft.Icon(ft.icons.KEYBOARD_ARROW_RIGHT, size=14, color=EXAM_COLORS['text_secondary']),
                                ft.Text("→ Next", size=11)
                            ], spacing=6),
                            ft.Row([
                                ft.Icon(ft.icons.FLAG, size=14, color=EXAM_COLORS['text_secondary']),
                                ft.Text("M Mark", size=11)
                            ], spacing=6)
                        ], spacing=5)
                    ]),
                    expand=1
                )
            ], spacing=12),
            padding=ft.padding.all(16),
            bgcolor=EXAM_COLORS['surface'],
            border_radius=8
        )
        
        # Submit Exam button for sidebar
        submit_exam_button = ft.Container(
            content=ft.ElevatedButton(
                t('submit_exam'),
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
        
        # Create or reuse sidebar scrollable column to preserve scroll position
        sidebar_scroll_content = [
            progress_overview,
            ft.Container(height=20),
            question_navigator,
            ft.Container(height=20),
            color_legend_and_shortcuts,
        ]

        if 'sidebar_scroll_column' not in exam_state or exam_state['sidebar_scroll_column'] is None:
            # First time - create sidebar scroll column
            sidebar_scroll_col = ft.Column(sidebar_scroll_content, spacing=0, scroll=ft.ScrollMode.AUTO)
            exam_state['sidebar_scroll_column'] = sidebar_scroll_col
        else:
            # Reuse existing scroll column and update content
            sidebar_scroll_col = exam_state['sidebar_scroll_column']
            sidebar_scroll_col.controls = sidebar_scroll_content

        # Sidebar with scrollable content area and fixed submit button
        sidebar = ft.Container(
            content=ft.Column([
                # Scrollable content area
                ft.Container(
                    content=sidebar_scroll_col,
                    expand=True
                ),
                # Fixed submit button at bottom
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

        # Create or reuse main layout row to preserve sidebar scroll
        if 'main_layout_row' not in exam_state or exam_state['main_layout_row'] is None:
            # First time - create main layout
            main_layout_container = ft.Container(
                content=ft.Row([
                    main_content,
                    ft.VerticalDivider(width=1, color=EXAM_COLORS['border']),
                    sidebar
                ], spacing=0),
                expand=True,
                padding=ft.padding.all(24),
                bgcolor=EXAM_COLORS['background']
            )
            exam_state['main_layout_row'] = main_layout_container
            column_controls.append(main_layout_container)
        else:
            # Reuse existing layout - sidebar scroll will be preserved
            main_layout_container = exam_state['main_layout_row']
            # Update the row content with updated main_content and sidebar
            main_layout_container.content.controls = [
                main_content,
                ft.VerticalDivider(width=1, color=EXAM_COLORS['border']),
                sidebar
            ]
            column_controls.append(main_layout_container)

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

    # Return the main container directly (no wrapper to avoid page reference issues)
    # Note: Fullscreen lock disabled for now due to technical limitations
    return main_container
