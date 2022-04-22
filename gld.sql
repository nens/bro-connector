-- gld.groundwater_level_dossier definition

-- Drop table

-- DROP TABLE gld.groundwater_level_dossier;

CREATE TABLE gld.groundwater_level_dossier (
	groundwater_level_dossier_id serial NOT NULL,
	groundwater_monitoring_tube_id int4 NULL,
	gmw_bro_id varchar(255) NULL,
	gld_bro_id varchar(255) NULL,
	research_start_date date NULL,
	research_last_date date NULL,
	research_last_correction timestamptz NULL,
	CONSTRAINT groundwater_level_dossier_pkey PRIMARY KEY (groundwater_level_dossier_id)
);


-- gld.measurement_point_metadata definition

-- Drop table

-- DROP TABLE gld.measurement_point_metadata;

CREATE TABLE gld.measurement_point_metadata (
	measurement_point_metadata_id serial NOT NULL,
	qualifier_by_category int4 NULL,
	censored_reason int4 NULL,
	qualifier_by_quantity numeric(100,10) NULL,
	interpolation_code int4 NULL,
	CONSTRAINT measurement_point_metadata_pkey PRIMARY KEY (measurement_point_metadata_id)
);


-- gld.measurement_time_series definition

-- Drop table

-- DROP TABLE gld.measurement_time_series;

CREATE TABLE gld.measurement_time_series (
	measurement_time_series_id serial NOT NULL,
	observation_id int4 NULL,
	CONSTRAINT measurement_time_series_pkey PRIMARY KEY (measurement_time_series_id)
);


-- gld.measurement_tvp definition

-- Drop table

-- DROP TABLE gld.measurement_tvp;

CREATE TABLE gld.measurement_tvp (
	measurement_tvp_id serial NOT NULL,
	measurement_time_series_id int4 NULL,
	measurement_time timestamptz NULL,
	field_value numeric(100,10) NULL,
	calculated_value numeric(100,10) NULL,
	corrected_value numeric(100,10) NULL,
	correction_time timestamptz NULL,
	correction_reason varchar(255) NULL,
	measurement_metadata_id int4 NULL,
	field_value_unit varchar(255) NULL,
	CONSTRAINT measurement_tvp_pkey PRIMARY KEY (measurement_tvp_id)
);


-- gld.observation definition

-- Drop table

-- DROP TABLE gld.observation;

CREATE TABLE gld.observation (
	observation_id serial NOT NULL,
	observationperiod interval NULL,
	observation_starttime timestamptz NULL,
	observation_endtime timestamptz NULL,
	observation_metadata_id int4 NULL,
	observation_process_id int4 NULL,
	groundwater_level_dossier_id int4 NULL,
	result_time timestamptz NULL,
	status varchar(255) NULL,
	CONSTRAINT observation_pkey PRIMARY KEY (observation_id)
);


-- gld.observation_metadata definition

-- Drop table

-- DROP TABLE gld.observation_metadata;

CREATE TABLE gld.observation_metadata (
	observation_metadata_id serial NOT NULL,
	date_stamp date NULL,
	parameter_measurement_serie_type int4 NULL,
	status int4 NULL,
	responsible_party_id int4 NULL,
	CONSTRAINT observation_metadata_pkey PRIMARY KEY (observation_metadata_id)
);


-- gld.observation_process definition

-- Drop table

-- DROP TABLE gld.observation_process;

CREATE TABLE gld.observation_process (
	observation_process_id serial NOT NULL,
	process_reference int4 NULL,
	parameter_measurement_instrument_type int4 NULL,
	parameter_air_pressure_compensation_type int4 NULL,
	process_type int4 NULL,
	parameter_evaluation_procedure int4 NULL,
	CONSTRAINT observation_process_pkey PRIMARY KEY (observation_process_id)
);


-- gld.responsible_party definition

-- Drop table

-- DROP TABLE gld.responsible_party;

CREATE TABLE gld.responsible_party (
	responsible_party_id serial NOT NULL,
	identification int4 NULL,
	organisation_name varchar(255) NULL,
	CONSTRAINT responsible_party_pkey PRIMARY KEY (responsible_party_id)
);


-- gld.type_air_pressure_compensation definition

-- Drop table

-- DROP TABLE gld.type_air_pressure_compensation;

CREATE TABLE gld.type_air_pressure_compensation (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_air_pressure_compensation_pkey PRIMARY KEY (id)
);


-- gld.type_censored_reason_code definition

-- Drop table

-- DROP TABLE gld.type_censored_reason_code;

CREATE TABLE gld.type_censored_reason_code (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_censored_reason_code_pkey PRIMARY KEY (id)
);


-- gld.type_evaluation_procedure definition

-- Drop table

-- DROP TABLE gld.type_evaluation_procedure;

CREATE TABLE gld.type_evaluation_procedure (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_evaluation_procedure_pkey PRIMARY KEY (id)
);


-- gld.type_interpolation_code definition

-- Drop table

-- DROP TABLE gld.type_interpolation_code;

CREATE TABLE gld.type_interpolation_code (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_interpolation_code_pkey PRIMARY KEY (id)
);


-- gld.type_measurement_instrument_type definition

-- Drop table

-- DROP TABLE gld.type_measurement_instrument_type;

CREATE TABLE gld.type_measurement_instrument_type (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_measement_instrument_type_pkey PRIMARY KEY (id)
);


-- gld.type_observation_type definition

-- Drop table

-- DROP TABLE gld.type_observation_type;

CREATE TABLE gld.type_observation_type (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_observation_type_pkey PRIMARY KEY (id)
);


-- gld.type_process_reference definition

-- Drop table

-- DROP TABLE gld.type_process_reference;

CREATE TABLE gld.type_process_reference (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_process_reference_pkey PRIMARY KEY (id)
);


-- gld.type_process_type definition

-- Drop table

-- DROP TABLE gld.type_process_type;

CREATE TABLE gld.type_process_type (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_process_type_pkey PRIMARY KEY (id)
);


-- gld.type_status_code definition

-- Drop table

-- DROP TABLE gld.type_status_code;

CREATE TABLE gld.type_status_code (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_status_code_pkey PRIMARY KEY (id)
);


-- gld.type_status_quality_control definition

-- Drop table

-- DROP TABLE gld.type_status_quality_control;

CREATE TABLE gld.type_status_quality_control (
	id int4 NOT NULL,
	value varchar(255) NULL,
	definition_nl varchar(255) NULL,
	imbro bool NULL,
	imbro_a bool NULL,
	CONSTRAINT type_status_quality_control_pkey PRIMARY KEY (id)
);