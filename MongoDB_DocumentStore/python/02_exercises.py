"""Solutions for Document Store exercises 1 and 2.
1) Insert five orders with different document shapes.
2) Find all orders containing a given SKU.
3) Aggregate revenue by customer city.
Run: python python/02_exercises.py
"""

import os
from pprint import pprint

from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

EXERCISE_ORDERS = [
    {
        "_id": 2001,
        "customer": {"name": "An", "city": "Hanoi"},
        "status": "paid",
        "items": [
            {"sku": "BK-01", "title": "Python Basics", "qty": 2, "price": 12.5},
            {"sku": "BK-07", "title": "SQL in Practice", "qty": 1, "price": 18.0},
        ],
        "tags": ["student", "online"],
    },
    {
        "_id": 2002,
        "customer": {"name": "Binh", "city": "Da Nang"},
        "status": "shipped",
        "items": [{"sku": "BK-03", "title": "Data Viz", "qty": 3, "price": 22.0}],
        "shipping": {"method": "express", "fee": 3.5},
    },
    {
        "_id": 2003,
        "customer": {"name": "Chi", "city": "Hanoi"},
        "status": "pending",
        "items": [{"sku": "BK-01", "title": "Python Basics", "qty": 1, "price": 12.5}],
        "coupon": "WELCOME10",
    },
    {
        "_id": 2004,
        "customer": {"name": "Dung", "city": "Hue"},
        "status": "paid",
        "items": [
            {"sku": "BK-09", "title": "Statistics", "qty": 1, "price": 30.0},
            {"sku": "BK-03", "title": "Data Viz", "qty": 1, "price": 22.0},
        ],
        "gift": True,
        "notes": "Deliver after 5 PM",
    },
    {
        "_id": 2005,
        "customer": {"name": "Em", "city": "Da Nang"},
        "status": "paid",
        "items": [{"sku": "BK-07", "title": "SQL in Practice", "qty": 2, "price": 18.0}],
        "payment": {"method": "card", "paid": True},
        "tags": ["returning-customer"],
    },
]


def main() -> None:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        orders = client["shop"]["exercise_orders"]

        # Use a dedicated collection and replace/upsert so repeated runs do not duplicate data.
        for order in EXERCISE_ORDERS:
            orders.replace_one({"_id": order["_id"]}, order, upsert=True)

        print("\n--- Five exercise orders ---")
        print("Document count:", orders.count_documents({}))
        for doc in orders.find({}).sort("_id", 1):
            pprint(doc)

        target_sku = "BK-01"  # Change this value to search for another SKU.
        print(f"\n--- Orders containing SKU {target_sku} ---")
        for doc in orders.find({"items.sku": target_sku}):
            pprint(doc)

        pipeline = [
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": "$customer.city",
                    "order_ids": {"$addToSet": "$_id"},
                    "units": {"$sum": "$items.qty"},
                    "revenue": {
                        "$sum": {"$multiply": ["$items.qty", "$items.price"]}
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "city": "$_id",
                    "orderCount": {"$size": "$order_ids"},
                    "units": 1,
                    "revenue": {"$round": ["$revenue", 2]},
                }
            },
            {"$sort": {"revenue": -1}},
        ]
        print("\n--- Revenue by city ---")
        for row in orders.aggregate(pipeline):
            pprint(row)
    finally:
        client.close()


if __name__ == "__main__":
    main()
