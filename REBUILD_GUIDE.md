# Step-by-Step Rebuild Guide for Quiz Examination System

## ⚠️ Important Changes Made

The application has been updated to correctly handle paths when packaged as an executable.

### What Was Fixed:
1. **Database path resolution** - Now correctly finds the database in packaged apps
2. **Assets path resolution** - Background images and assets load correctly
3. **Automatic setup** - First run automatically sets up necessary files

## 🔨 Building the Executable

### Step 1: Clean Previous Builds
```bash
rm -rf dist build *.spec
```

### Step 2: Verify Prerequisites
```bash
# Test paths and database
python3 test_paths.py

# You should see all checks pass with green checkmarks (✓)
```

### Step 3: Build the Executable
```bash
# Using the build script (recommended)
python3 build_exe.py

# OR manually
flet pack main.py --name QuizExamSystem --add-data "quiz_app.db:."
```

### Step 4: Locate the Executable
After successful build, find your executable in:
- **macOS**: `dist/QuizExamSystem.app` or `dist/QuizExamSystem`
- **Windows**: `dist/QuizExamSystem.exe`
- **Linux**: `dist/QuizExamSystem`

## 📦 Testing the Executable

### Test in Place (Quick Test)
```bash
# macOS/Linux
cd dist
./QuizExamSystem

# Windows
cd dist
QuizExamSystem.exe
```

### Important: Watch the Console Output
The app will print diagnostic messages like:
```
[CONFIG] Base path: /path/to/executable/directory
[CONFIG] Database path: /path/to/quiz_app.db
[SETUP] Running as packaged executable
[SETUP] Database found at: /path/to/quiz_app.db
```

**If you see errors about missing database:**
1. The database needs to be in the same directory as the executable
2. On first run, it should auto-copy from the bundled database
3. If it fails, manually copy `quiz_app.db` to the dist directory

## 🚀 Creating Distribution Package

### macOS
```bash
# Create distribution folder
mkdir QuizExamSystem_macOS
cp -r dist/QuizExamSystem.app QuizExamSystem_macOS/
cp quiz_app.db QuizExamSystem_macOS/

# Optional: Copy assets if they don't load
cp -r quiz_app/assets QuizExamSystem_macOS/

# Create ZIP for distribution
zip -r QuizExamSystem_macOS.zip QuizExamSystem_macOS/
```

### Windows
```powershell
# Create distribution folder
mkdir QuizExamSystem_Windows
copy dist\QuizExamSystem.exe QuizExamSystem_Windows\
copy quiz_app.db QuizExamSystem_Windows\

# Optional: Copy assets if they don't load
xcopy quiz_app\assets QuizExamSystem_Windows\assets\ /E /I

# Create ZIP for distribution (or use Windows Explorer)
```

## 🔍 Troubleshooting

### Problem 1: "Cannot login with admin/admin123"

**Diagnosis:**
```bash
# In the dist directory, check if database exists
ls -la quiz_app.db

# Check console output when running the app
./QuizExamSystem  # Look for [SETUP] messages
```

**Solutions:**
1. **Database not found**: Copy `quiz_app.db` to the same directory as the executable
   ```bash
   cp ../quiz_app.db ./
   ```

2. **Database corrupted**: Use a fresh database
   ```bash
   cd ..
   python3 test_db.py  # Creates fresh database
   cp quiz_app.db dist/
   ```

3. **Wrong directory**: Make sure `quiz_app.db` is in the **same folder** as the executable

### Problem 2: "Background images not showing"

**Diagnosis:**
Check console output for:
```
[SETUP] Copying assets from bundle
```

**Solutions:**
1. **Assets not bundled**: Make sure `main.py` has:
   ```python
   ft.app(target=main, assets_dir="quiz_app/assets")
   ```

2. **Manual copy**: Copy assets to executable directory
   ```bash
   cp -r quiz_app/assets dist/
   ```

3. **Rebuild with assets**: Rebuild the executable
   ```bash
   python3 build_exe.py
   ```

### Problem 3: "Module not found" or "Import Error"

**Solution:**
Reinstall dependencies and rebuild:
```bash
pip3 install -r requirements.txt
python3 build_exe.py
```

## ✅ Verification Checklist

Before distributing, verify:

- [ ] Executable runs without errors
- [ ] Login with `admin` / `admin123` works
- [ ] Background image shows on login screen
- [ ] Can navigate to admin dashboard
- [ ] Database operations work (create user, create exam, etc.)
- [ ] Console shows correct paths (check [CONFIG] and [SETUP] messages)

## 📝 User Instructions (for distribution)

Include these instructions when distributing:

```
Quiz Examination System - Installation Instructions

1. Extract the ZIP file to a folder on your computer
2. Open the folder and run QuizExamSystem (or QuizExamSystem.exe on Windows)
3. Login with:
   Username: admin
   Password: admin123

4. IMPORTANT: Change the admin password after first login!

System Requirements:
- macOS 10.13+, Windows 10+, or Linux
- 100MB free disk space
- No internet connection required

Troubleshooting:
- If login fails, ensure quiz_app.db is in the same folder as the executable
- On macOS, if blocked by security: System Preferences → Security → Allow
- On Windows, if blocked by SmartScreen: Click "More info" → "Run anyway"
```

## 🔄 Update Process

When you make code changes:

1. Test changes in development mode first
   ```bash
   python3 main.py
   ```

2. Rebuild the executable
   ```bash
   python3 build_exe.py
   ```

3. Test the new executable
   ```bash
   cd dist
   ./QuizExamSystem
   ```

4. If database schema changed, users need a fresh database
   - Include migration instructions
   - Or provide a database update tool
