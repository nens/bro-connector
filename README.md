
<img src=bro_connector/static/img/broconnector.png width="140">

# BRO-connector

- Django applicatie voor de aanlevering van grondwatergegevens naar de BRO, ontwikkeld in samenwerking met de Provincie Zeeland
- De BRO-connector ondersteunt de geautomatiseerde periodieke datalevering van het registratieobject GLD (grondwaterstanden). Momenteel wordt gewerkt de uitbreiding met het berichtenverkeer voor GMW (meetput), GMN (meetnet) en FRD (formatieweerstandonderzoek). Deze komt na verwachting eind 2023 beschikbaar.
- De BRO-connector is voor de Provincie Zeeland aangesloten op een Postgres database waarin het datamodel van de BRO is overgenomen. Bij de installatie wordt het datamodel automatisch gecreëerd. De BRO-connector is in principe ook toepasbaar op andere databases.
- Gebruik requirements.txt om de virtual environment aan te maken waarbinnen de applicatie kan draaien

## Installeren van Django applicatie op server

ARCHITECTUUR-DATA plaatje

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

4. Configureer de django applicatie
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

## Initialisatie voor jouw organisatie

 - Instellen bounding box voor je organisatie (optioneel)
 - Importeer data via Tools --> BRO Importer vanuit de uitgifte service voor een BRO-registratieobject
 -     gmw, frd, gld, gmn
 - organisatie instellen
 - accounts instellen voor gebruikers
 - project aanmaken voor aanlevering

## Automatisch importeren vanuit de BRO uitgifte service

Het is mogelijk om data automatisch uit de BRO te importeren naar je lokale database. <br>
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

## Standaard opzet van een domein-app (GMW, GLD, GMN, FRD)

Binnen de BRO-Connector worden momenteel 4, van de 5, categorieën ondersteund: GMW, GLD, GMN en FRD.
Voor ieder van deze groepen is een aparte Django sub-app ingericht, te vinden in de gelijknamig mapjes.
Tijdens de ontwikkeling van de applicatie is een poging gedaan om de sub-apps op eenzelfde wijze in te richten, om zo het gebruiksgemak te verhogen.

De meeste acties zullen plaats vinden onder het object wat aan de basis ligt van de andere objecten.
Dit is als volgt, [app, object]: GMW, Grondwatermonitoring Put - Statisch; GLD, Grondwaterstand Dossier; GMN, Grondwatermeetnet; FRD, Formatieweerstand Dossier.

Vanuit deze objecten kunnen berichten naar de BRO worden opgestuurd, door middel van acties.
Zodra de actie is uitgevoerd, is de voortgang van het versturen van berichten tevinden onder de relevante (synchronisatie) "logs".

## Omgaan met BRO Tokens

Het is noodzakelijk om gebruik te maken van de BRO authenticatie tokens wanneer er gegevens opgestuurd moeten worden naar de BRO.
De BRO-Connector bied de mogelijkheid om BRO tokens op te slaan onder de relevante partij.
De tokens worden versleuteld opgeslagen in de database en na de eerste invoer verborgen. 
Op deze manier kan niemand met toegang tot de app of database eenvoudig jouw tokens inzien, terwijl de app wel blijft functioneren.

Om dit te bereiken maakt de BRO-Connector gebruik van salting en Fernet-encryptie. Daarom moeten tijdens de installatie twee omgevingsvariabelen worden aangemaakt: FERNET_ENCRYPTION_KEY en SECURE_STRING_SALT. De waarden van deze variabelen kun je zelf genereren, maar ze worden ook automatisch gegenereerd door de Python-scripts die worden uitgevoerd tijdens install.cmd.
