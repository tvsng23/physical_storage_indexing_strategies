#!/usr/bin/env bash
# Hàm dùng chung. Chạy các script từ thư mục gốc sensorring/ hoặc bất kỳ đâu.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="python3"; fi

# Chờ một service ở trạng thái healthy (không chỉ UN: gossip báo UN trước khi mở cổng CQL)
wait_healthy() {
  local svc=$1
  echo -n "Waiting for $svc to be healthy"
  for _ in $(seq 1 120); do
    local id st
    id=$(docker compose ps -q "$svc")
    st=$(docker inspect -f '{{.State.Health.Status}}' "$id" 2>/dev/null)
    if [ "$st" = "healthy" ]; then echo " ✓"; return 0; fi
    echo -n "."; sleep 5
  done
  echo " TIMEOUT"; return 1
}

# Chờ nodetool (chạy trên cass1) báo đúng N dòng DN
wait_down() {
  local want=$1
  echo -n "Waiting for $want node(s) to show DN"
  for _ in $(seq 1 60); do
    local n
    n=$(docker compose exec -T cass1 nodetool status 2>/dev/null | grep -c '^DN')
    if [ "$n" -ge "$want" ]; then echo " ✓"; return 0; fi
    echo -n "."; sleep 3
  done
  echo " TIMEOUT"; return 1
}
