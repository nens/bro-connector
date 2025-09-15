SELECT a.*
FROM gld.measurement_tvp a
JOIN gld.measurement_tvp b
  ON a.observation_id = b.observation_id
 AND a.measurement_time = b.measurement_time
 AND a.measurement_tvp_id > b.measurement_tvp_id;

DELETE FROM gld.measurement_tvp a
USING gld.measurement_tvp b
WHERE
    a.measurement_tvp_id > b.measurement_tvp_id
    AND a.observation_id = b.observation_id
    AND a.measurement_time = b.measurement_time;