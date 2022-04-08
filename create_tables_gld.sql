DROP TABLE IF EXISTS gld.groundwater_level_dossier;
CREATE TABLE gld.groundwater_level_dossier (
    groundwater_level_dossier_id SERIAL PRIMARY KEY, --1..N relatie met NET
    groundwater_monitoring_tube_id integer,
    gmw_bro_id varchar(255),
    gld_bro_id varchar(255),
    research_start_date date,
    research_last_date date
);

DROP TABLE IF EXISTS gld.measurement_timeseries_TVP_observation;
CREATE TABLE gld.measurement_timeseries_TVP_observation (
    measurement_timeseries_TVP_observation_id SERIAL PRIMARY KEY,
    groundwater_level_dossier_id integer,
    observation_starttime timestamp with time zone, --resulteert in obeservationperiode in xml
    observation_endtime timestamp with time zone, --resulteert in obeservationperiode in xml
    result_time timestamp with time zone,
    metadata_observation_id integer
);

DROP TABLE IF EXISTS gld.observation;
CREATE TABLE gld.observation (
    observation_id SERIAL PRIMARY KEY,
    observationperiod INTERVAL,
    observation_starttime timestamp with time zone,
    observation_endtime timestamp with time zone
);

DROP TABLE IF EXISTS gld.observation_metadata;
CREATE TABLE gld.observation_metadata (
    observation_metadata_id SERIAL PRIMARY KEY,
    observation_id integer,
    date_stamp date,
    parameter_measurement_serie_type integer, --type_observation_type
    status integer, --type_status_code
    responsible_party_id integer --organisatie
);

DROP TABLE IF EXISTS gld.responsible_party;
CREATE TABLE gld.responsible_party (
    responsible_party_id SERIAL PRIMARY KEY,
    identification integer, --kvk nummer
    organisation_name varchar(255)
);

DROP TABLE IF EXISTS gld.observation_process;
CREATE TABLE gld.observation_process (
    observation_process_id SERIAL PRIMARY KEY,
    observation_id integer,
    sensor_id varchar (255),
    process_reference integer, --type_process_reference
    parameter_measurement_instrument_type integer, --type_measement_instrument_type
    parameter_air_pressure_compensation_type integer, --type_air_pressure_compensation_type
    process_type integer, --type_process_type
    parameter_evaluation_procedure integer --type_evaluation_procedure
);

DROP TABLE IF EXISTS gld.measurement_time_series;
CREATE TABLE gld.measurement_time_series (
    measurement_time_series_id SERIAL PRIMARY KEY,
    observation_id integer
    --point --tijdmeetwaardepaar TVP
);

DROP TABLE IF EXISTS gld.measurement_TVP;
CREATE TABLE gld.measurement_TVP (
    measurement_TVP_id SERIAL PRIMARY KEY,
    measurement_time_series_id integer,
    measurement_time timestamp with time zone,
    field_value numeric, --meetwaarde veld
    field_value_unit varchar(5),
    calculated_value numeric, --automatisch berekende hoogte
    corrected_value numeric, --gecorigeerde hoogte
    correction_time timestamp with time zone,
    correction_reason varchar(255)
);

DROP TABLE IF EXISTS gld.measurement_point_metadata;
CREATE TABLE gld.measurement_point_metadata (
    measurement_point_metadata_id SERIAL PRIMARY KEY,
    qualifier_by_category integer, --type_status_quality_control
    censored_reason integer, --type_censored_reason_code
    qualifier_by_quantity numeric,
    interpolation_code integer --type_interpolation_code
);
