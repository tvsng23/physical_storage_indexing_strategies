#!/usr/bin/env bash
# Bước 0: dựng cluster 3 node, tạo virtualenv, nạp 3000 số đo
source "$(dirname "$0")/lib.sh"
docker compose up -d || { echo "Thử chạy lại: docker compose up -d"; exit 1; }
wait_healthy cass1; wait_healthy cass2; wait_healthy cass3
docker compose exec cass1 nodetool status

echo "--- IP của từng container ---"
docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $(docker compose ps -q)

if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python sensorring.py load
