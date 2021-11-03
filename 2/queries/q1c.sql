SELECT station_name, city FROM station WHERE station_name LIKE '%' || city || '%' ORDER BY city, station_name;
