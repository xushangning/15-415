WITH t AS (SELECT
        id, start_time, start_station_name, start_station_id,
        end_time, end_station_name, end_station_id, bike_id
    FROM trip WHERE bike_id >= 500 and bike_id <= 600)
    SELECT
        t.bike_id,
        t.id AS former_trip_id,
        t.start_time AS former_start_time,
        t.end_time AS former_end_time,
        t1.id AS latter_trip_id,
        t1.start_time AS latter_start_time,
        t1.end_time AS latter_end_time
    FROM t JOIN t AS t1 ON t.bike_id = t1.bike_id
        AND t.id < t1.id
    WHERE t.start_time < t1.start_time
        AND t.end_time > t1.end_time
    ORDER BY bike_id, former_trip_id, latter_trip_id;
