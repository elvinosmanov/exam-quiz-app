# Windows Build Guide for Quiz Examination System

This guide explains how to build a Windows executable (.exe) for the Quiz Examination System.

## ⚠️ Important Note

**You MUST build the Windows executable on a Windows machine.** You cannot create a Windows .exe from macOS or Linux.

## Prerequisites

### 1. Windows Computer
- Windows 10 or Windows 11
- Administrator privileges (for installing Python)

### 2. Python Installation
1. Download Python 3.8 or higher from https://www.python.org/downloads/
2. **IMPORTANT**: During installation, check "Add Python to PATH"
3. Verify installation:
   ```cmd
   python --version
   ```
   Should show: `Python 3.x.x`

### 3. Get the Project Files

**Option A: Copy from macOS/Linux**
1. Create a ZIP of the entire project folder
2. Transfer to Windows machine
3. Extract the ZIP file

**Option B: Using Git (if project is on GitHub)**
```cmd
git clone <your-repository-url>
cd exam-quiz-app
```

**Option C: USB Drive**
1. Copy the entire project folder to USB drive
2. Paste on Windows machine

## Step-by-Step Build Instructions

### Step 1: Open Command Prompt
1. Press `Windows + R`
2. Type `cmd` and press Enter
3. Navigate to project folder:
   ```cmd
   cd C:\path\to\exam-quiz-app
   ```

### Step 2: Create Virtual Environment (Optional but Recommended)
```cmd
python -m venv venv
venv\Scripts\activate
```

You'll see `(venv)` appear in your command prompt.

### Step 3: Install Dependencies

**First, verify pip is working:**
```cmd
pip --version
```

**If you get "pip is not recognized" error, try:**
```cmd
python -m pip --version
```

**Then install dependencies:**
```cmd
pip install -r requirements.txt
```

**Or if pip didn't work above, use:**
```cmd
python -m pip install -r requirements.txt
```

This will install:
- Flet framework
- bcrypt for password security
- pandas, openpyxl for Excel support
- matplotlib for charts
- reportlab for PDF generation
- And other required packages

**Wait for installation to complete** (may take 5-10 minutes).

### Step 4: Initialize Database
```cmd
python test_db.py
```

You should see:
```
Creating tables...
✓ Tables created successfully
Creating default admin user...
✓ Admin user created
Creating system settings...
✓ System settings created
Database initialized at: C:\path\to\exam-quiz-app\quiz_app.db
```

### Step 5: Test the Application (Optional)
Before building, test that the app runs:
```cmd
python main.py
```

- The app window should open
- You should see the login screen with background image
- Login with: **admin** / **admin123**
- If everything works, close the app and proceed to build

### Step 6: Build the Executable
```cmd
python build_exe.py
```

**What happens:**
1. Cleans old build files
2. Runs `flet pack` with proper settings
3. Bundles database and assets
4. Creates executable in `dist` folder

**Build time:** 2-5 minutes depending on your computer

**Expected output:**
```
============================================================
Building Quiz Examination System Executable
============================================================

Cleaning old dist files...
✓ Cleaned dist folder

Building executable...
...
[PyInstaller messages]
...
============================================================
✓ BUILD SUCCESSFUL!
============================================================

Executable location: dist\QuizExamSystem
```

### Step 7: Locate the Executable

After successful build:
```
dist\
├── QuizExamSystem.exe          ← The executable file
├── quiz_app.db                 ← Will be created on first run
└── assets\                     ← Will be created on first run
    └── images\
```

## Testing the Executable

### Quick Test
1. Open File Explorer
2. Navigate to `dist` folder
3. Double-click `QuizExamSystem.exe`
4. The app should open with login screen
5. Login with: **admin** / **admin123**

### Command Line Test (See Debug Messages)
```cmd
cd dist
QuizExamSystem.exe
```

**Look for these messages in the command window:**
```
[CONFIG] Base path: C:\path\to\dist
[CONFIG] Database path: C:\path\to\dist\quiz_app.db
[SETUP] Running as packaged executable
[SETUP] Found bundled database, copying to writable location
[SETUP] Found bundled assets, copying to writable location
```

## Creating Distribution Package

### For Single User
Just copy `QuizExamSystem.exe` to any folder and run it.

### For Multiple Users
Create a distribution folder:

1. Create a folder named `QuizExamSystem_Windows`
2. Copy `dist\QuizExamSystem.exe` into it
3. Create a README.txt with instructions:

```
Quiz Examination System - Windows

Installation:
1. Double-click QuizExamSystem.exe
2. Windows may show a security warning - click "More info" then "Run anyway"
3. Login with:
   Username: admin
   Password: admin123
4. IMPORTANT: Change the admin password after first login!

System Requirements:
- Windows 10 or Windows 11
- 100MB free disk space
- No internet connection required

On first run, the app will:
- Create quiz_app.db (database file)
- Create assets folder (for images)
- These files will be in the same folder as the .exe

Support:
For issues, contact: [your email]
```

4. Create a ZIP file:
   - Right-click the folder
   - Select "Send to" → "Compressed (zipped) folder"

## Troubleshooting

### Problem: "Python is not recognized as a command"
**Solution:**
1. Reinstall Python
2. Make sure to check "Add Python to PATH" during installation
3. Restart Command Prompt after installation

### Problem: "pip install fails with error"
**Solution:**
1. Run Command Prompt as Administrator:
   - Search for "cmd"
   - Right-click "Command Prompt"
   - Select "Run as administrator"
2. Try installing again:
   ```cmd
   pip install -r requirements.txt
   ```

### Problem: "Module not found" error when building
**Solution:**
```cmd
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Problem: Executable doesn't open (no window appears)
**Solution:**
1. Run from command line to see error messages:
   ```cmd
   cd dist
   QuizExamSystem.exe
   ```
2. Check for error messages in the console

### Problem: "Windows protected your PC" warning
**This is normal!** Windows shows this for unsigned executables.

**Solution:**
1. Click "More info"
2. Click "Run anyway"

**To prevent this warning (advanced):**
- Sign the executable with a code signing certificate
- Costs money but makes it look more professional

### Problem: Background image doesn't show
**Solution:**
1. Run executable from command line
2. Look for message: `[SETUP] Found bundled assets`
3. If not found, rebuild:
   ```cmd
   python build_exe.py
   ```
4. Make sure `quiz_app\assets\images\background.png` exists before building

### Problem: Cannot login with admin/admin123
**Solution:**
1. Check if `quiz_app.db` exists in the dist folder after running the exe
2. If missing, the database wasn't bundled correctly
3. Rebuild:
   ```cmd
   python build_exe.py
   ```

### Problem: Build fails with "flet not found"
**Solution:**
```cmd
pip install flet flet-cli
python build_exe.py
```

## Advanced: Customizing the Build

### Change Executable Icon
1. Create or download an `.ico` file
2. Save it as `icon.ico` in project folder
3. Edit `build_exe.py` and add:
   ```python
   '--icon', 'icon.ico',
   ```

### Reduce File Size
The default executable is ~100-150MB. To reduce size:

1. Remove unused dependencies from `requirements.txt`
2. Use `--onefile` mode (already enabled)
3. Consider using UPX compression (advanced)

### Create Installer (Advanced)
Use **Inno Setup** to create a professional installer:

1. Download Inno Setup: https://jrsoftware.org/isdl.php
2. Create an installer script
3. Package the executable with installer

## Distribution Checklist

Before distributing to users:

- [ ] Test executable on a clean Windows machine (not the build machine)
- [ ] Verify login works with admin/admin123
- [ ] Test creating users, exams, and questions
- [ ] Check that data persists after closing and reopening
- [ ] Verify background images display correctly
- [ ] Include README with instructions
- [ ] Include default credentials
- [ ] Warn users to change admin password

## Updating the Executable

When you make code changes:

1. Make changes in development mode
2. Test with: `python main.py`
3. Rebuild executable: `python build_exe.py`
4. Test new executable
5. Distribute new version

**Note:** Users' database files are separate from the executable, so their data will be preserved when they replace the .exe file.

## File Locations After Installation

After a user runs the executable for the first time:

```
C:\Users\Username\Documents\QuizExamSystem\
├── QuizExamSystem.exe          ← The application
├── quiz_app.db                 ← User data (created on first run)
└── assets\                     ← Images (created on first run)
    └── images\
        ├── background.png
        ├── azercosmos-logo.png
        └── ...
```

## Support & Maintenance

### Backup User Data
Tell users to backup these files:
- `quiz_app.db` (contains all users, exams, questions, results)

### Restore Data
To restore data on a new installation:
1. Install/extract the executable
2. Copy the old `quiz_app.db` file to the same folder as the .exe
3. Run the executable

### Database Migration
If you change the database schema:
1. Create migration scripts
2. Include them with the new executable
3. Run migrations automatically on startup

## Additional Resources

- **Flet Documentation**: https://flet.dev/docs/
- **PyInstaller Documentation**: https://pyinstaller.org/
- **Python Windows FAQ**: https://docs.python.org/3/faq/windows.html

## Quick Reference Commands

```cmd
# Install dependencies
pip install -r requirements.txt

# Initialize database
python test_db.py

# Test application
python main.py

# Build executable
python build_exe.py

# Run executable
cd dist
QuizExamSystem.exe
```

## Build Script Explained

The `build_exe.py` script does:

```python
# 1. Checks database exists
# 2. Cleans old build files
# 3. Runs flet pack with:
#    - Database bundling
#    - Assets bundling
#    - Onefile mode (single .exe)
# 4. Creates executable in dist folder
```

## Success Indicators

✅ Build completes without errors
✅ `dist\QuizExamSystem.exe` exists
✅ File size is ~100-150MB
✅ Double-clicking opens the app
✅ Login screen shows with background image
✅ Can login with admin/admin123
✅ All features work normally
✅ Data persists between runs

---

**That's it! You now have a Windows executable of the Quiz Examination System.**

If you encounter any issues not covered in this guide, run the executable from command line and share the error messages for troubleshooting.
