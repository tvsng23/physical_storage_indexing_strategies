-- ===== Bài tập 1: đơn hàng =====
CREATE KEYSPACE IF NOT EXISTS shop2
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- "10 đơn mới nhất của một khách hàng"
CREATE TABLE IF NOT EXISTS shop2.orders_by_customer (
    customer_id text,
    order_ts    timestamp,
    order_id    uuid,
    total       decimal,
    PRIMARY KEY ((customer_id), order_ts, order_id)
) WITH CLUSTERING ORDER BY (order_ts DESC, order_id ASC);
-- SELECT * FROM shop2.orders_by_customer WHERE customer_id = 'c1' LIMIT 10;

-- "đơn theo ngày" (ghi dữ liệu vào CẢ HAI bảng)
CREATE TABLE IF NOT EXISTS shop2.orders_by_day (
    day         date,
    order_ts    timestamp,
    order_id    uuid,
    customer_id text,
    total       decimal,
    PRIMARY KEY ((day), order_ts, order_id)
) WITH CLUSTERING ORDER BY (order_ts DESC, order_id ASC);
-- SELECT * FROM shop2.orders_by_day WHERE day = '2026-11-01';

-- ===== Bài tập 2: truy vấn bỏ qua partition key (sẽ bị từ chối) =====
-- SELECT * FROM iot.readings_by_sensor WHERE temperature > 31.5;

-- ===== Câu hỏi 3 (báo cáo): "số đo trên 31.5°C trong một ngày" không cần ALLOW FILTERING =====
-- Phân vùng theo ngày + nhóm "nóng/không" hoặc dùng clustering theo temperature:
CREATE TABLE IF NOT EXISTS iot.readings_by_day_temp (
    day         date,
    temperature double,
    ts          timestamp,
    sensor_id   text,
    humidity    double,
    PRIMARY KEY ((day), temperature, ts, sensor_id)
) WITH CLUSTERING ORDER BY (temperature DESC, ts DESC, sensor_id ASC);
-- SELECT * FROM iot.readings_by_day_temp WHERE day = '2026-10-22' AND temperature > 31.5;

-- ===== Bài tập 3: partition theo bucket tháng =====
CREATE TABLE IF NOT EXISTS iot.readings_by_sensor_month (
    sensor_id   text,
    month       text,          -- ví dụ '2026-10'
    ts          timestamp,
    temperature double,
    humidity    double,
    PRIMARY KEY ((sensor_id, month), ts)
) WITH CLUSTERING ORDER BY (ts DESC);
-- Mỗi cảm biến có một partition mỗi tháng => partition luôn bị chặn kích thước (<< 100 MB).
-- SELECT * FROM iot.readings_by_sensor_month WHERE sensor_id = 'hn-01' AND month = '2026-10' LIMIT 10;

-- ===== Mở rộng: NetworkTopologyStrategy =====
-- (cass3 đặt vào DC2 bằng biến môi trường CASSANDRA_DC; xem README)
-- ALTER KEYSPACE iot WITH replication = {'class':'NetworkTopologyStrategy','datacenter1':2,'dc2':1};
-- CONSISTENCY LOCAL_QUORUM;  CONSISTENCY EACH_QUORUM;
