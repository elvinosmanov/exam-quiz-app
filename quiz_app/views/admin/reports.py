import flet as ft
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from datetime import datetime, timedelta
import io
import base64
import pandas as pd
from quiz_app.config import COLORS
from quiz_app.utils.localization import t
from quiz_app.database.database import Database
from quiz_app.utils.permissions import UnitPermissionManager

class Reports(ft.UserControl):
    def __init__(self, db, user_data=None):
        super().__init__()
        self.db = db
        self.user_data = user_data or {'role': 'admin'}  # Default to admin if not provided
        self.chart_images = {}  # Store chart images
        self.current_dialog = None  # Track current dialog

        # Initialize file picker for PDF downloads
        self.file_picker = ft.FilePicker(on_result=self.on_file_picker_result)
        self.pending_pdf_data = None  # Store PDF data temporarily

        # Create temp directory for PDFs
        import tempfile
        self.temp_dir = tempfile.mkdtemp(prefix="exam_pdfs_")

        # Set matplotlib style for better looking charts
        plt.style.use('default')
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        
    def did_mount(self):
        super().did_mount()
        # Add file picker to overlay
        if self.page and hasattr(self.page, 'overlay'):
            self.page.overlay.append(self.file_picker)
            self.page.update()
        # Load data first
        self.load_analytics_data()
        # Generate charts in background
        self.generate_charts()
        # Force rebuild of the entire UI with charts
        if self.page:
            # Clear and rebuild to show charts
            self.controls.clear()
            new_content = self.build()
            self.controls.append(new_content)
            self.update()
    
    def will_unmount(self):
        """Clean up when component is unmounted"""
        try:
            print("[DEBUG] Reports will_unmount called - starting cleanup")

            # 1. Close all matplotlib figures to prevent memory leaks and crashes
            try:
                print("[DEBUG] Closing all matplotlib figures")
                plt.close('all')  # Close all open figures
                print("[DEBUG] Matplotlib figures closed successfully")
            except Exception as e:
                print(f"[ERROR] Failed to close matplotlib figures: {e}")

            # 2. Clear chart images from memory
            try:
                if hasattr(self, 'chart_images'):
                    print(f"[DEBUG] Clearing {len(self.chart_images)} chart images")
                    self.chart_images.clear()
            except Exception as e:
                print(f"[ERROR] Failed to clear chart images: {e}")

            # 3. Clean up temporary directory
            try:
                if hasattr(self, 'temp_dir') and self.temp_dir:
                    import shutil
                    import os
                    if os.path.exists(self.temp_dir):
                        print(f"[DEBUG] Removing temp directory: {self.temp_dir}")
                        shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"[ERROR] Failed to cleanup temp directory: {e}")

            # 4. Clear pending PDF data
            try:
                if hasattr(self, 'pending_pdf_data'):
                    self.pending_pdf_data = None
            except Exception as e:
                print(f"[ERROR] Failed to clear pending PDF data: {e}")

            # 5. Clean up dialogs
            try:
                self.cleanup_dialogs()
            except Exception as e:
                print(f"[ERROR] Failed to cleanup dialogs: {e}")

            # 6. Remove file picker from overlay
            try:
                if hasattr(self, 'file_picker') and self.page and hasattr(self.page, 'overlay'):
                    if self.file_picker in self.page.overlay:
                        print("[DEBUG] Removing file picker from overlay")
                        self.page.overlay.remove(self.file_picker)
            except Exception as e:
                print(f"[ERROR] Failed to remove file picker: {e}")

            print("[DEBUG] Reports cleanup completed successfully")

        except Exception as ex:
            print(f"[CRITICAL ERROR] Cleanup failed: {ex}")
            import traceback
            traceback.print_exc()
        finally:
            # Always call parent will_unmount
            super().will_unmount()
    
    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Handle file picker result"""
        if e.path and self.pending_pdf_data:
            try:
                # Save the PDF to the selected location
                import shutil
                shutil.move(self.pending_pdf_data['temp_path'], e.path)
                self.show_message(t('success'), f"{t('file_saved')}: {e.path}")
            except Exception as ex:
                self.show_message(t('error'), f"{t('file_save_error')}: {str(ex)}")
                # Try to clean up temp file on error
                import os
                if os.path.exists(self.pending_pdf_data['temp_path']):
                    try:
                        os.remove(self.pending_pdf_data['temp_path'])
                    except:
                        pass
            finally:
                self.pending_pdf_data = None

    def save_pdf_with_picker(self, temp_filepath, suggested_filename):
        """Show file picker to save PDF"""
        try:
            self.pending_pdf_data = {
                'temp_path': temp_filepath,
                'suggested_name': suggested_filename
            }
            self.file_picker.save_file(
                dialog_title=t('save_pdf_as'),
                file_name=suggested_filename,
                allowed_extensions=["pdf"]
            )
        except Exception as ex:
            self.show_message(t('error'), f"{t('file_save_error')}: {str(ex)}")

    def cleanup_dialogs(self):
        """Force cleanup of any open dialogs"""
        try:
            print(f"[DEBUG] cleanup_dialogs called")

            # Close current dialog if exists
            if hasattr(self, 'current_dialog') and self.current_dialog:
                self.current_dialog.open = False
                self.current_dialog = None

            # Close page dialog if it's ours
            if self.page and hasattr(self.page, 'dialog') and self.page.dialog:
                try:
                    self.page.dialog.open = False
                    self.page.dialog = None
                    self.page.update()
                except:
                    pass

            print(f"[DEBUG] Dialog cleanup completed")
        except Exception as ex:
            print(f"[ERROR] Dialog cleanup failed: {ex}")
    
    def safe_show_dialog(self, title, content, actions=None, width=1200, height=800):
        """Show a dialog - SIMPLE VERSION like other pages"""
        if not self.page:
            return False
        
        # Default actions if none provided
        if actions is None:
            actions = [ft.TextButton(t('close'), on_click=self.close_dialog)]
        
        # Wrap content in Container with size - SAME AS OTHER PAGES!
        dialog_content = ft.Container(
            content=content,
            width=width,
            height=height,
            padding=ft.padding.all(10)
        )
        
        # Create dialog
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(str(title)),
            content=dialog_content,
            actions=actions,
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        # Show dialog - SAME AS OTHER PAGES!
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
        return True
    

    def build(self):
        return ft.Column([
            # Header section
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(t('reports'), size=28, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                        ft.Container(expand=True),
                        ft.Row([
                            ft.ElevatedButton(
                                text=t('export_pdf'),
                                icon=ft.icons.PICTURE_AS_PDF,
                                on_click=self.show_export_pdf_dialog,
                                style=ft.ButtonStyle(bgcolor=COLORS['error'], color=ft.colors.WHITE)
                            )
                        ], spacing=10)
                    ])
                ]),
                padding=ft.padding.only(bottom=20)
            ),

            # Key metrics cards
            self.create_metrics_section(),
            
            ft.Container(height=20),
            
            # Charts section
            self.create_charts_section(),
            
            ft.Container(height=20),
            
            # Detailed reports section
            self.create_reports_section()
            
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
    
    def create_metrics_section(self):
        """Create the key metrics cards section"""
        # Get current data or use defaults
        total_exams = getattr(self, 'total_exams', 0)
        total_sessions = getattr(self, 'total_sessions', 0)
        avg_score = getattr(self, 'avg_score', 0)
        pass_rate = getattr(self, 'pass_rate', 0)
        
        return ft.Container(
            content=ft.Column([
                ft.Text(t('statistics'), size=20, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_metric_card(t('total_exams'), str(total_exams), ft.icons.QUIZ, COLORS['primary']),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        content=self.create_metric_card(t('total_score'), str(total_sessions), ft.icons.TIMER, COLORS['success']),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        content=self.create_metric_card(t('average_score'), f"{avg_score}%", ft.icons.TRENDING_UP, COLORS['warning']),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        content=self.create_metric_card(t('pass_rate'), f"{pass_rate}%", ft.icons.CHECK_CIRCLE, COLORS['success']),
                        col={"xs": 12, "sm": 6, "md": 3},
                    )
                ])
            ]),
            bgcolor=COLORS['surface'],
            padding=ft.padding.all(20),
            border_radius=8,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
            )
        )
    
    def create_metric_card(self, title, value, icon, color):
        """Create individual metric card"""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(icon, color=color, size=30),
                    ft.Container(expand=True),
                ]),
                ft.Container(height=10),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Text(title, size=14, color=COLORS['text_secondary'])
            ], spacing=5),
            bgcolor=ft.colors.WHITE,
            padding=ft.padding.all(15),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, ft.colors.BLACK)),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=3,
                color=ft.colors.with_opacity(0.05, ft.colors.BLACK)
            )
        )
    
    def create_charts_section(self):
        """Create the charts section"""
        return ft.Container(
            content=ft.Column([
                ft.Text(t('analytics'), size=20, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_chart_container("performance_trend", t('exam_results')),
                        col={"xs": 12, "md": 6}
                    ),
                    ft.Container(
                        content=self.create_chart_container("score_distribution", t('score_distribution')),
                        col={"xs": 12, "md": 6}
                    )
                ]),
                ft.Container(height=15),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_chart_container("pass_fail_trend", t('pass_fail_trend')),
                        col={"xs": 12, "md": 6}
                    ),
                    ft.Container(
                        content=self.create_chart_container("question_difficulty", t('question_difficulty_analysis')),
                        col={"xs": 12, "md": 6}
                    )
                ])
            ]),
            bgcolor=COLORS['surface'],
            padding=ft.padding.all(20),
            border_radius=8,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
            )
        )
    
    def create_chart_container(self, chart_key, title):
        """Create container for individual chart"""
        # Check if chart image is available
        chart_content = None
        if chart_key in self.chart_images:
            chart_content = ft.Container(
                content=ft.Image(
                    src_base64=self.chart_images[chart_key],
                    fit=ft.ImageFit.CONTAIN
                ),
                expand=True,
                height=300,
                alignment=ft.alignment.center
            )
        else:
            chart_content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.BAR_CHART, size=50, color=COLORS['text_secondary']),
                    ft.Text("Chart will appear here", size=14, color=COLORS['text_secondary'])
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                height=300,
                bgcolor=ft.colors.with_opacity(0.05, ft.colors.BLACK),
                border_radius=8,
                alignment=ft.alignment.center
            )

        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                chart_content
            ], expand=True),
            bgcolor=ft.colors.WHITE,
            padding=ft.padding.all(15),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, ft.colors.BLACK)),
            expand=True
        )
    
    def create_reports_section(self):
        """Create the detailed reports section"""
        return ft.Container(
            content=ft.Column([
                ft.Text(t('detailed_reports'), size=20, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_report_summary_card(t('exam_performance'), t('detailed_analysis'), ft.icons.ASSESSMENT, 'exam_performance'),
                        col={"xs": 12, "sm": 6, "md": 4}
                    ),
                    ft.Container(
                        content=self.create_report_summary_card(t('user_progress'), t('individual_tracking'), ft.icons.PERSON, 'user_progress'),
                        col={"xs": 12, "sm": 6, "md": 4}
                    ),
                    ft.Container(
                        content=self.create_report_summary_card(t('question_analysis'), t('difficulty_performance'), ft.icons.HELP, 'question_analysis'),
                        col={"xs": 12, "sm": 6, "md": 4}
                    )
                ])
            ]),
            bgcolor=COLORS['surface'],
            padding=ft.padding.all(20),
            border_radius=8,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=5,
                color=ft.colors.with_opacity(0.1, ft.colors.BLACK)
            )
        )
    
    def create_report_summary_card(self, title, description, icon, report_key=None):
        """Create summary card for report categories"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, color=COLORS['primary'], size=40),
                ft.Container(height=10),
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Text(description, size=12, color=COLORS['text_secondary'], text_align=ft.TextAlign.CENTER),
                ft.Container(height=15),
                ft.ElevatedButton(
                    text=t('view') + " " + t('details'),
                    on_click=lambda e, k=report_key: self.show_detailed_report(k),
                    style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                )
            ], spacing=5, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.colors.WHITE,
            padding=ft.padding.all(20),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, ft.colors.BLACK)),
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=3,
                color=ft.colors.with_opacity(0.05, ft.colors.BLACK)
            )
        )
    
    def load_analytics_data(self):
        """Load analytics data from database"""
        try:
            # Apply unit-level filtering for experts
            perm_manager = UnitPermissionManager(self.db)
            filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data)

            # Get basic metrics with unit filtering
            query = "SELECT COUNT(*) as count FROM exams e WHERE e.is_active = 1 {filter_clause}".format(filter_clause=filter_clause)
            self.total_exams = self.db.execute_single(query, tuple(filter_params))['count']

            query = """
                SELECT COUNT(*) as count FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                WHERE es.is_completed = 1 {filter_clause}
            """.format(filter_clause=filter_clause)
            self.total_sessions = self.db.execute_single(query, tuple(filter_params))['count']

            # Get average score
            query = """
                SELECT AVG(es.score) as avg_score FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                WHERE es.is_completed = 1 AND es.score IS NOT NULL {filter_clause}
            """.format(filter_clause=filter_clause)
            avg_score_result = self.db.execute_single(query, tuple(filter_params))
            self.avg_score = round(avg_score_result['avg_score'], 1) if avg_score_result['avg_score'] else 0

            # Get pass rate (assuming 70% is passing)
            query = """
                SELECT COUNT(*) as count FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                WHERE es.is_completed = 1 AND es.score >= 70 {filter_clause}
            """.format(filter_clause=filter_clause)
            pass_sessions = self.db.execute_single(query, tuple(filter_params))['count']
            self.pass_rate = round((pass_sessions / self.total_sessions * 100), 1) if self.total_sessions > 0 else 0

            # Update metric cards
            self.update_metric_cards()

        except Exception as e:
            print(f"Error loading analytics data: {e}")
    
    def update_metric_cards(self):
        """Update the metric cards with real data"""
        try:
            # This will be called after UI is built to update with real data
            # For now, the data is loaded in load_analytics_data
            # In the future, we could find the cards and update their values dynamically
            print(f"[DEBUG] Metrics loaded: exams={self.total_exams}, sessions={self.total_sessions}, avg_score={self.avg_score}%, pass_rate={self.pass_rate}%")
        except Exception as ex:
            print(f"[ERROR] Error updating metric cards: {ex}")
    
    def generate_charts(self):
        """Generate all charts"""
        try:
            print("[DEBUG] Starting chart generation...")
            self.generate_performance_trend_chart()
            self.generate_score_distribution_chart()
            self.generate_pass_fail_trend_chart()
            self.generate_question_difficulty_chart()
            print(f"[DEBUG] Charts generated: {list(self.chart_images.keys())}")

            # Trigger UI update after charts are generated
            if hasattr(self, 'page') and self.page:
                self.update()
        except Exception as e:
            print(f"Error generating charts: {e}")
    
    def generate_performance_trend_chart(self):
        """Generate performance trend over time chart"""
        try:
            print("[DEBUG] Generating performance trend chart...")

            # Apply unit-level filtering for experts
            perm_manager = UnitPermissionManager(self.db)
            filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data)

            # Build query with unit filtering
            query = """
                SELECT DATE(es.end_time) as exam_date, AVG(es.score) as avg_score, COUNT(*) as session_count
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                WHERE es.is_completed = 1 AND es.score IS NOT NULL AND es.end_time IS NOT NULL
                {filter_clause}
                GROUP BY DATE(es.end_time)
                ORDER BY exam_date DESC
                LIMIT 30
            """.format(filter_clause=filter_clause)

            # Execute query
            sessions_data = self.db.execute_query(query, tuple(filter_params))

            print(f"[DEBUG] Performance trend data: {len(sessions_data) if sessions_data else 0} rows")

            if not sessions_data or len(sessions_data) == 0:
                print("[WARNING] No data for performance trend chart")
                return

            # Create chart with larger size for better quality
            fig, ax = plt.subplots(figsize=(10, 6))
            dates = [datetime.strptime(row['exam_date'], '%Y-%m-%d') for row in reversed(sessions_data)]
            scores = [row['avg_score'] for row in reversed(sessions_data)]

            ax.plot(dates, scores, marker='o', linewidth=2, markersize=6, color='#3182ce')
            ax.set_title(t('avg_exam_scores_over_time'), fontsize=14, fontweight='bold')
            ax.set_xlabel(t('date'))
            ax.set_ylabel(t('average_score'))
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 100)

            # Better date formatting with tick limiting
            if len(dates) > 10:
                # Limit to max 10 ticks to prevent the MAXTICKS warning
                ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))
            else:
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Convert to base64 image with higher DPI for sharper quality
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)

            self.chart_images['performance_trend'] = image_data
            print("[SUCCESS] Performance trend chart generated")

        except Exception as e:
            print(f"[ERROR] Error generating performance trend chart: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_score_distribution_chart(self):
        """Generate score distribution histogram"""
        try:
            print("[DEBUG] Generating score distribution chart...")

            # Apply unit-level filtering for experts
            perm_manager = UnitPermissionManager(self.db)
            filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data)

            # Get all scores with unit filtering
            query = """
                SELECT es.score FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                WHERE es.is_completed = 1 AND es.score IS NOT NULL {filter_clause}
            """.format(filter_clause=filter_clause)

            # Execute query
            scores_data = self.db.execute_query(query, tuple(filter_params))

            print(f"[DEBUG] Score distribution data: {len(scores_data) if scores_data else 0} scores")

            if not scores_data or len(scores_data) == 0:
                print("[WARNING] No data for score distribution chart")
                return

            scores = [row['score'] for row in scores_data]

            # Create histogram showing COUNT of exams per score range
            fig, ax = plt.subplots(figsize=(10, 6))

            # Create histogram with 10-point bins (0-10, 10-20, 20-30, etc.)
            bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
            ax.hist(scores, bins=bins, edgecolor='black', alpha=0.7, color='#38a169')
            ax.set_title(t('score_distribution'), fontsize=14, fontweight='bold')
            ax.set_xlabel(t('score') + ' (%)')
            ax.set_ylabel('Number of ' + t('exams'))
            ax.set_xlim(0, 100)
            ax.grid(True, alpha=0.3, axis='y')

            # Set x-axis to show bin edges
            ax.set_xticks(bins)

            plt.tight_layout()

            # Convert to base64 image with higher DPI for sharper quality
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)

            self.chart_images['score_distribution'] = image_data
            print("[SUCCESS] Score distribution chart generated")

        except Exception as e:
            print(f"[ERROR] Error generating score distribution chart: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_pass_fail_trend_chart(self):
        """Generate pass/fail rate trend over time chart"""
        try:
            print("[DEBUG] Generating pass/fail rate trend chart...")

            # Apply unit-level filtering for experts
            perm_manager = UnitPermissionManager(self.db)
            filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data)

            # Build query with unit filtering
            query = """
                SELECT
                    DATE(es.end_time) as exam_date,
                    COUNT(*) as total_exams,
                    SUM(CASE WHEN es.score >= 70 THEN 1 ELSE 0 END) as passed_exams,
                    ROUND((SUM(CASE WHEN es.score >= 70 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 1) as pass_rate
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                WHERE es.is_completed = 1 AND es.score IS NOT NULL AND es.end_time IS NOT NULL
                {filter_clause}
                GROUP BY DATE(es.end_time)
                ORDER BY exam_date DESC
                LIMIT 30
            """.format(filter_clause=filter_clause)

            # Execute query
            trend_data = self.db.execute_query(query, tuple(filter_params))

            print(f"[DEBUG] Pass/fail trend data: {len(trend_data) if trend_data else 0} rows")

            if not trend_data or len(trend_data) == 0:
                print("[WARNING] No data for pass/fail trend chart")
                return

            # Create chart
            fig, ax = plt.subplots(figsize=(8, 5))

            # Prepare data (reverse to show chronologically)
            dates = [datetime.strptime(row['exam_date'], '%Y-%m-%d') for row in reversed(trend_data)]
            pass_rates = [row['pass_rate'] for row in reversed(trend_data)]

            # Create area chart with color gradient
            ax.fill_between(dates, pass_rates, alpha=0.3, color='#38a169', label=t('pass_rate'))
            ax.plot(dates, pass_rates, marker='o', linewidth=2.5, markersize=7, color='#2f855a', label=t('pass_fail_trend'))

            # Add threshold line at 70%
            ax.axhline(y=70, color='#e53e3e', linestyle='--', linewidth=2, alpha=0.7, label='Target (70%)')

            # Styling
            ax.set_title(t('pass_rate_trend_over_time'), fontsize=14, fontweight='bold')
            ax.set_xlabel(t('date'))
            ax.set_ylabel(t('pass_rate') + ' (%)')
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')

            # Format x-axis with tick limiting
            if len(dates) > 10:
                ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))
            else:
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Convert to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)

            self.chart_images['pass_fail_trend'] = image_data
            print("[SUCCESS] Pass/fail rate trend chart generated")

        except Exception as e:
            print(f"[ERROR] Error generating pass/fail trend chart: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_question_difficulty_chart(self):
        """Generate question difficulty analysis"""
        try:
            print("[DEBUG] Generating question difficulty chart...")

            # Apply unit-level filtering for experts
            perm_manager = UnitPermissionManager(self.db)
            filter_clause, filter_params = perm_manager.get_content_query_filter(self.user_data)

            # Build query with unit filtering
            query = """
                SELECT q.difficulty_level,
                       AVG(CASE WHEN ua.is_correct = 1 THEN 100.0 ELSE 0.0 END) as success_rate,
                       COUNT(ua.id) as answer_count
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE ua.is_correct IS NOT NULL AND q.difficulty_level IS NOT NULL AND q.difficulty_level != ''
                {filter_clause}
                GROUP BY q.difficulty_level
                HAVING answer_count >= 5
            """.format(filter_clause=filter_clause)

            # Execute query
            question_data = self.db.execute_query(query, tuple(filter_params))

            print(f"[DEBUG] Question difficulty data: {len(question_data) if question_data else 0} difficulty levels")

            if not question_data or len(question_data) == 0:
                print("[WARNING] No data for question difficulty chart")
                return

            difficulties = [row['difficulty_level'].title() for row in question_data]
            success_rates = [row['success_rate'] for row in question_data]
            answer_counts = [row['answer_count'] for row in question_data]

            # Create bar chart instead of pie for better readability with larger size
            fig, ax = plt.subplots(figsize=(10, 6))

            # Color code bars based on difficulty
            colors_map = {'Easy': '#38a169', 'Medium': '#d69e2e', 'Hard': '#e53e3e'}
            bar_colors = [colors_map.get(d, '#718096') for d in difficulties]

            bars = ax.bar(difficulties, success_rates, color=bar_colors, alpha=0.8, edgecolor='black')
            ax.set_title(t('success_rate_by_difficulty'), fontsize=14, fontweight='bold')
            ax.set_xlabel(t('difficulty_level'))
            ax.set_ylabel(t('success_rate') + ' (%)')
            ax.set_ylim(0, 100)
            ax.grid(True, alpha=0.3, axis='y')

            # Add value labels on bars with answer count
            for i, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%\n({answer_counts[i]} answers)',
                       ha='center', va='bottom', fontsize=9)

            plt.tight_layout()

            # Convert to base64 image with higher DPI for sharper quality
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)

            self.chart_images['question_difficulty'] = image_data
            print("[SUCCESS] Question difficulty chart generated")

        except Exception as e:
            print(f"[ERROR] Error generating question difficulty chart: {e}")
            import traceback
            traceback.print_exc()
    
    def show_export_pdf_dialog(self, e):
        """Show dialog with PDF export options"""
        try:
            # Get all assignments (what users actually take)
            assignments = self.db.execute_query("""
                SELECT DISTINCT
                    ea.id,
                    ea.assignment_name as title,
                    ea.created_at
                FROM exam_assignments ea
                WHERE ea.id IN (SELECT DISTINCT assignment_id FROM exam_sessions WHERE assignment_id IS NOT NULL)
                ORDER BY ea.created_at DESC
            """)

            # Get standalone exams (legacy, without assignments)
            standalone_exams = self.db.execute_query("""
                SELECT DISTINCT
                    e.id,
                    e.title,
                    e.created_at
                FROM exams e
                WHERE e.is_active = 1
                AND e.id IN (SELECT DISTINCT exam_id FROM exam_sessions WHERE assignment_id IS NULL)
                ORDER BY e.created_at DESC
            """)

            # Add legacy suffix to standalone exams
            for exam in standalone_exams:
                exam['title'] = f"{exam['title']} ({t('legacy')})"

            # Combine both lists
            exams = assignments + standalone_exams

            # Get all students with exam attempts
            students = self.db.execute_query("""
                SELECT DISTINCT u.id, u.username, u.full_name, u.department, u.unit,
                       COUNT(DISTINCT es.id) as exam_count
                FROM users u
                JOIN exam_sessions es ON u.id = es.user_id
                WHERE u.role = 'examinee' AND es.is_completed = 1
                GROUP BY u.id
                ORDER BY u.full_name
            """)

            # Create tabs for different export options
            export_tabs = ft.Tabs(
                selected_index=0,
                animation_duration=300,
                tabs=[
                    # Tab 1: Export by Exam
                    ft.Tab(
                        text=t('export_by_exam'),
                        icon=ft.icons.QUIZ,
                        content=self.create_exam_export_tab(exams)
                    ),
                    # Tab 2: Export by Student
                    ft.Tab(
                        text=t('export_by_student'),
                        icon=ft.icons.PERSON,
                        content=self.create_student_export_tab(students)
                    ),
                    # Tab 3: Export Student's Specific Exam
                    ft.Tab(
                        text=t('student_exam'),
                        icon=ft.icons.ASSIGNMENT,
                        content=self.create_student_exam_export_tab(students, exams)
                    ),
                ],
                expand=1
            )

            content = ft.Container(
                content=export_tabs,
                padding=10
            )

            self.safe_show_dialog(
                title="📄 " + t('export_pdf_reports'),
                content=content,
                width=900,
                height=700
            )

        except Exception as ex:
            print(f"[ERROR] Error showing export dialog: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to load export options: {str(ex)}")

    def create_exam_export_tab(self, exams):
        """Create the exam export tab content"""
        if not exams:
            return ft.Container(
                content=ft.Text(t('no_exams_for_report'), size=14),
                padding=20
            )

        exam_items = []
        for exam in exams:
            exam_items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.QUIZ, color=COLORS['primary']),
                    title=ft.Text(exam['title'], weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"{t('created')}: {exam['created_at'][:10]}"),
                    trailing=ft.IconButton(
                        icon=ft.icons.PICTURE_AS_PDF,
                        icon_color=COLORS['error'],
                        tooltip=t('generate_pdf_report'),
                        on_click=lambda e, eid=exam['id'], title=exam['title']: self.generate_exam_pdf(eid, title)
                    )
                )
            )

        return ft.Container(
            content=ft.Column([
                ft.Text(t('select_exam_generate_pdf'), size=14),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column(exam_items, scroll=ft.ScrollMode.AUTO),
                    height=500,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=8,
                    padding=10
                )
            ], spacing=0),
            padding=10
        )

    def create_student_export_tab(self, students):
        """Create the student export tab content"""
        if not students:
            return ft.Container(
                content=ft.Text(t('no_students_completed'), size=14),
                padding=20
            )

        student_items = []
        for student in students:
            dept_unit = f"{student['department'] or 'N/A'}"
            if student.get('unit'):
                dept_unit += f" / {student['unit']}"
            student_items.append(
                ft.ListTile(
                    leading=ft.Icon(ft.icons.PERSON, color=COLORS['primary']),
                    title=ft.Text(student['full_name'], weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(f"{student['username']} • {dept_unit} • {student['exam_count']} {t('exams')}"),
                    trailing=ft.IconButton(
                        icon=ft.icons.PICTURE_AS_PDF,
                        icon_color=COLORS['error'],
                        tooltip=t('generate_pdf_report'),
                        on_click=lambda e, uid=student['id'], name=student['full_name']: self.generate_student_pdf(uid, name)
                    )
                )
            )

        return ft.Container(
            content=ft.Column([
                ft.Text(t('select_student_generate_pdf'), size=14),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column(student_items, scroll=ft.ScrollMode.AUTO),
                    height=500,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=8,
                    padding=10
                )
            ], spacing=0),
            padding=10
        )

    def create_student_exam_export_tab(self, students, exams):
        """Create the student-exam export tab content"""
        if not students or not exams:
            return ft.Container(
                content=ft.Text(t('no_data_student_exam'), size=14),
                padding=20
            )

        # Create dropdowns for student and exam selection
        self.selected_student_id = None
        self.selected_exam_id_for_student = None

        student_dropdown = ft.Dropdown(
            label=t('select_student'),
            hint_text=t('choose_student'),
            options=[ft.dropdown.Option(str(s['id']), s['full_name']) for s in students],
            on_change=lambda e: self.on_student_select_for_exam(e),
            width=400
        )

        exam_dropdown = ft.Dropdown(
            label=t('select_exam'),
            hint_text=t('choose_exam'),
            options=[ft.dropdown.Option(str(ex['id']), ex['title']) for ex in exams],
            on_change=lambda e: self.on_exam_select_for_student(e),
            width=400
        )

        generate_button = ft.ElevatedButton(
            text=t('generate_pdf_report'),
            icon=ft.icons.PICTURE_AS_PDF,
            on_click=self.generate_selected_student_exam_pdf,
            style=ft.ButtonStyle(bgcolor=COLORS['error'], color=ft.colors.WHITE),
            disabled=True
        )

        # Store references for enabling/disabling button
        self.student_exam_dropdown = student_dropdown
        self.exam_for_student_dropdown = exam_dropdown
        self.generate_student_exam_button = generate_button

        return ft.Container(
            content=ft.Column([
                ft.Text("Export detailed report for a specific student's specific exam:", size=14, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                ft.Text("Step 1: Select a student", size=12),
                student_dropdown,
                ft.Container(height=15),
                ft.Text("Step 2: Select an exam", size=12),
                exam_dropdown,
                ft.Container(height=20),
                generate_button,
                ft.Container(height=10),
                ft.Container(
                    content=ft.Text(
                        "This report will show detailed question-by-question breakdown with correct/incorrect answers.",
                        size=11,
                        color=ft.colors.GREY_700,
                        italic=True
                    ),
                    padding=10,
                    bgcolor=ft.colors.BLUE_50,
                    border_radius=8
                )
            ], spacing=5),
            padding=20
        )

    def on_student_select_for_exam(self, e):
        """Handle student selection for student-exam export"""
        self.selected_student_id = int(e.control.value) if e.control.value else None
        self.update_generate_button_state()

    def on_exam_select_for_student(self, e):
        """Handle exam selection for student-exam export"""
        self.selected_exam_id_for_student = int(e.control.value) if e.control.value else None
        self.update_generate_button_state()

    def update_generate_button_state(self):
        """Enable/disable generate button based on selections"""
        if hasattr(self, 'generate_student_exam_button'):
            self.generate_student_exam_button.disabled = not (
                self.selected_student_id and self.selected_exam_id_for_student
            )
            if self.page:
                self.page.update()

    def generate_selected_student_exam_pdf(self, e):
        """Generate PDF for selected student and exam/assignment"""
        if not self.selected_student_id or not self.selected_exam_id_for_student:
            self.show_message("Selection Required", "Please select both a student and an exam.")
            return

        # Get student name
        student = self.db.execute_single(
            "SELECT full_name FROM users WHERE id = ?",
            (self.selected_student_id,)
        )

        # Get assignment or exam title
        # First try to get assignment name
        assignment = self.db.execute_single(
            "SELECT assignment_name as title FROM exam_assignments WHERE id = ?",
            (self.selected_exam_id_for_student,)
        )

        # If not found, try exam title (legacy)
        if not assignment:
            assignment = self.db.execute_single(
                "SELECT title FROM exams WHERE id = ?",
                (self.selected_exam_id_for_student,)
            )

        if student and assignment:
            self.generate_student_exam_pdf(
                self.selected_student_id,
                self.selected_exam_id_for_student,
                student['full_name'],
                assignment['title']
            )

    def show_exam_report_selector(self, e):
        """Show dialog to select exam for PDF report"""
        try:
            # Get all exams
            exams = self.db.execute_query("""
                SELECT id, title, created_at FROM exams
                WHERE is_active = 1
                ORDER BY created_at DESC
            """)

            if not exams:
                self.show_message("No Exams", "No exams available for report generation.")
                return

            # Create exam selection list
            exam_items = []
            for exam in exams:
                exam_items.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.QUIZ, color=COLORS['primary']),
                        title=ft.Text(exam['title'], weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"Created: {exam['created_at'][:10]}"),
                        trailing=ft.IconButton(
                            icon=ft.icons.PICTURE_AS_PDF,
                            icon_color=COLORS['error'],
                            tooltip="Generate PDF Report",
                            on_click=lambda e, eid=exam['id'], title=exam['title']: self.generate_exam_pdf(eid, title)
                        )
                    )
                )

            content = ft.Column([
                ft.Text("Select an exam to generate detailed PDF report:", size=14),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column(exam_items, scroll=ft.ScrollMode.AUTO),
                    height=400,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=8,
                    padding=10
                )
            ], spacing=0)

            self.safe_show_dialog(
                title="📄 Generate Exam Report",
                content=content,
                width=700,
                height=600
            )

        except Exception as ex:
            print(f"[ERROR] Error showing exam selector: {ex}")
            self.show_message(t('error'), f"Failed to load exams: {str(ex)}")

    def show_student_report_selector(self, e):
        """Show dialog to select student for PDF report"""
        try:
            # Get all students with exam attempts
            students = self.db.execute_query("""
                SELECT DISTINCT u.id, u.username, u.full_name, u.department, u.unit,
                       COUNT(DISTINCT es.id) as exam_count
                FROM users u
                JOIN exam_sessions es ON u.id = es.user_id
                WHERE u.role = 'examinee' AND es.is_completed = 1
                GROUP BY u.id
                ORDER BY u.full_name
            """)

            if not students:
                self.show_message("No Students", "No students with completed exams found.")
                return

            # Create student selection list
            student_items = []
            for student in students:
                dept_unit = f"{student['department'] or 'N/A'}"
                if student.get('unit'):
                    dept_unit += f" / {student['unit']}"
                student_items.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.PERSON, color=COLORS['primary']),
                        title=ft.Text(student['full_name'], weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"{student['username']} • {dept_unit} • {student['exam_count']} exams"),
                        trailing=ft.IconButton(
                            icon=ft.icons.PICTURE_AS_PDF,
                            icon_color=COLORS['error'],
                            tooltip="Generate PDF Report",
                            on_click=lambda e, uid=student['id'], name=student['full_name']: self.generate_student_pdf(uid, name)
                        )
                    )
                )

            content = ft.Column([
                ft.Text("Select a student to generate detailed PDF report:", size=14),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column(student_items, scroll=ft.ScrollMode.AUTO),
                    height=400,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    border_radius=8,
                    padding=10
                )
            ], spacing=0)

            self.safe_show_dialog(
                title="📄 Generate Student Report",
                content=content,
                width=700,
                height=600
            )

        except Exception as ex:
            print(f"[ERROR] Error showing student selector: {ex}")
            self.show_message(t('error'), f"Failed to load students: {str(ex)}")

    def generate_exam_pdf(self, exam_id, exam_title):
        """Generate detailed PDF report for a specific exam"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors as rl_colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os

            # Get exam/assignment statistics
            exam_stats = self.db.execute_single("""
                SELECT
                    COUNT(es.id) as total_attempts,
                    AVG(es.score) as avg_score,
                    MAX(es.score) as max_score,
                    MIN(es.score) as min_score,
                    SUM(CASE WHEN es.score >= COALESCE(ea.passing_score, e.passing_score) THEN 1 ELSE 0 END) * 100.0 / COUNT(es.id) as pass_rate
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
                WHERE (es.assignment_id = ? OR (es.assignment_id IS NULL AND es.exam_id = ?)) AND es.is_completed = 1
            """, (exam_id, exam_id))

            # Get all attempts for this exam/assignment with session IDs
            attempts = self.db.execute_query("""
                SELECT
                    u.id as user_id, u.full_name, u.username, u.department,
                    es.id as session_id, es.score, es.duration_seconds, es.start_time,
                    es.correct_answers, es.total_questions
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                WHERE (es.assignment_id = ? OR (es.assignment_id IS NULL AND es.exam_id = ?)) AND es.is_completed = 1
                ORDER BY es.score DESC
            """, (exam_id, exam_id))

            # Create PDF with custom header/footer
            import re
            safe_title = re.sub(r'[^\w\s-]', '', exam_title).strip().replace(' ', '_')
            filename = f"exam_report_{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.temp_dir, filename)

            # Register Unicode font for Azerbaijani characters
            unicode_font_registered = False
            try:
                # Try Arial first (supports Azerbaijani)
                from reportlab.pdfbase.ttfonts import TTFont
                pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Italic', '/System/Library/Fonts/Supplemental/Arial Italic.ttf'))
                pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic')
                unicode_font = 'Arial'
                unicode_font_bold = 'Arial-Bold'
                unicode_font_registered = True
                print("[INFO] Registered Arial fonts for Azerbaijani text")
            except Exception as e:
                print(f"[WARN] Could not register Arial: {e}")
                try:
                    # Try DejaVu Sans as fallback
                    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
                    unicode_font = 'DejaVuSans'
                    unicode_font_bold = 'DejaVuSans-Bold'
                    unicode_font_registered = True
                    print("[INFO] Registered DejaVu Sans for text")
                except Exception as e2:
                    print(f"[WARN] Could not register DejaVu Sans: {e2}")
                    # Last resort: Helvetica (won't display special characters properly)
                    unicode_font = 'Helvetica'
                    unicode_font_bold = 'Helvetica-Bold'
                    print("[WARN] Using Helvetica (may not display Azerbaijani characters correctly)")

            # Custom document template with header and footer
            def add_header_footer(canvas_obj, doc):
                """Add header with logo and footer with confidential warning"""
                canvas_obj.saveState()

                # Header - Azercosmos Logo (Centered)
                logo_path = os.path.join(os.path.dirname(__file__), '../../assets/images/azercosmos-logo.png')
                logo_path = os.path.abspath(logo_path)  # Resolve to absolute path
                page_width = A4[0]
                logo_width = 150
                logo_height = 40

                if os.path.exists(logo_path):
                    try:
                        # Center the logo horizontally
                        x_position = (page_width - logo_width) / 2
                        canvas_obj.drawImage(logo_path, x_position, A4[1] - 60,
                                           width=logo_width, height=logo_height,
                                           preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        print(f"[ERROR] Failed to draw logo: {e}")
                        canvas_obj.setFont('Helvetica-Bold', 12)
                        canvas_obj.drawCentredString(page_width / 2, A4[1] - 40, "AZERCOSMOS")
                else:
                    print(f"[ERROR] Logo file not found at: {logo_path}")
                    canvas_obj.setFont('Helvetica-Bold', 12)
                    canvas_obj.drawCentredString(page_width / 2, A4[1] - 40, "AZERCOSMOS")

                # Footer - Confidential Warning
                footer_text = [
                    "SPECIAL WARNING",
                    "This document contains confidential information belonging to the Space Agency of the Republic of Azerbaijan (Azercosmos)."
                ]

                canvas_obj.setFont(unicode_font_bold, 8)
                canvas_obj.drawCentredString(A4[0] / 2, 50, footer_text[0])

                canvas_obj.setFont(unicode_font, 7)
                canvas_obj.drawCentredString(A4[0] / 2, 35, footer_text[1])

                # Page number
                canvas_obj.setFont('Helvetica', 8)
                canvas_obj.drawCentredString(A4[0] / 2, 15, f"Page {doc.page}")

                canvas_obj.restoreState()

            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                topMargin=80,
                bottomMargin=70
            )
            story = []
            styles = getSampleStyleSheet()

            # Update styles to use Unicode font
            styles['Normal'].fontName = unicode_font
            styles['Heading1'].fontName = unicode_font_bold
            styles['Heading2'].fontName = unicode_font_bold
            styles['Heading3'].fontName = unicode_font_bold

            # Title
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=rl_colors.HexColor('#2D3748'), fontName=unicode_font_bold)
            story.append(Paragraph(f"{t('exam_report')}: {exam_title}", title_style))
            story.append(Spacer(1, 0.3*inch))

            # Date
            story.append(Paragraph(f"{t('generated')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))

            # Statistics - Use Paragraphs for table cells
            story.append(Paragraph(t('performance_summary'), styles['Heading2']))
            stats_data = [
                [Paragraph(f'<b>{t("metric")}</b>', styles['Normal']), Paragraph(f'<b>{t("value")}</b>', styles['Normal'])],
                [Paragraph(t('total_attempts'), styles['Normal']), Paragraph(str(exam_stats['total_attempts']) if exam_stats else '0', styles['Normal'])],
                [Paragraph(t('average_score'), styles['Normal']), Paragraph(f"{exam_stats['avg_score']:.2f}%" if exam_stats and exam_stats['avg_score'] else 'N/A', styles['Normal'])],
                [Paragraph(t('highest_score'), styles['Normal']), Paragraph(f"{exam_stats['max_score']:.2f}%" if exam_stats and exam_stats['max_score'] else 'N/A', styles['Normal'])],
                [Paragraph(t('lowest_score'), styles['Normal']), Paragraph(f"{exam_stats['min_score']:.2f}%" if exam_stats and exam_stats['min_score'] else 'N/A', styles['Normal'])],
                [Paragraph(t('pass_rate'), styles['Normal']), Paragraph(f"{exam_stats['pass_rate']:.2f}%" if exam_stats and exam_stats['pass_rate'] else 'N/A', styles['Normal'])],
            ]

            stats_table = Table(stats_data, colWidths=[3*inch, 3*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#4299E1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), rl_colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, rl_colors.black)
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 0.5*inch))

            # Student attempts
            story.append(Paragraph(t('student_performance'), styles['Heading2']))
            story.append(Spacer(1, 0.2*inch))

            if attempts:
                # Use Paragraphs for table cells
                attempts_data = [[
                    Paragraph(f'<b>{t("student")}</b>', styles['Normal']),
                    Paragraph(f'<b>{t("department")}</b>', styles['Normal']),
                    Paragraph(f'<b>{t("exam_date")}</b>', styles['Normal']),
                    Paragraph(f'<b>{t("score")}</b>', styles['Normal']),
                    Paragraph(f'<b>{t("correct_total")}</b>', styles['Normal']),
                    Paragraph(f'<b>{t("duration_min")}</b>', styles['Normal'])
                ]]
                for attempt in attempts:
                    duration_min = attempt['duration_seconds'] // 60 if attempt['duration_seconds'] else 0
                    exam_date = attempt['start_time'][:10] if attempt['start_time'] else 'N/A'
                    attempts_data.append([
                        Paragraph(attempt['full_name'], styles['Normal']),
                        Paragraph(attempt['department'] or 'N/A', styles['Normal']),
                        Paragraph(exam_date, styles['Normal']),
                        Paragraph(f"{attempt['score']:.1f}%", styles['Normal']),
                        Paragraph(f"{attempt['correct_answers']}/{attempt['total_questions']}", styles['Normal']),
                        Paragraph(str(duration_min), styles['Normal'])
                    ])

                attempts_table = Table(attempts_data, colWidths=[1.5*inch, 1.2*inch, 0.9*inch, 0.8*inch, 1*inch, 0.8*inch])
                attempts_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#48BB78')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), rl_colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, rl_colors.black)
                ]))
                story.append(attempts_table)
                story.append(Spacer(1, 0.5*inch))

                # Add question-level analysis for each student
                story.append(Paragraph("Detailed Question Analysis by Student", styles['Heading2']))
                story.append(Spacer(1, 0.2*inch))

                for attempt in attempts:
                    # Get question details for this session
                    question_breakdown = self.db.execute_query("""
                        SELECT
                            q.question_text, q.question_type, q.points,
                            ua.is_correct
                        FROM user_answers ua
                        JOIN questions q ON ua.question_id = q.id
                        WHERE ua.session_id = ?
                        ORDER BY q.id
                    """, (attempt['session_id'],))

                    if question_breakdown:
                        # Student name header
                        student_header = f"{attempt['full_name']} ({attempt['username']}) - Score: {attempt['score']:.1f}%"
                        story.append(Paragraph(student_header, styles['Heading3']))
                        story.append(Spacer(1, 0.1*inch))

                        # Create question breakdown table with Paragraphs
                        q_data = [[
                            Paragraph('<b>#</b>', styles['Normal']),
                            Paragraph('<b>Question (preview)</b>', styles['Normal']),
                            Paragraph('<b>Type</b>', styles['Normal']),
                            Paragraph('<b>Points</b>', styles['Normal']),
                            Paragraph('<b>Result</b>', styles['Normal'])
                        ]]
                        for idx, qb in enumerate(question_breakdown, 1):
                            q_text = qb['question_text'][:60] + '...' if len(qb['question_text']) > 60 else qb['question_text']
                            result = '✓' if qb['is_correct'] else '✗'
                            q_data.append([
                                Paragraph(str(idx), styles['Normal']),
                                Paragraph(q_text, styles['Normal']),
                                Paragraph(qb['question_type'][:10], styles['Normal']),
                                Paragraph(str(qb['points']), styles['Normal']),
                                Paragraph(result, styles['Normal'])
                            ])

                        q_table = Table(q_data, colWidths=[0.3*inch, 3*inch, 0.8*inch, 0.5*inch, 0.5*inch])
                        q_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#E2E8F0')),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('ALIGN', (3, 0), (4, -1), 'CENTER'),
                            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
                            ('BACKGROUND', (0, 1), (-1, -1), rl_colors.white),
                        ]))
                        story.append(q_table)
                        story.append(Spacer(1, 0.3*inch))

            # Build PDF with custom header and footer
            doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

            # Close dialog and show file picker
            if self.page and self.page.dialog:
                self.page.dialog.open = False
                self.page.update()

            # Show file picker to save PDF
            self.save_pdf_with_picker(filepath, filename)

        except Exception as ex:
            print(f"[ERROR] Error generating exam PDF: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to generate exam PDF: {str(ex)}")

    def generate_student_pdf(self, user_id, student_name):
        """Generate detailed PDF report for a specific student"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors as rl_colors
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os

            # Get student statistics
            student_stats = self.db.execute_single("""
                SELECT
                    u.username, u.full_name, u.email, u.department, u.unit,
                    COUNT(es.id) as total_exams,
                    AVG(es.score) as avg_score,
                    MAX(es.score) as max_score,
                    MIN(es.score) as min_score
                FROM users u
                LEFT JOIN exam_sessions es ON u.id = es.user_id AND es.is_completed = 1
                WHERE u.id = ?
                GROUP BY u.id
            """, (user_id,))

            # Get all exam attempts with session IDs
            attempts = self.db.execute_query("""
                SELECT
                    COALESCE(ea.assignment_name, e.title) as exam_title,
                    es.id as session_id, es.score, es.duration_seconds, es.start_time,
                    es.correct_answers, es.total_questions,
                    CASE WHEN es.score >= COALESCE(ea.passing_score, e.passing_score) THEN 'PASS' ELSE 'FAIL' END as status
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
                WHERE es.user_id = ? AND es.is_completed = 1
                ORDER BY es.start_time DESC
            """, (user_id,))

            # Create PDF with custom header/footer
            import re
            safe_name = re.sub(r'[^\w\s-]', '', student_name).strip().replace(' ', '_')
            filename = f"student_report_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.temp_dir, filename)

            # Register Unicode font for Azerbaijani characters
            unicode_font_registered = False
            try:
                # Try Arial first (supports Azerbaijani)
                from reportlab.pdfbase.ttfonts import TTFont
                pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Italic', '/System/Library/Fonts/Supplemental/Arial Italic.ttf'))
                pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic')
                unicode_font = 'Arial'
                unicode_font_bold = 'Arial-Bold'
                unicode_font_registered = True
                print("[INFO] Registered Arial fonts for Azerbaijani text")
            except Exception as e:
                print(f"[WARN] Could not register Arial: {e}")
                try:
                    # Try DejaVu Sans as fallback
                    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
                    unicode_font = 'DejaVuSans'
                    unicode_font_bold = 'DejaVuSans-Bold'
                    unicode_font_registered = True
                    print("[INFO] Registered DejaVu Sans for text")
                except Exception as e2:
                    print(f"[WARN] Could not register DejaVu Sans: {e2}")
                    # Last resort: Helvetica (won't display special characters properly)
                    unicode_font = 'Helvetica'
                    unicode_font_bold = 'Helvetica-Bold'
                    print("[WARN] Using Helvetica (may not display Azerbaijani characters correctly)")

            # Custom document template with header and footer
            def add_header_footer(canvas_obj, doc):
                """Add header with logo and footer with confidential warning"""
                canvas_obj.saveState()

                # Header - Azercosmos Logo (Centered)
                logo_path = os.path.join(os.path.dirname(__file__), '../../assets/images/azercosmos-logo.png')
                logo_path = os.path.abspath(logo_path)  # Resolve to absolute path
                page_width = A4[0]
                logo_width = 150
                logo_height = 40

                if os.path.exists(logo_path):
                    try:
                        # Center the logo horizontally
                        x_position = (page_width - logo_width) / 2
                        canvas_obj.drawImage(logo_path, x_position, A4[1] - 60,
                                           width=logo_width, height=logo_height,
                                           preserveAspectRatio=True, mask='auto')
                    except Exception as e:
                        print(f"[ERROR] Failed to draw logo: {e}")
                        canvas_obj.setFont('Helvetica-Bold', 12)
                        canvas_obj.drawCentredString(page_width / 2, A4[1] - 40, "AZERCOSMOS")
                else:
                    print(f"[ERROR] Logo file not found at: {logo_path}")
                    canvas_obj.setFont('Helvetica-Bold', 12)
                    canvas_obj.drawCentredString(page_width / 2, A4[1] - 40, "AZERCOSMOS")

                # Footer - Confidential Warning
                footer_text = [
                    "SPECIAL WARNING",
                    "This document contains confidential information belonging to the Space Agency of the Republic of Azerbaijan (Azercosmos)."
                ]

                canvas_obj.setFont(unicode_font_bold, 8)
                canvas_obj.drawCentredString(A4[0] / 2, 50, footer_text[0])

                canvas_obj.setFont(unicode_font, 7)
                canvas_obj.drawCentredString(A4[0] / 2, 35, footer_text[1])

                # Page number
                canvas_obj.setFont('Helvetica', 8)
                canvas_obj.drawCentredString(A4[0] / 2, 15, f"Page {doc.page}")

                canvas_obj.restoreState()

            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                topMargin=80,
                bottomMargin=70
            )
            story = []
            styles = getSampleStyleSheet()

            # Update styles to use Unicode font
            styles['Normal'].fontName = unicode_font
            styles['Heading1'].fontName = unicode_font_bold
            styles['Heading2'].fontName = unicode_font_bold
            styles['Heading3'].fontName = unicode_font_bold

            # Title
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=rl_colors.HexColor('#2D3748'), fontName=unicode_font_bold)
            story.append(Paragraph(f"Student Report: {student_name}", title_style))
            story.append(Spacer(1, 0.3*inch))

            # Date
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))

            # Student Info - Use Paragraphs
            story.append(Paragraph("Student Information", styles['Heading2']))
            info_data = [
                [Paragraph('<b>Field</b>', styles['Normal']), Paragraph('<b>Value</b>', styles['Normal'])],
                [Paragraph('Full Name', styles['Normal']), Paragraph(student_stats['full_name'], styles['Normal'])],
                [Paragraph('Username', styles['Normal']), Paragraph(student_stats['username'], styles['Normal'])],
                [Paragraph('Email', styles['Normal']), Paragraph(student_stats['email'] or 'N/A', styles['Normal'])],
                [Paragraph('Department', styles['Normal']), Paragraph(student_stats['department'] or 'N/A', styles['Normal'])],
                [Paragraph('Unit', styles['Normal']), Paragraph(student_stats.get('unit') or 'N/A', styles['Normal'])],
            ]

            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#4299E1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), rl_colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, rl_colors.black)
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.5*inch))

            # Performance Summary - Use Paragraphs
            story.append(Paragraph("Performance Summary", styles['Heading2']))
            summary_data = [
                [Paragraph('<b>Metric</b>', styles['Normal']), Paragraph('<b>Value</b>', styles['Normal'])],
                [Paragraph('Total Exams Taken', styles['Normal']), Paragraph(str(student_stats['total_exams']), styles['Normal'])],
                [Paragraph('Average Score', styles['Normal']), Paragraph(f"{student_stats['avg_score']:.2f}%" if student_stats['avg_score'] else 'N/A', styles['Normal'])],
                [Paragraph('Highest Score', styles['Normal']), Paragraph(f"{student_stats['max_score']:.2f}%" if student_stats['max_score'] else 'N/A', styles['Normal'])],
                [Paragraph('Lowest Score', styles['Normal']), Paragraph(f"{student_stats['min_score']:.2f}%" if student_stats['min_score'] else 'N/A', styles['Normal'])],
            ]

            summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#48BB78')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), rl_colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, rl_colors.black)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.5*inch))

            # Exam History
            story.append(Paragraph("Exam History", styles['Heading2']))
            story.append(Spacer(1, 0.2*inch))

            if attempts:
                # Use Paragraphs for exam history table
                history_data = [[
                    Paragraph('<b>Exam</b>', styles['Normal']),
                    Paragraph('<b>Date</b>', styles['Normal']),
                    Paragraph('<b>Score</b>', styles['Normal']),
                    Paragraph('<b>Correct/Total</b>', styles['Normal']),
                    Paragraph('<b>Duration (min)</b>', styles['Normal']),
                    Paragraph('<b>Status</b>', styles['Normal'])
                ]]
                for attempt in attempts:
                    duration_min = attempt['duration_seconds'] // 60 if attempt['duration_seconds'] else 0
                    history_data.append([
                        Paragraph(attempt['exam_title'][:30], styles['Normal']),
                        Paragraph(attempt['start_time'][:10], styles['Normal']),
                        Paragraph(f"{attempt['score']:.1f}%", styles['Normal']),
                        Paragraph(f"{attempt['correct_answers']}/{attempt['total_questions']}", styles['Normal']),
                        Paragraph(str(duration_min), styles['Normal']),
                        Paragraph(attempt['status'], styles['Normal'])
                    ])

                history_table = Table(history_data, colWidths=[2.5*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.6*inch])
                history_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#9F7AEA')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), rl_colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, rl_colors.black)
                ]))
                story.append(history_table)
                story.append(Spacer(1, 0.5*inch))

                # Add question-level breakdown for each exam
                story.append(Paragraph("Question-Level Performance by Exam", styles['Heading2']))
                story.append(Spacer(1, 0.2*inch))

                for attempt in attempts:
                    # Get question details for this session
                    question_breakdown = self.db.execute_query("""
                        SELECT
                            q.question_text, q.question_type, q.points,
                            ua.is_correct
                        FROM user_answers ua
                        JOIN questions q ON ua.question_id = q.id
                        WHERE ua.session_id = ?
                        ORDER BY q.id
                    """, (attempt['session_id'],))

                    if question_breakdown:
                        # Exam title header
                        exam_header = f"{attempt['exam_title']} - {attempt['start_time'][:10]} - Score: {attempt['score']:.1f}% ({attempt['status']})"
                        story.append(Paragraph(exam_header, styles['Heading3']))
                        story.append(Spacer(1, 0.1*inch))

                        # Calculate correct/incorrect counts
                        correct_count = sum(1 for q in question_breakdown if q['is_correct'])
                        total_count = len(question_breakdown)

                        # Create question breakdown table with Paragraphs
                        q_data = [[
                            Paragraph('<b>#</b>', styles['Normal']),
                            Paragraph('<b>Question (preview)</b>', styles['Normal']),
                            Paragraph('<b>Type</b>', styles['Normal']),
                            Paragraph('<b>Points</b>', styles['Normal']),
                            Paragraph('<b>Result</b>', styles['Normal'])
                        ]]
                        for idx, qb in enumerate(question_breakdown, 1):
                            q_text = qb['question_text'][:50] + '...' if len(qb['question_text']) > 50 else qb['question_text']
                            result = '✓ Correct' if qb['is_correct'] else '✗ Wrong'
                            result_color = rl_colors.green if qb['is_correct'] else rl_colors.red

                            q_data.append([
                                Paragraph(str(idx), styles['Normal']),
                                Paragraph(q_text, styles['Normal']),
                                Paragraph(qb['question_type'][:10], styles['Normal']),
                                Paragraph(str(qb['points']), styles['Normal']),
                                Paragraph(result, styles['Normal'])
                            ])

                        q_table = Table(q_data, colWidths=[0.3*inch, 2.8*inch, 0.8*inch, 0.5*inch, 0.8*inch])

                        # Build style with conditional colors for results
                        table_style_commands = [
                            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#E2E8F0')),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('ALIGN', (3, 0), (4, -1), 'CENTER'),
                            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
                            ('BACKGROUND', (0, 1), (-1, -1), rl_colors.white),
                        ]

                        # Add color coding for correct/incorrect
                        for idx, qb in enumerate(question_breakdown, 1):
                            row = idx
                            if qb['is_correct']:
                                table_style_commands.append(('TEXTCOLOR', (4, row), (4, row), rl_colors.green))
                            else:
                                table_style_commands.append(('TEXTCOLOR', (4, row), (4, row), rl_colors.red))

                        q_table.setStyle(TableStyle(table_style_commands))
                        story.append(q_table)

                        # Add summary line
                        summary_text = f"<i>Summary: {correct_count} correct out of {total_count} questions</i>"
                        story.append(Spacer(1, 0.05*inch))
                        story.append(Paragraph(summary_text, styles['Normal']))
                        story.append(Spacer(1, 0.3*inch))

            # Build PDF with custom header and footer
            doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

            # Close dialog and show file picker
            if self.page and self.page.dialog:
                self.page.dialog.open = False
                self.page.update()

            # Show file picker to save PDF
            self.save_pdf_with_picker(filepath, filename)

        except Exception as ex:
            print(f"[ERROR] Error generating student PDF: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to generate student PDF: {str(ex)}")

    def generate_student_exam_pdf(self, user_id, exam_id, student_name, exam_title):
        """Generate detailed PDF report for a specific student's specific exam with question breakdown"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors as rl_colors
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os

            # Get exam session
            # exam_id parameter could be assignment_id or exam_id
            session = self.db.execute_single("""
                SELECT
                    es.id, es.score, es.duration_seconds, es.start_time, es.end_time,
                    es.correct_answers, es.total_questions,
                    COALESCE(ea.passing_score, e.passing_score) as passing_score,
                    COALESCE(ea.assignment_name, e.title) as title
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
                WHERE es.user_id = ?
                  AND (es.assignment_id = ? OR (es.assignment_id IS NULL AND es.exam_id = ?))
                  AND es.is_completed = 1
                ORDER BY es.start_time DESC
                LIMIT 1
            """, (user_id, exam_id, exam_id))

            if not session:
                self.show_message(t('no_data'), t('no_completed_exam_session'))
                return

            # Get detailed question-level data
            question_details = self.db.execute_query("""
                SELECT
                    q.id, q.question_text, q.question_type, q.points,
                    ua.answer_text, ua.is_correct, ua.selected_option_id,
                    GROUP_CONCAT(qo.option_text || '|' || qo.is_correct, ';;;') as options
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                LEFT JOIN question_options qo ON q.id = qo.question_id
                WHERE ua.session_id = ?
                GROUP BY q.id, ua.id
                ORDER BY q.id
            """, (session['id'],))

            # Create PDF with custom header/footer
            import re
            safe_name = re.sub(r'[^\w\s-]', '', student_name).strip().replace(' ', '_')
            safe_exam = re.sub(r'[^\w\s-]', '', exam_title).strip().replace(' ', '_')
            filename = f"detailed_report_{safe_name}_{safe_exam}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.temp_dir, filename)

            # Register Unicode font for Azerbaijani characters
            unicode_font_registered = False
            try:
                # Try Arial first (supports Azerbaijani)
                from reportlab.pdfbase.ttfonts import TTFont
                pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Italic', '/System/Library/Fonts/Supplemental/Arial Italic.ttf'))
                pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic')
                unicode_font = 'Arial'
                unicode_font_bold = 'Arial-Bold'
                unicode_font_registered = True
                print("[INFO] Registered Arial fonts for Azerbaijani text")
            except Exception as e:
                print(f"[WARN] Could not register Arial: {e}")
                try:
                    # Try DejaVu Sans as fallback
                    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
                    unicode_font = 'DejaVuSans'
                    unicode_font_bold = 'DejaVuSans-Bold'
                    unicode_font_registered = True
                    print("[INFO] Registered DejaVu Sans for text")
                except Exception as e2:
                    print(f"[WARN] Could not register DejaVu Sans: {e2}")
                    # Last resort: Helvetica (won't display special characters properly)
                    unicode_font = 'Helvetica'
                    unicode_font_bold = 'Helvetica-Bold'
                    print("[WARN] Using Helvetica (may not display Azerbaijani characters correctly)")

            # Custom document template with header and footer
            def add_header_footer(canvas_obj, doc):
                """Add header with logo and footer with confidential warning"""
                canvas_obj.saveState()

                # Header - Azercosmos Logo (Centered)
                logo_path = os.path.join(os.path.dirname(__file__), '../../assets/images/azercosmos-logo.png')
                logo_path = os.path.abspath(logo_path)  # Resolve to absolute path
                page_width = A4[0]
                logo_width = 150
                logo_height = 40
                logo_x = (page_width - logo_width) / 2  # Center horizontally

                if os.path.exists(logo_path):
                    try:
                        canvas_obj.drawImage(logo_path, logo_x, A4[1] - 60, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
                    except:
                        # If logo fails to load, just show text
                        canvas_obj.setFont('Helvetica-Bold', 10)
                        canvas_obj.drawCentredString(page_width / 2, A4[1] - 40, "AZERCOSMOS")
                else:
                    # Fallback if logo doesn't exist
                    canvas_obj.setFont('Helvetica-Bold', 10)
                    canvas_obj.drawCentredString(page_width / 2, A4[1] - 40, "AZERCOSMOS")

                # Footer - Confidential Warning
                canvas_obj.setFont('Helvetica-Bold', 8)
                canvas_obj.drawCentredString(A4[0] / 2, 50, t('special_warning'))

                canvas_obj.setFont('Helvetica', 7)
                canvas_obj.drawCentredString(A4[0] / 2, 35, t('confidential_text'))

                # Page number
                canvas_obj.setFont('Helvetica', 8)
                canvas_obj.drawCentredString(A4[0] / 2, 15, f"{t('page')} {doc.page}")

                canvas_obj.restoreState()

            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                topMargin=80,  # Space for header
                bottomMargin=70  # Space for footer
            )
            story = []
            styles = getSampleStyleSheet()

            # Update styles to use Unicode font
            styles['Normal'].fontName = unicode_font
            styles['Heading1'].fontName = unicode_font_bold
            styles['Heading2'].fontName = unicode_font_bold
            styles['Heading3'].fontName = unicode_font_bold

            # Custom styles
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20, textColor=rl_colors.HexColor('#2D3748'), fontName=unicode_font_bold)
            subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, textColor=rl_colors.grey, fontName=unicode_font)

            # Title
            story.append(Paragraph(t('detailed_exam_report'), title_style))
            story.append(Paragraph(f"{exam_title}", styles['Heading2']))
            story.append(Paragraph(f"{t('student')}: {student_name}", subtitle_style))
            story.append(Paragraph(f"{t('generated')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
            story.append(Spacer(1, 0.3*inch))

            # Exam Summary - Use Paragraphs
            story.append(Paragraph(t('exam_summary'), styles['Heading2']))
            duration_min = session['duration_seconds'] // 60 if session['duration_seconds'] else 0
            status = t('pass') if session['score'] >= session['passing_score'] else t('fail')
            status_color = rl_colors.green if session['score'] >= session['passing_score'] else rl_colors.red

            # Extract exam date from start_time
            exam_date = session['start_time'][:10] if session['start_time'] else 'N/A'

            summary_data = [
                [Paragraph(f'<b>{t("metric")}</b>', styles['Normal']), Paragraph(f'<b>{t("value")}</b>', styles['Normal'])],
                [Paragraph(t('exam_date'), styles['Normal']), Paragraph(exam_date, styles['Normal'])],
                [Paragraph(t('final_score'), styles['Normal']), Paragraph(f"{session['score']:.2f}%", styles['Normal'])],
                [Paragraph(t('correct_answers_count'), styles['Normal']), Paragraph(f"{session['correct_answers']} / {session['total_questions']}", styles['Normal'])],
                [Paragraph(t('passing_score'), styles['Normal']), Paragraph(f"{session['passing_score']}%", styles['Normal'])],
                [Paragraph(t('status'), styles['Normal']), Paragraph(status, styles['Normal'])],
                [Paragraph(t('duration'), styles['Normal']), Paragraph(f"{duration_min} {t('minutes_label')}", styles['Normal'])],
                [Paragraph(t('start_time'), styles['Normal']), Paragraph(session['start_time'][:19], styles['Normal'])],
                [Paragraph(t('end_time'), styles['Normal']), Paragraph(session['end_time'][:19] if session['end_time'] else 'N/A', styles['Normal'])],
            ]

            summary_table = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#4299E1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), rl_colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, rl_colors.black),
                ('TEXTCOLOR', (1, 5), (1, 5), status_color),  # Status color (row index adjusted)
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.4*inch))

            # Question-by-Question Breakdown
            story.append(Paragraph(t('question_by_question_breakdown'), styles['Heading2']))
            story.append(Spacer(1, 0.2*inch))

            if question_details:
                for idx, q in enumerate(question_details, 1):
                    # Question header with result icon
                    result_icon = "✓" if q['is_correct'] else "✗"
                    result_color = rl_colors.green if q['is_correct'] else rl_colors.red

                    q_header_style = ParagraphStyle(
                        f'QHeader{idx}',
                        parent=styles['Heading3'],
                        fontSize=12,
                        textColor=result_color,
                        spaceAfter=6
                    )

                    story.append(Paragraph(f"{result_icon} {t('question')} {idx}: {q['question_type'].upper()} ({q['points']} {t('pts')})", q_header_style))

                    # Question text
                    question_text = q['question_text'][:500]  # Limit length
                    story.append(Paragraph(f"<b>Q:</b> {question_text}", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))

                    # Handle different question types
                    if q['question_type'] in ['multiple_choice', 'true_false']:
                        # Parse options - Use Paragraphs
                        if q['options']:
                            options_list = q['options'].split(';;;')
                            options_data = [[
                                Paragraph(f'<b>{t("option")}</b>', styles['Normal']),
                                Paragraph(f'<b>{t("correct_answer_label")}</b>', styles['Normal']),
                                Paragraph(f'<b>{t("student_selected")}</b>', styles['Normal'])
                            ]]

                            for opt in options_list:
                                if '|' in opt:
                                    opt_text, is_correct = opt.rsplit('|', 1)
                                    is_correct_bool = is_correct == '1'

                                    # Check if this option was selected by the student
                                    was_selected = ''
                                    if q['selected_option_id']:
                                        # Find option ID (would need to enhance query to get option IDs)
                                        was_selected = '✓' if is_correct_bool and q['is_correct'] else ''

                                    options_data.append([
                                        Paragraph(opt_text[:60], styles['Normal']),
                                        Paragraph('✓' if is_correct_bool else '', styles['Normal']),
                                        Paragraph('✓' if q['answer_text'] and opt_text in q['answer_text'] else '', styles['Normal'])
                                    ])

                            if len(options_data) > 1:
                                opts_table = Table(options_data, colWidths=[3*inch, 1*inch, 1*inch])
                                opts_table.setStyle(TableStyle([
                                    ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#E2E8F0')),
                                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                                    ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
                                    ('BACKGROUND', (0, 1), (-1, -1), rl_colors.white),
                                ]))
                                story.append(opts_table)

                    elif q['question_type'] in ['short_answer', 'essay']:
                        # Show student's answer - Use Paragraphs
                        answer_data = [
                            [Paragraph(f'<b>{t("student_answer")}</b>', styles['Normal']),
                             Paragraph(q['answer_text'][:200] if q['answer_text'] else t('no_answer_provided'), styles['Normal'])],
                        ]

                        answer_table = Table(answer_data, colWidths=[1.5*inch, 4.5*inch])
                        answer_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (0, -1), rl_colors.HexColor('#E2E8F0')),
                            ('FONTSIZE', (0, 0), (-1, -1), 9),
                            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('BACKGROUND', (1, 0), (1, -1), rl_colors.white),
                        ]))
                        story.append(answer_table)

                    # Result
                    result_status = t('correct_uppercase') if q['is_correct'] else t('incorrect_uppercase')
                    result_text = f"<b>{t('result')}:</b> <font color=\"{'green' if q['is_correct'] else 'red'}\">{result_status}</font>"
                    story.append(Spacer(1, 0.05*inch))
                    story.append(Paragraph(result_text, styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))

                    # Add separator
                    story.append(Paragraph("<hr/>", styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))

            # Build PDF with custom header and footer
            doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

            # Close dialog and show file picker
            if self.page and self.page.dialog:
                self.page.dialog.open = False
                self.page.update()

            # Show file picker to save PDF
            self.save_pdf_with_picker(filepath, filename)

        except Exception as ex:
            print(f"[ERROR] Error generating student-exam PDF: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to generate detailed exam PDF: {str(ex)}")

    def export_pdf(self, e):
        """Export reports as PDF"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            
            # Create PDF with basic report in current directory
            import os
            filename = f"exam_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.temp_dir, filename)
            
            c = canvas.Canvas(filepath, pagesize=letter)
            width, height = letter
            
            # Title
            c.setFont("Helvetica-Bold", 24)
            c.drawString(50, height - 50, "Exam System Analytics Report")
            
            # Date
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 80, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Key metrics
            y_pos = height - 120
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, y_pos, "Key Performance Indicators")
            
            y_pos -= 30
            c.setFont("Helvetica", 12)
            c.drawString(50, y_pos, f"Total Active Exams: {self.total_exams}")
            y_pos -= 20
            c.drawString(50, y_pos, f"Total Completed Sessions: {self.total_sessions}")
            y_pos -= 20
            c.drawString(50, y_pos, f"Average Score: {self.avg_score}%")
            y_pos -= 20
            c.drawString(50, y_pos, f"Pass Rate: {self.pass_rate}%")
            
            c.save()
            
            # Show success message
            self.show_message("PDF Export", f"Report exported successfully!\nFile saved as: {filename}")
            
        except Exception as ex:
            self.show_message("Export Error", f"Failed to export PDF: {str(ex)}")
    
    def get_exam_filter_options(self):
        """Get exam/assignment options for filter dropdowns (used by User Progress)"""
        # Get assignments (these are what users actually take)
        assignments_data = self.db.execute_query("""
            SELECT DISTINCT
                ea.id,
                ea.assignment_name as title,
                'assignment' as type
            FROM exam_assignments ea
            WHERE ea.id IN (SELECT DISTINCT assignment_id FROM exam_sessions WHERE assignment_id IS NOT NULL)
            ORDER BY ea.created_at DESC
        """)

        # Get standalone exams (old exams without assignments)
        standalone_exams = self.db.execute_query("""
            SELECT DISTINCT
                e.id,
                e.title,
                'exam' as type
            FROM exams e
            WHERE e.is_active = 1
            AND e.id IN (SELECT DISTINCT exam_id FROM exam_sessions WHERE assignment_id IS NULL)
            ORDER BY e.created_at DESC
        """)

        # Combine both lists
        exams_data = assignments_data + standalone_exams

        # Create dropdown options
        options = [ft.dropdown.Option("all", "All Exams/Assignments")]
        options.extend([
            ft.dropdown.Option(
                str(item['id']),
                f"{item['title']}" + (" (Legacy)" if item.get('type') == 'exam' else "")
            )
            for item in exams_data
        ])

        return options, exams_data

    def get_topic_filter_options(self):
        """Get topic/category options for filter dropdowns (used by Exam Performance & Question Analysis)"""
        # Get all distinct exam titles (which serve as topics) from active exams
        topics_data = self.db.execute_query("""
            SELECT DISTINCT e.title
            FROM exams e
            WHERE e.title IS NOT NULL
            AND e.title != ''
            AND e.is_active = 1
            ORDER BY e.title
        """)

        # Create dropdown options
        options = [ft.dropdown.Option("all", t('all_topics'))]
        if topics_data:
            options.extend([
                ft.dropdown.Option(topic['title'], topic['title'])
                for topic in topics_data
            ])

        print(f"[DEBUG] Topic filter options: {len(options)} total ({len(options)-1} topics)")
        return options

    def show_detailed_report(self, report_type):
        """Show detailed report in a dialog"""
        try:
            print(f"[DEBUG] show_detailed_report called for: {report_type}")

            if report_type == "exam_performance":
                content = self.create_exam_performance_details()
            elif report_type == "user_progress":
                content = self.create_user_progress_details()
            elif report_type == "question_analysis":
                content = self.create_question_analysis_details()
            else:
                content = ft.Text(t('loading') + "...")

            # Use safe dialog creation with MUCH bigger size
            success = self.safe_show_dialog(
                title=f"{report_type} - Detailed Report",
                content=content,
                width=1400,
                height=900
            )

            if not success:
                print(f"[ERROR] Failed to show detailed report dialog")

        except Exception as ex:
            print(f"[ERROR] Failed to show detailed report: {ex}")
            # Don't show nested error dialogs - just log
            import traceback
            traceback.print_exc()
    
    def create_exam_performance_details(self, selected_topic=None):
        """Create detailed exam performance report with topic filter"""
        try:
            # Container ref for rebuilding
            container_ref = ft.Ref[ft.Container]()
            table_container_ref = ft.Ref[ft.Container]()

            # Get filter options
            filter_options = self.get_topic_filter_options()

            # Create filter dropdown
            topic_filter = ft.Dropdown(
                label=t('filter_by_topic'),
                options=filter_options,
                value=selected_topic if selected_topic else "all",
                width=350,
                on_change=None  # Will set below
            )

            def load_data(filter_value):
                """Load exam performance data based on topic filter"""
                # Build query with optional topic filter (filtering by exam title)
                query = """
                    SELECT
                        e.title,
                        e.category,
                        COUNT(es.id) as sessions_count,
                        AVG(es.score) as avg_score,
                        MIN(es.score) as min_score,
                        MAX(es.score) as max_score,
                        AVG(es.duration_seconds)/60 as avg_duration_minutes
                    FROM exams e
                    LEFT JOIN exam_sessions es ON e.id = es.exam_id AND es.is_completed = 1
                    WHERE e.is_active = 1
                """

                params = []
                if filter_value != "all":
                    query += " AND e.title = ?"
                    params.append(filter_value)

                query += """
                    GROUP BY e.id, e.title, e.category
                    ORDER BY sessions_count DESC
                """

                exam_details = self.db.execute_query(query, tuple(params)) if params else self.db.execute_query(query)

                if not exam_details:
                    return ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.ASSESSMENT_OUTLINED, size=60, color=COLORS['text_secondary']),
                            ft.Text("No exam data available", size=18, weight=ft.FontWeight.BOLD, color=COLORS['text_secondary'])
                        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.all(40),
                        alignment=ft.alignment.center,
                        expand=True
                    )

                # Create table
                table = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text(t('exam_title'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('sessions'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('average_score'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('min_score'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('max_score'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('avg_duration_min'), weight=ft.FontWeight.BOLD))
                    ],
                    rows=[],
                    width=float("inf"),
                    column_spacing=20,
                    border=ft.border.all(1, ft.colors.BLACK12),
                    border_radius=8
                )

                for exam in exam_details:
                    table.rows.append(
                        ft.DataRow([
                            ft.DataCell(ft.Text(exam['title'][:40] + "..." if len(exam['title']) > 40 else exam['title'], size=13)),
                            ft.DataCell(ft.Text(str(exam['sessions_count'] or 0), size=13)),
                            ft.DataCell(ft.Text(f"{exam['avg_score']:.1f}%" if exam['avg_score'] else "N/A", size=13)),
                            ft.DataCell(ft.Text(f"{exam['min_score']:.1f}%" if exam['min_score'] else "N/A", size=13)),
                            ft.DataCell(ft.Text(f"{exam['max_score']:.1f}%" if exam['max_score'] else "N/A", size=13)),
                            ft.DataCell(ft.Text(f"{exam['avg_duration_minutes']:.1f}" if exam['avg_duration_minutes'] else "N/A", size=13))
                        ])
                    )

                return ft.Container(
                    content=ft.ListView(
                        controls=[table],
                        expand=True,
                        auto_scroll=False
                    ),
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    padding=ft.padding.all(15),
                    border=ft.border.all(1, ft.colors.BLACK12),
                    expand=True
                )

            def on_filter_change(e):
                """Handle filter change"""
                # Rebuild table container
                table_container_ref.current.content = load_data(e.control.value)
                table_container_ref.current.update()

            topic_filter.on_change = on_filter_change

            # Initial table load
            initial_table = load_data(topic_filter.value)

            # Main container
            return ft.Container(
                ref=container_ref,
                content=ft.Column([
                    # Filter section
                    ft.Container(
                        content=ft.Row([
                            topic_filter
                        ]),
                        padding=ft.padding.only(bottom=15)
                    ),
                    # Table container
                    ft.Container(
                        ref=table_container_ref,
                        content=initial_table,
                        expand=True
                    )
                ], spacing=0),
                padding=ft.padding.all(20),
                expand=True
            )

        except Exception as e:
            print(f"[ERROR] create_exam_performance_details: {e}")
            import traceback
            traceback.print_exc()
            return ft.Text(f"Error loading exam details: {str(e)}")
    
    def create_user_progress_details(self, selected_exam_id=None):
        """Create detailed user progress report with internal filter"""
        try:
            print("[DEBUG] Starting create_user_progress_details")

            # Container refs for rebuilding
            container_ref = ft.Ref[ft.Container]()
            content_container_ref = ft.Ref[ft.Container]()

            # Get filter options
            filter_options, exams_data = self.get_exam_filter_options()

            # Create filter dropdown
            exam_filter = ft.Dropdown(
                label="Filter by Exam/Assignment",
                options=filter_options,
                value=str(selected_exam_id) if selected_exam_id else "all",
                width=350,
                on_change=None  # Will set below
            )

            def load_data(filter_value):
                """Load user progress data based on filter"""
                # Build query with exam filter
                query = """
                    SELECT
                        u.id,
                        u.username,
                        u.full_name,
                        u.department,
                        u.role,
                        COALESCE(COUNT(DISTINCT es.exam_id), 0) as exams_taken,
                        COALESCE(COUNT(es.id), 0) as total_attempts,
                        COALESCE(ROUND(AVG(es.score), 1), 0) as avg_score,
                        COALESCE(MAX(es.score), 0) as best_score,
                        COALESCE(SUM(CASE WHEN es.score >= 70 THEN 1 ELSE 0 END), 0) as passed_exams,
                        COALESCE(ROUND(AVG(es.duration_seconds)/60, 1), 0) as avg_duration_minutes,
                        MAX(es.end_time) as last_exam_date
                    FROM users u
                    LEFT JOIN exam_sessions es ON u.id = es.user_id AND es.is_completed = 1"""

                params = []
                where_conditions = ["u.is_active = 1", "u.role = 'examinee'"]

                # Add exam filter if selected
                if filter_value != "all":
                    where_conditions.append("(es.exam_id = ? OR es.exam_id IS NULL)")
                    params.append(int(filter_value))

                query += " WHERE " + " AND ".join(where_conditions)
                query += """
                    GROUP BY u.id, u.username, u.full_name, u.department, u.role
                    ORDER BY u.full_name
                    LIMIT 100
                """

                # Get user progress data with actual metrics
                user_progress_data = self.db.execute_query(query, tuple(params)) if params else self.db.execute_query(query)
            
                print(f"[DEBUG] Retrieved {len(user_progress_data) if user_progress_data else 0} users from database")

                if not user_progress_data:
                    return ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.PERSON_OFF, size=60, color=COLORS['text_secondary']),
                            ft.Text("No examinee users found", size=18, weight=ft.FontWeight.BOLD, color=COLORS['text_secondary']),
                            ft.Text("Add some examinees to see progress reports", size=14, color=COLORS['text_secondary'])
                        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.all(40),
                        alignment=ft.alignment.center,
                        expand=True
                    )
            
                # Calculate summary statistics
                total_users = len(user_progress_data)
                active_users = sum(1 for u in user_progress_data if u['total_attempts'] > 0)
                avg_score = sum(u['avg_score'] for u in user_progress_data if u['avg_score'] > 0) / active_users if active_users > 0 else 0
            
                # Summary cards
                summary_cards = ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(total_users), size=24, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                            ft.Text("Total Users", size=12, color=COLORS['text_secondary'])
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        width=100,
                        height=70,
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                        border_radius=8,
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['primary']))
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(active_users), size=24, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                            ft.Text("Active Users", size=12, color=COLORS['text_secondary'])
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        width=100,
                        height=70,
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['success']),
                        border_radius=8,
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['success']))
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"{avg_score:.1f}%", size=24, weight=ft.FontWeight.BOLD, color=COLORS['warning']),
                            ft.Text(t('average_score'), size=12, color=COLORS['text_secondary'])
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        width=100,
                        height=70,
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                        border_radius=8,
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['warning']))
                    )
                ], spacing=15)
            
                # Create comprehensive progress table
                progress_table = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text(t('username'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('department'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('exams'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('attempts_count'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('average_score'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('best_score'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('pass_rate'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('avg_duration'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('last_activity'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('actions'), weight=ft.FontWeight.BOLD))
                    ],
                    rows=[],
                    width=float("inf"),
                    column_spacing=15,
                    border=ft.border.all(1, ft.colors.BLACK12),
                    border_radius=8
                )
            
                # Populate table with data
                for user in user_progress_data:
                    exams_taken = user['exams_taken'] or 0
                    total_attempts = user['total_attempts'] or 0
                    passed_exams = user['passed_exams'] or 0
                    avg_score = user['avg_score'] or 0
                    best_score = user['best_score'] or 0
                    avg_duration = user['avg_duration_minutes'] or 0

                    # Calculate pass rate
                    pass_rate = (passed_exams / total_attempts * 100) if total_attempts > 0 else 0

                    # Format last exam date
                    last_exam = user['last_exam_date']
                    if last_exam:
                        try:
                            last_exam_formatted = last_exam[:10] if len(last_exam) >= 10 else last_exam
                        except:
                            last_exam_formatted = "Never"
                    else:
                        last_exam_formatted = "Never"

                    # Color coding
                    score_color = COLORS['success'] if avg_score >= 80 else (COLORS['warning'] if avg_score >= 60 else COLORS['error'])

                    progress_table.rows.append(
                        ft.DataRow([
                            ft.DataCell(ft.Column([
                                ft.Text(user['full_name'], weight=ft.FontWeight.BOLD, size=13),
                                ft.Text(f"@{user['username']}", size=11, color=COLORS['text_secondary'])
                            ], spacing=2)),
                            ft.DataCell(ft.Text(user['department'] or "N/A", size=13)),
                            ft.DataCell(ft.Text(str(exams_taken), size=13)),
                            ft.DataCell(ft.Text(str(total_attempts), size=13)),
                            ft.DataCell(ft.Text(f"{avg_score:.1f}%" if avg_score > 0 else "N/A", color=score_color, size=13, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(f"{best_score:.1f}%" if best_score > 0 else "N/A", size=13)),
                            ft.DataCell(ft.Text(f"{pass_rate:.1f}%" if total_attempts > 0 else "N/A", size=13)),
                            ft.DataCell(ft.Text(f"{avg_duration:.1f}m" if avg_duration > 0 else "N/A", size=13)),
                            ft.DataCell(ft.Text(last_exam_formatted, size=13)),
                            ft.DataCell(ft.IconButton(
                                icon=ft.icons.VISIBILITY,
                                tooltip="View Details",
                                on_click=lambda e, user_id=user['id']: self.show_individual_user_details(user_id),
                                icon_color=COLORS['primary'],
                                icon_size=16
                            ))
                        ])
                    )
            
                # Return the data container
                return ft.Column([
                    # Summary cards
                    ft.Container(
                        content=summary_cards,
                        padding=ft.padding.only(bottom=20)
                    ),
                    # Export button
                    ft.Container(
                        content=ft.ElevatedButton(
                            text="Export User Data",
                            icon=ft.icons.DOWNLOAD,
                            on_click=lambda e: self.export_user_progress_simple(user_progress_data),
                            style=ft.ButtonStyle(bgcolor=COLORS['success'], color=ft.colors.WHITE)
                        ),
                        padding=ft.padding.only(bottom=15)
                    ),
                    # Table
                    ft.Container(
                        content=ft.ListView(
                            controls=[progress_table],
                            expand=True,
                            auto_scroll=False
                        ),
                        bgcolor=ft.colors.WHITE,
                        border_radius=8,
                        padding=ft.padding.all(15),
                        border=ft.border.all(1, ft.colors.BLACK12),
                        expand=True
                    )
                ], spacing=0, expand=True)

            def on_filter_change(e):
                """Handle filter change"""
                # Rebuild content container
                content_container_ref.current.content = load_data(e.control.value)
                content_container_ref.current.update()

            exam_filter.on_change = on_filter_change

            # Initial data load
            initial_content = load_data(exam_filter.value)

            # Main container
            return ft.Container(
                ref=container_ref,
                content=ft.Column([
                    # Filter section
                    ft.Container(
                        content=ft.Row([
                            exam_filter
                        ]),
                        padding=ft.padding.only(bottom=15)
                    ),
                    # Content container
                    ft.Container(
                        ref=content_container_ref,
                        content=initial_content,
                        expand=True
                    )
                ], spacing=0),
                padding=ft.padding.all(20),
                expand=True
            )
            
        except Exception as e:
            print(f"[ERROR] Exception in create_user_progress_details: {e}")
            import traceback
            traceback.print_exc()
            
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.ERROR, size=60, color=COLORS['error']),
                    ft.Text("Error Loading User Progress", size=18, weight=ft.FontWeight.BOLD, color=COLORS['error']),
                    ft.Text(f"Error: {str(e)}", size=14),
                    ft.Text("Please check console for details", size=12, color=COLORS['text_secondary'])
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.all(40),
                alignment=ft.alignment.center
            )
    
    def get_department_options(self, user_data):
        """Get unique departments from user data for filter dropdown"""
        departments = set()
        for user in user_data:
            if user.get('department'):
                departments.add(user['department'])
        
        options = [ft.dropdown.Option("all", "All Departments")]
        for dept in sorted(departments):
            options.append(ft.dropdown.Option(dept, dept))
        return options
    
    def show_activity_logs(self, e):
        """Show audit/activity logs in a searchable dialog"""
        try:
            print("[DEBUG] Loading activity logs...")

            # Create filter controls
            action_filter = ft.Dropdown(
                label="Filter by Action",
                options=[
                    ft.dropdown.Option("ALL", "All Actions"),
                    ft.dropdown.Option("LOGIN_SUCCESS", "Login Success"),
                    ft.dropdown.Option("LOGIN_FAILED", "Login Failed"),
                    ft.dropdown.Option("LOGOUT", "Logout"),
                    ft.dropdown.Option("EXAM_START", "Exam Start"),
                    ft.dropdown.Option("EXAM_SUBMIT", "Exam Submit"),
                    ft.dropdown.Option("ADMIN_", "Admin Actions (any)")
                ],
                value="ALL",
                width=200
            )

            user_filter = ft.TextField(
                label="Filter by User ID",
                hint_text="Enter user ID",
                width=150
            )

            date_filter = ft.Dropdown(
                label="Time Period",
                options=[
                    ft.dropdown.Option("TODAY", "Today"),
                    ft.dropdown.Option("WEEK", "Last 7 Days"),
                    ft.dropdown.Option("MONTH", "Last 30 Days"),
                    ft.dropdown.Option("ALL", "All Time")
                ],
                value="WEEK",
                width=150
            )

            # Function to load and filter logs
            def load_logs():
                # Build query based on filters
                query = "SELECT * FROM audit_log WHERE 1=1"
                params = []

                # Action filter
                if action_filter.value and action_filter.value != "ALL":
                    if action_filter.value == "ADMIN_":
                        query += " AND action LIKE ?"
                        params.append("ADMIN_%")
                    else:
                        query += " AND action = ?"
                        params.append(action_filter.value)

                # User filter
                if user_filter.value and user_filter.value.strip():
                    try:
                        query += " AND user_id = ?"
                        params.append(int(user_filter.value.strip()))
                    except ValueError:
                        pass  # Invalid user ID, skip filter

                # Date filter
                if date_filter.value == "TODAY":
                    query += " AND DATE(created_at) = DATE('now')"
                elif date_filter.value == "WEEK":
                    query += " AND created_at >= datetime('now', '-7 days')"
                elif date_filter.value == "MONTH":
                    query += " AND created_at >= datetime('now', '-30 days')"

                query += " ORDER BY created_at DESC LIMIT 500"

                # Execute query with or without parameters
                if params:
                    logs = self.db.execute_query(query, tuple(params))
                else:
                    logs = self.db.execute_query(query)

                return logs or []

            # Load initial logs
            logs_data = load_logs()

            # Create logs table
            logs_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("ID", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Time", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("User ID", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Table", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Record ID", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Details", weight=ft.FontWeight.BOLD))
                ],
                rows=[],
                width=float("inf"),
                column_spacing=10,
                border=ft.border.all(1, ft.colors.BLACK12),
                border_radius=8
            )

            # Populate table
            for log in logs_data:
                # Format timestamp
                try:
                    timestamp = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).strftime("%m/%d %H:%M:%S")
                except:
                    timestamp = str(log['created_at'])[:19]

                # Color code actions
                action_color = COLORS['text_primary']
                if 'FAILED' in log['action']:
                    action_color = COLORS['error']
                elif 'SUCCESS' in log['action']:
                    action_color = COLORS['success']
                elif 'ADMIN' in log['action']:
                    action_color = ft.colors.PURPLE

                # Truncate details
                details = log['new_values'] or ""
                if len(details) > 50:
                    details = details[:47] + "..."

                logs_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Text(str(log['id']), size=11)),
                        ft.DataCell(ft.Text(timestamp, size=11)),
                        ft.DataCell(ft.Text(str(log['user_id']) if log['user_id'] else "N/A", size=11)),
                        ft.DataCell(ft.Text(log['action'], size=11, color=action_color, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(log['table_name'] or "", size=11)),
                        ft.DataCell(ft.Text(str(log['record_id']) if log['record_id'] else "", size=11)),
                        ft.DataCell(ft.Text(details, size=10))
                    ])
                )

            # Stats summary
            total_logs = len(logs_data)
            login_success = len([l for l in logs_data if l['action'] == 'LOGIN_SUCCESS'])
            login_failed = len([l for l in logs_data if l['action'] == 'LOGIN_FAILED'])
            exam_starts = len([l for l in logs_data if l['action'] == 'EXAM_START'])

            summary = ft.Container(
                content=ft.ResponsiveRow([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(total_logs), size=20, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                            ft.Text("Total Logs", size=11)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                        col={"xs": 6, "sm": 3},
                        padding=ft.padding.all(10),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                        border_radius=6
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(login_success), size=20, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                            ft.Text("Login Success", size=11)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                        col={"xs": 6, "sm": 3},
                        padding=ft.padding.all(10),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['success']),
                        border_radius=6
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(login_failed), size=20, weight=ft.FontWeight.BOLD, color=COLORS['error']),
                            ft.Text("Login Failed", size=11)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                        col={"xs": 6, "sm": 3},
                        padding=ft.padding.all(10),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['error']),
                        border_radius=6
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(exam_starts), size=20, weight=ft.FontWeight.BOLD, color=COLORS['warning']),
                            ft.Text("Exams Started", size=11)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                        col={"xs": 6, "sm": 3},
                        padding=ft.padding.all(10),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                        border_radius=6
                    )
                ]),
                padding=ft.padding.all(15),
                bgcolor=ft.colors.WHITE,
                border_radius=8
            )

            # Refresh function for filters
            def refresh_logs(e):
                logs_data = load_logs()
                logs_table.rows.clear()
                for log in logs_data:
                    try:
                        timestamp = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).strftime("%m/%d %H:%M:%S")
                    except:
                        timestamp = str(log['created_at'])[:19]

                    action_color = COLORS['text_primary']
                    if 'FAILED' in log['action']:
                        action_color = COLORS['error']
                    elif 'SUCCESS' in log['action']:
                        action_color = COLORS['success']
                    elif 'ADMIN' in log['action']:
                        action_color = ft.colors.PURPLE

                    details = log['new_values'] or ""
                    if len(details) > 50:
                        details = details[:47] + "..."

                    logs_table.rows.append(
                        ft.DataRow([
                            ft.DataCell(ft.Text(str(log['id']), size=11)),
                            ft.DataCell(ft.Text(timestamp, size=11)),
                            ft.DataCell(ft.Text(str(log['user_id']) if log['user_id'] else "N/A", size=11)),
                            ft.DataCell(ft.Text(log['action'], size=11, color=action_color, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(log['table_name'] or "", size=11)),
                            ft.DataCell(ft.Text(str(log['record_id']) if log['record_id'] else "", size=11)),
                            ft.DataCell(ft.Text(details, size=10))
                        ])
                    )
                if self.page:
                    self.page.update()

            # Content
            content = ft.Column([
                summary,
                ft.Container(height=15),
                ft.Container(
                    content=ft.Row([
                        action_filter,
                        user_filter,
                        date_filter,
                        ft.ElevatedButton(
                            "Apply Filters",
                            icon=ft.icons.FILTER_ALT,
                            on_click=refresh_logs,
                            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                        )
                    ], spacing=10, wrap=True),
                    padding=ft.padding.all(10),
                    bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                    border_radius=8
                ),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📋 Activity Log Entries", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.ListView(
                            controls=[logs_table],
                            expand=True,
                            auto_scroll=False
                        )
                    ], spacing=5),
                    padding=ft.padding.all(15),
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    expand=True
                )
            ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

            # Show dialog
            self.safe_show_dialog(
                title="🔒 System Activity Logs",
                content=content,
                width=1600,
                height=900
            )

        except Exception as ex:
            print(f"[ERROR] Error showing activity logs: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to load activity logs: {str(ex)}")

    def show_suspicious_activity(self, e):
        """Show detected suspicious exam behavior"""
        try:
            from quiz_app.utils.pattern_analyzer import get_pattern_analyzer

            analyzer = get_pattern_analyzer()

            # Get all suspicious sessions (score >= 30)
            suspicious_sessions = analyzer.get_suspicious_sessions(min_score=30)

            # Summary cards
            total_suspicious = len(suspicious_sessions)
            high_risk = len([s for s in suspicious_sessions if s['suspicion_score'] >= 70])
            medium_risk = len([s for s in suspicious_sessions if 50 <= s['suspicion_score'] < 70])
            low_risk = len([s for s in suspicious_sessions if 30 <= s['suspicion_score'] < 50])

            # Responsive summary cards
            summary_cards = ft.ResponsiveRow([
                ft.Container(
                    content=self.create_metric_card("Total Flagged", str(total_suspicious), ft.icons.WARNING, ft.colors.ORANGE),
                    col={"xs": 12, "sm": 6, "md": 3}
                ),
                ft.Container(
                    content=self.create_metric_card("High Risk", str(high_risk), ft.icons.ERROR, ft.colors.RED),
                    col={"xs": 12, "sm": 6, "md": 3}
                ),
                ft.Container(
                    content=self.create_metric_card("Medium Risk", str(medium_risk), ft.icons.WARNING_AMBER, ft.colors.ORANGE),
                    col={"xs": 12, "sm": 6, "md": 3}
                ),
                ft.Container(
                    content=self.create_metric_card("Low Risk", str(low_risk), ft.icons.INFO, ft.colors.YELLOW_700),
                    col={"xs": 12, "sm": 6, "md": 3}
                ),
            ])

            # Build table rows
            table_rows = []

            for session in suspicious_sessions[:100]:  # Show up to 100 recent
                # Parse issues detected
                issues_list = []
                try:
                    import json
                    issues_list = json.loads(session['issues_detected']) if session['issues_detected'] else []
                except:
                    issues_list = []

                # Color code based on suspicion score
                if session['suspicion_score'] >= 70:
                    score_color = ft.colors.RED
                    risk_level = "HIGH"
                elif session['suspicion_score'] >= 50:
                    score_color = ft.colors.ORANGE
                    risk_level = "MEDIUM"
                else:
                    score_color = ft.colors.YELLOW_700
                    risk_level = "LOW"

                table_rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(session['session_id']))),
                            ft.DataCell(ft.Text(session['username'])),
                            ft.DataCell(ft.Text(session['exam_title'])),
                            ft.DataCell(ft.Text(f"{session['exam_score']:.1f}%")),
                            ft.DataCell(ft.Row([
                                ft.Text(str(session['suspicion_score']), color=score_color, weight=ft.FontWeight.BOLD),
                                ft.Text(f" ({risk_level})", color=score_color, size=10)
                            ], spacing=5)),
                            ft.DataCell(ft.Text(', '.join(issues_list) if issues_list else 'N/A', size=11)),
                            ft.DataCell(
                                ft.IconButton(
                                    icon=ft.icons.VISIBILITY,
                                    tooltip="View Details",
                                    icon_color=COLORS['primary'],
                                    on_click=lambda e, sid=session['session_id']: self.show_pattern_details(sid)
                                )
                            ),
                        ]
                    )
                )

            # Create data table
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Session ID", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Student", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Exam", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('score'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Suspicion", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Issues Detected", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('actions'), weight=ft.FontWeight.BOLD)),
                ],
                rows=table_rows,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=8,
                horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
                heading_row_color=ft.colors.GREY_100,
            )

            # Build content with responsive layout
            content = ft.Column([
                ft.Container(height=10),
                summary_cards,
                ft.Container(height=20),
                ft.Text(
                    f"Showing {len(table_rows)} flagged exam session(s)",
                    size=14,
                    color=ft.colors.GREY_700,
                    italic=True
                ),
                ft.Container(height=10),
                # Scrollable table container
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            data_table
                        ], scroll=ft.ScrollMode.ALWAYS)
                    ]),
                    padding=ft.padding.all(15),
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    expand=True
                )
            ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

            # Show dialog
            self.safe_show_dialog(
                title="⚠️  Suspicious Activity Detection",
                content=content,
                width=1600,
                height=900
            )

        except Exception as ex:
            print(f"[ERROR] Error showing suspicious activity: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to load suspicious activity: {str(ex)}")

    def show_pattern_details(self, session_id):
        """Show detailed pattern analysis for a specific session"""
        try:
            # Get pattern analysis details
            pattern_data = self.db.execute_single("""
                SELECT * FROM pattern_analysis WHERE session_id = ?
            """, (session_id,))

            if not pattern_data:
                self.show_message("No Data", "No pattern analysis data found for this session.")
                return

            import json
            details = json.loads(pattern_data['details']) if pattern_data['details'] else {}
            issues = json.loads(pattern_data['issues_detected']) if pattern_data['issues_detected'] else []

            # Build details content
            details_controls = [
                ft.Text(f"Session ID: {session_id}", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text(f"Suspicion Score: {pattern_data['suspicion_score']}/100", size=14, color=ft.colors.RED if pattern_data['suspicion_score'] >= 70 else ft.colors.ORANGE),
                ft.Text(f"Issues Detected: {', '.join(issues)}", size=14),
                ft.Divider(),
                ft.Text("Detailed Analysis:", size=16, weight=ft.FontWeight.BOLD),
            ]

            # Rapid answers details
            if 'rapid_answers' in details:
                details_controls.append(ft.Text("🚀 Rapid Answers:", weight=ft.FontWeight.BOLD, color=ft.colors.ORANGE))
                for ra in details['rapid_answers'][:10]:  # Show up to 10
                    details_controls.append(
                        ft.Text(f"  • Question {ra['question_id']}: {ra['time_spent']}s (threshold: {ra['threshold']}s)", size=12)
                    )

            # Excessive changes details
            if 'excessive_changes' in details:
                details_controls.append(ft.Text("🔄 Excessive Answer Changes:", weight=ft.FontWeight.BOLD, color=ft.colors.ORANGE))
                for ec in details['excessive_changes'][:10]:  # Show up to 10
                    details_controls.append(
                        ft.Text(f"  • Question {ec['question_id']}: {ec['changes']} changes (threshold: {ec['threshold']})", size=12)
                    )

            # Similarity details
            if 'similarity' in details:
                sim = details['similarity']
                details_controls.append(ft.Text("👥 Answer Similarity:", weight=ft.FontWeight.BOLD, color=ft.colors.RED))
                details_controls.append(
                    ft.Text(f"  • {sim['similarity_percentage']}% similar to User ID {sim['similar_user_id']} (threshold: {sim['threshold']}%)", size=12)
                )

            content = ft.Column(details_controls, spacing=10, scroll=ft.ScrollMode.AUTO)

            self.safe_show_dialog(
                title=f"📊 Pattern Analysis Details - Session {session_id}",
                content=content,
                width=800,
                height=600
            )

        except Exception as ex:
            print(f"[ERROR] Error showing pattern details: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to load pattern details: {str(ex)}")

    def close_dialog(self, e=None):
        """Close the current dialog - SIMPLE VERSION like other pages"""
        if self.page and self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    
    def show_message(self, title, message):
        """Show a message dialog - SIMPLE VERSION like other pages"""
        actions = [ft.TextButton("OK", on_click=self.close_dialog)]
        self.safe_show_dialog(
            title=title,
            content=ft.Text(str(message)),
            actions=actions,
            width=400,
            height=200
        )
    
    
    def show_individual_user_details(self, user_id):
        """Show detailed information for a specific user - ENHANCED VERSION"""
        try:
            print(f"[DEBUG] show_individual_user_details called for user_id: {user_id}")

            # Get user basic info
            user_info = self.db.execute_single("""
                SELECT id, username, full_name, department, email
                FROM users WHERE id = ?
            """, (user_id,))

            if not user_info:
                self.show_message(t('error'), "User not found.")
                return

            # === PART A: OVERALL SUMMARY ===
            summary_stats = self.db.execute_single("""
                SELECT
                    COUNT(DISTINCT es.exam_id) as unique_exams_taken,
                    COUNT(es.id) as total_attempts,
                    COALESCE(ROUND(AVG(es.score), 1), 0) as avg_score,
                    COALESCE(MAX(es.score), 0) as best_score,
                    COALESCE(MIN(es.score), 0) as worst_score,
                    COALESCE(SUM(CASE WHEN es.score >= 70 THEN 1 ELSE 0 END), 0) as passed_count,
                    COALESCE(ROUND(AVG(es.duration_seconds)/60, 1), 0) as avg_duration_minutes,
                    COALESCE(SUM(es.duration_seconds), 0) as total_time_seconds,
                    MAX(es.end_time) as last_exam_date
                FROM exam_sessions es
                WHERE es.user_id = ? AND es.is_completed = 1
            """, (user_id,))

            # === PART C: COMPARISON TO OTHER USERS ===
            comparison_stats = self.db.execute_single("""
                SELECT
                    COALESCE(ROUND(AVG(score), 1), 0) as class_avg_score,
                    COUNT(DISTINCT user_id) as total_users,
                    COALESCE(ROUND(AVG(duration_seconds)/60, 1), 0) as class_avg_duration
                FROM exam_sessions
                WHERE is_completed = 1 AND score IS NOT NULL
            """)

            # Calculate percentile
            user_avg = summary_stats['avg_score']
            better_than = self.db.execute_single("""
                SELECT COUNT(DISTINCT user_id) as count
                FROM (
                    SELECT user_id, AVG(score) as avg_score
                    FROM exam_sessions
                    WHERE is_completed = 1 AND score IS NOT NULL
                    GROUP BY user_id
                ) user_avgs
                WHERE avg_score < ?
            """, (user_avg,))

            percentile = 0
            if comparison_stats['total_users'] > 1:
                percentile = round((better_than['count'] / (comparison_stats['total_users'] - 1)) * 100, 1)

            # Build summary cards
            pass_rate = round((summary_stats['passed_count'] / summary_stats['total_attempts'] * 100), 1) if summary_stats['total_attempts'] > 0 else 0

            summary_section = ft.Container(
                content=ft.Column([
                    # User header
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.PERSON, size=40, color=COLORS['primary']),
                            ft.Column([
                                ft.Text(user_info['full_name'], size=20, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                                ft.Text(f"@{user_info['username']} • {user_info['department'] or 'No Department'}", size=14, color=COLORS['text_secondary'])
                            ], spacing=2)
                        ], spacing=15),
                        padding=ft.padding.all(15),
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['primary']),
                        border_radius=8
                    ),
                    ft.Container(height=15),

                    # Overall Performance Summary
                    ft.Text("📊 Overall Performance Summary", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    ft.ResponsiveRow([
                        ft.Container(
                            content=ft.Column([
                                ft.Text(str(summary_stats['total_attempts']), size=24, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                                ft.Text("Total Exams", size=12, color=COLORS['text_secondary'])
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(10),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                            border_radius=8
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{summary_stats['avg_score']:.1f}%", size=24, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                                ft.Text(t('average_score'), size=12, color=COLORS['text_secondary'])
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(10),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['success']),
                            border_radius=8
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{pass_rate:.1f}%", size=24, weight=ft.FontWeight.BOLD, color=COLORS['warning']),
                                ft.Text(t('pass_rate'), size=12, color=COLORS['text_secondary'])
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(10),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                            border_radius=8
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{summary_stats['avg_duration_minutes']:.0f}m", size=24, weight=ft.FontWeight.BOLD, color=COLORS['error']),
                                ft.Text(t('avg_duration'), size=12, color=COLORS['text_secondary'])
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(10),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['error']),
                            border_radius=8
                        )
                    ]),
                    ft.Container(height=15),

                    # Comparison to Class Average
                    ft.Text("📈 Comparison to Class Average", size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(height=8),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text("Your Average:", size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{user_avg:.1f}%", size=14, color=COLORS['success']),
                                ft.Text(" vs Class Average:", size=14),
                                ft.Text(f"{comparison_stats['class_avg_score']:.1f}%", size=14, color=COLORS['text_secondary']),
                                ft.Text(f" ({'+' if user_avg > comparison_stats['class_avg_score'] else ''}{user_avg - comparison_stats['class_avg_score']:.1f}%)",
                                       size=14,
                                       color=COLORS['success'] if user_avg > comparison_stats['class_avg_score'] else COLORS['error'])
                            ], spacing=5),
                            ft.Container(height=5),
                            ft.Text(f"🏆 Better than {percentile:.1f}% of examinees ({better_than['count']} out of {comparison_stats['total_users']-1} other users)",
                                   size=13, color=COLORS['text_secondary']),
                            ft.Container(height=5),
                            ft.Row([
                                ft.Text(t('best_score') + ":", size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{summary_stats['best_score']:.1f}%", size=14, color=COLORS['success']),
                                ft.Text(" | " + t('worst_score') + ":", size=14),
                                ft.Text(f"{summary_stats['worst_score']:.1f}%", size=14, color=COLORS['error'])
                            ], spacing=5)
                        ], spacing=5),
                        padding=ft.padding.all(15),
                        bgcolor=ft.colors.with_opacity(0.05, COLORS['success']),
                        border_radius=8
                    )
                ], spacing=0),
                padding=ft.padding.all(15),
                bgcolor=ft.colors.WHITE,
                border_radius=8
            )

            # === Get exam list with session IDs for drilldown ===
            exam_list = self.db.execute_query("""
                SELECT
                    es.id as session_id,
                    COALESCE(ea.assignment_name, e.title) as exam_title,
                    es.score,
                    es.duration_seconds,
                    es.end_time,
                    es.attempt_number,
                    (CASE WHEN es.score >= COALESCE(ea.passing_score, 70) THEN 'Passed' ELSE 'Failed' END) as result
                FROM exam_sessions es
                JOIN exams e ON es.exam_id = e.id
                LEFT JOIN exam_assignments ea ON es.assignment_id = ea.id
                WHERE es.user_id = ? AND es.is_completed = 1
                ORDER BY es.end_time DESC
                LIMIT 20
            """, (user_id,))

            # Create exam history table with "View Questions" button
            details_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Exam", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('score'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Result", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('duration'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('date'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('actions'), weight=ft.FontWeight.BOLD))
                ],
                rows=[],
                width=float("inf"),
                column_spacing=15
            )

            if not exam_list:
                exam_history_section = ft.Container(
                    content=ft.Text("No exam history found for this user.", size=14, color=COLORS['text_secondary']),
                    padding=ft.padding.all(20),
                    alignment=ft.alignment.center
                )
            else:
                for exam in exam_list:
                    duration_minutes = (exam['duration_seconds'] or 0) / 60
                    exam_date = exam['end_time']
                    try:
                        exam_date_formatted = datetime.fromisoformat(exam_date.replace('Z', '+00:00')).strftime("%m/%d/%Y %H:%M")
                    except:
                        exam_date_formatted = str(exam_date)[:16] if exam_date else "N/A"

                    result_color = COLORS['success'] if exam['result'] == 'Passed' else COLORS['error']

                    details_table.rows.append(
                        ft.DataRow([
                            ft.DataCell(ft.Text(exam['exam_title'][:35] + "..." if len(exam['exam_title']) > 35 else exam['exam_title'], size=13)),
                            ft.DataCell(ft.Text(f"{exam['score']:.1f}%", size=13, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(exam['result'], color=result_color, size=13)),
                            ft.DataCell(ft.Text(f"{duration_minutes:.1f}m", size=13)),
                            ft.DataCell(ft.Text(exam_date_formatted, size=13)),
                            ft.DataCell(
                                ft.IconButton(
                                    icon=ft.icons.VISIBILITY,
                                    tooltip="View Question-by-Question Breakdown",
                                    on_click=lambda e, sid=exam['session_id'], title=exam['exam_title']: self.show_question_breakdown(sid, title, user_info['full_name']),
                                    icon_color=COLORS['primary'],
                                    icon_size=18
                                )
                            )
                        ])
                    )

                exam_history_section = ft.Container(
                    content=ft.Column([
                        ft.Text("📋 Recent Exam History", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.Container(
                            content=ft.ListView(
                                controls=[details_table],
                                expand=True,
                                auto_scroll=False
                            ),
                            height=350,
                            bgcolor=ft.colors.WHITE,
                            border_radius=8,
                            padding=ft.padding.all(10)
                        )
                    ], spacing=5),
                    padding=ft.padding.all(15),
                    bgcolor=ft.colors.WHITE,
                    border_radius=8
                )

            # Create complete content for dialog
            content = ft.Column([
                summary_section,
                ft.Container(height=15),
                exam_history_section
            ], spacing=0, scroll=ft.ScrollMode.AUTO)

            # Show dialog with user details
            success = self.safe_show_dialog(
                title=f"📊 Detailed Analytics - {user_info['full_name']}",
                content=content,
                width=1400,
                height=900
            )

            if not success:
                print(f"[ERROR] Failed to show user details dialog")

        except Exception as ex:
            print(f"[ERROR] Error showing individual user details: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to load user details: {str(ex)}")
    
    def show_question_breakdown(self, session_id, exam_title, user_name):
        """Show question-by-question breakdown for a specific exam session"""
        try:
            print(f"[DEBUG] show_question_breakdown called for session_id: {session_id}")

            # Get question-by-question details with time spent
            # Only show questions that were actually answered in this session (for question pool support)
            question_details = self.db.execute_query("""
                SELECT
                    q.id,
                    q.question_text,
                    q.question_type,
                    q.difficulty_level,
                    q.points as max_points,
                    ua.answer_text,
                    ua.selected_option_id,
                    ua.selected_option_ids,
                    ua.is_correct,
                    ua.points_earned,
                    ua.time_spent_seconds,
                    ua.answered_at,
                    (SELECT GROUP_CONCAT(option_text, ' | ')
                     FROM question_options
                     WHERE question_id = q.id AND is_correct = 1) as correct_answer
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                WHERE ua.session_id = ?
                AND ua.id IN (
                    SELECT MAX(id)
                    FROM user_answers
                    WHERE session_id = ?
                    GROUP BY question_id
                )
                ORDER BY ua.answered_at, q.order_index
            """, (session_id, session_id))

            if not question_details:
                self.show_message("No Data", "No question data found for this exam session.")
                return

            # Debug: Print time spent values
            print(f"[DEBUG] Question details count: {len(question_details)}")
            for idx, q in enumerate(question_details, 1):
                print(f"[DEBUG] Q{idx}: time_spent_seconds = {q['time_spent_seconds']}, answered_at = {q['answered_at']}")

            # Calculate statistics
            total_questions = len(question_details)
            correct_count = sum(1 for q in question_details if q['is_correct'] == 1)
            total_points_earned = sum(q['points_earned'] or 0 for q in question_details)
            total_max_points = sum(q['max_points'] or 1 for q in question_details)
            total_time_spent = sum(q['time_spent_seconds'] or 0 for q in question_details)
            avg_time_per_question = total_time_spent / total_questions if total_questions > 0 else 0

            print(f"[DEBUG] Total time spent: {total_time_spent}s, Average: {avg_time_per_question:.1f}s")

            # Summary header
            summary = ft.Container(
                content=ft.Column([
                    ft.Text(f"📝 {exam_title}", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"👤 {user_name}", size=14, color=COLORS['text_secondary']),
                    ft.Container(height=10),
                    ft.ResponsiveRow([
                        ft.Container(
                            content=ft.Column([
                                ft.Text(str(total_questions), size=20, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                                ft.Text(t('questions'), size=11)
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(8),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                            border_radius=6
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{correct_count}/{total_questions}", size=20, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                                ft.Text("Correct", size=11)
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(8),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['success']),
                            border_radius=6
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{total_points_earned:.1f}/{total_max_points:.1f}", size=20, weight=ft.FontWeight.BOLD, color=COLORS['warning']),
                                ft.Text("Points", size=11)
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(8),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                            border_radius=6
                        ),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{avg_time_per_question:.0f}s", size=20, weight=ft.FontWeight.BOLD, color=COLORS['error']),
                                ft.Text("Avg Time/Q", size=11)
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
                            col={"xs": 6, "sm": 3},
                            padding=ft.padding.all(8),
                            bgcolor=ft.colors.with_opacity(0.1, COLORS['error']),
                            border_radius=6
                        )
                    ])
                ], spacing=0),
                padding=ft.padding.all(15),
                bgcolor=ft.colors.WHITE,
                border_radius=8
            )

            # Question breakdown table
            breakdown_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("#", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('question'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('type'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('difficulty'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('user_answer'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('correct_answer'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('result'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('points'), weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text(t('time'), weight=ft.FontWeight.BOLD))
                ],
                rows=[],
                width=float("inf"),
                column_spacing=12,
                border=ft.border.all(1, ft.colors.BLACK12),
                border_radius=8
            )

            for idx, q in enumerate(question_details, 1):
                question_text = q['question_text'][:40] + "..." if len(q['question_text']) > 40 else q['question_text']

                # Format user's answer
                user_answer = "Not answered"
                if q['answer_text']:
                    user_answer = q['answer_text'][:30] + "..." if len(q['answer_text']) > 30 else q['answer_text']
                elif q['selected_option_id']:
                    option = self.db.execute_single("SELECT option_text FROM question_options WHERE id = ?", (q['selected_option_id'],))
                    user_answer = (option['option_text'][:30] + "...") if option and len(option['option_text']) > 30 else (option['option_text'] if option else "N/A")
                elif q['selected_option_ids']:
                    user_answer = "Multiple selected"

                # Color coding
                is_correct = q['is_correct'] == 1
                result_color = COLORS['success'] if is_correct else COLORS['error']
                result_icon = "✓" if is_correct else "✗"
                time_spent = q['time_spent_seconds'] or 0

                breakdown_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Text(str(idx), size=12)),
                        ft.DataCell(ft.Text(question_text, size=12)),
                        ft.DataCell(ft.Text(q['question_type'].replace('_', ' ').title(), size=11)),
                        ft.DataCell(ft.Text((q['difficulty_level'] or 'N/A').title(), size=11)),
                        ft.DataCell(ft.Text(user_answer, size=11)),
                        ft.DataCell(ft.Text(q['correct_answer'] or "Manual grading", size=11)),
                        ft.DataCell(ft.Text(result_icon, color=result_color, size=14, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{q['points_earned'] or 0:.1f}/{q['max_points'] or 1:.1f}", size=11)),
                        ft.DataCell(ft.Text(f"{time_spent}s", size=11, color=COLORS['warning'] if time_spent > avg_time_per_question * 1.5 else COLORS['text_secondary']))
                    ])
                )

            # Main content
            content = ft.Column([
                summary,
                ft.Container(height=15),
                ft.Container(
                    content=ft.Column([
                        ft.Text("📊 Question-by-Question Breakdown", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        ft.ListView(
                            controls=[breakdown_table],
                            expand=True,
                            auto_scroll=False
                        )
                    ], spacing=5),
                    padding=ft.padding.all(15),
                    bgcolor=ft.colors.WHITE,
                    border_radius=8,
                    expand=True
                )
            ], spacing=0, scroll=ft.ScrollMode.AUTO)

            # Show dialog
            self.safe_show_dialog(
                title=f"📋 Question Breakdown - {exam_title[:50]}",
                content=content,
                width=1600,
                height=900
            )

        except Exception as ex:
            print(f"[ERROR] Error showing question breakdown: {ex}")
            import traceback
            traceback.print_exc()
            self.show_message(t('error'), f"Failed to load question breakdown: {str(ex)}")

    def create_question_analysis_details(self, selected_topic=None):
        """Create detailed question analysis report with topic filter and toggle"""
        try:
            print(f"[DEBUG] create_question_analysis_details")

            # Container refs for rebuilding
            container_ref = ft.Ref[ft.Container]()
            content_container_ref = ft.Ref[ft.Container]()

            # Get filter options
            filter_options = self.get_topic_filter_options()

            # Create filter dropdown
            topic_filter = ft.Dropdown(
                label=t('filter_by_topic'),
                options=filter_options,
                value=selected_topic if selected_topic else "all",
                width=350,
                on_change=None  # Will set below
            )

            # Create toggle for showing all questions
            show_all_toggle = ft.Checkbox(
                label=t('showing_all_questions_including'),
                value=False,
                on_change=None  # Will set below
            )

            def load_data(filter_value, show_all):
                """Load question analysis data based on topic filter and toggle"""
                # Build query with optional topic filter (filtering by exam title)
                query = """
                    SELECT
                        q.id,
                        q.question_text,
                        q.question_type,
                        q.difficulty_level,
                        e.title as category,
                        COUNT(ua.id) as total_answers,
                        SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct_answers,
                        ROUND((SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(ua.id)), 1) as success_rate
                    FROM questions q
                    LEFT JOIN user_answers ua ON q.id = ua.question_id
                    LEFT JOIN exams e ON q.exam_id = e.id
                    WHERE ua.id IS NOT NULL
                """

                params = []
                if filter_value != "all":
                    query += " AND e.title = ?"
                    params.append(filter_value)
                    print(f"[DEBUG] Filtering by topic: {filter_value}")

                query += """
                    GROUP BY q.id, q.question_text, q.question_type, q.difficulty_level, e.title
                """

                # Add HAVING clause only if not showing all
                if not show_all:
                    query += " HAVING total_answers >= 3"

                query += """
                    ORDER BY success_rate ASC, total_answers DESC
                """

                print(f"[DEBUG] Final query: {query}")
                print(f"[DEBUG] Params: {params}, Show All: {show_all}")

                question_analysis = self.db.execute_query(query, tuple(params)) if params else self.db.execute_query(query)

                print(f"[DEBUG] Question analysis results: {len(question_analysis) if question_analysis else 0} questions")
                if question_analysis and len(question_analysis) > 0:
                    print(f"[DEBUG] First question: {question_analysis[0]}")

                if not question_analysis:
                    info_text = "Questions need at least 3 answers for analysis" if not show_all else "No question data available"
                    return ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.HELP_OUTLINE, size=60, color=COLORS['text_secondary']),
                            ft.Text("No question data available", size=18, weight=ft.FontWeight.BOLD, color=COLORS['text_secondary']),
                            ft.Text(info_text, size=14, color=COLORS['text_secondary'])
                        ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=ft.padding.all(40),
                        alignment=ft.alignment.center,
                        expand=True
                    )
            
                # Summary statistics
                total_questions = len(question_analysis)
                avg_success_rate = sum(q['success_rate'] for q in question_analysis) / total_questions
                difficult_questions = sum(1 for q in question_analysis if q['success_rate'] < 60)
            
                # Summary cards
                summary_cards = ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(total_questions), size=24, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                            ft.Text("Questions Analyzed", size=12, color=COLORS['text_secondary'])
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        width=120,
                        height=70,
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                        border_radius=8,
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['primary']))
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"{avg_success_rate:.1f}%", size=24, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                            ft.Text("Avg Success Rate", size=12, color=COLORS['text_secondary'])
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        width=120,
                        height=70,
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['success']),
                        border_radius=8,
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['success']))
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(difficult_questions), size=24, weight=ft.FontWeight.BOLD, color=COLORS['error']),
                            ft.Text("Difficult Questions", size=12, color=COLORS['text_secondary'])
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                        width=120,
                        height=70,
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['error']),
                        border_radius=8,
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['error']))
                    )
                ], spacing=15)
            
                # Create analysis table
                analysis_table = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text(t('question'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('exam_title'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('type'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('difficulty'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('total_answers'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('correct'), weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text(t('success_rate'), weight=ft.FontWeight.BOLD))
                    ],
                    rows=[],
                    width=float("inf"),
                    column_spacing=15,
                    border=ft.border.all(1, ft.colors.BLACK12),
                    border_radius=8
                )

                # Populate table
                for question in question_analysis:
                    question_text = question['question_text']
                    if len(question_text) > 45:
                        question_text = question_text[:42] + "..."

                    success_rate = question['success_rate']
                    success_color = COLORS['success'] if success_rate >= 80 else (COLORS['warning'] if success_rate >= 60 else COLORS['error'])

                    analysis_table.rows.append(
                        ft.DataRow([
                            ft.DataCell(ft.Text(question_text, size=13)),
                            ft.DataCell(ft.Text(question['category'] or "N/A", size=13, color=COLORS['text_secondary'])),
                            ft.DataCell(ft.Text(question['question_type'].title(), size=13)),
                            ft.DataCell(ft.Text(question['difficulty_level'].title(), size=13)),
                            ft.DataCell(ft.Text(str(question['total_answers']), size=13)),
                            ft.DataCell(ft.Text(str(question['correct_answers']), size=13)),
                            ft.DataCell(ft.Text(f"{success_rate:.1f}%", color=success_color, size=13, weight=ft.FontWeight.BOLD))
                        ])
                    )
            
                # Create info text based on filter state
                info_text = t('showing_questions_min_answers') if not show_all else t('showing_all_questions')

                # Return the data container
                return ft.Column([
                    # Summary cards
                    ft.Container(
                        content=summary_cards,
                        padding=ft.padding.only(bottom=20)
                    ),
                    # Info text
                    ft.Container(
                        content=ft.Column([
                            ft.Text(info_text, size=13, color=COLORS['text_secondary'], italic=True),
                            ft.Text(t('questions_low_success_review'),
                                  size=13, color=COLORS['warning'], weight=ft.FontWeight.BOLD)
                        ], spacing=5),
                        padding=ft.padding.only(bottom=15)
                    ),
                    # Table
                    ft.Container(
                        content=ft.ListView(
                            controls=[analysis_table],
                            expand=True,
                            auto_scroll=False
                        ),
                        bgcolor=ft.colors.WHITE,
                        border_radius=8,
                        padding=ft.padding.all(15),
                        border=ft.border.all(1, ft.colors.BLACK12),
                        expand=True
                    )
                ], spacing=0, expand=True)

            def on_change(e):
                """Handle filter or toggle change"""
                # Rebuild content container
                content_container_ref.current.content = load_data(topic_filter.value, show_all_toggle.value)
                content_container_ref.current.update()

            topic_filter.on_change = on_change
            show_all_toggle.on_change = on_change

            # Initial data load
            initial_content = load_data(topic_filter.value, show_all_toggle.value)

            # Main container
            return ft.Container(
                ref=container_ref,
                content=ft.Column([
                    # Filter section
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                topic_filter,
                                ft.Container(expand=True),
                                show_all_toggle
                            ]),
                        ]),
                        padding=ft.padding.only(bottom=15)
                    ),
                    # Content container
                    ft.Container(
                        ref=content_container_ref,
                        content=initial_content,
                        expand=True
                    )
                ], spacing=0),
                padding=ft.padding.all(20),
                expand=True
            )
            
        except Exception as e:
            print(f"Error creating question analysis details: {e}")
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.ERROR, size=60, color=COLORS['error']),
                    ft.Text("Error Loading Question Analysis", size=18, weight=ft.FontWeight.BOLD, color=COLORS['error']),
                    ft.Text(f"Error: {str(e)}", size=14)
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.all(40),
                alignment=ft.alignment.center
            )
    
    def export_user_progress_simple(self, user_data):
        """Simple export function for user progress data"""
        try:
            if not user_data:
                self.show_message("Export", "No user data available to export.")
                return
            
            import os
            from datetime import datetime
            
            # Create a more accessible file path (current directory)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"user_progress_report_{timestamp}.csv"
            filepath = os.path.join(self.temp_dir, filename)
            
            # Prepare CSV content
            csv_content = "Username,Full Name,Department,Role,Exams Taken,Total Attempts,Average Score,Best Score,Pass Rate,Last Activity\n"
            
            for user in user_data:
                exams_taken = user.get('exams_taken', 0) or 0
                total_attempts = user.get('total_attempts', 0) or 0
                passed_exams = user.get('passed_exams', 0) or 0
                avg_score = user.get('avg_score', 0) or 0
                best_score = user.get('best_score', 0) or 0
                last_exam_date = user.get('last_exam_date', '') or 'Never'
                
                pass_rate = (passed_exams / total_attempts * 100) if total_attempts > 0 else 0
                
                csv_content += f'"{user.get("username", "")}","{user.get("full_name", "")}","{user.get("department", "") or "N/A"}","{user.get("role", "")}",{exams_taken},{total_attempts},{avg_score:.1f},{best_score:.1f},{pass_rate:.1f},"{last_exam_date}"\n'
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            self.show_message("Export Success", f"User progress exported successfully!\nFile saved as: {filename}\nLocation: {filepath}\nUsers exported: {len(user_data)}")
            
        except Exception as ex:
            print(f"Error exporting user progress: {ex}")
            self.show_message("Export Error", f"Failed to export user data: {str(ex)}")