SELECT end_time, sum(duration) OVER (ORDER BY end_time)
    FROM trip WHERE bike_id = 697;
