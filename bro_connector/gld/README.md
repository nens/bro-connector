<img src=../static/img/broconnector.png width="140">

# Class Diagram for Groundwater Level Dossiers (GLD)

```mermaid
classDiagram

%% ---------------------------
%% Kernobjecten (GLD domein)
%% ---------------------------

class GroundwaterLevelDossier{
  int groundwater_level_dossier_id
  GroundwaterMonitoringTubeStatic groundwater_monitoring_tube
  GroundwaterMonitoringNet[] groundwater_monitoring_net  %% ManyToMany
  str gld_bro_id
  str quality_regime
  str correction_reason
  date research_start_date
  date research_last_date
  datetime research_last_correction
}

class Observation{
  int observation_id
  GroundwaterLevelDossier groundwater_level_dossier
  ObservationMetadata observation_metadata
  ObservationProcess observation_process
  datetime observation_starttime
  datetime result_time
  datetime observation_endtime
  bool up_to_date_in_bro
  str correction_reason
  str observation_id_bro
}

class ObservationMetadata{
  int observation_metadata_id
  str observation_type
  str status
  Organisation responsible_party
}

class ObservationProcess{
  int observation_process_id
  str process_reference
  str measurement_instrument_type
  str air_pressure_compensation_type
  str process_type
  str evaluation_procedure
}

class MeasurementTvp{
  int measurement_tvp_id
  Observation observation
  datetime measurement_time
  decimal field_value
  str field_value_unit
  decimal calculated_value
  decimal value_to_be_corrected
  datetime correction_time
  str correction_reason
  MeasurementPointMetadata measurement_point_metadata
  str comment
}

class MeasurementPointMetadata{
  int measurement_point_metadata_id
  str status_quality_control
  str censor_reason
  str censor_reason_datalens
  str value_limit
  str interpolation_code  %% afgeleid property
}

class gld_registration_log{
  int id
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

class gld_addition_log{
  int id
  str broid_registration
  Observation observation
  str addition_type
  str observation_identifier
  datetime start_date
  datetime end_date
  str validation_status
  str delivery_id
  str delivery_type
  str delivery_status
  str comments
  str last_changed
  bool corrections_applied
  str file
  str process_status
}

%% ---------------------------------
%% Externe objecten (uit GMN/GMW/BRO)
%% ---------------------------------

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
  str color           %% Used to visually distinguish organisations in the UI or reports
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
