SELECT station_name, count FROM (
        SELECT station_id, count(*) AS count
        FROM
            (SELECT
                date(start_time) AS date,
                start_station_id AS station_id
            FROM trip) AS t
            NATURAL JOIN station
            NATURAL JOIN (
                SELECT date, zip_code
                FROM weather WHERE events IS NOT NULL
            ) AS w
        GROUP BY station_id
    ) AS u NATURAL JOIN station
    ORDER BY count DESC, station_name LIMIT 1;
