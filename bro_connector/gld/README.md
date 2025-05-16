<img src=../static/img/broconnector.png width="140">

# Klassendiagram voor Grondwaterstand dossiers (GLD)

```mermaid
classDiagram
    class GroundwaterLevelDossier{
        int groundwater_level_dossier_id
        GroundwaterMonitoringNet groundwater_monitoring_net
        GroundwaterMonitoringTubeStatic groundwater_monitoring_tube
        str gld_bro_id
        date research_start_date
        date research_last_date
        datetime research_last_correction
    }
    GroundwaterLevelDossier ..> "takes place in a" GroundWaterMonitoringTubeStatic
    GroundwaterLevelDossier ..> "is part of a" GroundwaterMonitoringNet
    class Observation {
        int observation_id
        duration observationperiod
        datetime observation_starttime
        datetime result_time
        datetime observation_endtime
        ObservationMetadata observation_metadata
        ObservationProcess observation_process
        GroundwaterLevelDossier groundwater_level_dossier
        bool up_to_date_in_bro
    }
    Observation ..> "has" ObservationMetadata
    Observation ..> "is completed with" ObservationProcess
    Observation ..> "belongs in a" GroundwaterLevelDossier
    class ObservationMetadata {
        int observation_metadata_id
        date date_stamp
        str observation_type
        str status
        Organisation responsible_party
    }
    class ObservationProcess {
        int observationprocess_id
        str process_reference
        str measurement_instrument_type
        str air_pressure_compensation_type
        str process_type
        str evaluation_procedure
    }
    class MeasurementTvp {
        int measurement_tvp_id
        Observation observation
        datetime measurement_time
        float field_value
        str field_value_unit
        float calculated_value
        float corrected_value
        datetime correction_time
        str correction_reason
        MeasurementPointMetadata measurement_point_metadata
    }
    MeasurementTvp ..> "belongs in a" Observation
    MeasurementTvp ..> "has" MeasurementPointMetadata
    class MeasurementPointMetadata {
        int measurement_point_metadata_id
        str status_quality_control
        str censor_reason
        str censor_reason_datalens
        float value_limit
        str interpolation_code
    }
    class gld_registration_log{
        int id
        str date_modified
        str gmw_bro_id
        str gld_bro_id
        str filter_number
        str validation_status
        str delivery_id
        str delivery_type
        str delivery_status
        str comments
        str last_changed
        bool corrections_applied
        datetime timestamp_end_registration
        str quality_regime
        str file
        str process_status
    }
    class GroundWaterMonitoringTubeStatic{
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

    class Organisation{
        str name
        int company_number
        str color
        int bro_user
        int bro_token
    }
```

# Beschrijving

Onder het registratieobject kun je de volgende objecten beheren: GrondwaterstandsDossiers, Observaties, Meetpunt metadata, Meting en tijdwaarde paren, Ovservatie metadata, GLD registratie logs, GLD toevoegings logs

# Functies

Voor ieder object kun je in de Bro-connector een CRUD vinden waarin je gemakkelijk alle registratieobjecten kunt beheren.

# Commando's

### gld_additions_qc_quality_control

Gebruikswijze:
`python python manage.py gld_additions_qc_quality_control`

### gld_sync_to_bro

Gebruikswijze:
`python python manage.py gld_sync_to_bro`
Omschrijving:
Dit commando synchroniseert alle onderliggende objecten naar BRO.
