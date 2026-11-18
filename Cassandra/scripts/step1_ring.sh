#!/usr/bin/env bash
# Bước 1: partition key quyết định node nào lưu dữ liệu
source "$(dirname "$0")/lib.sh"

echo "=== token của vài cảm biến ==="
docker compose exec -T cass1 cqlsh -e \
  "SELECT DISTINCT sensor_id, token(sensor_id) FROM iot.readings_by_sensor LIMIT 5;"

echo "=== getendpoints, RF = 3 (cả 3 node đều giữ) ==="
docker compose exec -T cass1 nodetool getendpoints iot readings_by_sensor hn-01

echo "=== keyspace ring1 (RF = 1) ==="
docker compose exec -T cass1 cqlsh -e "$(cat cql/ring1.cql)"
for s in hn-01 hn-02 hn-03 hn-04 hn-05 hn-06; do
  echo "$s -> $(docker compose exec -T cass1 nodetool getendpoints ring1 sensors $s)"
done
docker compose exec -T cass1 nodetool status ring1
docker compose exec -T cass1 nodetool status iot

echo "=== vòng token (48 dòng, 16 vnode/node) ==="
docker compose exec -T cass1 nodetool ring
echo
echo "Kiểm chứng tay: tìm token đầu tiên >= token(hn-01) = -6927399588689370405"
echo "(nếu lớn hơn mọi token thì quay vòng về token nhỏ nhất), so với getendpoints ở trên."
