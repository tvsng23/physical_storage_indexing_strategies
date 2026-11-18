"""MongoDB from Python: insert, find, aggregate and pandas DataFrame.
Run from the project root after starting Docker:
    python -m pip install -r requirements.txt
    python python/01_python_demo.py
"""

import os
from pprint import pprint

import pandas as pd
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")


def main() -> None:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        orders = client["shop"]["orders"]

        # The lesson inserts order 1004. Replace/upsert makes this script rerunnable.
        orders.replace_one(
            {"_id": 1004},
            {
                "_id": 1004,
                "customer": {"name": "Hung", "city": "Hue"},
                "status": "paid",
                "items": [],
            },
            upsert=True,
        )
        print("Order 1004 inserted or replaced.")

        print("\n--- Paid orders (projection) ---")
        for doc in orders.find(
            {"status": "paid"},
            {"customer.name": 1, "status": 1},
        ):
            pprint(doc)

        pipeline = [
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": "$items.sku",
                    "units": {"$sum": "$items.qty"},
                }
            },
        ]
        result = list(orders.aggregate(pipeline))
        df = pd.DataFrame(result)
        print("\n--- Aggregation result as pandas DataFrame ---")
        print(df)
    finally:
        client.close()


if __name__ == "__main__":
    main()
