SELECT station_name, date, events FROM
        (SELECT
            *,
            rank() OVER (
                PARTITION BY station_id
                ORDER BY count DESC, date
            ) AS rank
        FROM (
            SELECT
                date(start_time) AS date,
                start_station_id AS station_id,
                count(*) AS count
            FROM trip GROUP BY date, station_id
        ) AS t) AS u
        JOIN station USING (station_id)
        JOIN weather USING (date)
    WHERE rank = 1 AND events <> ''
    ORDER BY station_name;
