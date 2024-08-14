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
    set PYTHON_CMD="%PYTHONPATH%\python.exe"
)

echo %PYTHON_CMD%

REM Create a virtual environment named "venv"
%PYTHON_CMD% -m venv "%CUR_DIR%\..\..\.venv"

echo Activating the created environment.

REM Activate the virtual environment
call "%CUR_DIR%\..\..\.venv\Scripts\activate"

echo Installing all required dependencies.

REM Install the required packages from requirements.txt
pip install -r "%CUR_DIR%\..\requirements.txt

REM Navigate to the "python_scripts" child folder
cd "%CUR_DIR%\python_scripts"

echo Creating a fernet key and salt string.

REM Run the first Python script
%PYTHON_CMD% generate_fernet_key.py

REM Run the second Python script
%PYTHON_CMD% generate_salt_string.py

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
if /I "%confirm%" NEQ "yes" (
    echo Operation canceled by the user.
    exit /b 0
)

REM Create a new PostgreSQL database
echo Creating new PostgreSQL database...
"%PGADMIN_PATH%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d postgres -c "CREATE DATABASE %PGDATABASE%;"

pause

REM Run the SQL file to create schemas
echo Running the SQL file to create schemas...
"%PGADMIN_PATH%\psql" -U %PGUSER% -h %PGHOST% -p %PGPORT% -d %PGDATABASE% -f %SQL_FILE_PATH%

pause

echo You are all set. All that is left is:

echo (1) Creating a superuser: You can do this is a shell with activated environment.

echo Run the following code from the BRO-connector folder. 

echo .venv\Scripts\activate

echo This activates the virtual environment.

echo python manage.py createsuperuser

echo Then you are instructed on how to create an user.

pause

echo (2) Adjust the database to fit the current state of the app. Run the following code:

echo python manage.py makemigrations bro tools gmw gld gmn folder

echo python manage.py migrate

echo If anything fails make sure you are in the right folder, and have the virtual environment activated.

echo Goodluck!

pause