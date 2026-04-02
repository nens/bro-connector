@echo off
REM ============================================================
REM  add_metadata_to_tvp.bat
REM  Activates the Python virtual environment and runs the
REM  Django management command: add_metadata_to_tvp
REM ============================================================

REM -- CONFIG: adjust these two paths to your project --
set VENV_PATH=C:\path\to\your\venv
set PROJECT_PATH=C:\path\to\your\project

REM -- Activate the virtual environment --
call "%VENV_PATH%\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment at: %VENV_PATH%
    pause
    exit /b 1
)

REM -- Move to the Django project directory --
cd /d "%PROJECT_PATH%"
if errorlevel 1 (
    echo [ERROR] Could not find project directory at: %PROJECT_PATH%
    pause
    exit /b 1
)

REM -- Run the management command --
echo Running: python manage.py write_start_obs
python manage.py write_start_obs
if errorlevel 1 (
    echo [ERROR] Command failed with exit code %errorlevel%
    pause
    exit /b 1
)

echo [OK] write_start_obs completed successfully.

REM -- Run the management command --
echo Running: python manage.py fresh_split_reeks
python manage.py fresh_split_reeks
if errorlevel 1 (
    echo [ERROR] Command failed with exit code %errorlevel%
    pause
    exit /b 1
)

echo [OK] fresh_split_reeks completed successfully.
pause
