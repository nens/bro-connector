
<img src=../static/img/broconnector.png width="140">

# ClassDiagram voor Groundwatermonitoring Meetnetten (GMN) #
```mermaid
classDiagram
    
    class GroundwaterMonitoringNet{
        int id
        BROProject project
        bool deliver_to_bro
        str gmn_bro_id
        Organisation delivery_accountable_party
        Organisation delivery_responsible_party
        str quality_regime
        str object_id_accountable_party
        str name
        str monitoring_purpose
        str groundwater_aspect
        date start_date_monitoring
        date end_date_monitoring
        bool removed_from_BRO
        str description
    }
    GroundwaterMonitoringNet ..> "is registered in a" BROProject

    class Subgroup{
        GroundwaterMonitoringNet gmn
        str name
        str code
        str description
    }
    Subgroup ..> "is part of a" GroundwaterMonitoringNet
    class MeasuringPoint{
        GroundwaterMonitoringNet gmn
        Subgroup subgroup
        GroundwaterMonitoringTubeStatic groundwater_monitoring_tube
        str code
        date added_to_gmn_date
        date deleted_from_gmn_date
        bool removed_from_BRO_gmn
    }
    MeasuringPoint ..> "is part of a" GroundwaterMonitoringNet
    MeasuringPoint ..> "can belong to a" Subgroup
    MeasuringPoint ..> "refers to a" GroundwaterMonitoringTubeStatic

    class GroundwaterMonitoringTubeStatic{
        int groundwater_monitoring_tube_static_id
        GroundwaterMonitoringWellStatic groundwater_monitoring_well_static
        bool deliver_gld_to_bro
        int tube_number
        str tube_type
        str artesian_well_cap_present
        str sediment_sump_present
        str tube_material
        float screen_length
        str sock_material
        float sediment_sump_length
    }
    class IntermediateEvent{
        GroundwaterMonitoringNet gmn
        MeasuringPoint measuring_point
        str event_type
        date event_date
        bool deliver_to_bro
        bool synced_to_bro
    }
    IntermediateEvent ..> "gmn" GroundwaterMonitoringNet
    IntermediateEvent ..> "measuring_point" MeasuringPoint
    
    class gmn_bro_sync_log{
        date date_modified
        str event_type
        str gmn_bro_id
        str object_id_accountable_party
        str validation_status
        str delivery_id
        str delivery_type
        str delivery_status
        str delivery_status_info
        str comments
        str last_changed
        bool corrections_applied
        datetime timestamp_end_registration
        str quality_regime
        str file
        str process_status
        MeasuringPoint measuringpoint
    }
    
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
```
# Beschrijving #
Onder GMN vind je een CRUD voor de GroundwaterMonitoring Meetnetten, meetpunten en tussentijdse gebeurtenissen.
# Functies #
### Delete selected Groundwater monitoring Meetnetten ###
Deze functie verwijderd alle geselecteerde objecten.
### Deliver GMN to BRO ###
Deze functie verstuurd alle geselecteerde objecten naar BRO.
### Check GMN status from BRO ###
Deze functie haalt de laatste status van de geselecteerde objecten op vanuit BRO en update deze in de lokale database.
# Commando's #
### gmn_create_provinciaal_meetnet ###
Gebruikswijze:
```python gmn_create_provinciaal_meetnet {meetnet_naam}```
Dit commando kan worden gebruikt om een nieuw meetnet op te zetten. Er wordt automatisch gechecked of er al een meetnet bestaat met de opgegeven naam.
### gmn_sync_to_bro ###
Gebruikswijze:
```python python manage.py gmn_sync_to_bro```
Dit commando synchroniseert alle onderliggende objecten naar BRO. Dit commando doet hetzelfde als Deliver GMN to BRO in de CRUD voor GMN objecten.
