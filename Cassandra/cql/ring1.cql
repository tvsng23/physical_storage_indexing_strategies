-- Bước 1: keyspace RF = 1 để thấy dữ liệu được chia giữa các node
CREATE KEYSPACE IF NOT EXISTS ring1
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};
CREATE TABLE IF NOT EXISTS ring1.sensors (sensor_id text PRIMARY KEY);
