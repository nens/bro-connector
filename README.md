<p align="center"><img src=bro_connector/static/img/broconnector.png width="320"></p>

# BRO-connector
- De BRO-connector is een maatwerk Django applicatie voor de aanlevering van grondwatergegevens naar de BRO, ontwikkeld in samenwerking met de Provincie Zeeland
- Deze applicatie bevat ook een validatiemodule DataLens voor het beoordelen van de tijdreeksen volgens het QC Protocol.
- De BRO-connector ondersteunt de geautomatiseerde periodieke datalevering van het registratieobject GLD (grondwaterstanden). Momenteel wordt gewerkt de uitbreiding met het berichtenverkeer voor GMW (meetput), GMN (meetnet) en FRD (formatieweerstandonderzoek). Deze komt na verwachting eind 2023 beschikbaar.
- De BRO-connector is voor de Provincie Zeeland aangesloten op een Postgres database waarin het datamodel van de BRO is overgenomen. Bij de installatie wordt het datamodel automatisch gecreëerd. De BRO-connector is in principe ook toepasbaar op andere databases.
- Gebruik requirements.txt om de virtual environment aan te maken waarbinnen de applicatie kan draaien

### Inhoudsopgave 
Deze ReadMe bevat de volgende beschrijvingen:
- [Architectuuur](https://github.com/nens/bro-connector/?tab=readme-ov-file#architectuur)
- [Installatie](https://github.com/nens/bro-connector/?tab=readme-ov-file#installeren-van-django-applicatie-op-server)
- [Screenshots](https://github.com/nens/bro-connector/?tab=readme-ov-file#screenshots)
- [Initialisatie](https://github.com/nens/bro-connector/?tab=readme-ov-file#initialisatie)
- [Automatisch importeren vanuit de BRO uitgifte service](https://github.com/nens/bro-connector/?tab=readme-ov-file#automatisch-importeren-vanuit-de-bro-uitgifte-service)
- [HTTPS verbinding opzetten voor je applicatie](https://github.com/nens/bro-connector/?tab=readme-ov-file#https-verbinding-opzetten-voor-je-applicatie)
- [Standaard opzet van een brodomein-app](https://github.com/nens/bro-connector/?tab=readme-ov-file#standaard-opzet-van-een-brodomein-app)
- [Instellen van BRO Tokens voor meerdere organisaties](https://github.com/nens/bro-connector/?tab=readme-ov-file#instellen-van-bro-tokens-voor-meerdere-organisaties)
- [Dataverwerking naar de BRO](https://github.com/nens/bro-connector/?tab=readme-ov-file#dataverwerking-naar-de-bro)

## Architectuur

TODO: toevoegen architectuurplaat incl. datastromen

## Installeren van Django applicatie
Voor de installatie van de BRO-connector zijn er twee opties. Voor een standaard installatie is deze uit te voeren via het script in de folder bro_connector\installation_help\install.cmd. Daarnaast kun je ook handmatige de installatie via een drietal stappen doorlopen waardoor je als gebruiker meer controle hebt over de procedure.
1. Clone 'bro-connector' naar een computer of (virtuele) server
2. Installeer een python virtual environment vanuit 'requirements.py' met Python versie 3.11
    - Voor het aanmaken en leveren van requests wordt het softwarepakket 'bro-exchange' gebruikt, voor meer informatie zie repo: https://github.com/nens/bro-exchange/. Dit pakket wordt automatisch geïnstalleerd vanuit de requirements.
    ```pip install -r requirements.txt```
3. Configureer de applicatie
    - Maak een database aan met postgis extensie (minimaal PostGIS 3.4)
    - Zorg dat er een schema 'django_admin' in de postgres database staat, hierin komen de admin tabellen (deze zitten niet in de database backup).
    - Specifieke instellingen staan in de main/localsecret.py. Hiervoor is een template toegevoegd (main/localsecret_template.py) Daarin staan de settings gedefiniëerd voor een productieomgeving, stagingomgeving of development omgeving en het type omgeving
    - Initialiseer de admin tabellen voor django door vanuit de folder bro_connector met de volgende commando's te draaien: 
    ```
    python manage.py makemigrations bro tools gmw gld gmn frd
    python manage.py migrate 
    ```
    - De overige tabellen staan al in de database, maar moeten nog gesynchroniseerd worden met de django applicatie.
    - Draai eerst 'python manage.py makemigrations' en vervolgens 'python manage.py migrate' (of python manage.py migrate --fake wanneer stap 3 is uitgevoerd).
    - Maak een superuser met 'python manage.py createsuperuser' .

## Screenshots
<img src=bro_connector/static/img/bro_connector_dashboard.PNG>

<img src=bro_connector/static/img/bro_connector_gld_log.PNG>

## Initialisatie
Na de installatie kun je de applicatie initialiseren zodat je direct alle data uit de BRO beschikbaar hebt in je eigen lokale omgeving. Hiervoor kun je de volgende stappen uitvoeren:
 - Instellen bounding box voor je organisatie (optioneel)
 - Importeer data via Tools --> BRO Importer vanuit de uitgifte service voor een BRO-registratieobject
 -     gmw, frd, gld, gmn
 - organisatie instellen
 - accounts instellen voor gebruikers
 - project aanmaken voor aanlevering

## Automatisch importeren vanuit de BRO uitgifte service
Het is mogelijk om data automatisch uit de BRO te importeren naar je lokale database. Hiervoor is een script ontwikkeld wat aangestuurd kan worden met het .bat bestandje 'bro_gegevens_ophalen.bat'.
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

## Standaard opzet van een brodomein-app
Binnen de BRO-Connector worden momenteel 4 van de 5 BRO-registratieobjecten ondersteund: GMW, GLD, GMN en FRD. Voor ieder van deze registratieobjecten is een aparte Django sub-app ingericht, te vinden in de gelijknamig mapjes.
Tijdens de ontwikkeling van de applicatie is een poging gedaan om de sub-apps op eenzelfde wijze in te richten, om zo het gebruiksgemak te verhogen.

De meeste acties zullen plaats vinden onder het object wat aan de basis ligt van de andere objecten.
Dit is als volgt, [app, object]: GMW, Grondwatermonitoring Put - Statisch; GLD, Grondwaterstand Dossier; GMN, Grondwatermeetnet; FRD, Formatieweerstand Dossier.

Vanuit deze objecten kunnen berichten naar de BRO worden opgestuurd door middel van acties.
Zodra de actie is uitgevoerd, is de voortgang van het versturen van berichten tevinden onder de relevante (synchronisatie) "logs".

## Instellen van BRO Tokens voor meerdere organisaties
Het is noodzakelijk om gebruik te maken van de BRO authenticatie tokens wanneer er gegevens opgestuurd moeten worden naar de BRO. De BRO-Connector bied de mogelijkheid om BRO tokens op te slaan onder de relevante partij.
De tokens worden versleuteld opgeslagen in de database en na de eerste invoer verborgen. 
Op deze manier kan niemand met toegang tot de app of database eenvoudig de tokens inzien, terwijl de app wel blijft functioneren.

Om dit te bereiken maakt de BRO-Connector gebruik van salting en Fernet-encryptie. Daarom moeten tijdens de installatie twee omgevingsvariabelen worden aangemaakt: FERNET_ENCRYPTION_KEY en SECURE_STRING_SALT. De waarden van deze variabelen kun je zelf genereren, maar ze worden ook automatisch gegenereerd door de Python-scripts die worden uitgevoerd tijdens install.cmd.

## Dataverwerking naar de BRO

Hieronder staan enkele processtappen in detail toegelicht voor het registreren van putgegevens en metingen en het sychroniseren naar de BRO.

### Registreren van een put


### Synchronisatie van de put naar de BRO

### Vastleggen van logger en handmetingen

### Synchronisatie van de metingen naar de BRO
