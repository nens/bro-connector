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