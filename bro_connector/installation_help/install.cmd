@echo off
setlocal enabledelayedexpansion

REM ============================================
REM BRO Connector Installation Script
REM ============================================

echo.
echo ============================================
echo BRO Connector Installation
echo ============================================
echo.

set "CUR_DIR=%~dp0"
set "ROOT_DIR=%CUR_DIR%\..\..\"
set "VENV_DIR=%ROOT_DIR%.venv"
set "REQUIREMENTS_FILE=%ROOT_DIR%requirements.txt"
set "GDAL_WHEEL=%CUR_DIR%gdal-3.10.2-cp312-cp312-win_amd64.whl"

REM ============================================
REM Step 1: Python Setup
REM ============================================
echo [Step 1/7] Python Setup
echo.

set /p PYTHONPATH="Enter your Python path (leave empty for system Python): "

if "%PYTHONPATH%"=="" (
    set "PYTHON_CMD=python"
) else (
    set "PYTHON_CMD=%PYTHONPATH%"
)

REM Verify Python installation
echo Verifying Python installation...
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found at specified path.
    echo Please ensure Python is installed and accessible.
    pause
    exit /b 1
)

%PYTHON_CMD% --version
echo.

REM ============================================
REM Step 1.5: Check for uv
REM ============================================
echo Checking for uv...
set "USE_UV=0"
uv --version >nul 2>&1
if not errorlevel 1 (
    echo uv detected! Will use uv for faster installation.
    set "USE_UV=1"
) else (
    echo uv not found. Will use pip for installation.
)
echo.

REM ============================================
REM Step 2: Virtual Environment Creation
REM ============================================
echo [Step 2/7] Creating Virtual Environment
echo.

if exist "%VENV_DIR%" (
    echo WARNING: Virtual environment already exists at %VENV_DIR%
    set /p OVERWRITE="Do you want to recreate it? (yes/no): "
    if /I "!OVERWRITE!" EQU "yes" (
        echo Removing existing virtual environment...
        rmdir /s /q "%VENV_DIR%"
    ) else (
        echo Using existing virtual environment.
        goto :activate_venv
    )
)

echo Creating virtual environment...
if %USE_UV%==1 (
    uv venv "%VENV_DIR%" --python "%PYTHON_CMD%"
) else (
    %PYTHON_CMD% -m venv "%VENV_DIR%"
)
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)
echo Virtual environment created successfully.
echo.

:activate_venv
REM ============================================
REM Step 3: Activate Virtual Environment
REM ============================================
echo [Step 3/7] Activating Virtual Environment
echo.

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment activation script not found.
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate"
echo Virtual environment activated.
echo.

REM ============================================
REM Step 4: Install Dependencies
REM ============================================
echo [Step 4/7] Installing Dependencies
echo.

REM Check if requirements.txt exists
if not exist "%REQUIREMENTS_FILE%" (
    echo ERROR: requirements.txt not found at %REQUIREMENTS_FILE%
    pause
    exit /b 1
)

REM Install GDAL wheel first if it exists
if exist "%GDAL_WHEEL%" (
    echo Installing GDAL from wheel...
    if %USE_UV%==1 (
        uv pip install "%GDAL_WHEEL%"
    ) else (
        pip install "%GDAL_WHEEL%"
    )
    if errorlevel 1 (
        echo WARNING: Failed to install GDAL wheel. Continuing with other dependencies...
    ) else (
        echo GDAL installed successfully.
    )
    echo.
) else (
    echo WARNING: GDAL wheel not found at %GDAL_WHEEL%
    echo You may need to install GDAL manually.
    echo.
)

echo Installing requirements from requirements.txt...
if %USE_UV%==1 (
    uv pip install -r "%REQUIREMENTS_FILE%"
) else (
    pip install -r "%REQUIREMENTS_FILE%"
)
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

REM ============================================
REM Step 5: Patch Third-Party Packages
REM ============================================
echo [Step 5/7] Patching Third-Party Packages
echo.

REM Patch reversion admin.py
set "REVERSION_FILE=%VENV_DIR%\Lib\site-packages\reversion\admin.py"
if exist "%REVERSION_FILE%" (
    echo Patching reversion admin.py...
    powershell -Command "(Get-Content -Path '%REVERSION_FILE%') -replace 'is_hidden\(\)', 'hidden' | Set-Content -Path '%REVERSION_FILE%'"
    
    findstr /c:"hidden" "%REVERSION_FILE%" >nul
    if !errorlevel!==0 (
        echo Reversion patch applied successfully.
    ) else (
        echo WARNING: Reversion patch may have failed.
    )
) else (
    echo WARNING: reversion\admin.py not found. Skipping patch.
)
echo.

REM Patch admin_auto_filters template
set "FILTER_FILE=%VENV_DIR%\Lib\site-packages\admin_auto_filters\templates\django-admin-autocomplete-filter\autocomplete-filter.html"
if exist "%FILTER_FILE%" (
    echo Patching admin_auto_filters template...
    (
        echo {%% load i18n %%}
        echo.
        echo ^<div class="form-group"^>
        echo     {{ spec.rendered_widget }}
        echo ^</div^>
    ) > "%FILTER_FILE%"
    echo Admin auto filters patch applied successfully.
) else (
    echo WARNING: admin_auto_filters template not found. Skipping patch.
)
echo.

REM ============================================
REM Step 6: Generate Security Keys
REM ============================================
echo [Step 6/7] Generating Security Keys
echo.

cd "%CUR_DIR%\python_scripts"

if not exist "generate_fernet_key.py" (
    echo ERROR: generate_fernet_key.py not found.
    pause
    exit /b 1
)

if not exist "generate_salt_string.py" (
    echo ERROR: generate_salt_string.py not found.
    pause
    exit /b 1
)

echo Generating Fernet encryption key...
python generate_fernet_key.py

echo Generating salt string...
python generate_salt_string.py

echo.
echo Security keys generated and saved to parent directory.
echo.

REM Read generated keys
set "FERNET_KEY_FILE=%CUR_DIR%\..\fernet_key.txt"
set "SALT_FILE=%CUR_DIR%\..\salt.txt"

if exist "%FERNET_KEY_FILE%" (
    set /p FERNET_KEY=<"%FERNET_KEY_FILE%"
) else (
    echo WARNING: Fernet key file not found.
    set "FERNET_KEY="
)

if exist "%SALT_FILE%" (
    set /p SALT_STRING=<"%SALT_FILE%"
) else (
    echo WARNING: Salt file not found.
    set "SALT_STRING="
)

REM ============================================
REM Step 7: Database Setup
REM ============================================
echo [Step 7/7] Database Setup
echo.

set /p SETUP_DB="Do you want to set up the PostgreSQL database now? (yes/no): "
if /I not "!SETUP_DB!" EQU "yes" (
    echo Skipping database setup.
    goto :create_localsecret
)

set /p PGUSER="Enter PostgreSQL username (default: postgres): "
if "!PGUSER!"=="" set "PGUSER=postgres"

set /p PGPASSWORD="Enter PostgreSQL password: "
if "!PGPASSWORD!"=="" (
    echo ERROR: PostgreSQL password is required.
    pause
    exit /b 1
)

set /p POSTGRES_VERSION="Enter PostgreSQL version (e.g., 16): "
if "!POSTGRES_VERSION!"=="" (
    echo ERROR: PostgreSQL version is required.
    pause
    exit /b 1
)

set "PGHOST=localhost"
set "PGPORT=5432"
set "PGDATABASE=bro_connector_db"
set "PGADMIN_PATH=C:\Program Files\PostgreSQL\!POSTGRES_VERSION!\bin"
set "SQL_FILE_PATH=%CUR_DIR%\create_schemas.sql"

REM Verify PostgreSQL installation
if not exist "%PGADMIN_PATH%\psql.exe" (
    echo ERROR: PostgreSQL not found at %PGADMIN_PATH%
    echo Please verify the PostgreSQL version and installation path.
    pause
    exit /b 1
)

REM Verify SQL file exists
if not exist "%SQL_FILE_PATH%" (
    echo ERROR: create_schemas.sql not found at %SQL_FILE_PATH%
    pause
    exit /b 1
)

echo.
echo Database Configuration:
echo   Database: !PGDATABASE!
echo   User: !PGUSER!
echo   Host: !PGHOST!
echo   Port: !PGPORT!
echo.

set /p CONFIRM_DB="Proceed with database creation? (yes/no): "
if /I not "!CONFIRM_DB!" EQU "yes" (
    echo Database creation cancelled.
    goto :create_localsecret
)

echo.
echo Creating database...
"%PGADMIN_PATH%\psql" -U !PGUSER! -h !PGHOST! -p !PGPORT! -d postgres -c "CREATE DATABASE !PGDATABASE!;"
if errorlevel 1 (
    echo WARNING: Database creation failed. It may already exist.
) else (
    echo Database created successfully.
)

echo.
echo Creating database schemas...
"%PGADMIN_PATH%\psql" -U !PGUSER! -h !PGHOST! -p !PGPORT! -d !PGDATABASE! -f "%SQL_FILE_PATH%"
if errorlevel 1 (
    echo ERROR: Failed to create schemas.
    pause
    exit /b 1
)
echo Schemas created successfully.
echo.

:create_localsecret
REM ============================================
REM Create localsecret.py Configuration
REM ============================================
echo.
echo Creating localsecret.py configuration file...
echo.

set "LOCALSECRET_FILE=%CUR_DIR%\..\main\localsecret.py"

REM Prompt for optional FTP and API credentials
set /p FTP_IP="Enter FTP IP (optional): "
set /p FTP_USER="Enter FTP username (optional): "
set /p FTP_PASSWORD="Enter FTP password (optional): "
set /p VALIDATION_KEY="Enter Lizard validation key (optional): "

(
    echo # Security Keys - IMPORTANT: Fill these in from generated files
    if defined FERNET_KEY (
        echo FERNET_ENCRYPTION_KEY = "!FERNET_KEY!"
    ) else (
        echo FERNET_ENCRYPTION_KEY = ""  # TODO: Copy from fernet_key.txt
    )
    if defined SALT_STRING (
        echo SALT_STRING = "!SALT_STRING!"
    ) else (
        echo SALT_STRING = ""  # TODO: Copy from salt.txt
    )
    echo.
    echo # Environment: development, staging, or production
    echo GDAL_DLL_VERSION = "" # TODO: Set GDAL_DLL_VERSION (e.g., "309" or "310") depending on installed GDAL
    echo ENV = "development"
    echo DEMO = ENV != "production"
    echo.
    echo # FTP Server Details
    echo ftp_ip = "!FTP_IP!"
    echo ftp_username = "!FTP_USER!"
    echo ftp_password = "!FTP_PASSWORD!"
    echo.
    echo # FTP Paths
    echo ftp_frd_path = "/"
    echo ftp_gld_pmg_path = "/"
    echo ftp_gld_hnm_path = "/"
    echo ftp_gld_path = "/"
    echo ftp_gmw_path = "/"
    echo ftp_gar_path = "/"
    echo.
    echo # Database Name
    if defined PGDATABASE (
        echo database = "!PGDATABASE!"
    ) else (
        echo database = "bro_connector_db"
    )
    echo.
    echo if ENV == "production":
    echo     # Production database settings
    if defined PGUSER (
        echo     user = "!PGUSER!"
        echo     password = "!PGPASSWORD!"
        echo     host = "!PGHOST!"
        echo     port = "!PGPORT!"
    ) else (
        echo     user = "postgres"
        echo     password = ""
        echo     host = "localhost"
        echo     port = "5432"
    )
    echo elif ENV == "staging":
    echo     # Staging database settings
    if defined PGUSER (
        echo     user = "!PGUSER!"
        echo     password = "!PGPASSWORD!"
        echo     host = "!PGHOST!"
        echo     port = "!PGPORT!"
    ) else (
        echo     user = "postgres"
        echo     password = ""
        echo     host = "localhost"
        echo     port = "5432"
    )
    echo else:
    echo     # Development database settings
    if defined PGUSER (
        echo     user = "!PGUSER!"
        echo     password = "!PGPASSWORD!"
        echo     host = "!PGHOST!"
        echo     port = "!PGPORT!"
    ) else (
        echo     user = "postgres"
        echo     password = ""
        echo     host = "localhost"
        echo     port = "5432"
    )
    echo.
    echo # Lizard API Keys
    echo validation_key = "!VALIDATION_KEY!"
) > "%LOCALSECRET_FILE%"

echo Configuration file created at %LOCALSECRET_FILE%
echo.

REM ============================================
REM Final Instructions
REM ============================================
echo.
echo ============================================
echo Installation Complete!
echo ============================================
echo.
echo Next steps:
echo.
echo 1. Review and update configuration:
echo    File: %LOCALSECRET_FILE%
if not defined FERNET_KEY (
    echo    - Add FERNET_ENCRYPTION_KEY from: %FERNET_KEY_FILE%
)
if not defined SALT_STRING (
    echo    - Add SALT_STRING from: %SALT_FILE%
)
echo    - Update FTP and API credentials as needed
echo    - Configure different settings for production/staging if needed
echo.
echo 2. Run Django migrations:
echo    cd "%ROOT_DIR%"
echo    .venv\Scripts\activate
echo    python manage.py makemigrations bro tools gmw gld gmn frd gar
echo    python manage.py migrate
echo.
echo 3. Create a superuser:
echo    python manage.py createsuperuser
echo.
echo 4. Start the development server:
echo    python manage.py runserver
echo.
echo For help, refer to the project documentation.
echo.

pause