# Building Executable for Quiz Examination System

## Quick Build

### Option 1: Using Build Script (Recommended)
```bash
python build_exe.py
```

### Option 2: Manual Build
```bash
flet pack main.py --name QuizExamSystem --add-data "quiz_app/assets:assets" --add-data "quiz_app.db:."
```

## Distribution Package

After building, create a distribution folder with:

```
QuizExamSystem/
├── QuizExamSystem.exe (or QuizExamSystem on Mac/Linux)
├── quiz_app.db
└── assets/
    └── images/
        └── (background images, etc.)
```

## Important Notes

### 1. Database File
- The `quiz_app.db` file MUST be in the same directory as the executable
- The executable will create/use the database in its own directory
- Default admin credentials: `admin` / `admin123`

### 2. Assets Folder
- If images don't load, ensure the `assets` folder is in the same directory as the executable
- The build process should embed assets, but having them available ensures compatibility

### 3. First Run
When distributing to users:
1. Extract all files to a folder
2. Run the executable
3. Login with default credentials
4. Change the admin password immediately

### 4. Platform-Specific Notes

#### Windows
- Executable name: `QuizExamSystem.exe`
- May show security warning on first run (click "More info" → "Run anyway")

#### macOS
- Executable name: `QuizExamSystem`
- May need to allow in System Preferences → Security & Privacy
- Run from Terminal first time: `chmod +x QuizExamSystem && ./QuizExamSystem`

#### Linux
- Executable name: `QuizExamSystem`
- Make executable: `chmod +x QuizExamSystem`
- Run: `./QuizExamSystem`

## Troubleshooting

### Problem: "Cannot login with admin/admin123"
**Solution**:
1. Ensure `quiz_app.db` is in the same directory as the executable
2. If database is missing, copy it from the development folder
3. Or run `test_db.py` to create a fresh database

### Problem: "Background images not showing"
**Solution**:
1. Ensure `assets/images/` folder exists next to the executable
2. Copy the entire `quiz_app/assets` folder to the distribution folder

### Problem: "Module not found" errors
**Solution**: Rebuild with all dependencies installed:
```bash
pip install -r requirements.txt
python build_exe.py
```

## Creating Fresh Database for Distribution

To create a clean database without test data:

```python
# Create a production database
python -c "from quiz_app.database.database import init_database; init_database()"
```

This creates a database with only the default admin user.
