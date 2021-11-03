CREATE MATERIALIZED VIEW IF NOT EXISTS bikes_reached_stations AS
    (SELECT bike_id, start_station_id AS station_id FROM trip)
    UNION (SELECT bike_id, end_station_id AS station_id FROM trip);
SELECT bike_id, COUNT(DISTINCT(station_id)) AS count
    FROM bikes_reached_stations GROUP BY bike_id ORDER BY count DESC, bike_id LIMIT 10;
