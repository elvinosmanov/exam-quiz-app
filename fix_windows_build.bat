@echo off
echo ========================================
echo Fix Windows Build Issues
echo ========================================
echo.

echo Step 1: Migrating database...
echo ----------------------------------------
python migrate_database.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Database migration failed!
    echo Please check if Python is installed and in PATH.
    pause
    exit /b 1
)

echo.
echo Step 2: Cleaning Python cache files...
echo ----------------------------------------

REM Delete all __pycache__ directories
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM Delete all .pyc files
del /s /q *.pyc 2>nul

REM Delete all .pyo files
del /s /q *.pyo 2>nul

echo Cache cleanup complete!

echo.
echo ========================================
echo All fixes applied successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Rebuild your .exe file using PyInstaller
echo 2. Test the application
echo.
pause
