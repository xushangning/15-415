WITH t AS (SELECT
        id, start_time, start_station_name, start_station_id,
        end_time, end_station_name, end_station_id,
        row_number() OVER (ORDER BY end_time) AS i
    FROM trip WHERE bike_id = 697 ORDER BY end_time)
    SELECT
        t.id AS former_trip_id,
        t.end_time AS former_end_time,
        t.end_station_name AS former_end_station_name,
        t1.id AS latter_trip_id,
        t1.start_time AS latter_start_time,
        t1.start_station_name AS latter_start_station_name
    FROM t JOIN t AS t1 ON t.i + 1 = t1.i
    WHERE t.end_station_id <> t1.start_station_id
    ORDER BY former_trip_id, latter_trip_id;
