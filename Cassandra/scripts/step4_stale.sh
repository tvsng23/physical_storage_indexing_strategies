#!/usr/bin/env bash
# Bước 4: tái hiện đọc dữ liệu cũ và cách Cassandra sửa
# Điều kiện: đã chạy step3 (cass2 và cass3 đang tắt). Nếu chưa, script tự đưa về trạng thái đó.
source "$(dirname "$0")/lib.sh"

docker compose start cass1 >/dev/null; wait_healthy cass1
docker compose stop cass3 >/dev/null

echo "=== bật cass2, tắt hinted handoff trên cass1 và cass2 ==="
docker compose start cass2; wait_healthy cass2
docker compose exec -T cass1 nodetool disablehandoff
docker compose exec -T cass2 nodetool disablehandoff

echo "=== ghi QUORUM khi cass3 vắng mặt ==="
docker compose exec -T cass1 cqlsh -e "CONSISTENCY QUORUM;
  INSERT INTO iot.readings_by_sensor (sensor_id, ts, temperature, humidity)
  VALUES ('hn-99', '2026-11-01 09:00:00', 41.0, 30);"

echo "=== bật cass3, tắt cass1 + cass2, đọc ONE từ cass3 ==="
docker compose start cass3; wait_healthy cass3
docker compose stop cass1 cass2
docker compose exec -T cass3 cqlsh -e "CONSISTENCY ONE;
  SELECT * FROM iot.readings_by_sensor WHERE sensor_id = 'hn-99';"
echo "(kỳ vọng: 0 rows -> đọc phải dữ liệu cũ)"

echo "=== bật lại cass1 + cass2, đọc ALL (read repair) ==="
docker compose start cass1 cass2
wait_healthy cass1; wait_healthy cass2
sleep 10   # chờ gossip: tránh Unavailable do cass3 chưa thấy 2 node kia sống lại
docker compose exec -T cass3 cqlsh -e "CONSISTENCY ALL;
  SELECT * FROM iot.readings_by_sensor WHERE sensor_id = 'hn-99';"

echo "=== anti-entropy repair ==="
docker compose exec -T cass3 nodetool repair iot

echo "=== kiểm tra hinted handoff đã bật lại (sau khi khởi động lại node) ==="
docker compose exec -T cass1 nodetool statushandoff
docker compose exec -T cass2 nodetool statushandoff
