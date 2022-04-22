

-----------------------------------------------------------
---- CREATING A BRO GLD OBSERVATION FROM TIMESERIES DATA --
-----------------------------------------------------------

-- Let's assume a timeseries input with complete metadata and length < 10.000

-- Starting from a measurement timeseries (each timeseries has a unique ID, 6 in this case) 
select * from gld.measurement_tvp mt where measurement_time_series_id = 6;

-- Create a measurepoint point metadata row
-- Each measurement should have metadata, which is stored in the measurement_point_metadata table
-- Each measurement metadata object has multiple properties (m for mandatory): quality(m), censored_reason, qualifier_by_quantity, interpolation_code (m)  
select * from gld.measurement_point_metadata mpm;
select * from gld.type_status_quality_control tsqc; -- quality of the measurement
select * from gld.type_interpolation_code tic; -- interpolation method, always discontinu
select * from gld.type_censored_reason_code tcrc;

-- insert the metadata, and update the measurements to refer to this metadata
insert into gld.measurement_point_metadata values (1, 3, null,null ,1); -- this metadata indicates 'NogNietBeoordeeld' quality, 'Discontinu' interpolation
update gld.measurement_tvp set measurement_metadata_id = 1 where measurement_time_series_id = 6;

-- Create a new measurement time series id from the timeseries data
insert into gld.measurement_time_series values (6 ,1);

-- Create new responsible party, only need to do this once
insert into gld.responsible_party values (1, 20168636, 'Provincie Zeeland');


-- Next step is creating the observation entity which holds the timeseries data we just defined 
-- An observation is related to 1 measurement timeserie, has 1 observation metadata, and 1 observation process data related to it

-- Create new observation metadata
-- The datestamp of the observation metadata should be the same as the observation 'resultTime' property (we'll include this later)
-- Best practice is to set the observation metadata datestamp to the datetime of the final measurement within the observation 
-- Create observation metadata which contains: reguliereMeting, voorlopig, ProvincieZeeland as responsible party
insert into gld.observation_metadata values (1, '2022-02-22 01:17:19',1, 1, 1);
select * from gld.observation_metadata om;
select * from gld.type_observation_type;
select * from gld.type_status_code tsc;
select * from gld.responsible_party rp;

-- Create new observation process data
-- This observation process includes: process_reference: NEN5120v1991, type_measurement_instrument: drukSensor (hierbij is geen air_pressure_compensation nodig)
-- air_pressure_compensation: capilair, process_type: algorithm, evalulation_procedure: oordeelDeskundige (dit kan later QC datakwaliteitscontrole worden)
insert into gld.observation_process values (1, 1, 4, 1, 1, 3);
select * from gld.observation_process op;
select * from gld.type_process_reference tpr;
select * from gld.type_measement_instrument_type tmit;
select * from gld.type_air_pressure_compensation tapc;
select * from gld.type_process_type tpt;
select * from gld.type_evaluation_procedure tep;

-- Now we have the observation metadata and process data, an observation can be created
-- An observation has a start and end time, which should be the first and final timestamp of timeseries
-- An observation always has groundwater_level_dossier_id, otherwise we can't deliver it to the BRO 
-- The groundwater_level_dossier_id can be extracted by using the information on the tube/filter id's/quality regime, which are unique for a groundwater level dossier
-- In this case a dummy value is used of an existing gld registration in the demo environment
-- An observation also has a 'resultTime' which should be equal to the observation_metadata 'dateStamp' date (make this the final measurement time) 
insert into gld.observation values (1, null, '2021-12-05 01:17:19', '2022-02-22 12:37:13', 1, 1, 6, null);
select * from gld.observation o; 
select * from gld.groundwater_level_dossier gld2 --check gld registrations here


-- Voeg rest van measurement timeseries ook toe als observations
-- Splits in een aantal voorlopig beoordeelde metingen en controle metingen


-- Let's assume a timeseries input with complete metadata and length < 10.000

-- Starting from a measurement timeseries (each timeseries has a unique ID, 6 in this case) 
select distinct(measurement_time_series_id) from gld.measurement_tvp mt order by measurement_time_series_id ;

-- Create a measurepoint point metadata row
-- Each measurement should have metadata, which is stored in the measurement_point_metadata table
-- Each measurement metadata object has multiple properties (m for mandatory): quality(m), censored_reason, qualifier_by_quantity, interpolation_code (m)  
select * from gld.measurement_point_metadata mpm;
select * from gld.type_status_quality_control tsqc; -- quality of the measurement
select * from gld.type_interpolation_code tic; -- interpolation method, always discontinu
select * from gld.type_censored_reason_code tcrc;

-- insert the metadata, and update the measurements to refer to this metadata
insert into gld.measurement_point_metadata values (2, 3, null,null ,1); -- this metadata indicates 'NogNietBeoordeeld' quality, 'Discontinu' interpolation
insert into gld.measurement_point_metadata values (3, 1, null,null ,1); -- this metadata indicates 'NogNietBeoordeeld' quality, 'Discontinu' interpolation

update gld.measurement_tvp set measurement_metadata_id = 2 where measurement_time_series_id > 6;

-- Create a new measurement time series id from the timeseries data
insert into gld.measurement_time_series (measurement_time_series_id) 
select distinct measurement_time_series_id from gld.measurement_tvp ;
update gld.measurement_time_series set observation_id = measurement_time_series_id;


-- Create new responsible party, only need to do this once
insert into gld.responsible_party values (1, 20168636, 'Provincie Zeeland');


-- Next step is creating the observation entity which holds the timeseries data we just defined 
-- An observation is related to 1 measurement timeserie, has 1 observation metadata, and 1 observation process data related to it

-- Create new observation metadata
-- The datestamp of the observation metadata should be the same as the observation 'resultTime' property (we'll include this later)
-- Best practice is to set the observation metadata datestamp to the datetime of the final measurement within the observation 
-- Create observation metadata which contains: reguliereMeting, voorlopig, ProvincieZeeland as responsible party
insert into gld.observation_metadata values (1, '2022-02-22 01:17:19',1, 9, 1);
insert into gld.observation_metadata values (2, '2022-02-22 01:17:19',2, 9, 1);

select * from gld.observation_metadata om;
select * from gld.type_observation_type;
select * from gld.type_status_code tsc;
select * from gld.responsible_party rp;

-- Create new observation process data
-- This observation process includes: process_reference: NEN5120v1991, type_measurement_instrument: drukSensor (hierbij is geen air_pressure_compensation nodig)
-- air_pressure_compensation: capilair, process_type: algorithm, evalulation_procedure: oordeelDeskundige (dit kan later QC datakwaliteitscontrole worden)
insert into gld.observation_process values (1, 1, 4, 99, 1, 3);
insert into gld.observation_process values (2, 1, 7, 99, 1, 3);
insert into gld.observation_process values (3, 1, 2, 99, 1, 3);

select * from gld.observation_process op;
select * from gld.type_process_reference tpr;
select * from gld.type_measurement_instrument_type tmit;
select * from gld.type_air_pressure_compensation tapc;
select * from gld.type_process_type tpt;
select * from gld.type_evaluation_procedure tep;

-- Now we have the observation metadata and process data, an observation can be created
-- An observation has a start and end time, which should be the first and final timestamp of timeseries
-- An observation always has groundwater_level_dossier_id, otherwise we can't deliver it to the BRO 
-- The groundwater_level_dossier_id can be extracted by using the information on the tube/filter id's/quality regime, which are unique for a groundwater level dossier
-- In this case a dummy value is used of an existing gld registration in the demo environment
-- An observation also has a 'resultTime' which should be equal to the observation_metadata 'dateStamp' date (make this the final measurement time) 
insert into gld.observation (observation_id, observation_starttime, observation_endtime, observation_metadata_id, observation_process_id, groundwater_level_dossier_id, result_time )
select distinct measurement_time_series_id,min(measurement_time),max(measurement_time),1,1,6,max(measurement_time)
from gld.measurement_tvp
group by measurement_time_series_id;

update gld.observation set groundwater_level_dossier_id = observation_id + 30;

--- Reguliere metingen
update gld.observation set observation_metadata_id = 2 where observation_id > 5;
update gld.observation set observation_process_id = 2 where observation_id > 8;

-- Controle metingen
update gld.observation set observation_metadata_id = 1 where observation_id <= 5;
update gld.observation set observation_process_id = 3 where observation_id <= 5;

