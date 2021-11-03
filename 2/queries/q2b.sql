WITH t AS (
        SELECT date(start_time) AS date, start_station_id AS station_id
        FROM trip WHERE duration <= 60
    )
    SELECT round(count(*) * 1.0/ (SELECT count(*) FROM t), 4)
    FROM t NATURAL JOIN station NATURAL JOIN weather
        WHERE events IS NOT NULL;
