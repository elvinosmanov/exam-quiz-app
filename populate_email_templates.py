#!/usr/bin/env python3
"""
Script to populate email templates in existing database
Run this to add default email templates without reinitializing the entire database
"""

import sys
import os

# Add the parent directory to path so we can import quiz_app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quiz_app.database.database import populate_email_templates

if __name__ == "__main__":
    print("=" * 60)
    print("Email Templates Population Script")
    print("=" * 60)
    print()

    try:
        populate_email_templates()
        print()
        print("=" * 60)
        print("✓ Success! Email templates have been populated.")
        print("=" * 60)
        print()
        print("You can now:")
        print("  1. Go to Admin → Settings → Email Templates")
        print("  2. View and customize the default templates")
        print("  3. Send emails after exam completion")
        print()
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Error: {e}")
        print("=" * 60)
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)
