"""
Permission Management System for Unit-Level Isolation

This module provides permission checking and filtering for the expert role system.
Experts can only see and manage content from their own unit (department + unit combination).

Key Features:
- Unit-level content isolation
- Owner-based edit permissions
- Admin override (admins see everything)
- Colleague discovery within same unit
"""

class UnitPermissionManager:
    """
    Manages unit-level permissions for content access and editing

    Permission Rules:
    1. Admin: Full access to all content
    2. Expert: Access to own unit's content only (department + unit match)
    3. Expert: Can only edit own content (not colleagues')
    4. Examinee: No content creation/viewing access
    """

    def __init__(self, db):
        """
        Initialize permission manager

        Args:
            db: Database instance
        """
        self.db = db

    def get_content_query_filter(self, user_data, table_alias=None, created_by_column='created_by'):
        """
        Generate SQL WHERE clause and parameters for filtering content by unit

        This is the core permission filter - use this in ALL content queries
        (exam_assignments, exams, questions, etc.)

        Args:
            user_data (dict): User data with keys: id, role, department, unit
            table_alias (str, optional): Table alias for created_by column (e.g., 'ea', 'e')
            created_by_column (str): Name of the created_by column (default: 'created_by')

        Returns:
            tuple: (where_clause: str, params: list)
                  - where_clause: SQL WHERE clause fragment (e.g., " AND created_by IN (...)")
                  - params: List of parameters for the query

        Examples:
            # Admin - no filter
            >>> get_content_query_filter({'role': 'admin', 'id': 1})
            ("", [])

            # Expert with department and unit
            >>> get_content_query_filter({'role': 'expert', 'id': 2, 'department': 'IT', 'unit': 'Software'})
            (" AND created_by IN (SELECT id FROM users WHERE department = ? AND unit = ?)", ['IT', 'Software'])

            # Expert with table alias
            >>> get_content_query_filter({'role': 'expert', 'id': 2, 'department': 'IT', 'unit': 'Software'}, 'ea')
            (" AND ea.created_by IN (SELECT id FROM users WHERE department = ? AND unit = ?)", ['IT', 'Software'])

            # Expert with custom created_by column
            >>> get_content_query_filter({'role': 'expert', 'id': 2, 'department': 'IT', 'unit': 'Software'}, 'pt', 'created_by_user_id')
            (" AND pt.created_by_user_id IN (SELECT id FROM users WHERE department = ? AND unit = ?)", ['IT', 'Software'])

            # Expert without department/unit (fallback to owner only)
            >>> get_content_query_filter({'role': 'expert', 'id': 2, 'department': None, 'unit': None})
            (" AND created_by = ?", [2])
        """
        role = user_data.get('role')
        user_id = user_data.get('id')
        department = user_data.get('department', '')
        unit = user_data.get('unit', '')

        # Add table alias prefix if provided
        created_by_col = f"{table_alias}.{created_by_column}" if table_alias else created_by_column

        # 1. Admin sees everything - no filter
        if role == 'admin':
            return "", []

        # 2. Expert - filter by department AND unit
        if role == 'expert':
            # If both department and unit are set, filter by unit
            if department and unit:
                return f"""
                    AND {created_by_col} IN (
                        SELECT id FROM users
                        WHERE department = ?
                        AND unit = ?
                        AND is_active = 1
                    )
                """, [department, unit]

            # Fallback: If department or unit missing, show only own content
            return f" AND {created_by_col} = ?", [user_id]

        # 3. Examinee and others - no content access
        return " AND 1=0", []

    def can_edit_content(self, content_owner_id, user_data):
        """
        Check if user can edit specific content

        Rules:
        - Admin: Can edit everything
        - Expert: Can only edit own content
        - Examinee: Cannot edit anything

        Args:
            content_owner_id (int): ID of the content creator
            user_data (dict): Current user data

        Returns:
            bool: True if user can edit, False otherwise

        Examples:
            # Admin can edit anything
            >>> can_edit_content(5, {'role': 'admin', 'id': 1})
            True

            # Expert can only edit own content
            >>> can_edit_content(2, {'role': 'expert', 'id': 2})
            True
            >>> can_edit_content(3, {'role': 'expert', 'id': 2})
            False
        """
        role = user_data.get('role')
        user_id = user_data.get('id')

        # Admin can edit everything
        if role == 'admin':
            return True

        # Expert can only edit own content
        if role == 'expert':
            return content_owner_id == user_id

        # Examinee and others cannot edit
        return False

    def can_create_users(self, user_role):
        """
        Check if user can create new users

        Only admins can create users

        Args:
            user_role (str): User's role

        Returns:
            bool: True if can create users
        """
        return user_role == 'admin'

    def can_view_all_content(self, user_role):
        """
        Check if user can view all content (system-wide)

        Only admins have this privilege

        Args:
            user_role (str): User's role

        Returns:
            bool: True if can view all
        """
        return user_role == 'admin'

    def get_unit_colleagues(self, user_data):
        """
        Get list of colleagues in the same unit

        Useful for showing "who else is in my unit" in the dashboard

        Args:
            user_data (dict): User data with department and unit

        Returns:
            list: List of colleague dicts with id, full_name, email, role
                  Empty list if department/unit not set

        Example:
            [
                {'id': 3, 'full_name': 'John Doe', 'email': 'john@example.com', 'role': 'expert'},
                {'id': 4, 'full_name': 'Jane Smith', 'email': 'jane@example.com', 'role': 'expert'}
            ]
        """
        department = user_data.get('department')
        unit = user_data.get('unit')
        user_id = user_data.get('id')

        # Need both department and unit
        if not (department and unit):
            return []

        # Query colleagues in same unit
        colleagues = self.db.execute_query("""
            SELECT id, full_name, email, role
            FROM users
            WHERE department = ?
            AND unit = ?
            AND id != ?
            AND is_active = 1
            ORDER BY full_name
        """, (department, unit, user_id))

        return colleagues if colleagues else []

    def get_user_context_info(self, user_data):
        """
        Get comprehensive context information for a user

        This includes:
        - Department and unit info
        - List of unit colleagues
        - Unit content statistics (assignments, questions)

        Useful for dashboard display

        Args:
            user_data (dict): User data

        Returns:
            dict: Context information with keys:
                  - department: Department name or None
                  - unit: Unit name or None
                  - colleagues: List of colleague dicts
                  - stats: Dict with 'assignments' and 'questions' counts

        Example:
            {
                'department': 'IT Department',
                'unit': 'Software Development',
                'colleagues': [...],
                'stats': {'assignments': 15, 'questions': 120}
            }
        """
        department = user_data.get('department')
        unit = user_data.get('unit')

        # Get colleagues
        colleagues = self.get_unit_colleagues(user_data)

        # Get unit content statistics
        stats = {
            'assignments': 0,
            'questions': 0,
            'exams': 0
        }

        if department and unit:
            # Count assignments created by unit members
            assignment_count = self.db.execute_single("""
                SELECT COUNT(*) as count
                FROM exam_assignments ea
                JOIN users u ON ea.created_by = u.id
                WHERE u.department = ?
                AND u.unit = ?
                AND ea.is_active = 1
            """, (department, unit))

            if assignment_count:
                stats['assignments'] = assignment_count['count']

            # Count questions created by unit members (via exams)
            question_count = self.db.execute_single("""
                SELECT COUNT(*) as count
                FROM questions q
                JOIN exams e ON q.exam_id = e.id
                JOIN users u ON e.created_by = u.id
                WHERE u.department = ?
                AND u.unit = ?
                AND q.is_active = 1
            """, (department, unit))

            if question_count:
                stats['questions'] = question_count['count']

            # Count exams created by unit members
            exam_count = self.db.execute_single("""
                SELECT COUNT(*) as count
                FROM exams e
                JOIN users u ON e.created_by = u.id
                WHERE u.department = ?
                AND u.unit = ?
                AND e.is_active = 1
            """, (department, unit))

            if exam_count:
                stats['exams'] = exam_count['count']

        return {
            'department': department,
            'unit': unit,
            'colleagues': colleagues,
            'stats': stats
        }

    def validate_expert_user(self, user_data):
        """
        Validate that expert user has required department and unit

        Args:
            user_data (dict): User data

        Returns:
            tuple: (is_valid: bool, error_message: str or None)

        Example:
            >>> validate_expert_user({'role': 'expert', 'department': None, 'unit': None})
            (False, 'Expert users must have department and unit assigned')

            >>> validate_expert_user({'role': 'expert', 'department': 'IT', 'unit': 'Software'})
            (True, None)
        """
        if user_data.get('role') != 'expert':
            return True, None

        department = user_data.get('department')
        unit = user_data.get('unit')

        if not department or not unit:
            return False, 'Expert users must have department and unit assigned'

        return True, None


# Convenience functions for common permission checks

def can_user_edit_content(content_owner_id, user_data, db):
    """
    Quick check if user can edit content

    Args:
        content_owner_id (int): Content creator ID
        user_data (dict): Current user data
        db: Database instance

    Returns:
        bool: True if can edit
    """
    manager = UnitPermissionManager(db)
    return manager.can_edit_content(content_owner_id, user_data)

def get_content_filter(user_data, db):
    """
    Quick access to content filter

    Args:
        user_data (dict): User data
        db: Database instance

    Returns:
        tuple: (where_clause, params)
    """
    manager = UnitPermissionManager(db)
    return manager.get_content_query_filter(user_data)

def get_dept_unit_abbreviation(department, section, unit, language='en'):
    """
    Get abbreviation for department/section/unit from config
    Priority: Unit > Section > Department

    Args:
        department (str): Department name (in either language)
        section (str): Section name (in either language) or None
        unit (str): Unit name (in either language) or None
        language (str): Language code ('en' or 'az')

    Returns:
        str: Abbreviation in the specified language, or "N/A" if not found
    """
    from quiz_app.config import ORGANIZATIONAL_STRUCTURE, get_department_key, get_section_key

    if not department:
        return "N/A"

    # Get department key
    dept_key = get_department_key(department)
    if not dept_key:
        return "N/A"

    dept_data = ORGANIZATIONAL_STRUCTURE.get(dept_key, {})
    abbr_key = 'abbr_en' if language == 'en' else 'abbr_az'

    # Priority 1: Check for unit abbreviation
    if unit:
        # Check if unit is in sections
        if section:
            section_key = get_section_key(department, section)
            if section_key:
                sections = dept_data.get("sections", {})
                section_data = sections.get(section_key, {})
                units = section_data.get("units", [])
                for unit_data in units:
                    if unit_data.get('name_az') == unit or unit_data.get('name_en') == unit:
                        return unit_data.get(abbr_key, "N/A")

        # Check if unit is directly under department
        units = dept_data.get("units", [])
        for unit_data in units:
            if unit_data.get('name_az') == unit or unit_data.get('name_en') == unit:
                return unit_data.get(abbr_key, "N/A")

    # Priority 2: Check for section abbreviation
    if section:
        section_key = get_section_key(department, section)
        if section_key:
            sections = dept_data.get("sections", {})
            section_data = sections.get(section_key, {})
            return section_data.get(abbr_key, "N/A")

    # Priority 3: Return department abbreviation
    return dept_data.get(abbr_key, "N/A")

def get_dept_unit_full_name(department, section, unit, language='en'):
    """
    Get full hierarchical name showing department and unit/section
    Format: "Department Name / Unit Name" or "Department Name / Section Name"

    Args:
        department (str): Department name (in either language)
        section (str): Section name (in either language) or None
        unit (str): Unit name (in either language) or None
        language (str): Language code ('en' or 'az')

    Returns:
        str: Full hierarchical name in the specified language, or "N/A" if not found
    """
    from quiz_app.config import ORGANIZATIONAL_STRUCTURE, get_department_key, get_section_key

    if not department:
        return "N/A"

    # Get department key
    dept_key = get_department_key(department)
    if not dept_key:
        return "N/A"

    dept_data = ORGANIZATIONAL_STRUCTURE.get(dept_key, {})
    name_key = 'name_en' if language == 'en' else 'name_az'

    # Get department full name
    dept_full_name = dept_data.get(name_key, "N/A")

    # If unit exists, show "Department / Unit"
    if unit:
        # Check if unit is in sections
        if section:
            section_key = get_section_key(department, section)
            if section_key:
                sections = dept_data.get("sections", {})
                section_data = sections.get(section_key, {})
                units = section_data.get("units", [])
                for unit_data in units:
                    if (unit_data.get('name_az') == unit or
                        unit_data.get('name_en') == unit or
                        unit_data.get('abbr_az') == unit or
                        unit_data.get('abbr_en') == unit):
                        unit_full_name = unit_data.get(name_key, unit)
                        return f"{dept_full_name} / {unit_full_name}"

        # Check if unit is directly under department
        units = dept_data.get("units", [])
        for unit_data in units:
            if (unit_data.get('name_az') == unit or
                unit_data.get('name_en') == unit or
                unit_data.get('abbr_az') == unit or
                unit_data.get('abbr_en') == unit):
                unit_full_name = unit_data.get(name_key, unit)
                return f"{dept_full_name} / {unit_full_name}"

        # If unit not found in config, show with raw unit name
        return f"{dept_full_name} / {unit}"

    # If section exists (but no unit), show "Department / Section"
    if section:
        section_key = get_section_key(department, section)
        if section_key:
            sections = dept_data.get("sections", {})
            section_data = sections.get(section_key, {})
            section_full_name = section_data.get(name_key, section)
            return f"{dept_full_name} / {section_full_name}"

        # If section not found in config, show with raw section name
        return f"{dept_full_name} / {section}"

    # If only department, return department name
    return dept_full_name
