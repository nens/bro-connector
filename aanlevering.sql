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