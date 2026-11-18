#!/usr/bin/env bash
# Mở rộng: lặp lại Bước 4 NHƯNG KHÔNG tắt hinted handoff -> còn đọc phải dữ liệu cũ không?
source "$(dirname "$0")/lib.sh"

docker compose start cass1 cass2 >/dev/null; wait_healthy cass1; wait_healthy cass2
docker compose stop cass3 >/dev/null
docker compose exec -T cass1 cqlsh -e "CONSISTENCY QUORUM;
  INSERT INTO iot.readings_by_sensor (sensor_id, ts, temperature, humidity)
  VALUES ('hn-98', '2026-11-01 10:00:00', 40.0, 31);"

docker compose start cass3; wait_healthy cass3
echo "Chờ 30 giây cho hint được gửi bù..."; sleep 30
docker compose stop cass1 cass2
docker compose exec -T cass3 cqlsh -e "CONSISTENCY ONE;
  SELECT * FROM iot.readings_by_sensor WHERE sensor_id = 'hn-98';"
docker compose start cass1 cass2; wait_healthy cass1; wait_healthy cass2
docker compose logs cass1 cass2 | grep "Finished hinted handoff"
