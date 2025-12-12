# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('quiz_app/assets/images', 'assets/images')],  # Removed quiz_app.db - created at runtime
    hiddenimports=[
        'quiz_app.database.database',
        'quiz_app.utils.auth',
        'quiz_app.utils.session',
        'quiz_app.utils.localization',
        'quiz_app.utils.email_handler',
        'quiz_app.utils.email_templates',
        'quiz_app.utils.email_ui_components',
        'quiz_app.utils.pdf_generator',
        'quiz_app.utils.permissions',
        'quiz_app.utils.view_switcher',
        'quiz_app.utils.question_selector',
        'quiz_app.utils.bulk_import',
        'quiz_app.views.auth.login_view',
        'quiz_app.views.admin.admin_dashboard',
        'quiz_app.views.admin.user_management',
        'quiz_app.views.admin.quiz_management',
        'quiz_app.views.admin.question_management',
        'quiz_app.views.admin.grading',
        'quiz_app.views.admin.reports',
        'quiz_app.views.admin.settings',
        'quiz_app.views.admin.base_admin_layout',
        'quiz_app.views.examinee.examinee_dashboard',
        'quiz_app.views.examinee.exam_interface',
        'bcrypt',
        'sqlite3',
        'openpyxl',
        'pandas',
        'PIL',
        'reportlab',
        # Email modules (required by password_generator.py)
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'smtplib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unused modules to reduce size
        'tkinter',
        'unittest',
        'test',
        'tests',
        'curses',
        # 'email.mime',  # REMOVED: needed by password_generator.py for email functionality
        'pydoc',
        'doctest',
        'argparse',
    ],
    noarchive=False,
    optimize=0,  # Keep docstrings intact (required by pandas/numpy)
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='QuizExamSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window - GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='QuizExamSystem.app',
    icon=None,
    bundle_identifier=None,
)
