CREATE SCHEMA gmw;
CREATE SCHEMA gld;
CREATE SCHEMA aanlevering;

-- gmw.delivered_locations definition

-- Drop table

-- DROP TABLE gmw.delivered_locations;

CREATE TABLE gmw.delivered_locations (
	location_id int4 NOT NULL,
	registration_object_id int4 NULL,
	referencesystem varchar NULL,
	horizontal_positioning_method varchar NULL,
	CONSTRAINT delivered_locations_pkey PRIMARY KEY (location_id)
);


-- gmw.delivered_vertical_positions definition

-- Drop table

-- DROP TABLE gmw.delivered_vertical_positions;

CREATE TABLE gmw.delivered_vertical_positions (
	id serial NOT NULL,
	delivered_vertical_positions_id int4 NULL,
	registration_object_id int4 NULL,
	local_vertical_reference_point varchar NULL,
	"offset" float8 NULL,
	vertical_datum varchar NULL,
	ground_level_position float8 NULL,
	ground_level_positioning_method varchar NULL,
	CONSTRAINT delivered_vertical_positions_pkey PRIMARY KEY (id)
);


-- gmw.groundwater_monitoring_tubes definition

-- Drop table

-- DROP TABLE gmw.groundwater_monitoring_tubes;

CREATE TABLE gmw.groundwater_monitoring_tubes (
	id serial NOT NULL,
	groundwater_monitoring_tube_id int4 NULL,
	registration_object_id int4 NULL,
	tube_number int4 NULL,
	tube_type varchar NULL,
	artesian_well_cap_present varchar NULL,
	sediment_sump_present varchar NULL,
	number_of_geo_ohm_cables int4 NULL,
	tube_top_diameter int4 NULL,
	variable_diameter varchar NULL,
	tube_status varchar NULL,
	tube_top_position float8 NULL,
	tube_top_positioning_method varchar NULL,
	tube_packing_material varchar NULL,
	tube_material varchar NULL,
	glue varchar NULL,
	screen_length float8 NULL,
	sock_material varchar NULL,
	plain_tube_part_length float8 NULL,
	sediment_sump_length float8 NULL,
	deliver_to_bro bool NULL,
	CONSTRAINT groundwater_monitoring_tubes_pkey PRIMARY KEY (id)
);


-- gmw.groundwater_monitoring_wells definition

-- Drop table

-- DROP TABLE gmw.groundwater_monitoring_wells;

CREATE TABLE gmw.groundwater_monitoring_wells (
	id serial NOT NULL,
	registration_object_id int4 NULL,
	registration_object_type varchar NULL,
	bro_id varchar(15) NULL,
	request_reference varchar(255) NULL,
	delivery_accountable_party int4 NULL,
	delivery_responsible_party int4 NULL,
	quality_regime varchar NULL,
	under_privilege varchar NULL,
	delivery_context varchar NULL,
	construction_standard varchar NULL,
	initial_function varchar NULL,
	number_of_standpipes int4 NULL,
	ground_level_stable varchar NULL,
	well_stability varchar NULL,
	nitg_code varchar(8) NULL,
	olga_code varchar(8) NULL,
	well_code varchar NULL,
	"owner" int4 NULL,
	maintenance_responsible_party int4 NULL,
	well_head_protector varchar NULL,
	well_construction_date date NULL,
	CONSTRAINT groundwater_monitoring_wells_pkey PRIMARY KEY (id)
);



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


-- aanlevering.gld_addition_log definition

-- Drop table

-- DROP TABLE aanlevering.gld_addition_log;

CREATE TABLE aanlevering.gld_addition_log (
	id bigserial NOT NULL,
	date_modified varchar(254) NULL,
	observation_id varchar(254) NULL,
	"start" varchar(254) NULL,
	"end" varchar(254) NULL,
	broid_registration varchar(254) NULL,
	procedure_uuid varchar(254) NULL,
	procedure_initialized varchar(254) NULL,
	validation_status varchar(254) NULL,
	levering_id varchar(254) NULL,
	levering_status varchar(254) NULL,
	"comments" varchar(50000) NULL,
	file varchar(254) NULL,
	addition_type varchar(254) NULL,
	CONSTRAINT gld_addition_log_voorlopig_pkey PRIMARY KEY (id)
);


-- aanlevering.gld_registration_log definition

-- Drop table

-- DROP TABLE aanlevering.gld_registration_log;

CREATE TABLE aanlevering.gld_registration_log (
	id serial NOT NULL,
	date_modified varchar(254) NULL,
	gwm_bro_id varchar(254) NULL,
	filter_id varchar(254) NULL,
	validation_status varchar(254) NULL,
	levering_id varchar(254) NULL,
	levering_status varchar(254) NULL,
	gld_bro_id varchar(254) NULL,
	"comments" varchar(10000) NULL,
	last_changed varchar(254) NULL,
	corrections_applied bool NULL,
	file varchar(254) NULL,
	quality_regime varchar(254) NULL,
	timestamp_end_registration timestamptz NULL,
	process_status varchar(254) NULL,
	CONSTRAINT gld_registration_log_pkey PRIMARY KEY (id)
);