#!/usr/bin/env python3
"""
Database Encryption Migration Script
=====================================

This script migrates an existing unencrypted SQLite database to an encrypted SQLCipher database.

IMPORTANT: Run this script ONCE before deploying the encrypted version.

Steps:
1. Backs up the original database
2. Creates a new encrypted database
3. Copies all data from the original to the encrypted database
4. Replaces the original database with the encrypted version

Usage:
    python migrate_to_encrypted_db.py
"""

import os
import shutil
import sqlite3
from datetime import datetime

try:
    from sqlcipher3 import dbapi2 as sqlcipher
    SQLCIPHER_AVAILABLE = True
except ImportError:
    SQLCIPHER_AVAILABLE = False
    print("ERROR: sqlcipher3-wheels is not installed!")
    print("Please run: pip install -r requirements.txt")
    exit(1)

from quiz_app.config import DATABASE_PATH
from quiz_app.database.database import DATABASE_ENCRYPTION_KEY

def migrate_to_encrypted():
    """Migrate existing unencrypted database to encrypted format"""

    # Verify original database exists
    if not os.path.exists(DATABASE_PATH):
        print(f"ERROR: Database not found at {DATABASE_PATH}")
        print("Please run test_db.py first to create the database.")
        return False

    print("=" * 70)
    print("DATABASE ENCRYPTION MIGRATION")
    print("=" * 70)
    print(f"Database: {DATABASE_PATH}")
    print(f"Encryption Key: {'*' * len(DATABASE_ENCRYPTION_KEY)}")
    print()

    # Step 1: Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{DATABASE_PATH}.backup_{timestamp}"
    print(f"[1/5] Creating backup: {backup_path}")
    try:
        shutil.copy2(DATABASE_PATH, backup_path)
        print(f"✓ Backup created successfully")
    except Exception as e:
        print(f"✗ Failed to create backup: {e}")
        return False

    # Step 2: Create encrypted database
    encrypted_path = f"{DATABASE_PATH}.encrypted"
    print(f"\n[2/5] Creating encrypted database: {encrypted_path}")
    try:
        # Remove if exists
        if os.path.exists(encrypted_path):
            os.remove(encrypted_path)

        # Create new encrypted database
        conn_encrypted = sqlcipher.connect(encrypted_path)
        conn_encrypted.execute(f"PRAGMA key='{DATABASE_ENCRYPTION_KEY}'")
        conn_encrypted.execute("PRAGMA cipher_page_size=4096")  # Performance optimization
        conn_encrypted.execute("PRAGMA kdf_iter=256000")  # Security hardening

        # Test the encrypted connection
        conn_encrypted.execute("CREATE TABLE test (id INTEGER)")
        conn_encrypted.execute("DROP TABLE test")
        conn_encrypted.commit()
        print(f"✓ Encrypted database created successfully")
    except Exception as e:
        print(f"✗ Failed to create encrypted database: {e}")
        if os.path.exists(encrypted_path):
            os.remove(encrypted_path)
        return False

    # Step 3: Copy data from original to encrypted
    print(f"\n[3/5] Copying data from original to encrypted database")
    try:
        # Attach the plain text database
        conn_encrypted.execute(f"ATTACH DATABASE '{DATABASE_PATH}' AS plaintext KEY ''")

        # Get all table names
        tables = conn_encrypted.execute(
            "SELECT name FROM plaintext.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        total_tables = len(tables)
        print(f"   Found {total_tables} tables to migrate")

        # Copy each table
        for idx, (table_name,) in enumerate(tables, 1):
            print(f"   [{idx}/{total_tables}] Copying table: {table_name}")
            conn_encrypted.execute(f"CREATE TABLE main.{table_name} AS SELECT * FROM plaintext.{table_name}")

        # Copy indices
        indices = conn_encrypted.execute(
            "SELECT sql FROM plaintext.sqlite_master WHERE type='index' AND sql IS NOT NULL"
        ).fetchall()

        print(f"   Copying {len(indices)} indices...")
        for (sql,) in indices:
            try:
                conn_encrypted.execute(sql)
            except sqlite3.OperationalError:
                pass  # Index might already exist

        conn_encrypted.commit()
        conn_encrypted.execute("DETACH DATABASE plaintext")
        print(f"✓ Data copied successfully")

    except Exception as e:
        print(f"✗ Failed to copy data: {e}")
        conn_encrypted.close()
        if os.path.exists(encrypted_path):
            os.remove(encrypted_path)
        return False
    finally:
        conn_encrypted.close()

    # Step 4: Verify encrypted database
    print(f"\n[4/5] Verifying encrypted database integrity")
    try:
        conn_test = sqlcipher.connect(encrypted_path)
        conn_test.execute(f"PRAGMA key='{DATABASE_ENCRYPTION_KEY}'")

        # Count tables
        tables = conn_test.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        # Try to read from users table (should exist in any quiz app database)
        users_count = conn_test.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        conn_test.close()
        print(f"✓ Verified {len(tables)} tables, {users_count} users")

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        if os.path.exists(encrypted_path):
            os.remove(encrypted_path)
        return False

    # Step 5: Replace original with encrypted
    print(f"\n[5/5] Replacing original database with encrypted version")
    try:
        # Remove original
        os.remove(DATABASE_PATH)
        # Rename encrypted to original name
        os.rename(encrypted_path, DATABASE_PATH)
        print(f"✓ Database replaced successfully")
    except Exception as e:
        print(f"✗ Failed to replace database: {e}")
        # Try to restore from backup
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, DATABASE_PATH)
            print("✓ Original database restored from backup")
        return False

    print("\n" + "=" * 70)
    print("MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"✓ Original database backed up to: {backup_path}")
    print(f"✓ Database is now encrypted with SQLCipher")
    print(f"✓ Encryption key: {DATABASE_ENCRYPTION_KEY}")
    print("\nIMPORTANT NOTES:")
    print("1. Keep the backup file safe in case you need to recover")
    print("2. The database is now encrypted - DB Browser will show 'encrypted or not a database'")
    print("3. Your application will automatically use the encrypted database")
    print("4. NEVER commit the encryption key to version control!")
    print("=" * 70)

    return True

if __name__ == "__main__":
    print("\n" + "⚠️ " * 15)
    print("WARNING: This script will encrypt your database.")
    print("Make sure you have backed up your data before proceeding.")
    print("⚠️ " * 15 + "\n")

    response = input("Do you want to continue? (yes/no): ")
    if response.lower() == 'yes':
        success = migrate_to_encrypted()
        if not success:
            print("\n✗ Migration failed. Please check the errors above.")
            exit(1)
    else:
        print("Migration cancelled.")
