// BÀI TẬP 1 + 2
// 1) Thêm 5 đơn hàng có hình dạng khác nhau.
// 2) Tìm tất cả đơn hàng có chứa một SKU cho trước.
// 3) (Trong cùng file) aggregation tính doanh thu theo thành phố.
// Chạy từ thư mục gốc bằng:
// Get-Content -Raw .\mongosh\02_exercises.js | docker compose exec -T mongo mongosh

use shop;
const exerciseOrders = db.exercise_orders;

// Dọn dữ liệu của riêng collection bài tập để có thể chạy lại.
exerciseOrders.deleteMany({});

exerciseOrders.insertMany([
  {
    _id: 2001,
    customer: { name: "An", city: "Hanoi" },
    status: "paid",
    items: [
      { sku: "BK-01", title: "Python Basics", qty: 2, price: 12.5 },
      { sku: "BK-07", title: "SQL in Practice", qty: 1, price: 18.0 }
    ],
    tags: ["student", "online"]
  },
  {
    _id: 2002,
    customer: { name: "Binh", city: "Da Nang" },
    status: "shipped",
    items: [{ sku: "BK-03", title: "Data Viz", qty: 3, price: 22.0 }],
    shipping: { method: "express", fee: 3.5 }
  },
  {
    _id: 2003,
    customer: { name: "Chi", city: "Hanoi" },
    status: "pending",
    items: [{ sku: "BK-01", title: "Python Basics", qty: 1, price: 12.5 }],
    coupon: "WELCOME10"
  },
  {
    _id: 2004,
    customer: { name: "Dung", city: "Hue" },
    status: "paid",
    items: [
      { sku: "BK-09", title: "Statistics", qty: 1, price: 30.0 },
      { sku: "BK-03", title: "Data Viz", qty: 1, price: 22.0 }
    ],
    gift: true,
    notes: "Deliver after 5 PM"
  },
  {
    _id: 2005,
    customer: { name: "Em", city: "Da Nang" },
    status: "paid",
    items: [{ sku: "BK-07", title: "SQL in Practice", qty: 2, price: 18.0 }],
    payment: { method: "card", paid: true },
    tags: ["returning-customer"]
  }
]);

print("\n--- Five inserted exercise orders ---");
print("Count:", exerciseOrders.countDocuments({}));
printjson(exerciseOrders.find({}).sort({ _id: 1 }).toArray());

// Thay giá trị targetSku để tìm SKU bất kỳ.
const targetSku = "BK-01";
print("\n--- Orders containing SKU:", targetSku, "---");
printjson(exerciseOrders.find({ "items.sku": targetSku }).toArray());

// Doanh thu = tổng qty * price của các mặt hàng, nhóm theo customer.city.
print("\n--- Revenue by city ---");
printjson(exerciseOrders.aggregate([
  { $unwind: "$items" },
  {
    $group: {
      _id: "$customer.city",
      totalOrders: { $addToSet: "$_id" },
      units: { $sum: "$items.qty" },
      revenue: { $sum: { $multiply: ["$items.qty", "$items.price"] } }
    }
  },
  {
    $project: {
      _id: 0,
      city: "$_id",
      orderCount: { $size: "$totalOrders" },
      units: 1,
      revenue: { $round: ["$revenue", 2] }
    }
  },
  { $sort: { revenue: -1 } }
]).toArray());
