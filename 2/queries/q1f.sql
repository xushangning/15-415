WITH bikes AS (SELECT DISTINCT(bike_id) FROM bikes_reached_stations),
    san_jose_stations AS (SELECT station_id FROM station WHERE city = 'San Jose')
SELECT COUNT(*) FROM (SELECT * FROM bikes EXCEPT ALL SELECT DISTINCT bike_id FROM (
    SELECT * FROM bikes, san_jose_stations EXCEPT ALL SELECT * FROM bikes_reached_stations
) AS t1) AS t2;
