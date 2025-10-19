import os

# Database configuration
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'quiz_app.db')

# Security settings
SECRET_KEY = "your-secret-key-change-in-production"
SESSION_TIMEOUT = 3600  # 1 hour in seconds

# File upload settings
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'quiz_app', 'assets', 'images')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Exam settings
DEFAULT_EXAM_DURATION = 60  # minutes
MAX_QUESTIONS_PER_EXAM = 100

# UI Settings
COLORS = {
    'primary': '#2563eb',
    'secondary': '#64748b',
    'success': '#10b981',
    'warning': '#f59e0b',
    'error': '#ef4444',
    'background': '#f8fafc',
    'surface': '#ffffff',
    'text_primary': '#1e293b',
    'text_secondary': '#64748b'
}