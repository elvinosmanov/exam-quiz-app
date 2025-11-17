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

# Organizational Structure (Real Azercosmos Structure)
# Flexible 3-level hierarchy: Department → Section (optional) → Unit (optional)
# Each entry has separate Azerbaijani (name_az) and English (name_en) names
ORGANIZATIONAL_STRUCTURE = {
    "vice_chairman": {
        "name_az": "İdarə Heyəti sədrinin müavini",
        "name_en": "Vice Chairman of the Board",
        "abbr_az": "SM",
        "abbr_en": "VC",
        "type": "department",
        "sections": {},
        "units": []
    },
    "chief_confidentiality": {
        "name_az": "Məxfi işlər üzrə baş mütəxəssis",
        "name_en": "Chief Confidentiality Specialist",
        "abbr_az": "Mİ",
        "abbr_en": "CCS",
        "type": "department",
        "sections": {},
        "units": []
    },
    "counsellor_international": {
        "name_az": "Beynəlxalq əlaqələr üzrə müşavir",
        "name_en": "Counsellor on International Relations",
        "abbr_az": "BM",
        "abbr_en": "CIR",
        "type": "department",
        "sections": {},
        "units": []
    },
    "corporate_affairs": {
        "name_az": "Korporativ işlər üzrə menecer",
        "name_en": "Corporate Affairs Manager",
        "abbr_az": "KM",
        "abbr_en": "CM",
        "type": "department",
        "sections": {},
        "units": []
    },
    "space_law": {
        "name_az": "Kosmik hüquq məsələləri üzə müşavir",
        "name_en": "Space Law Advisor",
        "abbr_az": "KHM",
        "abbr_en": "SLA",
        "type": "department",
        "sections": {},
        "units": []
    },
    "strategy_business": {
        "name_az": "Strategiya və biznesin inkişafı departamenti",
        "name_en": "Strategy and Business Development Department",
        "abbr_az": "SBD",
        "abbr_en": "SBD",
        "type": "department",
        "sections": {},
        "units": [
            {"name_az": "Layihələrin idarəedilməsi bölməsi", "name_en": "Project Management Office", "abbr_az": "LİB", "abbr_en": "PMO"},
            {"name_az": "Strategiya və bazar analitikası bölməsi", "name_en": "Strategy and Market Intelligence Unit", "abbr_az": "SAB", "abbr_en": "SMU"}
        ]
    },
    "satellite_ground": {
        "name_az": "Peyk və yerüstü sistemlər departamenti",
        "name_en": "Satellite and Ground-Based Systems Department",
        "abbr_az": "PYD",
        "abbr_en": "SGD",
        "type": "department",
        "sections": {},
        "units": [
            {"name_az": "Peyk əməliyyatları bölməsi", "name_en": "Satellite Operations Unit", "abbr_az": "PƏB", "abbr_en": "SOU"},
            {"name_az": "Uçuş dinamikası bölməsi", "name_en": "Flight Dynamics Unit", "abbr_az": "UDB", "abbr_en": "FDU"},
            {"name_az": "Peyk mühəndisliyi bölməsi", "name_en": "Satellite Engineering Unit", "abbr_az": "PMB", "abbr_en": "SEU"},
            {"name_az": "Antena və radiotezlik sistemləri bölməsi", "name_en": "Antenna and Radiofrequency Systems Unit", "abbr_az": "ARB", "abbr_en": "ARU"}
        ]
    },
    "marketing_corporate": {
        "name_az": "Marketinq və korporativ kommunikasiya departamenti",
        "name_en": "Marketing and Corporate Communications Department",
        "abbr_az": "MKD",
        "abbr_en": "MKD",
        "type": "department",
        "sections": {},
        "units": [
            {"name_az": "Brend və marketinq bölməsi", "name_en": "Brand and Marketing Unit", "abbr_az": "BMB", "abbr_en": "BMU"}
        ]
    },
    "technical_solutions": {
        "name_az": "Texniki həllər və müştəri əməliyyatları departamenti",
        "name_en": "Technical Solutions and Customer Operations Department",
        "abbr_az": "TMD",
        "abbr_en": "TCO",
        "type": "department",
        "sections": {
            "customer_operations": {
                "name_az": "Müştəri əməliyyatları şöbəsi",
                "name_en": "Customer Operations Section",
                "abbr_az": "MƏŞ",
                "abbr_en": "COS",
                "units": [
                    {"name_az": "Müştəri mühəndisliyi bölməsi", "name_en": "Customer Engineering Unit", "abbr_az": "MMB", "abbr_en": "CEU"}
                ]
            }
        },
        "units": [
            {"name_az": "Texniki həllər bölməsi", "name_en": "Solutions Engineering Unit", "abbr_az": "THB", "abbr_en": "SE"}
        ]
    },
    "sales": {
        "name_az": "Satış departamenti",
        "name_en": "Sales Department",
        "abbr_az": "SD",
        "abbr_en": "SD",
        "type": "department",
        "sections": {},
        "units": [
            {"name_az": "Telekommunikasiya peykləri üzrə satış bölməsi", "name_en": "Telecommunications Satellites Sales Unit", "abbr_az": "TSB", "abbr_en": "TSU"},
            {"name_az": "Yerin müşahidəsi üzrə kommersiya həlləri bölməsi", "name_en": "Earth Observation Commercial Solutions Unit", "abbr_az": "YMKH", "abbr_en": "EOCS"}
        ]
    },
    "gis": {
        "name_az": "Coğrafi informasiya sistemləri mərkəzi",
        "name_en": "Geographic Information Systems Center",
        "abbr_az": "CİS",
        "abbr_en": "GIS",
        "type": "department",
        "sections": {},
        "units": [
            {"name_az": "CİS rəqəmsallaşdırma bölməsi", "name_en": "CIS Digitalization Unit", "abbr_az": "RB", "abbr_en": "DU"},
            {"name_az": "Fotoqrammetrik emal bölməsi", "name_en": "Photogrammetric Processing Unit", "abbr_az": "FB", "abbr_en": "PPU"},
            {"name_az": "Süni intellekt bölməsi", "name_en": "Artificial Intelligence Unit", "abbr_az": "SİB", "abbr_en": "AIU"},
            {"name_az": "Tematik emal bölməsi", "name_en": "Thematic Processing Unit", "abbr_az": "TEB", "abbr_en": "TPU"}
        ]
    },
    "research_development": {
        "name_az": "Tədqiqat və inkişaf mərkəzi",
        "name_en": "Research and Development Center",
        "abbr_az": "TIM",
        "abbr_en": "RDC",
        "type": "department",
        "sections": {
            "spacecraft_production": {
                "name_az": "Kosmik Aparatların İstehsalı Şöbəsi",
                "name_en": "Spacecraft Production Section",
                "abbr_az": "KAİŞ",
                "abbr_en": "SPS",
                "units": [
                    {"name_az": "Quraşdırma, inteqrasiya və test bölməsi", "name_en": "Assembly, Integration and Test Unit", "abbr_az": "QITB", "abbr_en": "AITU"}
                ]
            },
            "space_systems": {
                "name_az": "Kosmik sistemlərin layihələndirməsi və inkişafı şöbəsi",
                "name_en": "Space Systems Design and Development Section",
                "abbr_az": "KSİŞ",
                "abbr_en": "SDS",
                "units": [
                    {"name_az": "Proqram təminatı həlləri bölməsi", "name_en": "Software Solutions Unit", "abbr_az": "PTB", "abbr_en": "SSU"},
                    {"name_az": "Mexanika bölməsi", "name_en": "Mechanics Unit", "abbr_az": "MB", "abbr_en": "MU"},
                    {"name_az": "Elektrik və elektronika bölməsi", "name_en": "Electrical and Electronics Unit", "abbr_az": "EEB", "abbr_en": "EEU"}
                ]
            }
        },
        "units": []
    },
    "finance": {
        "name_az": "Maliyyə departamenti",
        "name_en": "Finance Department",
        "abbr_az": "MD",
        "abbr_en": "FD",
        "type": "department",
        "sections": {},
        "units": []
    },
    "legal": {
        "name_az": "Hüquq departamenti",
        "name_en": "Legal Department",
        "abbr_az": "HD",
        "abbr_en": "LD",
        "type": "department",
        "sections": {},
        "units": []
    },
    "hr": {
        "name_az": "İnsan resurslarının idarəedilməsi və sənədləşmə departamenti",
        "name_en": "Human Resources Management and Documentation Department",
        "abbr_az": "İRSD",
        "abbr_en": "HRD",
        "type": "department",
        "sections": {},
        "units": [
            {"name_az": "Personalın idarəedilməsi və sənədlərlə iş bölməsi", "name_en": "Personnel Management and Documentation Unit", "abbr_az": "PSB", "abbr_en": "PDU"},
            {"name_az": "Təlim və inkişaf bölməsi", "name_en": "Learning and Development Unit", "abbr_az": "TİB", "abbr_en": "LDU"},
            {"name_az": "Kosmik Akademik proqramlar bölməsi", "name_en": "Space Academic Programs Unit", "abbr_az": "KAB", "abbr_en": "SAU"}
        ]
    },
    "it_security": {
        "name_az": "İnformasiya texnologiyaları və təhlükəsizliyi departamenti",
        "name_en": "IT and Security Department",
        "abbr_az": "İTD",
        "abbr_en": "IT",
        "type": "department",
        "sections": {},
        "units": [
            {"name_az": "Proqram təminatı mühəndisliyi bölməsi", "name_en": "Software Engineering Unit", "abbr_az": "PTB", "abbr_en": "SU"},
            {"name_az": "İT infrastruktur və xidmətlər bölməsi", "name_en": "IT infrastructure and Services Unit", "abbr_az": "İXB", "abbr_en": "İSU"},
            {"name_az": "Yerüstü sistemlər üzrə İT bölməsi", "name_en": "Ground Systems IT Unit", "abbr_az": "YSB", "abbr_en": "GSU"}
        ]
    },
    "internal_control": {
        "name_az": "Daxili nəzarət və audit şöbəsi",
        "name_en": "Internal Control and Audit Section",
        "abbr_az": "DNA",
        "abbr_en": "ICA",
        "type": "section",
        "sections": {},
        "units": []
    },
    "administrative": {
        "name_az": "Administrativ işlər departamenti",
        "name_en": "Administrative Affairs Department",
        "abbr_az": "AİD",
        "abbr_en": "AD",
        "type": "department",
        "sections": {},
        "units": []
    },
    "digital_development": {
        "name_az": "Rəqəmsal inkişaf ofisi",
        "name_en": "Digital Development Office",
        "abbr_az": "RİO",
        "abbr_en": "DO",
        "type": "department",
        "sections": {},
        "units": []
    },
    "spectrum_management": {
        "name_az": "Radiotezliklərin idarəedilməsi şöbəsi",
        "name_en": "Spectrum Management Section",
        "abbr_az": "RİŞ",
        "abbr_en": "SMS",
        "type": "section",
        "sections": {},
        "units": []
    },
    "trade_union": {
        "name_az": "Həmkarlar İttifaqının ilk təşkilatı",
        "name_en": "Trade Union",
        "abbr_az": "HİK",
        "abbr_en": "TU",
        "type": "department",
        "sections": {},
        "units": []
    },
    "chairman_office": {
        "name_az": "Sədrin icra ofisi",
        "name_en": "Executive Office of the Chairman",
        "abbr_az": "SİO",
        "abbr_en": "EOC",
        "type": "department",
        "sections": {},
        "units": []
    }
}

# Flat list of all department keys
DEPARTMENT_KEYS = list(ORGANIZATIONAL_STRUCTURE.keys())

def get_departments(language='en'):
    """
    Get list of all departments in the specified language

    Args:
        language (str): Language code ('en' or 'az')

    Returns:
        list: List of department names in the specified language
    """
    lang_key = 'name_en' if language == 'en' else 'name_az'
    return [dept_data[lang_key] for dept_data in ORGANIZATIONAL_STRUCTURE.values()]

def get_department_key(department_name):
    """
    Get department key from department name (supports both languages)

    Args:
        department_name (str): Department name in either language

    Returns:
        str: Department key, or None if not found
    """
    for key, data in ORGANIZATIONAL_STRUCTURE.items():
        if data.get('name_az') == department_name or data.get('name_en') == department_name:
            return key
    return None

def get_sections_for_department(department_name, language='en'):
    """
    Get list of sections for a given department in the specified language

    Args:
        department_name (str): Department name (in either language)
        language (str): Language code ('en' or 'az')

    Returns:
        list: List of section names for the department, or empty list if not found
    """
    # Get department key
    dept_key = get_department_key(department_name)
    if not dept_key:
        return []

    dept_data = ORGANIZATIONAL_STRUCTURE.get(dept_key, {})
    sections = dept_data.get("sections", {})

    lang_key = 'name_en' if language == 'en' else 'name_az'
    return [section_data[lang_key] for section_data in sections.values()]

def get_section_key(department_name, section_name):
    """
    Get section key from section name

    Args:
        department_name (str): Department name (in either language)
        section_name (str): Section name (in either language)

    Returns:
        str: Section key, or None if not found
    """
    dept_key = get_department_key(department_name)
    if not dept_key:
        return None

    dept_data = ORGANIZATIONAL_STRUCTURE.get(dept_key, {})
    sections = dept_data.get("sections", {})

    for key, data in sections.items():
        if data.get('name_az') == section_name or data.get('name_en') == section_name:
            return key
    return None

def get_units_for_department(department_name, section_name=None, language='en'):
    """
    Get list of units for a given department or section in the specified language

    Args:
        department_name (str): Department name (in either language)
        section_name (str, optional): Section name within the department (in either language)
        language (str): Language code ('en' or 'az')

    Returns:
        list: List of unit names in the specified language, or empty list if not found
    """
    # Get department key
    dept_key = get_department_key(department_name)
    if not dept_key:
        return []

    dept_data = ORGANIZATIONAL_STRUCTURE.get(dept_key, {})
    lang_key = 'name_en' if language == 'en' else 'name_az'

    if section_name:
        # Get units from specific section
        section_key = get_section_key(department_name, section_name)
        if not section_key:
            return []

        sections = dept_data.get("sections", {})
        section_data = sections.get(section_key, {})
        units = section_data.get("units", [])
        return [unit[lang_key] for unit in units]
    else:
        # Get direct units under department
        units = dept_data.get("units", [])
        return [unit[lang_key] for unit in units]

# Legacy support - keep DEPARTMENTS for backward compatibility
DEPARTMENTS = get_departments('en')