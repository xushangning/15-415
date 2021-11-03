SELECT ROUND(COUNT(*) * 1.0 / (SELECT COUNT(*) FROM trip), 4) FROM trip WHERE start_station_id = end_station_id;
