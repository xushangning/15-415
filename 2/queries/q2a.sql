SELECT station_name, count FROM (
        SELECT start_station_id AS station_id, count(*) AS count
        FROM
            (SELECT
                date(start_time) AS date,
                start_station_id
            FROM trip) AS t
            JOIN (SELECT date FROM weather WHERE events <> '') AS w
            USING (date)
        GROUP BY start_station_id
    ) AS u JOIN station USING (station_id)
    ORDER BY count DESC, station_name LIMIT 1;
