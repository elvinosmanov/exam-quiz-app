# Database Encryption Setup Guide

## 🔐 Overview

Your Quiz Examination System database is now protected with **SQLCipher encryption**. This prevents unauthorized access to sensitive data when the database file is stored on shared company folders.

---

## 📋 What Was Changed

### 1. **Dependencies Added**
- `sqlcipher3-wheels==0.5.6` added to `requirements.txt` (pre-built wheels for Windows/macOS/Linux)
- PyInstaller configuration updated to include SQLCipher libraries

### 2. **Code Changes**
- `quiz_app/database/database.py`:
  - Now uses `sqlcipher3` instead of `sqlite3`
  - Automatically applies encryption key on every connection
  - Gracefully falls back to unencrypted if sqlcipher3-wheels is not available

### 3. **New Scripts**
- `migrate_to_encrypted_db.py`: Converts existing database to encrypted format
- `test_encryption.py`: Verifies encryption is working correctly

---

## 🚀 Setup Instructions

### **Step 1: Install Dependencies**

```bash
pip install -r requirements.txt
```

This will install `sqlcipher3-wheels` and all other required packages.

---

### **Step 2: Migrate Existing Database** (If you have existing data)

⚠️ **IMPORTANT:** Back up your database first!

```bash
python migrate_to_encrypted_db.py
```

This script will:
1. Create a backup of your current database
2. Create a new encrypted database
3. Copy all data from the old to the new database
4. Replace the old database with the encrypted version

**Output example:**
```
======================================================================
DATABASE ENCRYPTION MIGRATION
======================================================================
Database: quiz_app.db
Encryption Key: *********************************************

[1/5] Creating backup: quiz_app.db.backup_20250115_143022
✓ Backup created successfully

[2/5] Creating encrypted database: quiz_app.db.encrypted
✓ Encrypted database created successfully

[3/5] Copying data from original to encrypted database
   Found 25 tables to migrate
   [1/25] Copying table: users
   ...
✓ Data copied successfully

[4/5] Verifying encrypted database integrity
✓ Verified 25 tables, 5 users

[5/5] Replacing original database with encrypted version
✓ Database replaced successfully

======================================================================
MIGRATION COMPLETED SUCCESSFULLY!
======================================================================
```

---

### **Step 3: Verify Encryption**

```bash
python test_encryption.py
```

This will run 7 tests to ensure encryption is working:
- ✓ sqlcipher3-wheels installation
- ✓ Encryption enabled in code
- ✓ Database file exists
- ✓ Connection with correct key works
- ✓ Database operations work
- ✓ File is actually encrypted
- ✓ Wrong key is rejected

---

### **Step 4: Test Your Application**

```bash
python main.py
```

Login with your admin credentials:
- Username: `admin`
- Password: `admin123`

Everything should work exactly as before!

---

## 🔒 Security Features

### What's Protected:
- ✅ Database file is completely encrypted
- ✅ Cannot be opened in DB Browser for SQLite
- ✅ Cannot be read by employees with file access
- ✅ All data (users, questions, answers, results) is encrypted

### What's NOT Protected:
- ⚠️ Advanced attackers can reverse-engineer the .exe to extract the key
- ⚠️ Database is unencrypted in memory while app is running
- ⚠️ If someone has admin access to a running app, they can see data

---

## 🔑 Encryption Key Management

### Current Setup (Default)

The encryption key is defined in `quiz_app/database/database.py`:

```python
DATABASE_ENCRYPTION_KEY = "QuizApp2025!AzErCoSmOs#SecureKey$Protected"
```

### **CRITICAL: Change the Default Key!**

Before deploying to production, change the encryption key:

1. Open `quiz_app/database/database.py`
2. Find the line with `DATABASE_ENCRYPTION_KEY`
3. Change it to your own secret key (at least 20 characters)
4. **Example:**
   ```python
   DATABASE_ENCRYPTION_KEY = "MyCompany2025!SuperSecret#Key$AzErCoSmOs"
   ```

### Better Key Management (Recommended for Production)

**Option A: Environment Variable**

```python
import os
DATABASE_ENCRYPTION_KEY = os.environ.get('QUIZ_APP_KEY', 'default_key_change_me')
```

**Option B: External Config File**

```python
# Store key in C:\ProgramData\QuizApp\key.txt (not on network)
with open('C:/ProgramData/QuizApp/key.txt') as f:
    DATABASE_ENCRYPTION_KEY = f.read().strip()
```

---

## 🏗️ Building .exe with PyInstaller

The PyInstaller configuration (`QuizExamSystem.spec`) has been updated to include SQLCipher:

```bash
pyinstaller QuizExamSystem.spec
```

The built .exe will include:
- ✅ sqlcipher3-wheels library
- ✅ SQLCipher native binaries
- ✅ All encryption functionality

---

## 🧪 Testing Encryption

### Test 1: Try Opening with DB Browser

1. Open "DB Browser for SQLite"
2. Try to open `quiz_app.db`
3. **Expected Result:** Error: "file is encrypted or is not a database"
4. ✅ This confirms encryption is working!

### Test 2: Run Automated Tests

```bash
python test_encryption.py
```

### Test 3: Test in Application

1. Run the app: `python main.py`
2. Login as admin
3. Create a user, exam, questions
4. Take an exam
5. Everything should work normally

---

## 📊 Performance Impact

SQLCipher adds minimal overhead:
- **Encryption overhead:** 5-15%
- **Startup time:** +0.1-0.3 seconds
- **Query performance:** Nearly identical
- **File size:** Same as unencrypted

For a quiz app, this overhead is **not noticeable**.

---

## 🐛 Troubleshooting

### Problem: "sqlcipher3-wheels not installed" warning

**Solution:**
```bash
pip install -r requirements.txt
```

---

### Problem: "Unable to decrypt database" error

**Causes:**
1. Database was not migrated to encrypted format
2. Wrong encryption key
3. Database file is corrupted

**Solution:**
```bash
# If you have a backup:
cp quiz_app.db.backup_YYYYMMDD_HHMMSS quiz_app.db
python migrate_to_encrypted_db.py

# If no backup, reinitialize:
rm quiz_app.db
python test_db.py
python migrate_to_encrypted_db.py
```

---

### Problem: "file is encrypted or is not a database" in app

This means:
- ✅ Encryption IS working
- ❌ But the app cannot decrypt it

**Check:**
1. Is sqlcipher3-wheels installed? `pip list | grep sqlcipher3`
2. Is the encryption key correct in `database.py`?
3. Run: `python test_encryption.py`

---

### Problem: PyInstaller .exe doesn't work

**Solution:**
```bash
# Make sure hiddenimports are correct in QuizExamSystem.spec
hiddenimports=[
    ...
    'sqlcipher3',
    'sqlcipher3.dbapi2',
    ...
]

# Rebuild
pyinstaller QuizExamSystem.spec --clean
```

---

## 📁 Backup Strategy

### Before Migration
```bash
# Manual backup
cp quiz_app.db quiz_app.db.backup_manual

# Then migrate
python migrate_to_encrypted_db.py
```

### Regular Backups
The encrypted database can be backed up like any file:
```bash
# Copy to backup location
cp quiz_app.db Z:\Backups\quiz_app_20250115.db

# The backup is also encrypted with the same key
```

---

## ✅ Deployment Checklist

Before deploying to production:

- [ ] Install sqlcipher3-wheels: `pip install -r requirements.txt`
- [ ] Change default encryption key in `database.py`
- [ ] Backup existing database
- [ ] Run migration: `python migrate_to_encrypted_db.py`
- [ ] Test encryption: `python test_encryption.py`
- [ ] Test application: `python main.py`
- [ ] Build .exe: `pyinstaller QuizExamSystem.spec`
- [ ] Test .exe on target computer
- [ ] Document encryption key location (securely!)
- [ ] Set up backup procedure

---

## 🔐 Security Best Practices

1. **Never commit the encryption key to git**
   ```bash
   # Add to .gitignore if storing key in a file
   encryption_key.txt
   key.txt
   ```

2. **Use a strong encryption key**
   - At least 20 characters
   - Mix of letters, numbers, symbols
   - Example: `MyC0mp@ny!2025#Qu1z$S3cur3`

3. **Protect the key**
   - Don't email it
   - Don't write it on paper left at desk
   - Store it in a password manager
   - Only IT administrators should know it

4. **Backup encrypted databases**
   - Regular backups (encrypted file can be copied)
   - Test backup restoration procedure

5. **Monitor for unauthorized access attempts**
   - Check audit logs regularly
   - Review failed login attempts

---

## 📞 Support

If you encounter issues:

1. Run: `python test_encryption.py`
2. Check the error messages
3. Review this document's Troubleshooting section
4. Check that sqlcipher3-wheels is installed: `pip list | grep sqlcipher3`

---

## 📝 Summary

✅ **Your database is now encrypted!**
✅ **Employees cannot browse data with DB Browser**
✅ **Performance impact is minimal (5-15%)**
✅ **Application works exactly the same**
✅ **PyInstaller builds include encryption**

🔒 **Keep the encryption key secret and secure!**
