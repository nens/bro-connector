
<img src=bro_connector_gld/static/img/broconnector.png width="140">

# BRO-connector

- Django applicatie voor de aanlevering van GLD naar de BRO, ontwikkeld in samenwerking met de Provincie Zeeland
- Gebruik requirements.txt om de virtual environment aan te maken waarbinnen de applicatie kan draaien (bro-exchange moet handmatig nog geinstalleerd worden via pip)

## Installeren van Django applicatie op server

1. Clone 'bro-connecor' naar de server
2. Installeer de python virtual environment op de server vanuit 'requirements.py' met python versie 3.8
- Hierbij moet het pakketje 'bro-exchange' nog los geinstalleerd worden in de environment! Instructies in de repo: https://github.com/nens/bro-exchange/
3. Restore een backup van de database op de server
- Backup bestand heet 'test_database_backup.sq', deze bevat gld, gmw en aanlevering schema's + tabellen + test data
- Zorg dat de user bro de juiste rechten heeft om schema's/tabellen te kunnen verwijderen en opnieuw aan te maken!
- Draai de command 'psql -p 5433 -h localhost -U postgres your_db < test_database_backup.sql' met de juist database als 'your_db'
- Zorg dat de nieuwe schema's ook de juiste rechten hebben voor de user bro, anders kan de django applicatie niet bij de data
- (mocht het nodig zijn, maak een nieuwe backup: 'pg_dump -p 5433 -h localhost -U postgres --no-owner --clean gld_zeeland_productie > test_database_backup.sql')

4. Initialiseer de django applicatie
- Check settings.py en vul de juiste database gegevens in 
- Zorg dat er een schema 'django_admin' in de postgres database staat, hierin komen de admin tabellen (deze zitten niet in de database backup)
- Zorg dat het default search path voor de database in 'settings.py' op 'django_admin' staat (staat goed in de repo)
- Initialiseer de admin tabellen voor django door 'python manage.py migrate' te draaien
- De overige tabellen staan al in de database, maar moeten nog gesynchroniseerd worden met de django applicatie
- Draai eerst 'python manage.py makemigrations' en vervolgens 'python manage.py migrate --fake' 
- Maak een superuser met 'python manage.py createsuperuser' 


