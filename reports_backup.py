import flet as ft
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import io
import base64
import pandas as pd
from quiz_app.config import COLORS
from quiz_app.database.database import Database

class Reports(ft.UserControl):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.chart_images = {}  # Store chart images
        self.current_dialog = None  # Track current dialog
        
        # Set matplotlib style for better looking charts
        plt.style.use('default')
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = 'white'
        
    def did_mount(self):
        super().did_mount()
        # Load data first
        self.load_analytics_data()
        # Generate charts in background
        self.generate_charts()
        # Update the UI with loaded data
        if self.page:
            self.update()
    
    def will_unmount(self):
        """Clean up when component is unmounted"""
        super().will_unmount()
        self.cleanup_dialogs()
    
    def cleanup_dialogs(self):
        """Force cleanup of any open dialogs"""
        try:
            print(f"[DEBUG] cleanup_dialogs called")
            if hasattr(self, 'current_dialog') and self.current_dialog:
                self.current_dialog.open = False
                self.current_dialog = None
            
            if self.page and hasattr(self.page, 'overlay'):
                # Clear any dialogs from this component
                self.page.overlay.clear()
                self.page.update()
                
            print(f"[DEBUG] Dialog cleanup completed")
        except Exception as ex:
            print(f"[ERROR] Dialog cleanup failed: {ex}")
    
    def safe_show_dialog(self, title, content, actions=None):
        """Safely show a dialog with proper error handling"""
        try:
            print(f"[DEBUG] safe_show_dialog called: {title}")
            
            # Ensure we have a page
            if not self.page:
                print(f"[ERROR] No page available for dialog")
                return False
            
            # Close any existing dialog
            if hasattr(self, 'current_dialog') and self.current_dialog:
                print(f"[DEBUG] Closing existing dialog before creating new one")
                self.close_dialog()
            
            # Default actions if none provided
            if actions is None:
                actions = [ft.TextButton("Close", on_click=self.close_dialog)]
            
            # Create dialog with safe defaults
            self.current_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(str(title)),
                content=content,
                actions=actions,
                actions_alignment=ft.MainAxisAlignment.END
            )
            
            # Add to overlay and open
            self.page.overlay.append(self.current_dialog)
            self.current_dialog.open = True
            self.page.update()
            
            print(f"[DEBUG] Dialog created and opened successfully")
            return True
            
        except Exception as ex:
            print(f"[ERROR] Failed to show dialog safely: {ex}")
            # Try to clean up if something went wrong
            try:
                if hasattr(self, 'current_dialog'):
                    self.current_dialog = None
                if self.page and hasattr(self.page, 'overlay') and len(self.page.overlay) > 0:
                    self.page.overlay.clear()
                    self.page.update()
            except:
                pass
            return False
    
    def build(self):
        return ft.Column([
            # Header section
            ft.Container(
                content=ft.Row([
                    ft.Text("Reports & Analytics", size=28, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                    ft.Container(expand=True),
                    ft.Row([
                        ft.ElevatedButton(
                            text="Export PDF",
                            icon=ft.icons.PICTURE_AS_PDF,
                            on_click=self.export_pdf,
                            style=ft.ButtonStyle(bgcolor=COLORS['error'], color=ft.colors.WHITE)
                        ),
                        ft.ElevatedButton(
                            text="Export Excel",
                            icon=ft.icons.TABLE_VIEW,
                            on_click=self.export_excel,
                            style=ft.ButtonStyle(bgcolor=COLORS['success'], color=ft.colors.WHITE)
                        ),
                        ft.ElevatedButton(
                            text="Refresh",
                            icon=ft.icons.REFRESH,
                            on_click=self.refresh_data,
                            style=ft.ButtonStyle(bgcolor=COLORS['primary'], color=ft.colors.WHITE)
                        )
                    ], spacing=10)
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
                ft.Text("Key Performance Indicators", size=20, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_metric_card("Total Exams", str(total_exams), ft.icons.QUIZ, COLORS['primary']),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        content=self.create_metric_card("Total Sessions", str(total_sessions), ft.icons.TIMER, COLORS['success']),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        content=self.create_metric_card("Average Score", f"{avg_score}%", ft.icons.TRENDING_UP, COLORS['warning']),
                        col={"xs": 12, "sm": 6, "md": 3},
                    ),
                    ft.Container(
                        content=self.create_metric_card("Pass Rate", f"{pass_rate}%", ft.icons.CHECK_CIRCLE, COLORS['success']),
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
                ft.Text("Performance Analytics", size=20, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_chart_container("performance_trend", "Exam Performance Trend"),
                        col={"xs": 12, "md": 6}
                    ),
                    ft.Container(
                        content=self.create_chart_container("score_distribution", "Score Distribution"),
                        col={"xs": 12, "md": 6}
                    )
                ]),
                ft.Container(height=15),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_chart_container("department_performance", "Department Performance"),
                        col={"xs": 12, "md": 6}
                    ),
                    ft.Container(
                        content=self.create_chart_container("question_difficulty", "Question Difficulty Analysis"),
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
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                ft.Container(
                    content=ft.Text("Generating chart...", size=14, color=COLORS['text_secondary']),
                    height=250,
                    bgcolor=ft.colors.with_opacity(0.05, ft.colors.BLACK),
                    border_radius=8,
                    padding=ft.padding.all(20),
                    alignment=ft.alignment.center
                )
            ]),
            bgcolor=ft.colors.WHITE,
            padding=ft.padding.all(15),
            border_radius=8,
            border=ft.border.all(1, ft.colors.with_opacity(0.1, ft.colors.BLACK))
        )
    
    def create_reports_section(self):
        """Create the detailed reports section"""
        return ft.Container(
            content=ft.Column([
                ft.Text("Detailed Reports", size=20, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Container(height=10),
                ft.ResponsiveRow([
                    ft.Container(
                        content=self.create_report_summary_card("Exam Performance", "Detailed analysis of all exams", ft.icons.ASSESSMENT),
                        col={"xs": 12, "sm": 6, "md": 4}
                    ),
                    ft.Container(
                        content=self.create_report_summary_card("User Progress", "Individual user performance tracking", ft.icons.PERSON),
                        col={"xs": 12, "sm": 6, "md": 4}
                    ),
                    ft.Container(
                        content=self.create_report_summary_card("Question Analysis", "Question difficulty and performance", ft.icons.HELP),
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
    
    def create_report_summary_card(self, title, description, icon):
        """Create summary card for report categories"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, color=COLORS['primary'], size=40),
                ft.Container(height=10),
                ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=COLORS['text_primary']),
                ft.Text(description, size=12, color=COLORS['text_secondary'], text_align=ft.TextAlign.CENTER),
                ft.Container(height=15),
                ft.ElevatedButton(
                    text="View Details",
                    on_click=lambda e, t=title: self.show_detailed_report(t),
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
            # Get basic metrics
            self.total_exams = self.db.execute_single("SELECT COUNT(*) as count FROM exams WHERE is_active = 1")['count']
            self.total_sessions = self.db.execute_single("SELECT COUNT(*) as count FROM exam_sessions WHERE is_completed = 1")['count']
            
            # Get average score
            avg_score_result = self.db.execute_single("SELECT AVG(score) as avg_score FROM exam_sessions WHERE is_completed = 1 AND score IS NOT NULL")
            self.avg_score = round(avg_score_result['avg_score'], 1) if avg_score_result['avg_score'] else 0
            
            # Get pass rate (assuming 70% is passing)
            pass_sessions = self.db.execute_single("SELECT COUNT(*) as count FROM exam_sessions WHERE is_completed = 1 AND score >= 70")['count']
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
            self.generate_performance_trend_chart()
            self.generate_score_distribution_chart()
            self.generate_department_performance_chart()
            self.generate_question_difficulty_chart()
        except Exception as e:
            print(f"Error generating charts: {e}")
    
    def generate_performance_trend_chart(self):
        """Generate performance trend over time chart"""
        try:
            # Get exam sessions data grouped by date
            sessions_data = self.db.execute_query("""
                SELECT DATE(end_time) as exam_date, AVG(score) as avg_score, COUNT(*) as session_count
                FROM exam_sessions 
                WHERE is_completed = 1 AND score IS NOT NULL AND end_time IS NOT NULL
                GROUP BY DATE(end_time)
                ORDER BY exam_date DESC
                LIMIT 30
            """)
            
            if not sessions_data:
                return
            
            # Create chart
            fig, ax = plt.subplots(figsize=(8, 5))
            dates = [datetime.strptime(row['exam_date'], '%Y-%m-%d') for row in reversed(sessions_data)]
            scores = [row['avg_score'] for row in reversed(sessions_data)]
            
            ax.plot(dates, scores, marker='o', linewidth=2, markersize=6, color='#3182ce')
            ax.set_title('Average Exam Scores Over Time', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Average Score (%)')
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Convert to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            self.chart_images['performance_trend'] = base64.b64encode(buffer.getvalue()).decode()
            
        except Exception as e:
            print(f"Error generating performance trend chart: {e}")
    
    def generate_score_distribution_chart(self):
        """Generate score distribution histogram"""
        try:
            # Get all scores
            scores_data = self.db.execute_query("""
                SELECT score FROM exam_sessions 
                WHERE is_completed = 1 AND score IS NOT NULL
            """)
            
            if not scores_data:
                return
            
            scores = [row['score'] for row in scores_data]
            
            # Create histogram
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.hist(scores, bins=20, edgecolor='black', alpha=0.7, color='#38a169')
            ax.set_title('Score Distribution', fontsize=14, fontweight='bold')
            ax.set_xlabel('Score (%)')
            ax.set_ylabel('Number of Exams')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Convert to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            self.chart_images['score_distribution'] = base64.b64encode(buffer.getvalue()).decode()
            
        except Exception as e:
            print(f"Error generating score distribution chart: {e}")
    
    def generate_department_performance_chart(self):
        """Generate department performance comparison"""
        try:
            # Get department performance data
            dept_data = self.db.execute_query("""
                SELECT u.department, AVG(es.score) as avg_score, COUNT(es.id) as exam_count
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                WHERE es.is_completed = 1 AND es.score IS NOT NULL AND u.department IS NOT NULL
                GROUP BY u.department
                HAVING exam_count >= 3
                ORDER BY avg_score DESC
            """)
            
            if not dept_data:
                return
            
            departments = [row['department'] for row in dept_data]
            avg_scores = [row['avg_score'] for row in dept_data]
            
            # Create bar chart
            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(departments, avg_scores, color='#d69e2e', alpha=0.8, edgecolor='black')
            ax.set_title('Average Performance by Department', fontsize=14, fontweight='bold')
            ax.set_xlabel('Department')
            ax.set_ylabel('Average Score (%)')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%', ha='center', va='bottom')
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Convert to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            self.chart_images['department_performance'] = base64.b64encode(buffer.getvalue()).decode()
            
        except Exception as e:
            print(f"Error generating department performance chart: {e}")
    
    def generate_question_difficulty_chart(self):
        """Generate question difficulty analysis"""
        try:
            # Get question performance data
            question_data = self.db.execute_query("""
                SELECT q.difficulty_level, 
                       AVG(CASE WHEN ua.is_correct = 1 THEN 100.0 ELSE 0.0 END) as success_rate,
                       COUNT(ua.id) as answer_count
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                WHERE ua.is_correct IS NOT NULL
                GROUP BY q.difficulty_level
                HAVING answer_count >= 10
            """)
            
            if not question_data:
                return
            
            difficulties = [row['difficulty_level'].title() for row in question_data]
            success_rates = [row['success_rate'] for row in question_data]
            
            # Create pie chart
            fig, ax = plt.subplots(figsize=(8, 5))
            colors = ['#e53e3e', '#d69e2e', '#38a169']  # Red, Yellow, Green
            ax.pie(success_rates, labels=[f'{d}\n({r:.1f}%)' for d, r in zip(difficulties, success_rates)], 
                   colors=colors[:len(difficulties)], autopct='', startangle=90)
            ax.set_title('Success Rate by Question Difficulty', fontsize=14, fontweight='bold')
            plt.tight_layout()
            
            # Convert to base64 image
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            self.chart_images['question_difficulty'] = base64.b64encode(buffer.getvalue()).decode()
            
        except Exception as e:
            print(f"Error generating question difficulty chart: {e}")
    
    def export_pdf(self, e):
        """Export reports as PDF"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            
            # Create PDF with basic report
            filename = f"exam_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = f"/tmp/{filename}"  # You might want to use a proper temp directory or downloads folder
            
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
    
    def export_excel(self, e):
        """Export data as Excel"""
        try:
            # Get detailed data for Excel export
            sessions_data = self.db.execute_query("""
                SELECT 
                    u.username,
                    u.full_name,
                    u.department,
                    e.title as exam_title,
                    es.score,
                    es.duration_seconds,
                    es.start_time,
                    es.end_time
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                JOIN exams e ON es.exam_id = e.id
                WHERE es.is_completed = 1
                ORDER BY es.end_time DESC
            """)
            
            if sessions_data:
                df = pd.DataFrame(sessions_data)
                
                # Format data
                if 'duration_seconds' in df.columns:
                    df['duration_minutes'] = df['duration_seconds'] / 60
                
                filename = f"exam_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                filepath = f"/tmp/{filename}"  # You might want to use a proper temp directory or downloads folder
                
                df.to_excel(filepath, index=False)
                
                self.show_message("Excel Export", f"Data exported successfully!\nFile saved as: {filename}")
            else:
                self.show_message("Excel Export", "No data available to export.")
                
        except Exception as ex:
            self.show_message("Export Error", f"Failed to export Excel: {str(ex)}")
    
    def refresh_data(self, e):
        """Refresh all analytics data"""
        self.load_analytics_data()
        self.generate_charts()
        if self.page:
            self.update()
        self.show_message("Refresh", "Analytics data refreshed successfully!")
    
    def show_detailed_report(self, report_type):
        """Show detailed report in a dialog"""
        try:
            print(f"[DEBUG] show_detailed_report called for: {report_type}")
            
            if report_type == "Exam Performance":
                content = self.create_exam_performance_details()
            elif report_type == "User Progress":
                content = self.create_user_progress_details()
            elif report_type == "Question Analysis":
                content = self.create_question_analysis_details()
            else:
                content = ft.Text("Report details coming soon...")
            
            # Use safe dialog creation
            dialog_content = ft.Container(
                content=content,
                width=800,
                height=500
            )
            
            success = self.safe_show_dialog(
                title=f"{report_type} - Detailed Report",
                content=dialog_content
            )
            
            if not success:
                print(f"[ERROR] Failed to show detailed report dialog")
                
        except Exception as ex:
            print(f"[ERROR] Failed to show detailed report: {ex}")
            self.safe_show_dialog("Error", ft.Text(f"Failed to load detailed report: {str(ex)}"))
    
    def create_exam_performance_details(self):
        """Create detailed exam performance report"""
        try:
            exam_details = self.db.execute_query("""
                SELECT 
                    e.title,
                    COUNT(es.id) as sessions_count,
                    AVG(es.score) as avg_score,
                    MIN(es.score) as min_score,
                    MAX(es.score) as max_score,
                    AVG(es.duration_seconds)/60 as avg_duration_minutes
                FROM exams e
                LEFT JOIN exam_sessions es ON e.id = es.exam_id AND es.is_completed = 1
                WHERE e.is_active = 1
                GROUP BY e.id, e.title
                ORDER BY sessions_count DESC
            """)
            
            if not exam_details:
                return ft.Text("No exam data available.")
            
            # Create table
            table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Exam Title")),
                    ft.DataColumn(ft.Text("Sessions")),
                    ft.DataColumn(ft.Text("Avg Score")),
                    ft.DataColumn(ft.Text("Min Score")),
                    ft.DataColumn(ft.Text("Max Score")),
                    ft.DataColumn(ft.Text("Avg Duration (min)"))
                ],
                rows=[],
                width=float("inf"),
                column_spacing=20
            )
            
            for exam in exam_details:
                table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Text(exam['title'][:30] + "..." if len(exam['title']) > 30 else exam['title'])),
                        ft.DataCell(ft.Text(str(exam['sessions_count'] or 0))),
                        ft.DataCell(ft.Text(f"{exam['avg_score']:.1f}%" if exam['avg_score'] else "N/A")),
                        ft.DataCell(ft.Text(f"{exam['min_score']:.1f}%" if exam['min_score'] else "N/A")),
                        ft.DataCell(ft.Text(f"{exam['max_score']:.1f}%" if exam['max_score'] else "N/A")),
                        ft.DataCell(ft.Text(f"{exam['avg_duration_minutes']:.1f}" if exam['avg_duration_minutes'] else "N/A"))
                    ])
                )
            
            return ft.Container(
                content=ft.ListView(
                    controls=[table],
                    expand=True,
                    auto_scroll=False
                ),
                expand=True
            )
            
        except Exception as e:
            return ft.Text(f"Error loading exam details: {str(e)}")
    
    def create_user_progress_details(self):
        """Create detailed user progress report with professional UI and working filters"""
        try:
            print("[DEBUG] Starting create_user_progress_details")
            
            # DEBUG: First check if there are any users at all
            all_users = self.db.execute_query("SELECT COUNT(*) as count FROM users")
            examinees = self.db.execute_query("SELECT COUNT(*) as count FROM users WHERE role = 'examinee'")
            active_examinees = self.db.execute_query("SELECT COUNT(*) as count FROM users WHERE role = 'examinee' AND is_active = 1")
            
            print(f"[DEBUG] Total users: {all_users[0]['count'] if all_users else 0}")
            print(f"[DEBUG] Examinees: {examinees[0]['count'] if examinees else 0}")
            print(f"[DEBUG] Active examinees: {active_examinees[0]['count'] if active_examinees else 0}")
            
            # Simple query first - just get basic user data
            user_progress_data = self.db.execute_query("""
                SELECT 
                    u.id,
                    u.username,
                    u.full_name,
                    u.department,
                    u.role,
                    0 as exams_taken,
                    0 as total_attempts,
                    0 as avg_score,
                    0 as best_score,
                    0 as passed_exams,
                    0 as avg_duration_minutes,
                    NULL as last_exam_date,
                    0 as recent_activity
                FROM users u
                WHERE u.is_active = 1
                ORDER BY u.full_name
                LIMIT 50
            """)
            
            print(f"[DEBUG] Retrieved {len(user_progress_data) if user_progress_data else 0} users from database")
            
            if not user_progress_data:
                return ft.Container(
                    content=ft.Column([
                        ft.Text("No user data available in the database.", size=16, color=COLORS['text_secondary']),
                        ft.Text(f"Total users in DB: {all_users[0]['count'] if all_users else 0}", size=14),
                        ft.Text(f"Active examinees: {active_examinees[0]['count'] if active_examinees else 0}", size=14)
                    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.all(40),
                    alignment=ft.alignment.center
                )
            
            print(f"[DEBUG] Sample user data: {user_progress_data[0] if user_progress_data else 'None'}")
            
            # Create simple table
            simple_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Name", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Username", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Department", weight=ft.FontWeight.BOLD)),
                    ft.DataColumn(ft.Text("Role", weight=ft.FontWeight.BOLD))
                ],
                rows=[],
                width=float("inf"),
                border=ft.border.all(1, ft.colors.BLACK12),
                border_radius=8
            )
            
            # Populate table
            for user in user_progress_data:
                simple_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Text(user.get('full_name', ''), size=14)),
                        ft.DataCell(ft.Text(user.get('username', ''), size=14)),
                        ft.DataCell(ft.Text(user.get('department', 'N/A'), size=14)),
                        ft.DataCell(ft.Text(user.get('role', ''), size=14))
                    ])
                )
            
            print(f"[DEBUG] Created table with {len(simple_table.rows)} rows")
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("User Progress - Detailed Report (Debug Mode)", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Found {len(user_progress_data)} users", size=14, color=COLORS['text_secondary']),
                    ft.Container(height=20),
                    ft.Container(
                        content=simple_table,
                        bgcolor=ft.colors.WHITE,
                        border_radius=8,
                        padding=ft.padding.all(20),
                        border=ft.border.all(1, ft.colors.BLACK12)
                    )
                ], spacing=10),
                padding=ft.padding.all(20),
                expand=True
            )
            
        except Exception as e:
            print(f"[ERROR] Exception in create_user_progress_details: {e}")
            import traceback
            traceback.print_exc()
            
            return ft.Container(
                content=ft.Column([
                    ft.Text("Error Loading User Progress", size=18, weight=ft.FontWeight.BOLD, color=COLORS['error']),
                    ft.Text(f"Error: {str(e)}", size=14),
                    ft.Text("Please check console for details", size=12, color=COLORS['text_secondary'])
                ], spacing=10),
                padding=ft.padding.all(20)
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
    
    def on_search_change(self, e):
        """Handle search field changes"""
        try:
            self.apply_all_filters()
        except Exception as ex:
            print(f"Error in search change: {ex}")
    
    def on_filter_change(self, e):
        """Handle filter dropdown changes"""
        try:
            self.apply_all_filters()
        except Exception as ex:
            print(f"Error in filter change: {ex}")
                    u.department,
                    u.role,
                    COALESCE(COUNT(DISTINCT es.exam_id), 0) as exams_taken,
                    COALESCE(COUNT(es.id), 0) as total_attempts,
                    COALESCE(AVG(es.score), 0) as avg_score,
                    COALESCE(MAX(es.score), 0) as best_score,
                    COALESCE(MIN(es.score), 0) as lowest_score,
                    COALESCE(SUM(CASE WHEN es.score >= 70 THEN 1 ELSE 0 END), 0) as passed_exams,
                    COALESCE(AVG(es.duration_seconds)/60, 0) as avg_duration_minutes,
                    MAX(es.end_time) as last_exam_date,
                    COALESCE(COUNT(CASE WHEN DATE(es.end_time) >= DATE('now', '-7 days') THEN 1 END), 0) as recent_activity
                FROM users u
                LEFT JOIN exam_sessions es ON u.id = es.user_id AND es.is_completed = 1
                WHERE u.role = 'examinee' AND u.is_active = 1
                GROUP BY u.id, u.username, u.full_name, u.department, u.role
                ORDER BY u.full_name
            """)
            
            print(f"[DEBUG] Retrieved {len(user_progress_data) if user_progress_data else 0} users from database")
            
            # If no examinees found, try getting ALL users as fallback
            if not user_progress_data:
                print("[DEBUG] No examinees found, trying ALL users...")
                user_progress_data = self.db.execute_query("""
                    SELECT 
                        u.id,
                        u.username,
                        u.full_name,
                        u.department,
                        u.role,
                        0 as exams_taken,
                        0 as total_attempts,
                        0 as avg_score,
                        0 as best_score,
                        0 as lowest_score,
                        0 as passed_exams,
                        0 as avg_duration_minutes,
                        NULL as last_exam_date,
                        0 as recent_activity
                    FROM users u
                    WHERE u.is_active = 1
                    ORDER BY u.full_name
                """)
                print(f"[DEBUG] Fallback query retrieved {len(user_progress_data) if user_progress_data else 0} users")
            
            if not user_progress_data:
                return ft.Container(
                    content=ft.Column([
                        ft.Text("No user data available in the database.", size=16, color=COLORS['text_secondary']),
                        ft.Text(f"Total users in DB: {all_users[0]['count'] if all_users else 0}", size=14, color=COLORS['text_secondary']),
                        ft.Text(f"Active examinees: {active_examinees[0]['count'] if active_examinees else 0}", size=14, color=COLORS['text_secondary'])
                    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.all(40),
                    alignment=ft.alignment.center
                )
            
            # Store data for filtering
            self.original_user_data = user_progress_data.copy()
            self.filtered_user_data = user_progress_data.copy()
            
            # Debug: Print first user to see data structure
            if user_progress_data:
                print(f"[DEBUG] Sample user data: {user_progress_data[0]}")
                print(f"[DEBUG] User data keys: {list(user_progress_data[0].keys())}")
            
            # Calculate summary statistics
            total_users = len(user_progress_data)
            active_users = sum(1 for u in user_progress_data if (u.get('total_attempts', 0) or 0) > 0)
            avg_user_score = sum((u.get('avg_score', 0) or 0) for u in user_progress_data if (u.get('total_attempts', 0) or 0) > 0) / active_users if active_users > 0 else 0
            
            # Summary cards with consistent styling
            summary_cards = ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text(str(total_users), size=28, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                        ft.Text("Total Users", size=14, color=COLORS['text_secondary'])
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    width=120,
                    height=80,
                    bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                    border_radius=12,
                    padding=ft.padding.all(15),
                    border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['primary']))
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text(str(active_users), size=28, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                        ft.Text("Active Users", size=14, color=COLORS['text_secondary'])
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    width=120,
                    height=80,
                    bgcolor=ft.colors.with_opacity(0.1, COLORS['success']),
                    border_radius=12,
                    padding=ft.padding.all(15),
                    border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['success']))
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{avg_user_score:.1f}%", size=28, weight=ft.FontWeight.BOLD, color=COLORS['warning']),
                        ft.Text("Avg User Score", size=14, color=COLORS['text_secondary'])
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
                    width=140,
                    height=80,
                    bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                    border_radius=12,
                    padding=ft.padding.all(15),
                    border=ft.border.all(1, ft.colors.with_opacity(0.2, COLORS['warning']))
                )
            ], spacing=20, alignment=ft.MainAxisAlignment.START)
            
            # Initialize filter controls with proper styling and working functionality
            self.search_field = ft.TextField(
                hint_text="Search by name, username, or department...",
                prefix_icon=ft.icons.SEARCH,
                width=400,
                height=50,
                on_change=self.on_search_change,
                border_radius=10,
                bgcolor=ft.colors.WHITE,
                border_color=ft.colors.with_opacity(0.3, COLORS['primary']),
                focused_border_color=COLORS['primary']
            )
            
            self.dept_filter = ft.Dropdown(
                hint_text="All Departments",
                options=self.get_department_options(user_progress_data),
                value="all",
                width=200,
                height=50,
                on_change=self.on_filter_change,
                bgcolor=ft.colors.WHITE,
                border_radius=10,
                border_color=ft.colors.with_opacity(0.3, COLORS['primary'])
            )
            
            self.score_filter = ft.Dropdown(
                hint_text="All Scores",
                options=[
                    ft.dropdown.Option("all", "All Scores"),
                    ft.dropdown.Option("90-100", "90-100%"),
                    ft.dropdown.Option("80-89", "80-89%"),
                    ft.dropdown.Option("70-79", "70-79%"),
                    ft.dropdown.Option("60-69", "60-69%"),
                    ft.dropdown.Option("0-59", "Below 60%")
                ],
                value="all",
                width=150,
                height=50,
                on_change=self.on_filter_change,
                bgcolor=ft.colors.WHITE,
                border_radius=10,
                border_color=ft.colors.with_opacity(0.3, COLORS['primary'])
            )
            
            self.exam_count_filter = ft.Dropdown(
                hint_text="All Counts",
                options=[
                    ft.dropdown.Option("all", "All Counts"),
                    ft.dropdown.Option("10+", "10+ Exams"),
                    ft.dropdown.Option("5-9", "5-9 Exams"),
                    ft.dropdown.Option("1-4", "1-4 Exams"),
                    ft.dropdown.Option("0", "No Exams")
                ],
                value="all",
                width=150,
                height=50,
                on_change=self.on_filter_change,
                bgcolor=ft.colors.WHITE,
                border_radius=10,
                border_color=ft.colors.with_opacity(0.3, COLORS['primary'])
            )
            
            self.activity_filter = ft.Dropdown(
                hint_text="All Activity",
                options=[
                    ft.dropdown.Option("all", "All Activity"),
                    ft.dropdown.Option("recent", "Active (7 days)"),
                    ft.dropdown.Option("moderate", "Moderate (30 days)"),
                    ft.dropdown.Option("inactive", "Inactive (30+ days)")
                ],
                value="all",
                width=180,
                height=50,
                on_change=self.on_filter_change,
                bgcolor=ft.colors.WHITE,
                border_radius=10,
                border_color=ft.colors.with_opacity(0.3, COLORS['primary'])
            )
            
            # Filter controls with professional layout
            filters_container = ft.Container(
                content=ft.Column([
                    # Search bar
                    ft.Container(
                        content=self.search_field,
                        padding=ft.padding.only(bottom=15)
                    ),
                    # Filter dropdowns in organized rows
                    ft.Row([
                        self.dept_filter,
                        self.score_filter,
                        self.exam_count_filter,
                        self.activity_filter
                    ], spacing=15, wrap=True),
                    # Action buttons
                    ft.Container(
                        content=ft.Row([
                            ft.ElevatedButton(
                                text="Reset Filters",
                                icon=ft.icons.REFRESH,
                                on_click=self.reset_user_filters,
                                style=ft.ButtonStyle(
                                    bgcolor=COLORS['secondary'],
                                    color=ft.colors.WHITE,
                                    padding=ft.padding.symmetric(horizontal=20, vertical=12)
                                ),
                                height=45
                            ),
                            ft.ElevatedButton(
                                text="Export Filtered Data",
                                icon=ft.icons.DOWNLOAD,
                                on_click=lambda e: self.export_user_progress(self.filtered_user_data),
                                style=ft.ButtonStyle(
                                    bgcolor=COLORS['success'],
                                    color=ft.colors.WHITE,
                                    padding=ft.padding.symmetric(horizontal=20, vertical=12)
                                ),
                                height=45
                            )
                        ], spacing=15),
                        padding=ft.padding.only(top=15)
                    )
                ], spacing=10),
                padding=ft.padding.all(20),
                bgcolor=ft.colors.with_opacity(0.05, COLORS['surface']),
                border_radius=12,
                border=ft.border.all(1, ft.colors.with_opacity(0.1, COLORS['text_secondary']))
            )
            
            # Create progress table with better styling
            self.progress_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("User", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Department", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Exams", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Total Attempts", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Avg Score", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Best Score", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Pass Rate", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Avg Duration", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Last Activity", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Recent Activity", weight=ft.FontWeight.BOLD, size=14)),
                    ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD, size=14))
                ],
                rows=[],
                width=float("inf"),
                column_spacing=20,
                heading_row_color=ft.colors.with_opacity(0.08, COLORS['primary']),
                border=ft.border.all(1, ft.colors.with_opacity(0.15, COLORS['text_secondary'])),
                border_radius=8
            )
            
            # Populate table with initial data
            self.update_progress_table()
            
            # If update_progress_table didn't work, populate manually
            if not self.progress_table.rows:
                print("[DEBUG] Table is empty, trying to populate manually...")
                self.populate_initial_table_data()
                
            # Final check - if still no rows, create a simple fallback
            if not self.progress_table.rows:
                print("[DEBUG] Still no rows, creating fallback data row...")
                self.progress_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Text(f"Found {len(self.filtered_user_data)} users but table display failed")),
                        *[ft.DataCell(ft.Text("---")) for _ in range(10)]
                    ])
                )
            
            # Table container with proper styling
            table_container = ft.Container(
                content=ft.ListView(
                    controls=[self.progress_table],
                    expand=True,
                    auto_scroll=False
                ),
                bgcolor=ft.colors.WHITE,
                border_radius=12,
                padding=ft.padding.all(20),
                border=ft.border.all(1, ft.colors.with_opacity(0.1, COLORS['text_secondary'])),
                expand=True
            )
            
            # Main layout
            return ft.Container(
                content=ft.Column([
                    # Summary cards
                    ft.Container(
                        content=summary_cards,
                        padding=ft.padding.only(bottom=25)
                    ),
                    # Filters
                    ft.Container(
                        content=filters_container,
                        padding=ft.padding.only(bottom=25)
                    ),
                    # Table
                    table_container
                ], spacing=0),
                padding=ft.padding.all(20),
                expand=True
            )
            
        except Exception as e:
            print(f"Error creating user progress details: {e}")
            import traceback
            traceback.print_exc()
            
            # Emergency fallback - create a simple table
            try:
                simple_users = self.db.execute_query("SELECT id, username, full_name, department FROM users LIMIT 10")
                if simple_users:
                    print(f"[DEBUG] Creating emergency fallback table with {len(simple_users)} users")
                    simple_table = ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("ID")),
                            ft.DataColumn(ft.Text("Username")),
                            ft.DataColumn(ft.Text("Name")),
                            ft.DataColumn(ft.Text("Department"))
                        ],
                        rows=[
                            ft.DataRow([
                                ft.DataCell(ft.Text(str(user['id']))),
                                ft.DataCell(ft.Text(user['username'])),
                                ft.DataCell(ft.Text(user['full_name'])),
                                ft.DataCell(ft.Text(user['department'] or 'N/A'))
                            ]) for user in simple_users
                        ]
                    )
                    return ft.Container(
                        content=ft.Column([
                            ft.Text("Emergency Fallback - Basic User List", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Error: {str(e)}", color=COLORS['error']),
                            simple_table
                        ]),
                        padding=ft.padding.all(20)
                    )
            except Exception as fallback_error:
                print(f"[ERROR] Even fallback failed: {fallback_error}")
            
            return ft.Container(
                content=ft.Text(f"Error loading user progress: {str(e)}", color=COLORS['error']),
                padding=ft.padding.all(20)
            )
                        ], spacing=2)),
                        ft.DataCell(ft.Text(user['department'] or "N/A")),
                        ft.DataCell(ft.Text(str(exams_taken))),
                        ft.DataCell(ft.Text(str(total_attempts))),
                        ft.DataCell(ft.Text(f"{avg_score:.1f}%" if avg_score > 0 else "N/A", color=score_color)),
                        ft.DataCell(ft.Text(f"{best_score:.1f}%" if best_score > 0 else "N/A")),
                        ft.DataCell(ft.Text(f"{pass_rate:.1f}%" if total_attempts > 0 else "N/A")),
                        ft.DataCell(ft.Text(f"{avg_duration:.1f}m" if avg_duration > 0 else "N/A")),
                        ft.DataCell(ft.Text(last_exam_formatted)),
                        ft.DataCell(ft.Text(str(recent_activity), color=activity_color)),
                        ft.DataCell(ft.Row([
                            ft.IconButton(
                                icon=ft.icons.VISIBILITY,
                                tooltip="View Details",
                                on_click=lambda e, user_id=user['id']: self.show_individual_user_details(user_id),
                                icon_color=COLORS['primary']
                            ),
                            ft.IconButton(
                                icon=ft.icons.TIMELINE,
                                tooltip="Progress Chart",
                                on_click=lambda e, user_id=user['id']: self.show_user_progress_chart(user_id),
                                icon_color=COLORS['success']
                            )
                        ], spacing=5))
                    ])
                )
            
            # Summary statistics
            total_users = len(user_progress_data)
            active_users = sum(1 for u in user_progress_data if (u['total_attempts'] or 0) > 0)
            avg_user_score = sum((u['avg_score'] or 0) for u in user_progress_data) / total_users if total_users > 0 else 0
            
            summary_container = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(total_users), size=20, weight=ft.FontWeight.BOLD, color=COLORS['primary']),
                            ft.Text("Total Users", size=12)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                        padding=ft.padding.all(15),
                        border_radius=8
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(active_users), size=20, weight=ft.FontWeight.BOLD, color=COLORS['success']),
                            ft.Text("Active Users", size=12)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['success']),
                        padding=ft.padding.all(15),
                        border_radius=8
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"{avg_user_score:.1f}%", size=20, weight=ft.FontWeight.BOLD, color=COLORS['warning']),
                            ft.Text("Avg User Score", size=12)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=ft.colors.with_opacity(0.1, COLORS['warning']),
                        padding=ft.padding.all(15),
                        border_radius=8
                    )
                ], spacing=15, alignment=ft.MainAxisAlignment.SPACE_AROUND),
                padding=ft.padding.only(bottom=20)
            )
            
            # Return complete user progress interface
            return ft.Column([
                summary_container,
                search_container,
                ft.Container(
                    content=ft.ListView(
                        controls=[progress_table],
                        expand=True,
                        auto_scroll=False
                    ),
                    expand=True
                )
            ], spacing=10, expand=True)
            
        except Exception as e:
            print(f"Error creating user progress details: {e}")
            return ft.Container(
                content=ft.Text(f"Error loading user progress data: {str(e)}"),
                padding=ft.padding.all(20)
            )
    
    def create_question_analysis_details(self):
        """Create detailed question analysis report"""
        return ft.Text("Question analysis details coming soon...")
    
    def close_dialog(self, e=None):
        """Close the current dialog"""
        try:
            print(f"[DEBUG] close_dialog called, current_dialog exists: {hasattr(self, 'current_dialog')}")
            
            if hasattr(self, 'current_dialog') and self.current_dialog and self.page:
                print(f"[DEBUG] Closing dialog, open status: {self.current_dialog.open}")
                
                # Set open to False first
                self.current_dialog.open = False
                
                # Update the page to process the close
                self.page.update()
                
                # Clean up reference
                self.current_dialog = None
                
                print(f"[DEBUG] Dialog closed successfully")
                
        except Exception as ex:
            print(f"[ERROR] Error closing dialog: {ex}")
            
            # Emergency cleanup - try to recover gracefully
            try:
                print(f"[DEBUG] Attempting emergency cleanup")
                
                if self.page and hasattr(self.page, 'overlay'):
                    overlay_count = len(self.page.overlay)
                    print(f"[DEBUG] Emergency cleanup, overlay count: {overlay_count}")
                    
                    # Close all dialogs in overlay
                    for i, dialog in enumerate(list(self.page.overlay)):
                        try:
                            if hasattr(dialog, 'open'):
                                print(f"[DEBUG] Closing overlay dialog {i}")
                                dialog.open = False
                        except Exception as dialog_ex:
                            print(f"[DEBUG] Failed to close dialog {i}: {dialog_ex}")
                    
                    # Update page
                    self.page.update()
                    
                    # Clear overlay
                    self.page.overlay.clear()
                    
                    # Update again
                    self.page.update()
                    
                # Clean up reference
                self.current_dialog = None
                
                print(f"[DEBUG] Emergency cleanup completed")
                
            except Exception as cleanup_ex:
                print(f"[ERROR] Emergency cleanup failed: {cleanup_ex}")
                # Last resort - just clear the reference
                self.current_dialog = None
    
    def show_message(self, title, message):
        """Show a message dialog"""
        try:
            print(f"[DEBUG] show_message called: {title}")
            
            # Use safe dialog creation with OK button
            actions = [ft.TextButton("OK", on_click=self.close_dialog)]
            success = self.safe_show_dialog(
                title=title,
                content=ft.Text(str(message)),
                actions=actions
            )
            
            if not success:
                print(f"[ERROR] Failed to show message dialog: {title}")
                
        except Exception as ex:
            print(f"[ERROR] Failed to show message dialog: {ex}")
    
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
    
    def on_search_change(self, e):
        """Handle search field changes"""
        try:
            self.apply_all_filters()
        except Exception as ex:
            print(f"Error in search change: {ex}")
    
    def on_filter_change(self, e):
        """Handle filter dropdown changes"""
        try:
            self.apply_all_filters()
        except Exception as ex:
            print(f"Error in filter change: {ex}")
    
    def apply_all_filters(self):
        """Apply all active filters to user data and update table"""
        try:
            if not hasattr(self, 'original_user_data'):
                return
            
            # Start with original data
            filtered_data = self.original_user_data.copy()
            
            # Apply search filter
            search_term = self.search_field.value.lower() if self.search_field.value else ""
            if search_term:
                filtered_data = [
                    user for user in filtered_data
                    if (search_term in (user.get('full_name', '') or '').lower() or
                        search_term in (user.get('username', '') or '').lower() or
                        search_term in (user.get('department', '') or '').lower())
                ]
            
            # Apply department filter
            if hasattr(self, 'dept_filter') and self.dept_filter.value and self.dept_filter.value != "all":
                filtered_data = [
                    user for user in filtered_data
                    if (user.get('department', '') or '') == self.dept_filter.value
                ]
            
            # Apply score range filter
            if hasattr(self, 'score_filter') and self.score_filter.value and self.score_filter.value != "all":
                score_range = self.score_filter.value
                if score_range == "90-100":
                    filtered_data = [u for u in filtered_data if (u.get('avg_score', 0) or 0) >= 90]
                elif score_range == "80-89":
                    filtered_data = [u for u in filtered_data if 80 <= (u.get('avg_score', 0) or 0) < 90]
                elif score_range == "70-79":
                    filtered_data = [u for u in filtered_data if 70 <= (u.get('avg_score', 0) or 0) < 80]
                elif score_range == "60-69":
                    filtered_data = [u for u in filtered_data if 60 <= (u.get('avg_score', 0) or 0) < 70]
                elif score_range == "0-59":
                    filtered_data = [u for u in filtered_data if (u.get('avg_score', 0) or 0) < 60]
            
            # Apply exam count filter
            if hasattr(self, 'exam_count_filter') and self.exam_count_filter.value and self.exam_count_filter.value != "all":
                count_range = self.exam_count_filter.value
                if count_range == "10+":
                    filtered_data = [u for u in filtered_data if (u.get('exams_taken', 0) or 0) >= 10]
                elif count_range == "5-9":
                    filtered_data = [u for u in filtered_data if 5 <= (u.get('exams_taken', 0) or 0) <= 9]
                elif count_range == "1-4":
                    filtered_data = [u for u in filtered_data if 1 <= (u.get('exams_taken', 0) or 0) <= 4]
                elif count_range == "0":
                    filtered_data = [u for u in filtered_data if (u.get('exams_taken', 0) or 0) == 0]
            
            # Apply activity filter
            if hasattr(self, 'activity_filter') and self.activity_filter.value and self.activity_filter.value != "all":
                activity_level = self.activity_filter.value
                if activity_level == "recent":
                    filtered_data = [u for u in filtered_data if (u.get('recent_activity', 0) or 0) > 0]
                elif activity_level == "moderate":
                    # Users with activity in last 30 days but not last 7
                    filtered_data = [u for u in filtered_data if (u.get('recent_activity', 0) or 0) == 0 and u.get('last_exam_date')]
                elif activity_level == "inactive":
                    # Users with no recent activity
                    filtered_data = [u for u in filtered_data if not u.get('last_exam_date') or (u.get('recent_activity', 0) or 0) == 0]
            
            # Update filtered data and refresh table
            self.filtered_user_data = filtered_data
            self.update_progress_table()
            
            # Update the UI if we have page reference
            if hasattr(self, 'page') and self.page:
                self.page.update()
            
        except Exception as ex:
            print(f"Error applying filters: {ex}")
            import traceback
            traceback.print_exc()
    
    def populate_initial_table_data(self):
        """Populate table with initial data - fallback method"""
        try:
            if not hasattr(self, 'progress_table') or not hasattr(self, 'filtered_user_data'):
                return
            
            print(f"[DEBUG] Populating initial table data with {len(self.filtered_user_data)} users")
            
            # Clear existing rows
            self.progress_table.rows.clear()
            
            # Add all user data to table
            for user in self.filtered_user_data:
                exams_taken = user.get('exams_taken', 0) or 0
                total_attempts = user.get('total_attempts', 0) or 0
                passed_exams = user.get('passed_exams', 0) or 0
                avg_score = user.get('avg_score', 0) or 0
                best_score = user.get('best_score', 0) or 0
                avg_duration = user.get('avg_duration_minutes', 0) or 0
                recent_activity = user.get('recent_activity', 0) or 0
                
                # Calculate pass rate
                pass_rate = (passed_exams / total_attempts * 100) if total_attempts > 0 else 0
                
                # Format last exam date
                last_exam = user.get('last_exam_date', '')
                if last_exam:
                    try:
                        last_exam_formatted = last_exam[:10] if len(last_exam) >= 10 else last_exam
                    except:
                        last_exam_formatted = "Never"
                else:
                    last_exam_formatted = "Never"
                
                # Color code based on performance
                score_color = COLORS['success'] if avg_score >= 80 else (COLORS['warning'] if avg_score >= 60 else COLORS['error'])
                activity_color = COLORS['success'] if recent_activity > 0 else COLORS['text_secondary']
                
                self.progress_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Column([
                            ft.Text(user.get('full_name', ''), weight=ft.FontWeight.BOLD, size=13),
                            ft.Text(f"@{user.get('username', '')}", size=11, color=COLORS['text_secondary'])
                        ], spacing=2)),
                        ft.DataCell(ft.Text(user.get('department', 'N/A'), size=13)),
                        ft.DataCell(ft.Text(str(exams_taken), size=13)),
                        ft.DataCell(ft.Text(str(total_attempts), size=13)),
                        ft.DataCell(ft.Text(f"{avg_score:.1f}%" if avg_score > 0 else "N/A", color=score_color, size=13, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{best_score:.1f}%" if best_score > 0 else "N/A", size=13)),
                        ft.DataCell(ft.Text(f"{pass_rate:.1f}%" if total_attempts > 0 else "N/A", size=13)),
                        ft.DataCell(ft.Text(f"{avg_duration:.1f}m" if avg_duration > 0 else "N/A", size=13)),
                        ft.DataCell(ft.Text(last_exam_formatted, size=13)),
                        ft.DataCell(ft.Text(str(recent_activity), color=activity_color, size=13, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Row([
                            ft.IconButton(
                                icon=ft.icons.VISIBILITY,
                                tooltip="View Details",
                                on_click=lambda e, user_id=user['id']: self.show_individual_user_details(user_id),
                                icon_color=COLORS['primary'],
                                icon_size=18
                            ),
                            ft.IconButton(
                                icon=ft.icons.TIMELINE,
                                tooltip="Progress Chart",
                                on_click=lambda e, user_id=user['id']: self.show_user_progress_chart(user_id),
                                icon_color=COLORS['success'],
                                icon_size=18
                            )
                        ], spacing=5))
                    ])
                )
            
            print(f"[DEBUG] Successfully added {len(self.progress_table.rows)} rows to table")
            
        except Exception as ex:
            print(f"Error populating initial table data: {ex}")
            import traceback
            traceback.print_exc()
    
    def update_progress_table(self):
        """Update the progress table with current filtered data"""
        try:
            if not hasattr(self, 'progress_table'):
                print("[DEBUG] No progress_table attribute found")
                return
            
            if not hasattr(self, 'filtered_user_data'):
                print("[DEBUG] No filtered_user_data attribute found")
                return
            
            print(f"[DEBUG] Updating progress table with {len(self.filtered_user_data)} filtered users")
            
            # Clear existing rows
            self.progress_table.rows.clear()
            
            # Add filtered data to table
            for user in self.filtered_user_data:
                exams_taken = user.get('exams_taken', 0) or 0
                total_attempts = user.get('total_attempts', 0) or 0
                passed_exams = user.get('passed_exams', 0) or 0
                avg_score = user.get('avg_score', 0) or 0
                best_score = user.get('best_score', 0) or 0
                avg_duration = user.get('avg_duration_minutes', 0) or 0
                recent_activity = user.get('recent_activity', 0) or 0
                
                # Calculate pass rate
                pass_rate = (passed_exams / total_attempts * 100) if total_attempts > 0 else 0
                
                # Format last exam date
                last_exam = user.get('last_exam_date', '')
                if last_exam:
                    try:
                        last_exam_formatted = last_exam[:10] if len(last_exam) >= 10 else last_exam
                    except:
                        last_exam_formatted = "Never"
                else:
                    last_exam_formatted = "Never"
                
                # Color code based on performance
                score_color = COLORS['success'] if avg_score >= 80 else (COLORS['warning'] if avg_score >= 60 else COLORS['error'])
                activity_color = COLORS['success'] if recent_activity > 0 else COLORS['text_secondary']
                
                self.progress_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Column([
                            ft.Text(user.get('full_name', ''), weight=ft.FontWeight.BOLD, size=13),
                            ft.Text(f"@{user.get('username', '')}", size=11, color=COLORS['text_secondary'])
                        ], spacing=2)),
                        ft.DataCell(ft.Text(user.get('department', 'N/A'), size=13)),
                        ft.DataCell(ft.Text(str(exams_taken), size=13)),
                        ft.DataCell(ft.Text(str(total_attempts), size=13)),
                        ft.DataCell(ft.Text(f"{avg_score:.1f}%" if avg_score > 0 else "N/A", color=score_color, size=13, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Text(f"{best_score:.1f}%" if best_score > 0 else "N/A", size=13)),
                        ft.DataCell(ft.Text(f"{pass_rate:.1f}%" if total_attempts > 0 else "N/A", size=13)),
                        ft.DataCell(ft.Text(f"{avg_duration:.1f}m" if avg_duration > 0 else "N/A", size=13)),
                        ft.DataCell(ft.Text(last_exam_formatted, size=13)),
                        ft.DataCell(ft.Text(str(recent_activity), color=activity_color, size=13, weight=ft.FontWeight.BOLD)),
                        ft.DataCell(ft.Row([
                            ft.IconButton(
                                icon=ft.icons.VISIBILITY,
                                tooltip="View Details",
                                on_click=lambda e, user_id=user['id']: self.show_individual_user_details(user_id),
                                icon_color=COLORS['primary'],
                                icon_size=18
                            ),
                            ft.IconButton(
                                icon=ft.icons.TIMELINE,
                                tooltip="Progress Chart",
                                on_click=lambda e, user_id=user['id']: self.show_user_progress_chart(user_id),
                                icon_color=COLORS['success'],
                                icon_size=18
                            )
                        ], spacing=5))
                    ])
                )
            
            # Add "no data" row if filtered data is empty
            if not self.filtered_user_data:
                self.progress_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Text("No users match the current filters", style=ft.TextThemeStyle.BODY_LARGE, color=COLORS['text_secondary'])),
                        *[ft.DataCell(ft.Text("")) for _ in range(10)]
                    ])
                )
            else:
                print(f"[DEBUG] Successfully updated table with {len(self.progress_table.rows)} rows")
            
        except Exception as ex:
            print(f"Error updating progress table: {ex}")
            import traceback
            traceback.print_exc()
    
    def reset_user_filters(self, e):
        """Reset all user filters to default values"""
        try:
            print(f"[DEBUG] Resetting user filters")
            
            # Reset all filter controls to default values
            if hasattr(self, 'search_field'):
                self.search_field.value = ""
            if hasattr(self, 'dept_filter'):
                self.dept_filter.value = "all"
            if hasattr(self, 'score_filter'):
                self.score_filter.value = "all"
            if hasattr(self, 'exam_count_filter'):
                self.exam_count_filter.value = "all"
            if hasattr(self, 'activity_filter'):
                self.activity_filter.value = "all"
            
            # Reset filtered data to original
            if hasattr(self, 'original_user_data'):
                self.filtered_user_data = self.original_user_data.copy()
                self.update_progress_table()
            
            # Update the UI
            if hasattr(self, 'page') and self.page:
                self.page.update()
                
        except Exception as ex:
            print(f"Error resetting user filters: {ex}")
    
    def apply_user_filters(self, e):
        """Legacy method - redirects to new implementation"""
        self.apply_all_filters()
    
    def filter_user_data(self, search_term, user_data):
        """Filter user data based on search term (legacy method)"""
        print(f"[DEBUG] Filtering users by search term: {search_term}")
    
    def filter_user_data_by_dept(self, department, user_data):
        """Filter user data by department (legacy method)"""
        print(f"[DEBUG] Filtering users by department: {department}")
    
    def export_user_progress(self, user_data):
        """Export user progress data to Excel"""
        try:
            if not user_data:
                self.show_message("Export", "No user data available to export.")
                return
                
            # Prepare data for export
            export_data = []
            for user in user_data:
                exams_taken = user['exams_taken'] or 0
                total_attempts = user['total_attempts'] or 0
                passed_exams = user['passed_exams'] or 0
                avg_score = user['avg_score'] or 0
                best_score = user['best_score'] or 0
                avg_duration = user['avg_duration_minutes'] or 0
                pass_rate = (passed_exams / total_attempts * 100) if total_attempts > 0 else 0
                
                # Performance category
                if avg_score >= 90:
                    performance_category = "Excellent (90-100%)"
                elif avg_score >= 80:
                    performance_category = "Good (80-89%)"
                elif avg_score >= 70:
                    performance_category = "Satisfactory (70-79%)"
                elif avg_score >= 60:
                    performance_category = "Needs Improvement (60-69%)"
                else:
                    performance_category = "Poor (<60%)"
                
                export_data.append({
                    'User ID': user['id'],
                    'Username': user['username'],
                    'Full Name': user['full_name'],
                    'Department': user['department'] or 'N/A',
                    'Role': user.get('role', 'examinee'),
                    'Unique Exams Taken': exams_taken,
                    'Total Attempts': total_attempts,
                    'Exams Passed': passed_exams,
                    'Average Score (%)': round(avg_score, 2) if avg_score else 0,
                    'Best Score (%)': round(best_score, 2) if best_score else 0,
                    'Pass Rate (%)': round(pass_rate, 2),
                    'Average Duration (min)': round(avg_duration, 1),
                    'Performance Category': performance_category,
                    'Last Activity Date': user['last_exam_date'] or 'Never',
                    'Recent Activity (7 days)': user.get('recent_activity', 0)
                })
            
            if export_data:
                # Enhanced Excel export with multiple sheets
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"user_progress_detailed_{timestamp}.xlsx"
                filepath = f"/tmp/{filename}"
                
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    # Main user data sheet
                    df_users = pd.DataFrame(export_data)
                    df_users.to_excel(writer, sheet_name='User Progress', index=False)
                    
                    # Summary statistics
                    total_users = len(user_data)
                    active_users = sum(1 for u in user_data if (u.get('total_attempts', 0) or 0) > 0)
                    avg_score_all = sum(u.get('avg_score', 0) or 0 for u in user_data if (u.get('total_attempts', 0) or 0) > 0) / active_users if active_users > 0 else 0
                    
                    summary_data = [
                        ['Total Users', total_users],
                        ['Active Users (with attempts)', active_users],
                        ['Overall Average Score (%)', round(avg_score_all, 2)],
                        ['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                        ['Data Source', 'Quiz Examination System - User Progress Report']
                    ]
                    df_summary = pd.DataFrame(summary_data, columns=['Metric', 'Value'])
                    df_summary.to_excel(writer, sheet_name='Summary', index=False)
                
                success_msg = f"Enhanced user progress report exported!\nFile: {filename}\nUsers: {len(export_data)}\nSheets: User Progress, Summary"
                self.show_message("Export Success", success_msg)
            else:
                self.show_message("Export", "No data available to export.")
                
        except Exception as ex:
            print(f"Error exporting user progress: {ex}")
            self.show_message("Export Error", f"Failed to export user data: {str(ex)}")
    
    def show_individual_user_details(self, user_id):
        """Show detailed information for a specific user"""
        try:
            print(f"[DEBUG] show_individual_user_details called for user_id: {user_id}")
            
            # Get detailed user exam history
            user_details = self.db.execute_query("""
                SELECT 
                    u.username,
                    u.full_name,
                    u.department,
                    e.title as exam_title,
                    es.score,
                    es.duration_seconds,
                    es.start_time,
                    es.end_time,
                    es.attempt_number,
                    (CASE WHEN es.score >= 70 THEN 'Passed' ELSE 'Failed' END) as result
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                JOIN exams e ON es.exam_id = e.id
                WHERE u.id = ? AND es.is_completed = 1
                ORDER BY es.end_time DESC
                LIMIT 20
            """, (user_id,))
            
            if not user_details:
                self.show_message("User Details", "No exam history found for this user.")
                return
            
            user_info = user_details[0]  # Get user info from first record
            
            # Create user details table
            details_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Exam")),
                    ft.DataColumn(ft.Text("Score")),
                    ft.DataColumn(ft.Text("Result")),
                    ft.DataColumn(ft.Text("Duration")),
                    ft.DataColumn(ft.Text("Date")),
                    ft.DataColumn(ft.Text("Attempt"))
                ],
                rows=[],
                width=float("inf"),
                column_spacing=15
            )
            
            for detail in user_details:
                duration_minutes = (detail['duration_seconds'] or 0) / 60
                exam_date = detail['end_time']
                try:
                    exam_date_formatted = datetime.fromisoformat(exam_date.replace('Z', '+00:00')).strftime("%m/%d/%Y %H:%M")
                except:
                    exam_date_formatted = str(exam_date)[:16] if exam_date else "N/A"
                
                result_color = COLORS['success'] if detail['result'] == 'Passed' else COLORS['error']
                
                details_table.rows.append(
                    ft.DataRow([
                        ft.DataCell(ft.Text(detail['exam_title'][:30] + "..." if len(detail['exam_title']) > 30 else detail['exam_title'])),
                        ft.DataCell(ft.Text(f"{detail['score']:.1f}%")),
                        ft.DataCell(ft.Text(detail['result'], color=result_color)),
                        ft.DataCell(ft.Text(f"{duration_minutes:.1f}m")),
                        ft.DataCell(ft.Text(exam_date_formatted)),
                        ft.DataCell(ft.Text(str(detail['attempt_number'])))
                    ])
                )
            
            # Create user summary info
            user_summary = ft.Container(
                content=ft.Column([
                    ft.Text(f"📊 {user_info['full_name']}", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"👤 Username: {user_info['username']}", size=14),
                    ft.Text(f"🏢 Department: {user_info['department'] or 'N/A'}", size=14),
                    ft.Text(f"📈 Total Exam Sessions: {len(user_details)}", size=14)
                ], spacing=5),
                padding=ft.padding.all(15),
                bgcolor=ft.colors.with_opacity(0.1, COLORS['primary']),
                border_radius=8
            )
            
            # Create content for dialog
            content = ft.Column([
                user_summary,
                ft.Container(height=15),
                ft.Text("Recent Exam History", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(height=10),
                ft.Container(
                    content=ft.ListView(
                        controls=[details_table],
                        expand=True,
                        auto_scroll=False
                    ),
                    height=300
                )
            ], spacing=5)
            
            # Show dialog with user details
            dialog_content = ft.Container(
                content=content,
                width=700,
                height=500
            )
            
            success = self.safe_show_dialog(
                title=f"User Details - {user_info['full_name']}",
                content=dialog_content
            )
            
            if not success:
                print(f"[ERROR] Failed to show user details dialog")
                
        except Exception as ex:
            print(f"Error showing individual user details: {ex}")
            self.show_message("Error", f"Failed to load user details: {str(ex)}")
    
    def show_user_progress_chart(self, user_id):
        """Show progress chart for a specific user"""
        try:
            print(f"[DEBUG] show_user_progress_chart called for user_id: {user_id}")
            
            # Get user's score progression over time
            progress_data = self.db.execute_query("""
                SELECT 
                    u.full_name,
                    e.title as exam_title,
                    es.score,
                    DATE(es.end_time) as exam_date
                FROM exam_sessions es
                JOIN users u ON es.user_id = u.id
                JOIN exams e ON es.exam_id = e.id
                WHERE u.id = ? AND es.is_completed = 1 AND es.score IS NOT NULL
                ORDER BY es.end_time
                LIMIT 50
            """, (user_id,))
            
            if not progress_data or len(progress_data) < 2:
                self.show_message("Progress Chart", "Not enough data to generate a progress chart for this user.")
                return
            
            user_name = progress_data[0]['full_name']
            
            try:
                # Generate progress chart
                fig, ax = plt.subplots(figsize=(10, 6))
                
                dates = [datetime.strptime(row['exam_date'], '%Y-%m-%d') for row in progress_data]
                scores = [row['score'] for row in progress_data]
                
                ax.plot(dates, scores, marker='o', linewidth=2, markersize=8, color='#3182ce')
                ax.set_title(f'Score Progress for {user_name}', fontsize=16, fontweight='bold')
                ax.set_xlabel('Date')
                ax.set_ylabel('Score (%)')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(0, 100)
                
                # Add horizontal line at 70% (passing score)
                ax.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Passing Score (70%)')
                ax.legend()
                
                # Format x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                # Convert to base64 image
                buffer = io.BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                plt.close()
                
                chart_image = base64.b64encode(buffer.getvalue()).decode()
                
                # Create image display
                chart_display = ft.Image(
                    src_base64=chart_image,
                    width=700,
                    height=400,
                    fit=ft.ImageFit.CONTAIN
                )
                
                # Show chart in dialog
                dialog_content = ft.Container(
                    content=ft.Column([
                        chart_display,
                        ft.Container(height=10),
                        ft.Text(f"Total Exams: {len(progress_data)} | Latest Score: {scores[-1]:.1f}% | Average Score: {sum(scores)/len(scores):.1f}%", 
                               size=14, text_align=ft.TextAlign.CENTER)
                    ]),
                    width=750,
                    height=500
                )
                
                success = self.safe_show_dialog(
                    title=f"Progress Chart - {user_name}",
                    content=dialog_content
                )
                
                if not success:
                    print(f"[ERROR] Failed to show progress chart dialog")
                    
            except Exception as chart_ex:
                print(f"Error generating progress chart: {chart_ex}")
                self.show_message("Chart Error", f"Failed to generate progress chart: {str(chart_ex)}")
                
        except Exception as ex:
            print(f"Error showing user progress chart: {ex}")
            self.show_message("Error", f"Failed to load progress chart: {str(ex)}")