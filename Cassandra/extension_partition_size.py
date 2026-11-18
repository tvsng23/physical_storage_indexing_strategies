"""Mở rộng: nạp 200.000 số đo cho MỘT cảm biến vào hai schema để so sánh kích thước partition.
Chạy:  python extension_partition_size.py
Sau đó: bash scripts/extension_partition_size.sh
"""
import random
from datetime import datetime, timedelta

from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.policies import WhiteListRoundRobinPolicy

profile = ExecutionProfile(load_balancing_policy=WhiteListRoundRobinPolicy(["127.0.0.1"]))
cluster = Cluster(["127.0.0.1"], execution_profiles={EXEC_PROFILE_DEFAULT: profile})
s = cluster.connect()

s.execute("""CREATE KEYSPACE IF NOT EXISTS iot
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 3}""")
s.execute("""CREATE TABLE IF NOT EXISTS iot.big_unbounded (
  sensor_id text, ts timestamp, temperature double, humidity double,
  PRIMARY KEY ((sensor_id), ts)) WITH CLUSTERING ORDER BY (ts DESC)""")
s.execute("""CREATE TABLE IF NOT EXISTS iot.big_bucketed (
  sensor_id text, month text, ts timestamp, temperature double, humidity double,
  PRIMARY KEY ((sensor_id, month), ts)) WITH CLUSTERING ORDER BY (ts DESC)""")

ins_u = s.prepare("INSERT INTO iot.big_unbounded (sensor_id, ts, temperature, humidity) VALUES (?,?,?,?)")
ins_b = s.prepare("INSERT INTO iot.big_bucketed (sensor_id, month, ts, temperature, humidity) VALUES (?,?,?,?,?)")

N = 200_000
start = datetime(2024, 1, 1)
rows_u, rows_b = [], []
for i in range(N):
    ts = start + timedelta(minutes=5 * i)          # ~2 năm dữ liệu
    t, h = round(random.uniform(22, 32), 1), round(random.uniform(55, 90), 1)
    rows_u.append(("hn-big", ts, t, h))
    rows_b.append(("hn-big", ts.strftime("%Y-%m"), ts, t, h))

execute_concurrent_with_args(s, ins_u, rows_u, concurrency=64)
execute_concurrent_with_args(s, ins_b, rows_b, concurrency=64)
print(f"loaded {N} rows into big_unbounded and big_bucketed")
cluster.shutdown()
