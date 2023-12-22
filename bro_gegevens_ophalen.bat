@echo off

rem Set the path to your virtual environment activate script
set VENV_SCRIPT=.\venv\Scripts\activate

rem Set the path to your Python script
set SCRIPT=import_bro_data

rem Activate the virtual environment
call %VENV_SCRIPT%

rem Run the Python script with two arguments (kvk_number and type)
python manage.py %SCRIPT% --kvk_number %1 --type %2
