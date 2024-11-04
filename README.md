<p align="center"><img src=bro_connector/static/img/broconnector.png width="320"></p>

# BRO-connector
De BRO-connector is een maatwerk Django applicatie voor de aanlevering van grondwatergegevens naar de BRO, ontwikkeld in samenwerking met de Provincie Zeeland. Daarbij bevat de applicatie ook een validatiemodule DataLens voor het beoordelen van de tijdreeksen volgens het QC Protocol. De BRO-connector ondersteunt de geautomatiseerde periodieke datalevering. Het berichtenverkeer is beschikbaar voor de BRO-registratieobjecten GMW (meetput), GMN (meetnet) en FRD (formatieweerstandonderzoek). De BRO-connector is voor de Provincie Zeeland aangesloten op een PostgreSQL database waarin het datamodel van de BRO op hoofdlijnen overgenomen is. De BRO-connector is in principe ook toepasbaar op andere databases. Deze beschrijving bevat informatie over de technische architectuur, de installatie en initialisatie van de applicatie binnen je eigen organisatie, en natuurlijk het gebruik van deze beheeromgeving voor je grondwatergegevens.

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
Hieronder staat de globale architectuur van de BRO-connector weergegeven. De applicatie is zowel lokaal als op een server te installeren. Dit laatste is aan te raden voor een productieomgeving, waarbij de applicatie is ontwikkeld voor een Windows-omgeving als zal deze onder voorbehoud ook draaien op ene Linux server. De applicatie is ontwikkeld in Django, een webframework voor Python en maakt gebruikt van een PostgreSQL database voor de opslag. De webserver is via een https verbinding op te zetten zodat gebruikers vanaf hun computer de gegevens via een browser kunnen raadplegen. Daarnaast maakt de applicatie verbinding met het bronhouderportaal van de BRO voor het ophalen en toesturen van gegevens.
<img src=bro_connector/static/img/architectuur.png width="720">

## Installeren van Django applicatie
Voor de installatie van de BRO-connector zijn er twee opties. Voor een standaard installatie is deze uit te voeren via het script in de folder bro_connector\installation_help\install.cmd. Daarnaast kun je ook handmatige de installatie via een drietal stappen doorlopen waardoor je als gebruiker meer controle hebt over de procedure.
1. Clone 'bro-connector' naar een computer of (virtuele) server
2. Installeer een python virtual environment vanuit 'requirements.py' met Python versie 3.11
    - Voor het aanmaken en leveren van requests wordt het softwarepakket 'bro-exchange' gebruikt, voor meer informatie zie repo: https://github.com/nens/bro-exchange/. Dit pakket wordt automatisch geïnstalleerd vanuit de requirements.
    ```pip install -r requirements.txt```
3. Configureer de applicatie
    - Maak een database aan met postgis extensie (minimaal Postgresql 13 met PostGIS 3.4)
    - Maak een schema 'django_admin' in de postgres database aan, hierin komen de admin-tabellen.
    - Specifieke instellingen staan in de main/localsecret.py. Hiervoor is een template toegevoegd (main/localsecret_template.py) Daarin staat gedefiniëerd of het een productieomgeving, stagingomgeving of development omgeving betreft incl. settings en aanvullende keys. Voor het aanmaken van een Fernet en Salt key kunnen de scripts in bro_connector\installation_help\python_scripts uitgevoerd worden.
    - Initialiseer de admin tabellen voor django door vanuit de folder bro_connector met de volgende commando's te draaien: 
    ```
    python manage.py makemigrations bro tools gmw gld gmn frd
    python manage.py migrate 
    ```
    - De overige tabellen staan al in de database, maar moeten nog gesynchroniseerd worden met de django applicatie.
    - Draai eerst 'python manage.py makemigrations' en vervolgens 'python manage.py migrate' (of python manage.py migrate --fake wanneer stap 3 is uitgevoerd).
    - Maak een superuser met 'python manage.py createsuperuser' .

## Screenshots
<img src=screenshots/bro_connector_login_screen.png>

<img src=screenshots/bro_connector_dashboard_overview.png>

<img src=bro_connector/static/img/bro_connector_gld_log.PNG>

<img src=screenshots/bro_connector_GMW_map_zeeland.png>

<img src=screenshots/20241104_MeetopstellingVisualisatie.png>

<img src=screenshots/bro_connector_GMW_Datalens_overview.png>

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
Voor de registratie van een nieuwe put en synchronisatie naar de BRO verloopt het proces via de volgende stappen:
1. Ga in de linkertab naar "GMW" en selecteer de tabel "Grondwatermonitoring Putten - Statisch". 
2. Klik op "Add Grondwatermonitoring Put - Statisch" en vul de benodigde kenmerken in. Voor de aanlevering naar de BRO selecteer ook de optie "Deliver gmw to bro", anders is de put enkel beheerd binnen de lokale omgeving van de BRO-connector
3. Vul eventueel ook dynamische informatie over de put in via de tabel "Grondwatermonitoring Putten - Dynamisch" en informatie over de filters op een identieke wijze in de overige tabellen van het "GMW" domein. Al deze tabellen zijn gerelateerd aan elkaar en de relatie met andere tabel (bijv. put) is zichtbaar in het bovenste veld van de tabellen.

### Synchronisatie van de put naar de BRO
Een geregistreerde put binnen de BRO-connector kan gesynchroniseerd worden naar de BRO door een taak uit te voeren. Daarvoor kan een gebruiker onderstaande taak starten:
1. Voor synchronisatie naar de BRO ga naar "Grondwatermonitoring Putten - Statisch" en selecteer "Deliver GMW to bro" in de actiebalk in de menubalk.

### Vastleggen van logger en handmetingen
De aanlevering van tijdseries van zowel logger als handmetingen verloopt via Observaties. Een Observatie is een set aan waarnemingen (in de BRO bekend als tijdmeetwaardereeks met tijdmeetwaardeparen). Om data op te slaan binnen het BRO model is het volgende nodig:
1. Start een Grondwaterstand Dossier voor een nieuwe reeks.
2. Voer in het Grondwaterstand Dossier menu de actie "Check GLD status from BRO" uit voor het ophalen van bestaande openstaande dossiers voor deze put en controleer status "Fully Delivered".
3. Maak een nieuwe observatie in de tabel Observatie. Indien het observatieproces en observatiemetdata niet bestaan, zorg dat deze eerst aangemaakt worden en vul in bij het observatieproces.
4. Voer waarnemingen in via "Metingen Tijd-Waarde Paren"

### Synchronisatie van de metingen naar de BRO
Voor de aanlevering van een reeks aan waarnemingen aan de BRO dien je de volgende stappen uit te voeren.
1. Sluit de Observatie behorend bij de reeks aan waarnemingen (tijdmeetwaardeparen) via de actie "Close Observation" door binnen de GLD in het menu "Observatie" de gewenste te selecteren en daarna de actie te starten. 
2. Synchroniseer de data via "Grondwaterstand Dossier" door de betreffende GLD aan te klikken en de actie "Deliver GLD to BRO" uit te voeren.
3. Voor het toevoegen van nieuwe waarnemingen kun je een nieuwe observatie aanmaken en daarvoor tijdmeetwaardeparen toevoegen. Deze actie wordt bij de provincie Zeeland automatisch uitgevoerd bij het sluiten van een Observatie zodat de dagelijkse leveringen van nieuwe waarnemingen automatisch op een nieuwe Observatie plaatsvindt.


