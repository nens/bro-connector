
<img src=bro_connector/static/img/broconnector.png width="140">

# BRO-connector

- Django applicatie voor de aanlevering van GLD naar de BRO, ontwikkeld in samenwerking met de Provincie Zeeland
- Gebruik requirements.txt om de virtual environment aan te maken waarbinnen de applicatie kan draaien

## Installeren van Django applicatie op server

1. Clone 'bro-connecor' naar de server
2. Installeer de python virtual environment op de server vanuit 'requirements.py' met python versie 3.8
 &nbsp;- Voor het aanmaken en leveren van requests wordt het pakketje 'bro-exchange' gebruikt, voor instructies zie repo: https://github.com/nens/bro-exchange/. Dit pakket wordt automatisch geïnstalleerd vanuit de requirements.
3. Optioneel: restore een backup van de database op de server
 &nbsp;- Backup bestand heet 'test_database_backup.sql', deze bevat gld, gmw en aanlevering schema's + tabellen + test data
 &nbsp;- Zorg dat de user bro de juiste rechten heeft om schema's/tabellen te kunnen verwijderen en opnieuw aan te maken!
 &nbsp;- Draai de command 'psql -p [port] -h localhost -U postgres [your_db] < test_database_backup.sql' met de juiste database en port als 'your_db' en 'port'
 &nbsp;- Zorg dat de nieuwe schema's ook de juiste rechten hebben voor de user bro, anders kan de django applicatie niet bij de data
 &nbsp;- (mocht het nodig zijn, maak een nieuwe backup: 'pg_dump -p [port] -h localhost -U postgres --no-owner --clean [your_db] > test_database_backup.sql')

4. Initialiseer de django applicatie
 &nbsp;- Specifieke instellingen zijn in te stellen in de settings (bro_connector_gld/settings). Daarin zijn er apparte settings voor een productieomgeving, testomgeving en stagingomgeving
 &nbsp;- Inloggegevens worden opgegeven in localsecret.py. Hiervoor is een template toegevoegd (bro_connector_gld/localsecret_template.py). Note: ga altijd zorgvuldig met inloggegevens om.
 &nbsp;- Geef de juiste database gegevens op in de settings
 &nbsp;- Stel in de base settings (bro_connector_gld/settings/base.py) de omgeving in onder 'ENVIRONMNENT' (production/test/staging). NOTE: wanneer de production environment wordt gekozen, is de applicatie aangesloten op de productieomgeving van de bronhouderportaal. Bij selectie van test / staging is de applicatie aangesloten op de demo omgeving van de bronhouderportaal
 &nbsp;- Zorg dat er een schema 'django_admin' in de postgres database staat, hierin komen de admin tabellen (deze zitten niet in de database backup)
 &nbsp;- Zorg dat het default search path voor de database in 'base.py' op 'django_admin' staat (staat goed in de repo)
 &nbsp;- Initialiseer de admin tabellen voor django door 'python manage.py migrate' te draaien
 &nbsp;- De overige tabellen staan al in de database, maar moeten nog gesynchroniseerd worden met de django applicatie
 &nbsp;- Draai eerst 'python manage.py makemigrations' en vervolgens 'python manage.py migrate --fake' 
 &nbsp;- Maak een superuser met 'python manage.py createsuperuser' 


