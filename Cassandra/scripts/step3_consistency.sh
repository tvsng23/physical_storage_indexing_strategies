#!/usr/bin/env bash
# Bước 3: mất node thì mức consistency nào còn chạy
source "$(dirname "$0")/lib.sh"

echo "=== 3 node sống ==="
$PY sensorring.py cl

echo; echo "=== tắt cass3 ==="
docker compose stop cass3
wait_down 1
$PY sensorring.py cl

echo; echo "=== tắt thêm cass2 ==="
docker compose stop cass2
wait_down 2
$PY sensorring.py cl
