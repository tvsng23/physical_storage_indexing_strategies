// Chương 1 - Document Store (MongoDB)
// Các ví dụ CRUD, aggregation và index trong phần lý thuyết.
// Chạy từ thư mục gốc bằng:
// Get-Content -Raw .\mongosh\01_lesson_demo.js | docker compose exec -T mongo mongosh

use shop;
const orders = db.orders;

// CREATE: xóa trước đúng các _id mẫu để script có thể chạy lại.
orders.deleteMany({ _id: { $in: [1001, 1002, 1003] } });

orders.insertOne({
  _id: 1001,
  customer: { name: "Linh", city: "Hanoi" },
  status: "paid",
  items: [
    { sku: "BK-01", title: "Python Basics", qty: 2, price: 12.5 },
    { sku: "BK-07", title: "SQL in Practice", qty: 1, price: 18.0 }
  ],
  tags: ["student", "first-order"]
});

orders.insertMany([
  {
    _id: 1002,
    customer: { name: "Nam", city: "Da Nang" },
    status: "shipped",
    items: [{ sku: "BK-03", title: "Data Viz", qty: 1, price: 22.0 }]
  },
  {
    _id: 1003,
    customer: { name: "Mai", city: "Hanoi" },
    status: "paid",
    items: [{ sku: "BK-01", title: "Python Basics", qty: 1, price: 12.5 }],
    coupon: "WELCOME10"
  }
]);

// READ: các kiểu truy vấn trong bài.
print("\n--- All orders ---");
printjson(orders.find({}).toArray());

print("\n--- Orders with status = paid ---");
printjson(orders.find({ status: "paid" }).toArray());

print("\n--- Orders from Hanoi (dot notation) ---");
printjson(orders.find({ "customer.city": "Hanoi" }).toArray());

print("\n--- Orders containing SKU BK-01 ---");
printjson(orders.find({ "items.sku": "BK-01" }).toArray());

print("\n--- Paid orders having coupon field ---");
printjson(orders.find({ status: "paid", coupon: { $exists: true } }).toArray());

print("\n--- Orders with an item price greater than 20 ---");
printjson(orders.find({ "items.price": { $gt: 20 } }).toArray());

print("\n--- Projection, sort and limit ---");
printjson(
  orders.find(
    { status: { $in: ["paid", "shipped"] } },
    { _id: 1, status: 1 }
  ).sort({ _id: -1 }).limit(2).toArray()
);

// UPDATE and DELETE: dùng đúng các toán tử được giới thiệu trong bài.
orders.updateOne({ _id: 1001 }, { $set: { status: "shipped" } });
orders.updateMany({ status: "paid" }, { $set: { reviewed: false } });
orders.updateOne({ _id: 1002 }, { $push: { tags: "gift" } });
orders.updateOne({ _id: 1003 }, { $unset: { coupon: "" } });
orders.deleteOne({ _id: 1003 });

print("\n--- Orders after update/delete ---");
printjson(orders.find({}).sort({ _id: 1 }).toArray());

// AGGREGATION: units and revenue by SKU.
print("\n--- Aggregation: units and revenue by SKU ---");
printjson(orders.aggregate([
  { $match: { status: { $in: ["paid", "shipped"] } } },
  { $unwind: "$items" },
  {
    $group: {
      _id: "$items.sku",
      units: { $sum: "$items.qty" },
      revenue: { $sum: { $multiply: ["$items.qty", "$items.price"] } }
    }
  },
  { $sort: { revenue: -1 } },
  { $limit: 5 }
]).toArray());

// INDEX: compound index on nested customer.city and status.
print("\n--- Create compound index ---");
print(orders.createIndex({ "customer.city": 1, status: 1 }));

print("\n--- Explain query after index creation ---");
printjson(
  orders.find({ "customer.city": "Hanoi", status: "paid" })
    .explain("executionStats")
);
