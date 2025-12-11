"""
Migration: Organizational Structure Management
Creates table for storing organizational hierarchy (departments, sections, units)
and migrates existing data from config.py
"""

from quiz_app.config import ORGANIZATIONAL_STRUCTURE


def create_organizational_structure_table(db):
    """Create organizational_structure table"""
    db.execute_update("""
        CREATE TABLE IF NOT EXISTS organizational_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('department', 'section', 'unit')),
            name_az TEXT NOT NULL,
            name_en TEXT NOT NULL,
            abbr_az TEXT NOT NULL,
            abbr_en TEXT NOT NULL,
            parent_key TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_key) REFERENCES organizational_structure(key) ON DELETE CASCADE
        )
    """)
    print("✓ Created organizational_structure table")


def migrate_config_data(db):
    """Migrate organizational structure data from config.py to database"""

    # Check if data already exists
    existing = db.execute_query("SELECT COUNT(*) as count FROM organizational_structure")
    if existing and existing[0]['count'] > 0:
        print("ℹ Organizational structure data already exists in database, skipping migration")
        return

    print("→ Migrating organizational structure from config.py...")

    # Insert departments and their direct units
    for dept_key, dept_data in ORGANIZATIONAL_STRUCTURE.items():
        # Insert department
        db.execute_insert("""
            INSERT INTO organizational_structure (key, type, name_az, name_en, abbr_az, abbr_en, parent_key)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
        """, (
            dept_key,
            dept_data.get('type', 'department'),
            dept_data.get('name_az', ''),
            dept_data.get('name_en', ''),
            dept_data.get('abbr_az', ''),
            dept_data.get('abbr_en', '')
        ))

        # Insert sections under this department
        sections = dept_data.get('sections', {})
        for section_key, section_data in sections.items():
            full_section_key = f"{dept_key}.{section_key}"
            db.execute_insert("""
                INSERT INTO organizational_structure (key, type, name_az, name_en, abbr_az, abbr_en, parent_key)
                VALUES (?, 'section', ?, ?, ?, ?, ?)
            """, (
                full_section_key,
                section_data.get('name_az', ''),
                section_data.get('name_en', ''),
                section_data.get('abbr_az', ''),
                section_data.get('abbr_en', ''),
                dept_key
            ))

            # Insert units under this section
            section_units = section_data.get('units', [])
            for idx, unit_data in enumerate(section_units):
                unit_key = f"{full_section_key}.unit_{idx}"
                db.execute_insert("""
                    INSERT INTO organizational_structure (key, type, name_az, name_en, abbr_az, abbr_en, parent_key)
                    VALUES (?, 'unit', ?, ?, ?, ?, ?)
                """, (
                    unit_key,
                    unit_data.get('name_az', ''),
                    unit_data.get('name_en', ''),
                    unit_data.get('abbr_az', ''),
                    unit_data.get('abbr_en', ''),
                    full_section_key
                ))

        # Insert direct units under this department (not under a section)
        dept_units = dept_data.get('units', [])
        for idx, unit_data in enumerate(dept_units):
            unit_key = f"{dept_key}.unit_{idx}"
            db.execute_insert("""
                INSERT INTO organizational_structure (key, type, name_az, name_en, abbr_az, abbr_en, parent_key)
                VALUES (?, 'unit', ?, ?, ?, ?, ?)
            """, (
                unit_key,
                unit_data.get('name_az', ''),
                unit_data.get('name_en', ''),
                unit_data.get('abbr_az', ''),
                unit_data.get('abbr_en', ''),
                dept_key
            ))

    # Count migrated entries
    result = db.execute_query("SELECT COUNT(*) as count FROM organizational_structure")
    count = result[0]['count'] if result else 0
    print(f"✓ Migrated {count} organizational entries to database")


def run_migration(db):
    """Run the organizational structure migration"""
    print("\n=== Running Organizational Structure Migration ===")

    try:
        create_organizational_structure_table(db)
        migrate_config_data(db)
        print("✓ Organizational structure migration completed successfully\n")
        return True
    except Exception as e:
        print(f"✗ Migration failed: {e}\n")
        return False


if __name__ == "__main__":
    # For testing purposes
    from quiz_app.database.database import Database
    db = Database()
    run_migration(db)
