# bro-provincie-zeeland

- Django applicatie voor de aanlevering van GLD naar de BRO
- Gebruik requirements.txt om de virtual environment aan te maken waarbinnen de applicatie kan draaien (gwmpy moet handmatig nog geinstalleerd worden via pip)

# Restoring the backup database
Voorbeeld voor local databases
pg_dump -p 5433 -h localhost -U postgres gld_zeeland_productie > C:\Users\Emile.deBadts\Downloads\backup.sql
psql -p 5433 -h localhost -U postgres test_restore < C:\Users\Emile.deBadts\Downloads\backup.sql
