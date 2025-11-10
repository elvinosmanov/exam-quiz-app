"""
Migration to add email notification system
- email_templates: Customizable email templates (passed/failed/pending × English/Azerbaijani)
- email_log: Track email notifications sent by HR/Experts
- language_preference: Add language preference to users table
"""

import sqlite3
import os
from quiz_app.config import DATABASE_PATH

def get_default_templates():
    """Return default email templates for all types and languages"""

    templates = [
        # English - Passed
        {
            'template_type': 'passed',
            'language': 'en',
            'subject': '🎉 Exam Results - {{exam_name}}',
            'body_template': '''Dear {{full_name}},

Congratulations! You have successfully passed the {{exam_name}} examination.

📊 Your Results:
• Final Score: {{score}}%
• Passing Score: {{passing_score}}%
• Status: PASSED ✅

Questions Summary:
• Correct Answers: {{correct}}
• Incorrect Answers: {{incorrect}}
• Unanswered: {{unanswered}}

Well done on your achievement! Keep up the excellent work.

Best regards,
HR Department'''
        },

        # English - Failed
        {
            'template_type': 'failed',
            'language': 'en',
            'subject': 'Exam Results - {{exam_name}}',
            'body_template': '''Dear {{full_name}},

Thank you for completing the {{exam_name}} examination.

📊 Your Results:
• Final Score: {{score}}%
• Passing Score: {{passing_score}}%
• Status: Not Passed

Questions Summary:
• Correct Answers: {{correct}}
• Incorrect Answers: {{incorrect}}
• Unanswered: {{unanswered}}

Don't be discouraged! Every challenge is an opportunity to learn and grow.
We encourage you to review the material and continue improving.

You can do this! 💪

Best regards,
HR Department'''
        },

        # English - Pending
        {
            'template_type': 'pending',
            'language': 'en',
            'subject': 'Exam Submission Confirmed - {{exam_name}}',
            'body_template': '''Dear {{full_name}},

Your {{exam_name}} examination has been successfully submitted.

Your answers are currently under review by our evaluation team.
You will be notified once the grading process is complete.

Thank you for your patience.

Best regards,
HR Department'''
        },

        # Azerbaijani - Passed
        {
            'template_type': 'passed',
            'language': 'az',
            'subject': '🎉 İmtahan Nəticələri - {{exam_name}}',
            'body_template': '''Hörmətli {{full_name}},

Təbrik edirik! Siz {{exam_name}} imtahanını uğurla keçmisiniz.

📊 Nəticələriniz:
• Yekun Bal: {{score}}%
• Keçid Balı: {{passing_score}}%
• Status: KEÇDİ ✅

Sualların Xülasəsi:
• Düzgün Cavablar: {{correct}}
• Səhv Cavablar: {{incorrect}}
• Cavabsız: {{unanswered}}

Təbrik edirik! Uğurlarınızın davamını arzulayırıq.

Hörmətlə,
İnsan Resursları Şöbəsi'''
        },

        # Azerbaijani - Failed
        {
            'template_type': 'failed',
            'language': 'az',
            'subject': 'İmtahan Nəticələri - {{exam_name}}',
            'body_template': '''Hörmətli {{full_name}},

{{exam_name}} imtahanını tamamladığınız üçün təşəkkür edirik.

📊 Nəticələriniz:
• Yekun Bal: {{score}}%
• Keçid Balı: {{passing_score}}%
• Status: Keçmədi

Sualların Xülasəsi:
• Düzgün Cavablar: {{correct}}
• Səhv Cavablar: {{incorrect}}
• Cavabsız: {{unanswered}}

Ruhdan düşməyin! Hər çətinlik öyrənmək və inkişaf etmək üçün fürsətdir.
Materialı yenidən nəzərdən keçirməyi və təkmilləşməyə davam etməyi tövsiyə edirik.

Siz bacararıq! 💪

Hörmətlə,
İnsan Resursları Şöbəsi'''
        },

        # Azerbaijani - Pending
        {
            'template_type': 'pending',
            'language': 'az',
            'subject': 'İmtahan Təqdim Edildi - {{exam_name}}',
            'body_template': '''Hörmətli {{full_name}},

{{exam_name}} imtahanınız uğurla təqdim edilmişdir.

Cavablarınız hazırda qiymətləndirmə komandamız tərəfindən nəzərdən keçirilir.
Qiymətləndirmə prosesi başa çatdıqdan sonra sizə məlumat veriləcək.

Səbriniz üçün təşəkkür edirik.

Hörmətlə,
İnsan Resursları Şöbəsi'''
        }
    ]

    return templates


def migrate():
    """Add email system tables and default templates"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        # Create email_templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_type TEXT NOT NULL,
                language TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_template TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(template_type, language)
            )
        ''')

        # Create email_log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                recipient_email TEXT NOT NULL,
                recipient_name TEXT,
                sent_by INTEGER NOT NULL,
                email_type TEXT NOT NULL,
                language TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES exam_sessions (id),
                FOREIGN KEY (sent_by) REFERENCES users (id)
            )
        ''')

        # Add language_preference column to users table if it doesn't exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN language_preference TEXT DEFAULT 'en'")
            print("  ✓ Added language_preference column to users table")
        except sqlite3.OperationalError:
            print("  ℹ language_preference column already exists")

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_templates_type_lang ON email_templates(template_type, language)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_log_session ON email_log(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_log_sent_by ON email_log(sent_by)')

        # Insert default templates
        templates = get_default_templates()
        for template in templates:
            try:
                cursor.execute('''
                    INSERT INTO email_templates (template_type, language, subject, body_template)
                    VALUES (?, ?, ?, ?)
                ''', (
                    template['template_type'],
                    template['language'],
                    template['subject'],
                    template['body_template']
                ))
                print(f"  ✓ Inserted default template: {template['template_type']} ({template['language']})")
            except sqlite3.IntegrityError:
                print(f"  ℹ Template already exists: {template['template_type']} ({template['language']})")

        conn.commit()
        print("\n✓ Migration successful: Email notification system tables created")
        print("  - email_templates: Customizable email templates")
        print("  - email_log: Email notification tracking")
        print("  - 6 default templates added (3 types × 2 languages)")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
