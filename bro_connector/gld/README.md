# Klassendiagram voor Grondwaterstand dossiers (GLD) #
```mermaid
classDiagram
        class Organisation{
        str name
        int company_number
        str color
        int bro_user
        int bro_token
    }
    class GroundwaterLevelDossier{
        int groundwater_level_dossier_id
        GroundwaterMonitoringTubeStatic groundwater_monitoring_tube
        str gld_bro_id
        datetime research_start_date
        datetime research_last_date
        datetime research_last_correction
    }
    GroundwaterLevelDossier ..> "groundwater_monitoring_tube" GroundWaterMonitoringTubeStatic
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
    Observation ..> "obseration_metadata" ObservationMetadata
    Observation ..> "observation_process" ObservationProcess
    Observation ..> "groundwater_level_dossier" GroundwaterLevelDossier
    class ObservationMetadata {
        int observation_metadata_id
        date date_stamp
        str observation_type
        str status
        Organisation responsible_party
    }
    ObservationMetadata ..> "responsible_party" Organisation
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
        datetime measurement_type
        float field_value
        str field_value_unit
        float calculated_value
        float corrected_value
        datetime correction_time
        str correction_reason
        MeasurementPointMetadata measurement_point_metadata
    }
    MeasurementTvp ..> "observation" Observation
    MeasurementTvp ..> "measurement_point_metadata" MeasurementPointMetadata
    class MeasurementPointMetadata {
        int measurement_point_metadata_id
        str status_quality_control
        str censor_reason
        str censor_Reason_artesia
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
        str corrections_applied
        datetime timestamp_end_registration
        str quality_rgime
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
```
# Beschrijving #
Onder het registratieobject kun je de volgende objecten beheren: GrondwaterstandsDossiers, Observaties, Meetpunt metadata, Meting en tijdwaarde paren, Ovservatie metadata, GLD registratie logs, GLD toevoegings logs
# Functies #
Voor ieder object kun je in de Bro-connector een CRUD vinden waarin je gemakkelijk alle registratieobjecten kunt beheren.
# Commando's #
### gld_additions_qc_quality_control ###
Gebruikswijze:
```python python manage.py gld_additions_qc_quality_control```
### gld_sync_to_bro ###
Gebruikswijze:
```python python manage.py gld_sync_to_bro```
Omschrijving:
Dit commando synchroniseert alle onderliggende objecten naar BRO.