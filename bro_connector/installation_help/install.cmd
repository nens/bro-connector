@echo off
REM Navigate to the parent directory
cd ..

echo Starting the installation.

echo Using local python installation to create a virtual environment.

REM Create a virtual environment named "venv"
python -m venv ..\.venv

echo Activating the created environment.

REM Activate the virtual environment
call ..\.venv\Scripts\activate

echo Installing all required dependencies.

REM Install the required packages from requirements.txt
pip install -r requirements.txt

REM Navigate to the "python_scripts" child folder
cd .\installation_help\python_scripts

echo Creating a fernet key and salt string.

REM Run the first Python script
python generate_fernet_key.py

REM Run the second Python script
python generate_salt_string.py

echo All done!

REM Deactivate the virtual environment
deactivate

pause