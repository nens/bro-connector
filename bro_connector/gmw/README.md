
<img src=../static/img/broconnector.png width="140">

# Klassendiagram voor Grondwatermonitoringsput (GMW) #
```mermaid
classDiagram
    class GroundwaterMonitoringWellStatic{
        int groundwater_monitoring_well_static_id
        str internal_id
        str bro_id
        BROProject project
        Organisation delivery_accountable_party
        Organisation delivery_responsible_party
        str quality_regime
        str under_privilege
        str delivery_context
        str construction_standard
        str initial_function
        str nitg_code
        str olga_code
        str well_code
        int monitoring_pdok_id
        coordinates coordinates
        coordinates coordinates_4236
        str reference_system
        str horizontal_positioning_method
        str local_vertical_reference_point
        float well_offset
        str vertical_datum
        bool in_management
        bool deliver_gmw_to_bro
        bool complete_bro
        date last_horizontal_positioning_date
        coordinates construction_coordinates
    }
    GroundwaterMonitoringWellStatic ..> "is registered in a" BROProject

    class GroundwaterMonitoringWellDynamic{
        int groundwater_monitoring_well_dynamic_id
        GroundwaterMonitoringWellStatic groundwater_monitoring_well_static
        datetime date_from
        str ground_level_stable
        str well_stability
        int owner
        int maintenance_responsible_party
        str well_head_protector
        float ground_level_position
        str ground_level_positioning_method
        str well_head_protector_subtype
        str lock
        str key
        str place
        str street
        str location_description
        str label
        str foundation
        str collision_protection
        str remark
    }
    GroundwaterMonitoringWellDynamic ..> "belongs to a" GroundwaterMonitoringWellStatic

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
    GroundwaterMonitoringTubeStatic ..> "is found in a" GroundwaterMonitoringWellStatic

    class GroundwaterMonitoringTubeDynamic{
        int groundwater_monitoring_tube_dynamic_id
        GroundwaterMonitoringTubeStatic groundwater_monitoring_tube_static
        datetime date_from
        int tube_top_diameter
        str variable_diameter
        str tube_status
        float tube_top_position
        str tube_top_positioning_method
        str tube_packing_material
        str glue
        float plain_tube_part_length
        float inserted_part_diameter
        float inserted_part_length
        str inserted_part_material
    }
    GroundwaterMonitoringTubeDynamic ..> "belongs to a" GroundwaterMonitoringTubeStatic

    class GeoOhmCable{
        int geo_ohm_cable_id
        GroundwaterMonitoringTubeStatic groundwater_monitoring_tube_static
        int cable_number
    }
    GeoOhmCable ..> "is connected to a" GroundwaterMonitoringTubeStatic

    class ElectrodeStatic{
        int electrode_static_id
        GeoOhmCable geo_ohm_cable
        str electrode_packing_material
        str electrode_position
        int electrode_number
    }
    ElectrodeStatic ..> "is part of a" GeoOhmCable

    class ElectrodeDynamic{
        int electrode_dynamic_id
        ElectrodeStatic electrode_static
        datetime date_from
        str electrode_status
    }
    ElectrodeDynamic ..> "belongs to a" ElectrodeStatic

    class Event{
        int change_id
        str event_name
        date event_date
        GroundwaterMonitoringWellStatic groundwater_monitoring_well_static
        GroundwaterMonitoringWellDynamic groundwater_monitoring_well_dynamic
        GroundwaterMonitoringTubeDynamic groundwater_monitoring_tube_dynamic
        ElectrodeDynamic electrode_dynamic
        bool delivered_to_bro
    }
    Event ..> "happens in a" GroundwaterMonitoringWellStatic
    Event ..> "changes" GroundwaterMonitoringWellDynamic
    Event ..> "changes" GroundwaterMonitoringTubeDynamic
    Event ..> "changes" ElectrodeDynamic

    class gmw_registration_log{
        str date_modified
        str bro_id
        str event_id
        str validation_status
        str delivery_id
        str delivery_type
        str delivery_status
        str comments
        str last_changed
        bool corrections_applied
        str quality_regime
        str file
        str process_status
        str object_id_accountable_party
    }

    class Picture{
        int picture_id
        GroundwaterMonitoringWellStatic groundwater_monitoring_well_static
        datetime recording_datetime
        image picture
        str description
    }
    Picture ..> "is created of" GroundwaterMonitoringWellStatic

    class MaintenanceParty{
        int maintenance_party_id
        str surname
        str first_name
        str function
        str organisation
        str adress
        str postal_code
        str place
        int phone
        int mobilephone
        str email
    }

    class Maintenance{
        int maintenance_id
        GroundwaterMonitoringWellStatic groundwater_monitoring_well_static
        GroundwaterMonitoringTubeStatic groundwater_monitoring_tube_static
        date notification_date
        str kind_of_maintenance
        str description
        Picture picture
        MaintenanceParty reporter
        date execution_date
        MaintenanceParty execution_by
    }
    Maintenance ..> "done for a" GroundwaterMonitoringWellStatic
    Maintenance ..> "execution by" MaintenanceParty



    class Organisation{
        str name
        int company_number
        str color
        int bro_user
        int bro_token
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
# GMW - Grondwatermonitoringsput

De Grondwatermonitoringsput is één van de meest belangrijke, en complexe, objecten binnen de BRO.
Eén of meerdere putten zijn nodig voor alle andere object-types binnen het grondwaterdomein van de BRO.

Binnen de BRO-Connector zijn alle relevante objecten die vallen binnen het GMW domein opgenomen.
Voor de attributen die door de tijd heen kunnen verschillen zijn aparte objecten aangemaakt: "statisch" voor de constante* variabelen en "dynamisch" voor flexibele variabelen.

*Er zijn een aantal attributen die op het moment onder de statische sub-groep vallen, die potentieel wel kunnen veranderen. Deze veranderingen gaan gepaard met berichten die op het moment nog niet worden ondersteund in de applicatie, vandaar hun indeling in de app. (Eigenaar, coordinaten -> Dit zijn gegevens die wel mogelijk veranderen of bijgesteld worden.)

## Grondwatermonitorings Put - Statisch

Het hoofd-object binnen de GMW categorie. Alle andere objecten zijn op een manier terug te leiden naar deze.
Vanuit deze object-groep zijn dan ook de belangrijkste acties beschikbaar:

1. Deliver GMW to BRO: Levert alle relevante gebeurtenissen voor de geselecteerde putten aan de BRO (waar mogelijk).
2. Check GMW Status from BRO: Controleert de status van een put, als er een levering te vinden is in de logs.
3. Generate FieldForm: Genereerd een locaties bestand voor de FieldForm mobiele-app. FTP-instellingen noodzakelijk.
4. Delete selected: Standaard functionaliteit binnen Django om meerdere entiteiten te verwijderen.
