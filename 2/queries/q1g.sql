SELECT city, station_name, count FROM (
        SELECT
            city, station_name, count,
            RANK() OVER (PARTITION BY city ORDER BY count DESC) AS rank
        FROM (
            SELECT station_id, COUNT(*) AS count
            FROM (
                SELECT id, start_station_id AS station_id FROM trip
                UNION ALL SELECT id, end_station_id AS station_id FROM trip
            ) AS t GROUP BY station_id
        ) AS t2 NATURAL JOIN station
    ) AS t3 WHERE rank = 1 ORDER BY city;
