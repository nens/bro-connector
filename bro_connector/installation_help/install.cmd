@echo off
REM Navigate to the parent directory
echo Starting the installation.

set "CUR_DIR=%~dp0"

set /p PYTHONPATH="Enter your python path (optional): "

echo Using local python installation to create a virtual environment.


REM Set default Python executable based on user input or fallback to system Python
if "%PYTHONPATH%"=="" (
    set PYTHON_CMD="python"
) else (
    set PYTHON_CMD= %PYTHONPATH%
)

echo %PYTHON_CMD%

REM Create a virtual environment named "venv"
%PYTHON_CMD% -m venv "%CUR_DIR%\..\..\.venv"

echo Activating the created environment.

REM Activate the virtual environment
call "%CUR_DIR%\..\..\.venv\Scripts\activate"

echo Installing all required dependencies.

REM Install the required packages from requirements.txt
pip install -r "%CUR_DIR%\..\..\requirements.txt

set FILE_PATH=%CUR_DIR%\..\..\.venv\Lib\site-packages\reversion\admin.py

REM Use PowerShell to replace "is_hidden()" with "hidden" in the file
powershell -Command "(Get-Content -Path '%FILE_PATH%') -replace 'is_hidden\(\)', 'hidden' | Set-Content -Path '%FILE_PATH%'"

pause

REM Check if the replacement was successful
findstr /c:"hidden" "%FILE_PATH%" >nul
if %errorlevel%==0 (
    echo Replacement successful: "is_hidden()" has been changed to "hidden" in %FILE_PATH%.
) else (
    echo Replacement failed or string not found in %FILE_PATH%.
)

REM Define the path to the file that needs modification
set FILE_PATH=%CUR_DIR%\..\..\.venv\Lib\site-packages\admin_auto_filters\templates\django-admin-autocomplete-filter\autocomplete-filter.html

REM Write the new content to the file
(
    echo ^{%% load i18n %%^}
    echo.
    echo ^<div class="form-group"^>
    echo     ^{{ spec.rendered_widget ^}}
    echo ^</div^>
) > "%FILE_PATH%"

REM Navigate to the "python_scripts" child folder
cd "%CUR_DIR%\python_scripts"

echo Creating a fernet key and salt string.

REM Run the first Python script
%PYTHON_CMD% generate_fernet_key.py

REM Run the second Python script
%PYTHON_CMD% generate_salt_string.py

echo The SALT_STRING and FERNET_ENCRYPTION_KEY have to be added to main/localsecret.py

echo Let's create the database for the application.

REM Prompt the user for the PostgreSQL username
set /p PGUSER="Enter PostgreSQL username (default: postgres): "

REM If the user does not provide a username, use "postgres" as the default
if "%PGUSER%"=="" set PGUSER=postgres

REM Prompt the user for the PostgreSQL password
set /p PGPASSWORD="Enter PostgreSQL password (default: postgres): "

REM If the user does not provide a password, use "postgres" as the default
if "%PGPASSWORD%"=="" set PGPASSWORD=postgres

SET PGHOST=localhost
SET PGPORT=5432
SET PGDATABASE=bro_connector_db

set /p POSTGRES_VERSION="Enter your PostgreSQL version: "


SET PGADMIN_PATH=C:\Program Files\PostgreSQL\%POSTGRES_VERSION%\bin

SET SQL_FILE_PATH="%CUR_DIR%\create_schemas.sql"

REM Prompt the user for confirmation to proceed
set /p confirm="Do you want to create the database '%PGDATABASE%' and run the SQL script? (yes/no): "

REM Check the user's response
if /I "%confirm%" EQU "yes" (
    REM Create a new PostgreSQL database
    echo Creating new PostgreSQL database...
    "%PGADMIN_PATH%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d postgres -c "CREATE DATABASE %PGDATABASE%;"

    REM Run the SQL file to create schemas
    echo Running the SQL file to create schemas...
    "%PGADMIN_PATH%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d %PGDATABASE% -f %SQL_FILE_PATH%
)

REM Read values from files
set /p FERNET_KEY=<%CUR_DIR%\fernet_key.txt
set /p SALT_STRING=<%CUR_DIR%\salt.txt

echo "%FERNET_KEY%"
echo "%SALT_STRING%"
echo %CUR_DIR%
pause

REM Create the file with placeholders
(
    echo # Constants and sensitive keys
    echo FERNET_ENCRYPTION_KEY = "%FERNET_KEY%"
    echo SALT_STRING = "%SALT_STRING%"
    echo.
    echo # Environment configuration
    echo env = "development"
    echo.
    echo # FTP server details
    echo ftp_ip = 'ftp.example.com'
    echo ftp_username = 'your_username'
    echo ftp_password = 'your_password'
    echo.
    echo # FTP paths
    echo ftp_frd_path = '/FRD'
    echo ftp_gld_path = '/GLD'
    echo ftp_maintenance_path = '/ONDERHOUD'
    echo ftp_gar_path = '/GAR'
    echo.
    echo # Database name
    echo database = "db_bro_connector"
    echo.
    echo # Database settings based on environment
    echo if env == "production":
    echo    user = ""
    echo    password = ""
    echo    host = ""
    echo    port = ""
    echo elif env == "staging":
    echo    user = ""
    echo    password = ""
    echo    host = ""
    echo    port = ""
    echo else:
    echo    user = "postgres"
    echo    password = "postgres"
    echo    host = "localhost"
    echo    port = "5432"
    echo.
    echo # Lizard keys
    echo validation_key = ""
) > %CUR_DIR%\..\main\localsecret.py

del %CUR_DIR%\salt.txt
del %CUR_DIR%\fernet_key.txt

echo Warning! Currently all settings [production, staging and test] point to the same database. Correct this if wanted in the folder bro_connector/main/localsecret.py

pause

echo You are all set. All that is left is:

echo (1) Adjust the database to fit the current state of the app. Run the following code in a terminal:

echo python manage.py makemigrations bro tools gmw gld gmn frd

echo python manage.py migrate

pause

echo (2) Creating a superuser

echo Run the following code from the bro_connector folder. (with in it all the app folders: gmw, gld and so on...) 

echo ..\.venv\Scripts\activate

echo This activates the virtual environment.

echo python manage.py createsuperuser

echo Then you are instructed on how to create an user.

echo If anything fails make sure you are in the right folder, and have the virtual environment activated.

echo You can start the app by running: 

echo python manage.py runserver

echo Goodluck!

pause