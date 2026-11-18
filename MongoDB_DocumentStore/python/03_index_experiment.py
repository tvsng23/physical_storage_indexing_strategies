import os
from pymongo import MongoClient, InsertOne

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
CITIES = ["Hanoi", "Da Nang", "Hue", "HCMC", "Can Tho"]
STATUSES = ["paid", "pending", "shipped"]


def main() -> None:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        collection = client["shop"]["index_lab"]
        collection.drop()

        operations = []
        for i in range(10_000):
            doc = {
                "_id": i + 1,
                "customer": {"name": f"Customer_{i + 1}", "city": CITIES[i % len(CITIES)]},
                "status": STATUSES[i % len(STATUSES)],
                "amount": ((i * 17) % 50_000) / 100 + 10,
            }
            operations.append(InsertOne(doc))

        # Insert in batches to avoid sending one oversized bulk request.
        for start in range(0, len(operations), 1_000):
            collection.bulk_write(operations[start : start + 1_000], ordered=False)

        print("Inserted documents:", collection.count_documents({}))
        query = {"customer.city": "Hanoi", "status": "paid"}

        print("\n--- EXPLAIN BEFORE INDEX (expect COLLSCAN) ---")
        before = collection.find(query).explain()
        print("Execution stats:")
        print(before.get("executionStats", {}))
        print("Query planner:")
        print(before.get("queryPlanner", {}))

        print("\n--- CREATE COMPOUND INDEX ---")
        print(collection.create_index([("customer.city", 1), ("status", 1)]))

        print("\n--- EXPLAIN AFTER INDEX (expect IXSCAN) ---")
        after = collection.find(query).explain()
        print("Execution stats:")
        print(after.get("executionStats", {}))
        print("Query planner:")
        print(after.get("queryPlanner", {}))
    finally:
        client.close()


if __name__ == "__main__":
    main()
