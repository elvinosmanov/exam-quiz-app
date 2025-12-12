# Database Development Guide

## 🚨 CRITICAL: How to Add Database Tables & Columns Correctly

### The Problem
Migration files (`migration_*.py`) are NOT included in PyInstaller builds, causing the .exe to fail with "no such table" or "no such column" errors.

### The Solution
**ALWAYS add new tables AND new columns directly to `create_tables()` in `quiz_app/database/database.py`**

### Why Dev Works But .exe Fails
Your development database (`quiz_app.db`) accumulates columns from migrations over time and NEVER gets recreated. The .exe creates a fresh database using ONLY `create_tables()` - missing any columns from migrations!

---

## ✅ Correct Workflow for Adding New Tables

### Step 1: Add Table to `create_tables()` Function

**File**: `quiz_app/database/database.py`

```python
def create_tables():
    # ... existing tables ...

    # Your new table - ADD HERE!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS your_new_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ... rest of function ...
```

### Step 2: Add Indexes (if needed)

In the same function, add indexes before `conn.commit()`:

```python
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_your_table_name ON your_new_table(name)')

    conn.commit()
```

### Step 3: Test Locally **WITH FRESH DATABASE** (CRITICAL!)

```bash
# ⚠️ ALWAYS delete old database before testing!
rm quiz_app.db

# Reinitialize from scratch
python test_db.py

# Run app
python main.py

# Test the exact feature you added
# If it crashes → column is missing from create_tables()
```

**WHY THIS IS CRITICAL**: Your old database has columns from past migrations. If you don't delete it, you'll never catch missing columns until the .exe fails!

### Step 4: Build and Test .exe

```bash
python build_exe.py
# Test the generated .exe
```

---

## ❌ NEVER Do This (Anti-Pattern)

**DON'T create migration files for new tables:**

```python
# ❌ BAD - DON'T DO THIS
# quiz_app/database/migration_add_new_table.py

def migrate():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS new_table (...)
    ''')
```

**Why it fails:**
- Migration files aren't included in PyInstaller build
- .exe can't find the migration file
- Tables never get created
- App crashes with "no such table" error

---

## ✅ When to Use Migration Files

Migration files should ONLY be used for:

### 1. Adding Columns to Existing Tables
```python
# ✅ GOOD - Modifying existing schema
db.execute_update("ALTER TABLE users ADD COLUMN new_field TEXT")
```

### 2. Data Transformations
```python
# ✅ GOOD - One-time data migration
db.execute_update("UPDATE users SET status = 'active' WHERE status IS NULL")
```

### 3. Complex Schema Changes
```python
# ✅ GOOD - Renaming tables, complex refactoring
# Create new table → Copy data → Drop old table
```

---

## 🔍 Checklist Before Adding Any Database Changes

- [ ] **Is this a new table?** → Add to `create_tables()`
- [ ] **Is this a new column?** → Use migration OR add to `create_tables()`
- [ ] **Is this a data transformation?** → Use migration
- [ ] **Did you add indexes?** → Add to `create_tables()`
- [ ] **Did you test with fresh database?** → `rm quiz_app.db && python test_db.py`
- [ ] **Did you test the .exe?** → Build and run

---

## 🚨 Common Mistakes to Avoid

### Mistake 1: Creating Migration for New Table
```python
# ❌ WRONG
# migration_new_feature.py
cursor.execute("CREATE TABLE new_feature (...)")
```
**Fix**: Add directly to `create_tables()` instead

### Mistake 2: Forgetting Indexes
```python
# ❌ WRONG - Table created but no index
CREATE TABLE big_table (...)
```
**Fix**: Always add indexes for foreign keys and frequently queried fields

### Mistake 3: Not Testing Fresh Database
```python
# ❌ WRONG - Only testing with existing database
python main.py  # Works because table already exists
```
**Fix**: Always test with `rm quiz_app.db && python test_db.py`

### Mistake 4: Not Testing .exe Build
```python
# ❌ WRONG - Only testing in development
python main.py  # Works in dev, fails in .exe
```
**Fix**: Always build and test the .exe before pushing

---

## 📋 Development Workflow Summary

```bash
# 1. Add table to create_tables() in database.py
# 2. Delete existing database
rm quiz_app.db

# 3. Reinitialize database
python test_db.py

# 4. Test application
python main.py

# 5. Build .exe
python build_exe.py

# 6. Test .exe
./dist/QuizExamSystem.exe  # Windows
./dist/QuizExamSystem.app  # macOS

# 7. If all works, commit
git add quiz_app/database/database.py
git commit -m "feat: add new_table for feature X"
git push
```

---

## 🎯 Quick Reference

| Task | Method | File |
|------|--------|------|
| Add new table | `create_tables()` | `database.py` |
| Add new column | Migration OR `create_tables()` | `database.py` or `migration_*.py` |
| Add index | `create_tables()` | `database.py` |
| Transform data | Migration | `migration_*.py` |
| Default data | `create_tables()` | `database.py` |

---

## 💡 Why This Architecture?

### PyInstaller Behavior:
- ✅ Includes: Python files imported in main code
- ✅ Includes: Files listed in `hiddenimports`
- ❌ Excludes: Migration files (not imported directly)
- ❌ Excludes: Files discovered at runtime

### Our Solution:
- All tables in `create_tables()` → Always included in .exe
- Migrations only for data changes → Not critical for fresh installs
- `CREATE TABLE IF NOT EXISTS` → Safe for upgrades

---

## 🆘 Troubleshooting

### Error: "no such table: X"
1. Check if table is in `create_tables()` function
2. If not, add it there (not in a migration)
3. Delete `quiz_app.db` and run `python test_db.py`
4. Rebuild .exe

### Error: "table X already exists"
- Use `CREATE TABLE IF NOT EXISTS` (always!)
- Never use `CREATE TABLE` without `IF NOT EXISTS`

### .exe works in dev but fails in production
- Migration files aren't included in build
- Move table creation from migration to `create_tables()`

---

## 📞 Need Help?

If you're unsure whether to use `create_tables()` or a migration:
- **Default choice: Use `create_tables()`**
- Only use migrations if you absolutely need data transformation

When in doubt, put it in `create_tables()` - it's safer for .exe builds!
