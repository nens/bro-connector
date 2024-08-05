
<img src=bro_connector/static/img/broconnector.png width="140">

# GMN - Grondwatermonitoringsnet

Het Grondwatermonitoringsnet verbind een groep van meetpunten.
Een meetpunt heeft een directe link aan de GMW, hij wijst namelijk naar een Filter.

## Grondwatermonitoringsnet

Het hoofd-object binnen de GMN categorie. Alle andere objecten zijn op een manier terug te leiden naar deze.
Vanuit deze object-groep zijn dan ook de belangrijkste acties beschikbaar:

1. Deliver GMN to BRO: Levert alle relevante gebeurtenissen voor de geselecteerde meetnetten aan de BRO (waar mogelijk).
2. Check GMN Status from BRO: Controleert de status van een put, als er een levering te vinden is in de logs.
3. Generate FieldForm: Genereerd een locaties bestand voor de FieldForm mobiele-app. FTP-instellingen noodzakelijk.
4. Delete selected: Standaard functionaliteit binnen Django om meerdere entiteiten te verwijderen.