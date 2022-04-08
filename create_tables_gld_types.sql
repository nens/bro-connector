DROP TABLE IF EXISTS gld.type_evaluation_procedure;
CREATE TABLE gld.type_evaluation_procedure (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_censored_reason_code;
CREATE TABLE gld.type_censored_reason_code (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_interpolation_code;
CREATE TABLE gld.type_interpolation_code (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_status_code;
CREATE TABLE gld.type_status_code (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_process_reference;
CREATE TABLE gld.type_process_reference (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_process_reference;
CREATE TABLE gld.type_process_reference (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_observation_type;
CREATE TABLE gld.type_observation_type (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_process_type;
CREATE TABLE gld.type_process_type (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_status_quality_control;
CREATE TABLE gld.type_status_quality_control (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_air_pressure_compensation_type;
CREATE TABLE gld.type_air_pressure_compensation_type (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);

DROP TABLE IF EXISTS gld.type_measurement_instrument_type;
CREATE TABLE gld.type_measurement_instrument_type (
    id integer,
    value varchar(255),
    definition_NL varchar(255),
    IMBRO boolean,
    IMBRO_A boolean
);
