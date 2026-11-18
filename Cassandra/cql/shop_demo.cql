-- Phần demo trong bài (cluster 1 node, keyspace shop)
CREATE KEYSPACE IF NOT EXISTS shop
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
USE shop;

CREATE TABLE IF NOT EXISTS readings_by_sensor (
    sensor_id   text,
    ts          timestamp,
    temperature double,
    humidity    double,
    PRIMARY KEY ((sensor_id), ts)
) WITH CLUSTERING ORDER BY (ts DESC);

INSERT INTO readings_by_sensor (sensor_id, ts, temperature, humidity) VALUES ('hn-01', '2026-10-22 08:00:00', 27.5, 71);
INSERT INTO readings_by_sensor (sensor_id, ts, temperature, humidity) VALUES ('hn-01', '2026-10-22 08:05:00', 27.8, 70);
INSERT INTO readings_by_sensor (sensor_id, ts, temperature, humidity) VALUES ('hn-02', '2026-10-22 08:00:00', 25.1, 80);

SELECT * FROM readings_by_sensor WHERE sensor_id = 'hn-01' LIMIT 10;
SELECT * FROM readings_by_sensor WHERE sensor_id = 'hn-01' AND ts >= '2026-10-22 08:02:00';
