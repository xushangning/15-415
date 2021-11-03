SELECT city, COUNT(station_id) AS count FROM station GROUP BY city ORDER BY count DESC, city;
