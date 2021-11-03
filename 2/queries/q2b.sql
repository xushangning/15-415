WITH t AS (
        SELECT date(start_time) AS date FROM trip WHERE duration <= 60
    )
    SELECT round(count(*) * 100.0 / (SELECT count(*) FROM t), 4)
    FROM t JOIN weather USING (date) WHERE events <> '';
