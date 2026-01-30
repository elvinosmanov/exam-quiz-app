import sqlite3
import tempfile
import unittest
from pathlib import Path

from quiz_app.database.database import Database


class TestSchemaEnforcement(unittest.TestCase):
    """Regression tests for ensuring preset template schema columns exist."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'test.db'
        self._bootstrap_legacy_schema()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _bootstrap_legacy_schema(self):
        """Create a legacy schema missing the is_active column."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exam_preset_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_by_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

    def test_adds_missing_is_active_column(self):
        """ensure_column_exists should add the column when it is absent."""
        db = Database(db_path=str(self.db_path))

        added = db.ensure_column_exists(
            'exam_preset_templates',
            'is_active',
            'BOOLEAN DEFAULT 1'
        )

        self.assertTrue(added, 'Column addition should return True when ALTER TABLE runs')
        self.assertIn(
            'is_active',
            self._get_columns(),
            'Schema should include the newly added column'
        )

    def test_is_active_column_addition_is_idempotent(self):
        """Calling ensure_column_exists twice should only alter schema once."""
        db = Database(db_path=str(self.db_path))
        first_run = db.ensure_column_exists(
            'exam_preset_templates',
            'is_active',
            'BOOLEAN DEFAULT 1'
        )
        second_run = db.ensure_column_exists(
            'exam_preset_templates',
            'is_active',
            'BOOLEAN DEFAULT 1'
        )

        self.assertTrue(first_run, 'First ensure call should perform alteration')
        self.assertFalse(second_run, 'Second ensure call should no-op')
        self.assertIn('is_active', self._get_columns())

    def _get_columns(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(exam_preset_templates)')
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns


if __name__ == '__main__':
    unittest.main()







