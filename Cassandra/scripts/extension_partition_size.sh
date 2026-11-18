#!/usr/bin/env bash
# Mở rộng: so sánh kích thước partition giữa schema không bucket và bucket theo tháng
source "$(dirname "$0")/lib.sh"
$PY extension_partition_size.py
for n in cass1 cass2 cass3; do docker compose exec -T $n nodetool flush iot; done
echo "=== big_unbounded (một partition khổng lồ) ==="
docker compose exec -T cass1 nodetool tablehistograms iot big_unbounded
echo "=== big_bucketed (partition theo tháng) ==="
docker compose exec -T cass1 nodetool tablehistograms iot big_bucketed
