"""
PDF Generator for Exam Export
Generates printable exam papers and answer keys with variants
"""

import os
import json
import random
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, PageTemplate, Frame
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class ExamPDFGenerator:
    def __init__(self, db):
        self.db = db
        self.logo_path = "quiz_app/assets/images/azercosmos-logo.png"
        self.footer_text = [
            "SPECIAL WARNING",
            "This document contains confidential information belonging to the Space Agency of the Republic of Azerbaijan (Azercosmos)."
        ]
        self.font_map = self._register_fonts()
        self.font_family = self.font_map['family']
        self.normal_font = self.font_map['normal']
        self.bold_font = self.font_map['bold']
        self.italic_font = self.font_map['italic']
        self.bold_italic_font = self.font_map['bold_italic']
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _register_fonts(self):
        """Register a Unicode-capable font family for Azerbaijani support"""
        font_candidates = [
            {
                'family': 'AzerSans',
                'variants': {
                    'normal': ('AzerSans', '/System/Library/Fonts/Supplemental/Arial.ttf'),
                    'bold': ('AzerSans-Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
                    'italic': ('AzerSans-Italic', '/System/Library/Fonts/Supplemental/Arial Italic.ttf'),
                    'bold_italic': ('AzerSans-BoldItalic', '/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf')
                }
            },
            {
                'family': 'AzerSans',
                'variants': {
                    'normal': ('AzerSans', 'C:\\\\Windows\\\\Fonts\\\\arial.ttf'),
                    'bold': ('AzerSans-Bold', 'C:\\\\Windows\\\\Fonts\\\\arialbd.ttf'),
                    'italic': ('AzerSans-Italic', 'C:\\\\Windows\\\\Fonts\\\\ariali.ttf'),
                    'bold_italic': ('AzerSans-BoldItalic', 'C:\\\\Windows\\\\Fonts\\\\arialbi.ttf')
                }
            },
            {
                'family': 'DejaVuSans',
                'variants': {
                    'normal': ('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
                    'bold': ('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
                    'italic': ('DejaVuSans-Italic', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf'),
                    'bold_italic': ('DejaVuSans-BoldItalic', '/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf')
                }
            }
        ]

        for candidate in font_candidates:
            variants = candidate['variants']
            normal_name, normal_path = variants['normal']
            bold_name, bold_path = variants['bold']

            if not (os.path.exists(normal_path) and os.path.exists(bold_path)):
                continue

            italic_name, italic_path = variants['italic']
            bold_italic_name, bold_italic_path = variants['bold_italic']

            # Fallback to normal if italic variants are missing
            if not os.path.exists(italic_path):
                italic_path = normal_path
            if not os.path.exists(bold_italic_path):
                bold_italic_path = bold_path if os.path.exists(bold_path) else normal_path

            try:
                for font_name, font_path in [
                    (normal_name, normal_path),
                    (bold_name, bold_path),
                    (italic_name, italic_path),
                    (bold_italic_name, bold_italic_path)
                ]:
                    if font_name not in pdfmetrics.getRegisteredFontNames():
                        pdfmetrics.registerFont(TTFont(font_name, font_path))

                pdfmetrics.registerFontFamily(
                    candidate['family'],
                    normal=normal_name,
                    bold=bold_name,
                    italic=italic_name,
                    boldItalic=bold_italic_name
                )

                return {
                    'family': candidate['family'],
                    'normal': normal_name,
                    'bold': bold_name,
                    'italic': italic_name,
                    'bold_italic': bold_italic_name
                }
            except Exception as font_error:
                print(f"[PDF] Failed to register font {candidate['family']}: {font_error}")
                continue

        # Default fallback to Helvetica if Unicode fonts are unavailable
        return {
            'family': 'Helvetica',
            'normal': 'Helvetica',
            'bold': 'Helvetica-Bold',
            'italic': 'Helvetica-Oblique',
            'bold_italic': 'Helvetica-BoldOblique'
        }

    def _setup_styles(self):
        """Setup custom paragraph styles"""
        # Update base styles to use Unicode-capable fonts
        base_normal = self.styles['Normal']
        base_normal.fontName = self.font_family
        base_normal.fontSize = 11
        base_normal.leading = 14

        heading1 = self.styles['Heading1']
        heading1.fontName = self.bold_font

        heading2 = self.styles['Heading2']
        heading2.fontName = self.bold_font
        heading2.fontSize = 14

        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=self.bold_font
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#424242'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName=self.font_family
        ))

        # Topic header style
        self.styles.add(ParagraphStyle(
            name='TopicHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1565c0'),
            spaceAfter=8,
            spaceBefore=12,
            fontName=self.bold_font
        ))

        # Question style
        self.styles.add(ParagraphStyle(
            name='Question',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leading=14,
            fontName=self.font_family
        ))

        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#d32f2f'),
            alignment=TA_CENTER,
            leading=10,
            fontName=self.font_family
        ))

    def _add_footer(self, canvas, doc):
        """Add footer to each page"""
        canvas.saveState()
        # Position footer at bottom of page
        footer_y = 15*mm

        # Draw footer text
        canvas.setFont(self.bold_font, 8)
        canvas.setFillColor(colors.HexColor('#d32f2f'))
        canvas.drawCentredString(A4[0]/2, footer_y + 8, self.footer_text[0])

        canvas.setFont(self.normal_font, 7)
        text = self.footer_text[1]
        canvas.drawCentredString(A4[0]/2, footer_y, text)

        canvas.restoreState()

    def generate_instance_id(self, assignment_id, variant_num):
        """Generate unique exam instance ID"""
        return f"EXAM-{assignment_id:06d}-V{variant_num}"

    def get_assignment_topics(self, assignment_id):
        """Get assignment record and associated topics (exam templates) with pool settings"""
        # Get the assignment details
        assignment = self.db.execute_single(
            "SELECT * FROM exam_assignments WHERE id = ?",
            (assignment_id,)
        )

        if not assignment:
            return None, []

        # Get all exam templates for this assignment
        templates = self.db.execute_query(
            """SELECT e.id,
                      e.title,
                      e.category,
                      COALESCE(aet.easy_count, 0) AS easy_count,
                      COALESCE(aet.medium_count, 0) AS medium_count,
                      COALESCE(aet.hard_count, 0) AS hard_count
               FROM assignment_exam_templates aet
               JOIN exams e ON aet.exam_id = e.id
               WHERE aet.assignment_id = ?
               ORDER BY aet.order_index""",
            (assignment_id,)
        )

        if templates:
            return assignment, templates

        # Fallback: use primary exam
        primary_exam = self.db.execute_single(
            "SELECT id, title, category FROM exams WHERE id = ?",
            (assignment['exam_id'],)
        )

        if not primary_exam:
            primary_exam = {
                'id': assignment['exam_id'],
                'title': 'Exam',
                'category': ''
            }

        primary_exam['easy_count'] = assignment.get('easy_questions_count', 0) or 0
        primary_exam['medium_count'] = assignment.get('medium_questions_count', 0) or 0
        primary_exam['hard_count'] = assignment.get('hard_questions_count', 0) or 0

        return assignment, [primary_exam]

    def get_topic_questions(self, topic_id, difficulty_counts=None, randomize=False):
        """Get questions for a topic, optionally filtered by difficulty"""
        questions = []

        if difficulty_counts:
            # Get questions by difficulty level
            for level in ['easy', 'medium', 'hard']:
                count = difficulty_counts.get(level, 0)
                if count > 0:
                    level_questions = self.db.execute_query(
                        """SELECT * FROM questions
                           WHERE exam_id = ? AND difficulty_level = ? AND is_active = 1
                           ORDER BY RANDOM() LIMIT ?""",
                        (topic_id, level, count)
                    )
                    questions.extend(level_questions)
        else:
            # Get all questions
            questions = self.db.execute_query(
                "SELECT * FROM questions WHERE exam_id = ? AND is_active = 1",
                (topic_id,)
            )

        if randomize and questions:
            random.shuffle(questions)

        return questions

    def get_question_options(self, question_id):
        """Get options for a multiple choice question"""
        return self.db.execute_query(
            "SELECT * FROM question_options WHERE question_id = ? ORDER BY order_index",
            (question_id,)
        )

    def create_question_snapshot(self, assignment_id, randomize=False):
        """Create snapshot of questions for this variant"""
        assignment, topics = self.get_assignment_topics(assignment_id)
        if not assignment:
            return []

        assignment_pool_counts = {
            'easy': assignment.get('easy_questions_count', 0) or 0,
            'medium': assignment.get('medium_questions_count', 0) or 0,
            'hard': assignment.get('hard_questions_count', 0) or 0
        }
        assignment_pool_total = sum(assignment_pool_counts.values())
        use_question_pool = bool(assignment.get('use_question_pool'))

        # When multiple templates exist but none store template-level counts,
        # fall back to assignment-level counts exactly once across all templates.
        if (
            use_question_pool
            and len(topics) > 1
            and assignment_pool_total > 0
            and all(
                (topic.get('easy_count', 0) or 0)
                + (topic.get('medium_count', 0) or 0)
                + (topic.get('hard_count', 0) or 0) == 0
                for topic in topics
            )
        ):
            print("[PDF] Multi-template preset without per-template counts detected; using assignment-level distribution")
            return self._snapshot_from_shared_pool(topics, assignment_pool_counts, randomize)

        snapshot_data = []

        for topic in topics:
            topic_counts = {
                'easy': topic.get('easy_count', 0) or 0,
                'medium': topic.get('medium_count', 0) or 0,
                'hard': topic.get('hard_count', 0) or 0
            }

            difficulty_counts = None
            if use_question_pool:
                topic_total = sum(topic_counts.values())
                if topic_total > 0:
                    difficulty_counts = topic_counts
                elif assignment_pool_total > 0:
                    difficulty_counts = assignment_pool_counts

            questions = self.get_topic_questions(
                topic['id'],
                difficulty_counts=difficulty_counts,
                randomize=randomize
            )
            snapshot_data.append({
                'topic_id': topic['id'],
                'topic_title': topic['title'],
                'questions': [q['id'] for q in questions]
            })

        return snapshot_data
    
    def _snapshot_from_shared_pool(self, topics, assignment_counts, randomize):
        """Select questions across multiple templates using assignment-level counts."""
        exam_ids = [topic['id'] for topic in topics]
        selected_by_exam = {exam_id: [] for exam_id in exam_ids}

        for difficulty in ['easy', 'medium', 'hard']:
            requested = assignment_counts.get(difficulty, 0) or 0
            if requested <= 0:
                continue

            placeholders = ",".join(["?"] * len(exam_ids))
            query = f"""
                SELECT * FROM questions
                WHERE exam_id IN ({placeholders})
                  AND difficulty_level = ?
                  AND is_active = 1
            """
            params = tuple(exam_ids) + (difficulty,)
            available = self.db.execute_query(query, params)

            available_count = len(available)
            print(f"[PDF] {difficulty.capitalize()} pool: {available_count} available across templates, {requested} requested")

            if available_count == 0:
                continue

            if available_count < requested:
                requested = available_count

            chosen = random.sample(available, requested) if available_count > requested else available

            for question in chosen:
                selected_by_exam.setdefault(question['exam_id'], []).append(question)

        snapshot = []
        for topic in topics:
            questions = selected_by_exam.get(topic['id'], [])
            if randomize and questions:
                random.shuffle(questions)
            snapshot.append({
                'topic_id': topic['id'],
                'topic_title': topic['title'],
                'questions': [q['id'] for q in questions]
            })

        return snapshot

    def generate_exam_paper(self, assignment, snapshot, variant_num, output_path):
        """Generate printable exam paper PDF"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=30*mm  # Space for footer
        )

        story = []
        exam_id = self.generate_instance_id(assignment['id'], variant_num)

        # Header with logo (preserve aspect ratio: 4.61:1)
        if os.path.exists(self.logo_path):
            logo_width = 60*mm
            logo_height = logo_width / 4.61  # Preserve aspect ratio
            logo = Image(self.logo_path, width=logo_width, height=logo_height)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 6*mm))

        # Title
        variant_text = f" - VARIANT {variant_num}" if variant_num > 1 else ""
        story.append(Paragraph(f"EXAMINATION PAPER{variant_text}", self.styles['CustomTitle']))
        story.append(Spacer(1, 3*mm))

        # Calculate total points from snapshot
        total_points = 0
        for topic_data in snapshot:
            for q_id in topic_data['questions']:
                question = self.db.execute_single("SELECT points FROM questions WHERE id = ?", (q_id,))
                if question:
                    total_points += question.get('points', 1.0)

        # Assignment info
        assignment_title = assignment.get('assignment_name') or assignment.get('title', 'Exam')
        total_questions = sum(len(topic_data['questions']) for topic_data in snapshot)
        info_text = f"""
        <b>Assignment:</b> {assignment_title}<br/>
        <b>Duration:</b> {assignment['duration_minutes']} minutes |
        <b>Questions:</b> {total_questions} |
        <b>Total Points:</b> {int(total_points) if total_points == int(total_points) else total_points}
        """
        story.append(Paragraph(info_text, self.styles['CustomSubtitle']))
        story.append(Spacer(1, 5*mm))

        # Student info fields with Paragraphs for Unicode support
        info_table = Table([
            [Paragraph('<b>Student Name:</b>', self.styles['Normal']), Paragraph('__________________________________________', self.styles['Normal'])],
            [Paragraph('<b>Date:</b>', self.styles['Normal']), Paragraph('__________________________________________', self.styles['Normal'])],
            [Paragraph('<b>Exam ID:</b>', self.styles['Normal']), Paragraph(exam_id, self.styles['Normal'])]
        ], colWidths=[35*mm, 135*mm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 8*mm))

        # Add questions grouped by topic
        question_number = 1
        for topic_data in snapshot:
            # Topic header
            story.append(Paragraph(f"TOPIC: {topic_data['topic_title']}", self.styles['TopicHeader']))
            story.append(Spacer(1, 4*mm))

            # Get questions
            for q_id in topic_data['questions']:
                question = self.db.execute_single(
                    "SELECT * FROM questions WHERE id = ?",
                    (q_id,)
                )

                if not question:
                    continue

                # Question text with instruction for question type
                instruction = ""
                if question['question_type'] == 'single_choice':
                    instruction = ' <i>(Select one answer)</i>'
                elif question['question_type'] == 'multiple_choice':
                    instruction = ' <i>(Select all correct answers)</i>'

                # Add points display
                points = question.get('points', 1.0)
                points_text = f" <b>[{int(points) if points == int(points) else points} point{'s' if points != 1 else ''}]</b>"

                q_text = f"<b>{question_number}.</b> {question['question_text']}{instruction}{points_text}"
                story.append(Paragraph(q_text, self.styles['Question']))
                story.append(Spacer(1, 2*mm))

                # Format based on question type
                if question['question_type'] in ['multiple_choice', 'single_choice']:
                    options = self.get_question_options(question['id'])
                    option_labels = ['A', 'B', 'C', 'D', 'E', 'F']
                    # Each option on a new line
                    for i, opt in enumerate(options):
                        option_text = f"{option_labels[i]}) {opt['option_text']}"
                        story.append(Paragraph(option_text, self.styles['Normal']))
                        story.append(Spacer(1, 1*mm))
                    story.append(Spacer(1, 3*mm))

                elif question['question_type'] == 'true_false':
                    # Each option on a new line
                    story.append(Paragraph("A) True", self.styles['Normal']))
                    story.append(Spacer(1, 1*mm))
                    story.append(Paragraph("B) False", self.styles['Normal']))
                    story.append(Spacer(1, 4*mm))

                elif question['question_type'] == 'short_answer':
                    # 3 lines for short answer - use table for proper line rendering
                    line_width = 170*mm  # Fit within page margins (210mm - 40mm margins)
                    for i in range(3):
                        line_table = Table([['']], colWidths=[line_width])
                        line_table.setStyle(TableStyle([
                            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.black),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ]))
                        story.append(line_table)
                    story.append(Spacer(1, 3*mm))

                elif question['question_type'] == 'essay':
                    # 12 lines for essay - use table for proper line rendering
                    line_width = 170*mm  # Fit within page margins
                    for i in range(12):
                        line_table = Table([['']], colWidths=[line_width])
                        line_table.setStyle(TableStyle([
                            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.black),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ]))
                        story.append(line_table)
                    story.append(Spacer(1, 3*mm))

                question_number += 1

            story.append(Spacer(1, 5*mm))

        # Build PDF with footer on every page
        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
        return exam_id

    def generate_answer_key(self, assignment, snapshot, variant_num, output_path):
        """Generate answer key PDF"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=30*mm  # Space for footer
        )

        story = []
        exam_id = self.generate_instance_id(assignment['id'], variant_num)

        # Header with logo (preserve aspect ratio)
        if os.path.exists(self.logo_path):
            logo_width = 60*mm
            logo_height = logo_width / 4.61
            logo = Image(self.logo_path, width=logo_width, height=logo_height)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 6*mm))

        # Title
        variant_text = f" - VARIANT {variant_num}" if variant_num > 1 else ""
        story.append(Paragraph(f"ANSWER KEY{variant_text} - CONFIDENTIAL", self.styles['CustomTitle']))
        story.append(Spacer(1, 3*mm))

        # Exam info
        assignment_title = assignment.get('assignment_name') or assignment.get('title', 'Exam')
        info_text = f"""
        <b>Exam ID:</b> {exam_id}<br/>
        <b>Assignment:</b> {assignment_title}<br/>
        <b>Generated:</b> {datetime.now().strftime('%B %d, %Y %I:%M %p')}
        """
        story.append(Paragraph(info_text, self.styles['CustomSubtitle']))
        story.append(Spacer(1, 8*mm))

        # Answers grouped by topic
        question_number = 1
        topic_points = {}

        for topic_data in snapshot:
            # Topic header
            story.append(Paragraph(f"TOPIC: {topic_data['topic_title']}", self.styles['TopicHeader']))
            story.append(Spacer(1, 3*mm))

            topic_total = 0

            # Get answers - simple format
            for q_id in topic_data['questions']:
                question = self.db.execute_single(
                    "SELECT * FROM questions WHERE id = ?",
                    (q_id,)
                )

                if not question:
                    continue

                points = question.get('points', 1.0)
                topic_total += points

                # Format answer based on question type - SIMPLE FORMAT
                if question['question_type'] in ['multiple_choice', 'single_choice']:
                    options = self.get_question_options(question['id'])
                    correct = next((opt for opt in options if opt['is_correct']), None)
                    if correct:
                        option_labels = ['A', 'B', 'C', 'D', 'E', 'F']
                        option_index = options.index(correct)
                        answer_text = f"{option_labels[option_index]}"
                    else:
                        answer_text = "[Not set]"

                elif question['question_type'] == 'true_false':
                    answer_text = question.get('correct_answer')
                    if answer_text is None or (isinstance(answer_text, str) and not answer_text.strip()):
                        answer_text = '[Not set]'

                elif question['question_type'] in ['short_answer', 'essay']:
                    answer_text = question.get('correct_answer')
                    if answer_text is None or (isinstance(answer_text, str) and not answer_text.strip()):
                        answer_text = '[See rubric]'
                    explanation = question.get('explanation')
                    if explanation:
                        answer_text = f"{answer_text} - {explanation}"

                else:
                    answer_text = question.get('correct_answer')
                    if answer_text is None or (isinstance(answer_text, str) and not answer_text.strip()):
                        answer_text = '[Not set]'

                # Simple format: "1. A  [2 pts]"
                answer_text = str(answer_text)
                answer_line = f"<b>{question_number}.</b> {answer_text}  <i>[{points} pts]</i>"
                story.append(Paragraph(answer_line, self.styles['Normal']))
                story.append(Spacer(1, 3*mm))

                question_number += 1

            topic_points[topic_data['topic_title']] = topic_total
            story.append(Spacer(1, 5*mm))

        # Grading section on a new page for clarity
        story.append(PageBreak())
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph("GRADING SECTION:", self.styles['TopicHeader']))
        story.append(Spacer(1, 5*mm))

        # Build grading data with Paragraphs for Unicode support
        grading_data = [[
            Paragraph('<b>Topic</b>', self.styles['Normal']),
            Paragraph('<b>Score</b>', self.styles['Normal']),
            Paragraph('<b>Total</b>', self.styles['Normal'])
        ]]
        total_points = 0
        for topic, points in topic_points.items():
            grading_data.append([
                Paragraph(topic, self.styles['Normal']),
                Paragraph('____', self.styles['Normal']),
                Paragraph(f'{points} pts', self.styles['Normal'])
            ])
            total_points += points

        grading_data.append([Paragraph('', self.styles['Normal']), Paragraph('', self.styles['Normal']), Paragraph('', self.styles['Normal'])])
        grading_data.append([
            Paragraph('<b>TOTAL SCORE:</b>', self.styles['Normal']),
            Paragraph('____', self.styles['Normal']),
            Paragraph(f'<b>{total_points} pts</b>', self.styles['Normal'])
        ])
        grading_data.append([
            Paragraph('<b>Percentage:</b>', self.styles['Normal']),
            Paragraph('____%', self.styles['Normal']),
            Paragraph('', self.styles['Normal'])
        ])
        grading_data.append([
            Paragraph('<b>Result:</b>', self.styles['Normal']),
            Paragraph('[ ] Pass  [ ] Fail', self.styles['Normal']),
            Paragraph('', self.styles['Normal'])
        ])

        grading_table = Table(grading_data, colWidths=[80*mm, 40*mm, 30*mm])
        grading_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEABOVE', (0, -4), (-1, -4), 1, colors.black),
        ]))
        story.append(grading_table)
        story.append(Spacer(1, 8*mm))

        # Grader info with Paragraphs for Unicode support
        grader_data = [
            [Paragraph('<b>Student Name:</b>', self.styles['Normal']), Paragraph('__________________________________', self.styles['Normal'])],
            [Paragraph('<b>Graded By:</b>', self.styles['Normal']), Paragraph('__________________________________', self.styles['Normal'])],
            [Paragraph('<b>Date:</b>', self.styles['Normal']), Paragraph('__________________________________', self.styles['Normal'])],
            [Paragraph('<b>Remarks:</b>', self.styles['Normal']), Paragraph('__________________________________', self.styles['Normal'])]
        ]
        grader_table = Table(grader_data, colWidths=[35*mm, 135*mm])
        grader_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(grader_table)

        # Build PDF with footer on every page
        doc.build(story, onFirstPage=self._add_footer, onLaterPages=self._add_footer)
        return exam_id
