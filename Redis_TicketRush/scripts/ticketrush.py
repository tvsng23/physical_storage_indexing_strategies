"""
TicketRush - Redis Key-Value Store Lab

Implements the chapter's concert-ticketing lab:
1. Seat holds and race conditions (naive GET/SET vs SET NX EX)
2. Atomic hold/confirm/release with Lua scripts
3. General-admission flash sale
4. Fixed-window and sliding-window rate limiting
5. Virtual waiting room using sorted sets
6. Concurrent stress test
7. Exercises: leaderboard, user profiles/city index, cache-aside benchmark

"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable

import redis
from redis.exceptions import RedisError

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 1
PREFIX = "ticketrush"

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True,
    socket_connect_timeout=3,
)

# ---------- Shared helpers ----------

def key(name: str) -> str:
    """Add a namespace to every key created by this lab."""
    return f"{PREFIX}:{name}"


def race(fn: Callable[[int], object], n: int = 50) -> list:
    """Run fn(i) concurrently from n worker threads."""
    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(fn, range(n)))


def reset_lab_data() -> int:
    """Delete only this lab's namespaced keys from Redis DB 1."""
    keys = list(r.scan_iter(match=f"{PREFIX}:*"))
    if not keys:
        print("No existing TicketRush keys to remove.")
        return 0
    deleted = r.delete(*keys)
    print(f"Deleted {deleted} TicketRush keys from Redis DB {REDIS_DB}.")
    return deleted


def require_redis() -> None:
    r.ping()
    print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}, database {REDIS_DB}.")


# ---------- Step 1: Seat holds and race condition ----------

def hold_naive(event: str, seat: str, user: str) -> bool:
    """Intentionally unsafe check-then-act implementation for demonstration."""
    hold_key = key(f"hold:{event}:{seat}")
    if r.get(hold_key) is None:
        time.sleep(0.01)  # widen the race window so the bug is visible
        r.set(hold_key, user, ex=300)
        return True
    return False


def hold_nx(event: str, seat: str, user: str, ttl: int = 300) -> bool:
    """Atomic hold: only set the key if it does not already exist."""
    return bool(r.set(key(f"hold:{event}:{seat}"), user, nx=True, ex=ttl))


def demo_race_condition() -> None:
    print("\nSTEP 1 - Race condition")
    reset_lab_data()
    naive_wins = race(lambda i: hold_naive("c1", "A1", f"user{i}"), n=50)
    print("Naive GET then SET winners (expect more than 1 sometimes):", sum(naive_wins))

    reset_lab_data()
    safe_wins = race(lambda i: hold_nx("c1", "A1", f"user{i}"), n=50)
    print("SET NX EX winners (expected exactly 1):", sum(safe_wins))
    print("Remaining TTL:", r.ttl(key("hold:c1:A1")), "seconds")


# ---------- Step 2: Atomic hold, confirm and release with Lua ----------

HOLD_SCRIPT = r.register_script("""
if redis.call('SISMEMBER', KEYS[2], ARGV[2]) == 1 then return 0 end
if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'EX', ARGV[3]) then return 1 end
return 0
""")

CONFIRM_SCRIPT = r.register_script("""
if redis.call('GET', KEYS[1]) == ARGV[1] then
  redis.call('SADD', KEYS[2], ARGV[2])
  redis.call('DEL', KEYS[1])
  return 1
end
return 0
""")

RELEASE_SCRIPT = r.register_script("""
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
""")


def hold(event: str, seat: str, user: str, ttl: int = 300) -> bool:
    return bool(HOLD_SCRIPT(
        keys=[key(f"hold:{event}:{seat}"), key(f"sold:{event}")],
        args=[user, seat, ttl],
    ))


def confirm(event: str, seat: str, user: str) -> bool:
    return bool(CONFIRM_SCRIPT(
        keys=[key(f"hold:{event}:{seat}"), key(f"sold:{event}")],
        args=[user, seat],
    ))


def release(event: str, seat: str, user: str) -> bool:
    return bool(RELEASE_SCRIPT(
        keys=[key(f"hold:{event}:{seat}")],
        args=[user],
    ))


def seat_map(event: str, seats: Iterable[str]) -> dict[str, str]:
    sold = r.smembers(key(f"sold:{event}"))
    result = {}
    for seat in seats:
        if seat in sold:
            result[seat] = "sold"
        elif r.exists(key(f"hold:{event}:{seat}")):
            result[seat] = "held"
        else:
            result[seat] = "free"
    return result


def demo_atomic_seat_flow() -> None:
    print("\nSTEP 2 - Atomic seat lifecycle")
    reset_lab_data()
    print("Linh holds A1:", hold("c1", "A1", "linh"))
    print("Nam tries A1:", hold("c1", "A1", "nam"))
    print("Nam confirms Linh's hold:", confirm("c1", "A1", "nam"))
    print("Linh confirms A1:", confirm("c1", "A1", "linh"))
    print("Nam tries already-sold A1:", hold("c1", "A1", "nam"))
    print("Seat map:", seat_map("c1", ["A1", "A2"]))
    print("Sold seats:", sorted(r.smembers(key("sold:c1"))))


# ---------- Step 3: General-admission flash sale ----------

def buy_general(event: str, user: str) -> bool:
    """Atomic decrement prevents the stock count from being oversold."""
    stock_key = key(f"stock:{event}")
    left = r.decr(stock_key)
    if left < 0:
        r.incr(stock_key)
        return False
    r.sadd(key(f"buyers:{event}"), user)
    return True


def demo_flash_sale() -> None:
    print("\nSTEP 3 - General-admission flash sale")
    reset_lab_data()
    r.set(key("stock:g1"), 100)
    successful = race(lambda i: buy_general("g1", f"user{i}"), n=500)
    print("Successful purchases:", sum(successful))
    print("Remaining stock:", r.get(key("stock:g1")))
    print("Unique buyers:", r.scard(key("buyers:g1")))


# ---------- Step 4: Rate limiting ----------

def allow_fixed(user: str, limit: int = 5, window: int = 10) -> bool:
    """Fixed window: one counter for each user and time window."""
    window_id = int(time.time() // window)
    counter_key = key(f"rl:fixed:{user}:{window_id}")
    pipe = r.pipeline()
    pipe.incr(counter_key)
    pipe.expire(counter_key, window, nx=True)
    count, _ = pipe.execute()
    return count <= limit


SLIDING_SCRIPT = r.register_script("""
local now, window, limit = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now - window)
if redis.call('ZCARD', KEYS[1]) < limit then
  redis.call('ZADD', KEYS[1], now, ARGV[4])
  redis.call('PEXPIRE', KEYS[1], window)
  return 1
end
return 0
""")


def allow_sliding(user: str, limit: int = 5, window_ms: int = 10_000) -> bool:
    now_ms = int(time.time() * 1000)
    return bool(SLIDING_SCRIPT(
        keys=[key(f"rl:sliding:{user}")],
        args=[now_ms, window_ms, limit, uuid.uuid4().hex],
    ))


def try_hold(event: str, seat: str, user: str) -> str:
    if not allow_sliding(user):
        return "rate_limited"
    return "ok" if hold(event, seat, user) else "taken"


def demo_rate_limiting() -> None:
    print("\nSTEP 4 - Rate limiting")
    reset_lab_data()
    print("Fixed-window requests:", [allow_fixed("linh") for _ in range(8)])
    reset_lab_data()
    print("Sliding-window requests:", [allow_sliding("linh") for _ in range(8)])
    print("Expected: first five allowed, remaining three rejected.")


# ---------- Step 5: Virtual waiting room ----------

def join_queue(event: str, user: str) -> int:
    queue_key = key(f"queue:{event}")
    r.zadd(queue_key, {user: time.time()}, nx=True)
    rank = r.zrank(queue_key, user)
    return rank + 1 if rank is not None else 0


def admit(event: str, n: int) -> list[str]:
    popped = r.zpopmin(key(f"queue:{event}"), n)
    return [user for user, _score in popped]


def demo_waiting_room() -> None:
    print("\nSTEP 5 - Virtual waiting room")
    reset_lab_data()
    for user in ["u1", "u2", "u3"]:
        print(user, "position:", join_queue("c1", user))
    print("u1 rejoins; keeps position:", join_queue("c1", "u1"))
    print("Admitted:", admit("c1", 2))
    print("u3's new position:", join_queue("c1", "u3"))


# ---------- Step 6: Concurrent stress test ----------

def stress_test() -> None:
    print("\nSTEP 6 - Stress test: 100 buyers, 20 seats")
    reset_lab_data()
    seats = [f"S{i}" for i in range(1, 21)]

    def buyer(i: int):
        user = f"user{i}"
        for seat in seats:
            if hold("c1", seat, user):
                time.sleep(random.random() * 0.05)  # simulate payment time
                if confirm("c1", seat, user):
                    return seat
                release("c1", seat, user)
        return None

    sold_seats = [seat for seat in race(buyer, n=100) if seat]
    unique_seats = len(set(sold_seats))
    sold_count = r.scard(key("sold:c1"))
    print("Tickets sold:", len(sold_seats))
    print("Unique seats:", unique_seats)
    print("Members in sold set:", sold_count)
    print("PASS:", len(sold_seats) == unique_seats == sold_count == 20)


# ---------- Exercise 1: Leaderboard with sorted set ----------

def leaderboard_add(player: str, score: int) -> None:
    r.zadd(key("leaderboard"), {player: score})


def leaderboard_top(n: int = 3) -> list[tuple[str, float]]:
    return r.zrevrange(key("leaderboard"), 0, n - 1, withscores=True)


def leaderboard_rank(player: str) -> int | None:
    rank = r.zrevrank(key("leaderboard"), player)
    return rank + 1 if rank is not None else None


def demo_leaderboard() -> None:
    print("\nEXERCISE 1 - Leaderboard")
    reset_lab_data()
    for player, score in [("linh", 1200), ("nam", 950), ("mai", 1430), ("an", 1200)]:
        leaderboard_add(player, score)
    print("Top 3:", leaderboard_top(3))
    print("Linh's rank:", leaderboard_rank("linh"))


# ---------- Exercise 2: User hashes and city sets ----------

def save_user_profile(user_id: str, name: str, city: str, age: int) -> None:
    r.hset(key(f"user:{user_id}"), mapping={
        "name": name,
        "city": city,
        "age": age,
    })
    r.sadd(key(f"city:{city.lower().replace(' ', '_')}"), user_id)


def get_users_in_city(city: str) -> list[dict]:
    city_key = key(f"city:{city.lower().replace(' ', '_')}")
    user_ids = r.smembers(city_key)
    profiles = []
    for user_id in sorted(user_ids):
        profile = r.hgetall(key(f"user:{user_id}"))
        if profile:
            profiles.append({"user_id": user_id, **profile})
    return profiles


def demo_user_profiles() -> None:
    print("\nEXERCISE 2 - User profiles and city index")
    reset_lab_data()
    save_user_profile("u1", "Linh", "Hanoi", 21)
    save_user_profile("u2", "Nam", "Da Nang", 22)
    save_user_profile("u3", "Mai", "Hanoi", 20)
    print("Users in Hanoi:", get_users_in_city("Hanoi"))


# ---------- Exercise 3: Cache-aside benchmark ----------

def slow_query(product_id: int) -> dict:
    """Simulate a slower database/API lookup."""
    time.sleep(0.02)
    return {"id": product_id, "title": f"Product {product_id}", "price": 12.5}


def get_product(product_id: int, cache_ttl: int = 300) -> dict:
    cache_key = key(f"product:{product_id}")
    cached = r.get(cache_key)
    if cached is not None:
        return json.loads(cached)

    product = slow_query(product_id)
    r.set(cache_key, json.dumps(product), ex=cache_ttl)
    return product


def cache_aside_benchmark(requests: int = 100) -> None:
    print(f"\nEXERCISE 3 - Cache-aside benchmark ({requests} repeated requests)")
    reset_lab_data()

    # First request is a cache miss; subsequent requests should be cache hits.
    start = time.perf_counter()
    for _ in range(requests):
        get_product(7)
    elapsed = time.perf_counter() - start
    print(f"Total time: {elapsed:.4f} seconds")
    print(f"Average per request: {elapsed / requests * 1000:.3f} ms")
    print("Cached value:", r.get(key("product:7")))


# ---------- Command-line entry point ----------

def run_all() -> None:
    require_redis()
    demo_race_condition()
    demo_atomic_seat_flow()
    demo_flash_sale()
    demo_rate_limiting()
    demo_waiting_room()
    stress_test()
    demo_leaderboard()
    demo_user_profiles()
    cache_aside_benchmark()


def main() -> None:
    parser = argparse.ArgumentParser(description="Redis TicketRush lab")
    parser.add_argument(
        "task",
        nargs="?",
        choices=["all", "step1", "step2", "step3", "step4", "step5", "step6",
                 "exercise1", "exercise2", "exercise3", "reset"],
        default="all",
        help="Which lab section to run (default: all)",
    )
    args = parser.parse_args()

    try:
        require_redis()
        tasks = {
            "all": run_all,
            "step1": demo_race_condition,
            "step2": demo_atomic_seat_flow,
            "step3": demo_flash_sale,
            "step4": demo_rate_limiting,
            "step5": demo_waiting_room,
            "step6": stress_test,
            "exercise1": demo_leaderboard,
            "exercise2": demo_user_profiles,
            "exercise3": cache_aside_benchmark,
            "reset": reset_lab_data,
        }
        if args.task == "all":
            # run_all performs its own connection check; avoid duplicate output.
            run_all()
        else:
            tasks[args.task]()
    except RedisError as exc:
        raise SystemExit(
            "Cannot connect to Redis. Start the Docker service and check port 6379.\n"
            f"Redis error: {exc}"
        ) from exc


if __name__ == "__main__":
    main()
