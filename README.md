
<img src=bro_connector/static/img/broconnector.png width="140">

# BRO-connector

- Django applicatie voor de aanlevering van grondwatergegevens naar de BRO, ontwikkeld in samenwerking met de Provincie Zeeland
- De BRO-connector ondersteunt de geautomatiseerde periodieke datalevering van het registratieobject GLD (grondwaterstanden). Momenteel wordt gewerkt de uitbreiding met het berichtenverkeer voor GMW (meetput), GMN (meetnet) en FRD (formatieweerstandonderzoek). Deze komt na verwachting eind 2023 beschikbaar.
- De BRO-connector is voor de Provincie Zeeland aangesloten op een Postgres database waarin het datamodel van de BRO is overgenomen. Bij de installatie wordt het datamodel automatisch gecreëerd. De BRO-connector is in principe ook toepasbaar op andere databases.
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

## Data Importeren vanuit de BRO uitgifte service

Het is mogelijk om data uit de BRO te importeren naar je lokale database. <br>
Hiervoor is een script ontwikkeld wat aangestuurd kan worden met het .bat bestandje 'bro_gegevens_ophalen.bat'. <br>
Het script kan als volgt gebruikt worden: bro_gegevens_ophalen.bat [kvk_nummer] [type_bericht]

- kvk_nummer: het kvk nummer van de organisatie waaronder de gegevens staan.
- type_bericht: het type BRO bericht, zoals gmw of gld.

## HTTPS verbinding opzetten voor je applicatie

Om een HTTPS verbinding op te zetten zijn er een aantal stappen noodzakelijk:

1) Voeg SSL settings toe aan base:

```python
CSRF_TRUSTED_ORIGINS = [
    "https://hosting.example.url/",
    "https://hosting.example.url/admin",
]

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

2) Installeer pyOpenSSL (pip install pyOpenSSL)

3) Verkrijg een HTTPS certificaat voor je domein.

4) Splits het certificaat in een .pem en een .key file.*
   
*Als je een .pfx bestand hebt kan je OpenSSL gebruiken om deze te splitsen (https://stackoverflow.com/questions/15413646/converting-pfx-to-pem-using-openssl).

   `openssl pkcs12 -in file.pfx -out file.pem -nodes`
   
   `openssl pkcs12 -in file.pfx -out file.withkey.pem`
   
   `openssl rsa -in file.withkey.pem -out file.key`

   file.pem en file.key gebruiken we uit dit voorbeeld.

6) Draai je server met het runserver_plus command:

   e.g. `runserver_plus hosting.example.url:8000 --cert-file file.pem --key-file file.key`

   In dit voorbeeld draait de server op port 8000.
