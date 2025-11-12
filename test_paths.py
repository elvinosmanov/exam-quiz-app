"""
Test script to verify paths for packaged executable
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quiz_app.config import DATABASE_PATH, UPLOAD_FOLDER, BASE_PATH, DATA_DIR

print("=" * 70)
print("PATH VERIFICATION TEST")
print("=" * 70)

print(f"\n✓ BASE_PATH: {BASE_PATH}")
print(f"✓ DATA_DIR: {DATA_DIR}")
print(f"✓ DATABASE_PATH: {DATABASE_PATH}")
print(f"✓ UPLOAD_FOLDER: {UPLOAD_FOLDER}")

print("\n" + "=" * 70)
print("FILE EXISTENCE CHECK")
print("=" * 70)

# Check database
if os.path.exists(DATABASE_PATH):
    size = os.path.getsize(DATABASE_PATH)
    print(f"✓ Database exists: {DATABASE_PATH} ({size:,} bytes)")
else:
    print(f"✗ Database NOT found: {DATABASE_PATH}")

# Check assets
assets_dir = "quiz_app/assets"
if os.path.exists(assets_dir):
    print(f"\n✓ Assets directory exists: {assets_dir}")

    # List images
    images_dir = os.path.join(assets_dir, "images")
    if os.path.exists(images_dir):
        images = [f for f in os.listdir(images_dir) if not f.startswith('.')]
        print(f"✓ Found {len(images)} image(s):")
        for img in images:
            print(f"  - {img}")
    else:
        print(f"✗ Images directory NOT found: {images_dir}")
else:
    print(f"✗ Assets directory NOT found: {assets_dir}")

# Test database connection
print("\n" + "=" * 70)
print("DATABASE CONNECTION TEST")
print("=" * 70)

try:
    from quiz_app.database.database import Database
    db = Database()

    # Test query
    result = db.execute_single("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
    if result:
        admin_count = result['count']
        print(f"✓ Database connection successful!")
        print(f"✓ Found {admin_count} admin user(s)")

        # Get admin username
        admin = db.execute_single("SELECT username FROM users WHERE role = 'admin' LIMIT 1")
        if admin:
            print(f"✓ Admin username: {admin['username']}")
    else:
        print("✗ Could not query database")

except Exception as e:
    print(f"✗ Database connection failed: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
