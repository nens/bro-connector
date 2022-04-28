# BRO GLD Module Provincie Zeeland

- Django applicatie voor de aanlevering van GLD naar de BRO
- Gebruik requirements.txt om de virtual environment aan te maken waarbinnen de applicatie kan draaien (gwmpy moet handmatig nog geinstalleerd worden via pip)

## Restoring the backup database
Voorbeeld voor local databases
- Backup bestand heet 'test_database_backup.sq', deze bevat gld, gmw en aanlevering schema's + tabellen + data
- psql -p 5433 -h localhost -U postgres your_db < test_database_backup.sql

Nieuwe backup maken:
- - pg_dump -p 5433 -h localhost -U postgres --no-owner --clean gld_zeeland_productie > test_database_backup.sql
