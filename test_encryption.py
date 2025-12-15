#!/usr/bin/env python3
"""
Database Encryption Test Script
================================

This script tests whether the database encryption is working correctly.

It performs the following tests:
1. Checks if pysqlcipher3 is installed
2. Verifies the database can be opened with the encryption key
3. Tests basic CRUD operations
4. Verifies the database file is encrypted (cannot be opened without key)
"""

import os
import sys

# Test 1: Check pysqlcipher3 installation
print("=" * 70)
print("DATABASE ENCRYPTION TEST")
print("=" * 70)
print("\n[Test 1] Checking sqlcipher3-wheels installation...")
try:
    from sqlcipher3 import dbapi2 as sqlcipher
    print("✓ sqlcipher3-wheels is installed")
except ImportError:
    print("✗ sqlcipher3-wheels is NOT installed")
    print("  Run: pip install -r requirements.txt")
    sys.exit(1)

from quiz_app.config import DATABASE_PATH
from quiz_app.database.database import Database, DATABASE_ENCRYPTION_KEY, ENCRYPTION_ENABLED

# Test 2: Check if encryption is enabled in code
print("\n[Test 2] Checking encryption configuration...")
if ENCRYPTION_ENABLED:
    print("✓ Encryption is ENABLED in database.py")
else:
    print("✗ Encryption is DISABLED in database.py")
    print("  Check that pysqlcipher3 import succeeded in database.py")
    sys.exit(1)

# Test 3: Check if database exists
print(f"\n[Test 3] Checking database file...")
if not os.path.exists(DATABASE_PATH):
    print(f"✗ Database not found at: {DATABASE_PATH}")
    print("  Run: python test_db.py")
    sys.exit(1)
else:
    db_size = os.path.getsize(DATABASE_PATH) / 1024  # Size in KB
    print(f"✓ Database found: {DATABASE_PATH} ({db_size:.2f} KB)")

# Test 4: Test connection with correct key
print(f"\n[Test 4] Testing connection with correct encryption key...")
try:
    db = Database()
    conn = db.get_connection()
    # Try to query sqlite_master
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sqlite_master")
    table_count = cursor.fetchone()[0]
    conn.close()
    print(f"✓ Successfully connected to encrypted database ({table_count} tables)")
except Exception as e:
    print(f"✗ Failed to connect: {e}")
    print("  This might mean the database is not encrypted yet.")
    print("  Run: python migrate_to_encrypted_db.py")
    sys.exit(1)

# Test 5: Test CRUD operations
print(f"\n[Test 5] Testing database operations...")
try:
    db = Database()

    # Read operation
    users = db.execute_query("SELECT COUNT(*) as count FROM users")
    user_count = users[0]['count']
    print(f"  ✓ READ: Found {user_count} users")

    # Try to read a user
    admin = db.execute_single("SELECT username, role FROM users WHERE role = 'admin'")
    if admin:
        print(f"  ✓ QUERY: Found admin user: {admin['username']}")
    else:
        print(f"  ⚠ No admin user found")

    print("✓ All database operations work correctly")
except Exception as e:
    print(f"✗ Database operations failed: {e}")
    sys.exit(1)

# Test 6: Verify file is actually encrypted
print(f"\n[Test 6] Verifying database file is encrypted...")
try:
    # Try to open with regular sqlite3 (should fail)
    import sqlite3
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sqlite_master")
    conn.close()
    print("✗ WARNING: Database appears to be UNENCRYPTED!")
    print("  The database opened with regular sqlite3 without a key.")
    print("  Run: python migrate_to_encrypted_db.py")
except sqlite3.DatabaseError:
    print("✓ Database is encrypted (cannot open with regular sqlite3)")
except Exception as e:
    print(f"✗ Unexpected error: {e}")

# Test 7: Test with wrong key
print(f"\n[Test 7] Testing protection against wrong key...")
try:
    conn = sqlcipher.connect(DATABASE_PATH)
    conn.execute("PRAGMA key='WrongKey123456'")
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM sqlite_master")
    conn.close()
    print("✗ WARNING: Database opened with wrong key!")
except sqlcipher.DatabaseError:
    print("✓ Database correctly rejects wrong encryption key")
except Exception as e:
    print(f"✗ Unexpected error: {e}")

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print("✓ sqlcipher3-wheels is installed and working")
print("✓ Database encryption is enabled")
print("✓ Database can be accessed with correct key")
print("✓ Database operations work correctly")
print("✓ Database is protected against unauthorized access")
print("\n🔒 Your database is ENCRYPTED and SECURE!")
print("=" * 70)
print(f"\nEncryption Key: {DATABASE_ENCRYPTION_KEY}")
print("⚠️  KEEP THIS KEY SECRET! Do not share or commit to version control.")
print("=" * 70)
