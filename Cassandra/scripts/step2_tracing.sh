#!/usr/bin/env bash
# Bước 2: truy vấn theo partition so với quét toàn bảng (ALLOW FILTERING)
source "$(dirname "$0")/lib.sh"

echo "=== Không có ALLOW FILTERING: bị từ chối ==="
docker compose exec -T cass1 cqlsh -e \
  "SELECT * FROM iot.readings_by_sensor WHERE temperature > 31.5;" 2>&1 | head -5

echo
echo "=== Theo partition key ==="
docker compose exec -T cass1 cqlsh -e "CONSISTENCY ONE; TRACING ON;
  SELECT ts, temperature FROM iot.readings_by_sensor WHERE sensor_id = 'hn-01' LIMIT 3;" \
  | grep -E "Executing|live rows|Request complete"

echo
echo "=== ALLOW FILTERING (quét toàn cluster) ==="
docker compose exec -T cass1 cqlsh -e "CONSISTENCY ONE; TRACING ON;
  SELECT count(*) FROM iot.readings_by_sensor WHERE temperature > 31.5 ALLOW FILTERING;" \
  | grep -E "range requests|Executing|live rows|Request complete"
