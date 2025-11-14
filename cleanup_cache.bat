@echo off
echo Cleaning Python cache files...

REM Delete all __pycache__ directories
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

REM Delete all .pyc files
del /s /q *.pyc

REM Delete all .pyo files
del /s /q *.pyo

echo Cache cleanup complete!
pause
