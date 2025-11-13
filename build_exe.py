#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build script for creating executable of Quiz Examination System
"""
import os
import subprocess
import shutil
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def build_executable():
    """Build the executable using flet pack"""

    print("=" * 60)
    print("Building Quiz Examination System Executable")
    print("=" * 60)

    # Ensure database exists
    if not os.path.exists('quiz_app.db'):
        print("\n⚠️  Database not found. Running initialization...")
        subprocess.run([sys.executable, 'test_db.py'], check=True)
        print("✓ Database initialized")

    # Clean old build files
    for folder in ['dist', 'build']:
        if os.path.exists(folder):
            print(f"\nCleaning old {folder} files...")
            shutil.rmtree(folder)
            print(f"✓ Cleaned {folder} folder")

    # Build command
    # Database and assets will be bundled into the executable
    # At runtime, they'll be extracted to _MEIPASS temporary directory
    cmd = [
        'flet', 'pack', 'main.py',
        '--name', 'QuizExamSystem',
        '--add-data', 'quiz_app.db:.',
        '--add-data', 'quiz_app/assets/images:assets/images',
        '--pyinstaller-options', '--console',  # Enable console window for debugging
    ]

    print("\nBuilding executable...")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✓ BUILD SUCCESSFUL!")
        print("=" * 60)
        print("\nExecutable location: dist/QuizExamSystem")
        print("\nIMPORTANT: Copy the following to the same directory as the executable:")
        print("  - quiz_app.db (database file)")
        print("  - assets/ folder (if not embedded)")
        print("\n" + "=" * 60)

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("✗ BUILD FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        return False

    return True

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
