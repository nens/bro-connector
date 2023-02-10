
<img src=bro_connector/static/img/broconnector.png width="140">

# BRO-connector

- Django applicatie voor de aanlevering van GLD gegevens naar de BRO, ontwikkeld in samenwerking met de Provincie Zeeland
- Gebruik requirements.txt om de virtual environment aan te maken waarbinnen de applicatie kan draaien

## Installeren van Django applicatie op server

1. Clone 'bro-connector' naar de server

2. Installeer een python virtual environment op de server vanuit 'requirements.py' met python versie 3.8
    - Voor het aanmaken en leveren van requests wordt het pakketje 'bro-exchange' gebruikt, voor meer informatie zie repo: https://github.com/nens/bro-exchange/. Dit pakket wordt automatisch geïnstalleerd vanuit de requirements.

3. Optioneel: restore een backup van de database op de server
    - Backup bestand heet 'test_database_backup.sql', deze bevat gld, gmw en aanlevering schema's + tabellen + test data
    - Zorg dat de user bro de juiste rechten heeft om schema's/tabellen te kunnen verwijderen en opnieuw aan te maken!
    - Draai de command 'psql -p [port] -h localhost -U postgres [your_db] < test_database_backup.sql' met de juiste database en port als 'your_db' en 'port'
    - Zorg dat de nieuwe schema's ook de juiste rechten hebben voor de user bro, anders kan de django applicatie niet bij de data
    - (mocht het nodig zijn, maak een nieuwe backup: 'pg_dump -p [port] -h localhost -U postgres --no-owner --clean [your_db] > test_database_backup.sql')

4. Initialiseer de django applicatie
    - Specifieke instellingen staand in de settings (bro_connector_gld/settings). Daarin staan settings voor een productieomgeving, testomgeving en stagingomgeving
    - Inloggegevens worden opgegeven in localsecret.py. Hiervoor is een template toegevoegd (bro_connector_gld/localsecret_template.py). Note: ga altijd zorgvuldig met inloggegevens om.
    - Geef de juiste databasegegevens op in de settings
    - Stel in de base settings (bro_connector_gld/settings/base.py) de omgeving in onder 'ENVIRONMNENT' (production/test/staging). NOTE: wanneer de production environment wordt gekozen, is de applicatie aangesloten op de productieomgeving van de bronhouderportaal. Bij selectie van test / staging is de applicatie aangesloten op de demo-omgeving van de bronhouderportaal
    - Zorg dat er een schema 'django_admin' in de postgres database staat, hierin komen de admin tabellen (deze zitten niet in de database backup)
    - Zorg dat het default search path voor de database in 'base.py' op 'django_admin' staat (staat goed in de repo)
    - Initialiseer de admin tabellen voor django door 'python manage.py migrate' te draaien
    - De overige tabellen staan al in de database, maar moeten nog gesynchroniseerd worden met de django applicatie
    - Draai eerst 'python manage.py makemigrations' en vervolgens 'python manage.py migrate' (of python manage.py migrate --fake wanneer stap 3 is uitgevoerd)
    - Maak een superuser met 'python manage.py createsuperuser' 

## Screenshots

<img src=bro_connector/static/img/bro_connector_dashboard.PNG>

<img src=bro_connector/static/img/bro_connector_gld_log.PNG>
