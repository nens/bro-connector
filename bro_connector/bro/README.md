
<img src=../static/img/broconnector.png width="140">

# ClassDiagram voor de overkoepelende BRO objecten #
```mermaid
classDiagram

    class Organisation{
        str name
        int company_number
        str color
        str bro_user
        str bro_token
    }
    class BROProject{
        str name
        int project_number
        Organisation owner
        list[Organisation] authorized
    }
    BROProject ..> "owner" Organisation
    BROProject ..> "authorized" Organisation

```

# BRO

Voor de BRO zijn een aantal objecten overkoepelend.
Deze zijn dus relevant voor meer dan één object type.
Op dit moment onderscheiden we twee objecten:

1. De Organisatie
2. Het Project

## Organisaties

Uitleg over de werking van Organisaties....


## Projecten

Uitleg over de werking van Projecten....
