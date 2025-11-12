@echo off
REM Build script for Windows - Quiz Examination System
REM Double-click this file to build the executable

echo ============================================================
echo Quiz Examination System - Windows Build Script
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo [1/4] Python found
python --version
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo [2/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created
) else (
    echo [2/4] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [3/4] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed
echo.

REM Check if database exists
if not exist "quiz_app.db" (
    echo Database not found. Creating database...
    python test_db.py
    if errorlevel 1 (
        echo ERROR: Failed to create database
        pause
        exit /b 1
    )
)
echo.

REM Build executable
echo [4/4] Building executable...
python build_exe.py
if errorlevel 1 (
    echo.
    echo ============================================================
    echo BUILD FAILED!
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD SUCCESSFUL!
echo ============================================================
echo.
echo Executable location: dist\QuizExamSystem.exe
echo.
echo To test the executable:
echo   1. Open File Explorer
echo   2. Navigate to the 'dist' folder
echo   3. Double-click QuizExamSystem.exe
echo.
echo Login credentials:
echo   Username: admin
echo   Password: admin123
echo.
echo ============================================================
pause
