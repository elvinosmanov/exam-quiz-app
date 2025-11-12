import os
import sys

def get_base_path():
    """Get base path for both development and packaged executable"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # Use the directory where the executable is located
        base = os.path.dirname(sys.executable)
    else:
        # Running in development
        base = os.path.dirname(os.path.dirname(__file__))

    print(f"[CONFIG] Base path: {base}")
    return base

def get_data_dir():
    """Get writable data directory for database and uploads"""
    if getattr(sys, 'frozen', False):
        # For packaged app, use executable directory (writable by user)
        data_dir = os.path.dirname(sys.executable)
    else:
        # Development mode
        data_dir = os.path.dirname(os.path.dirname(__file__))

    # Ensure directory exists and is writable
    os.makedirs(data_dir, exist_ok=True)
    print(f"[CONFIG] Data directory: {data_dir}")
    return data_dir

# Base path for the application
BASE_PATH = get_base_path()
DATA_DIR = get_data_dir()

# Database configuration
DATABASE_PATH = os.path.join(DATA_DIR, 'quiz_app.db')
print(f"[CONFIG] Database path: {DATABASE_PATH}")

# Security settings
SECRET_KEY = "your-secret-key-change-in-production"
SESSION_TIMEOUT = 3600  # 1 hour in seconds

# File upload settings
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'assets', 'images')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"[CONFIG] Upload folder: {UPLOAD_FOLDER}")

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
    'info': '#3b82f6',
    'background': '#f8fafc',
    'surface': '#ffffff',
    'text_primary': '#1e293b',
    'text_secondary': '#64748b'
}

# Organizational Structure (Department → Units mapping)
# NOTE: This is temporary structure - will be updated with real Azercosmos departments
ORGANIZATIONAL_STRUCTURE = {
    "Department 1": [
        "Unit 1",
        "Unit 2",
        "Unit 3"
    ],
    "Department 2": [
        "Unit 1",
        "Unit 2",
        "Unit 3",
        "Unit 4"
    ],
    "Department 3": [
        "Unit 1",
        "Unit 2"
    ],
    "Department 4": [
        "Unit 1",
        "Unit 2",
        "Unit 3"
    ]
}

# Flat list of all departments
DEPARTMENTS = list(ORGANIZATIONAL_STRUCTURE.keys())

def get_units_for_department(department):
    """
    Get list of units for a given department

    Args:
        department (str): Department name

    Returns:
        list: List of unit names for the department, or empty list if not found
    """
    return ORGANIZATIONAL_STRUCTURE.get(department, [])