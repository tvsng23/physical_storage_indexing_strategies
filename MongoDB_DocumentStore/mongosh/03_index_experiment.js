// BÀI TẬP 3
// Tạo 10.000 document, chạy explain trước/sau khi tạo index.
// Chạy từ thư mục gốc bằng:
// Get-Content -Raw .\mongosh\03_index_experiment.js | docker compose exec -T mongo mongosh

use shop;
const lab = db.index_lab;

// Chỉ xóa collection thí nghiệm này, không xóa các collection khác.
lab.drop();

const cities = ["Hanoi", "Da Nang", "Hue", "HCMC", "Can Tho"];
const statuses = ["paid", "pending", "shipped"];
const batchSize = 1000;

for (let start = 0; start < 10000; start += batchSize) {
  const batch = [];
  const end = Math.min(start + batchSize, 10000);

  for (let i = start; i < end; i++) {
    batch.push({
      _id: i + 1,
      customer: {
        name: `Customer_${i + 1}`,
        city: cities[i % cities.length]
      },
      status: statuses[i % statuses.length],
      amount: ((i * 17) % 50000) / 100 + 10,
      createdAt: new Date(2025, 0, 1 + (i % 365))
    });
  }

  lab.insertMany(batch);
}

print("Inserted documents:", lab.countDocuments({}));
const filter = { "customer.city": "Hanoi", status: "paid" };

print("\n--- EXPLAIN BEFORE INDEX (expect COLLSCAN) ---");
printjson(lab.find(filter).explain("executionStats"));

print("\n--- CREATE COMPOUND INDEX ---");
print(lab.createIndex({ "customer.city": 1, status: 1 }));

print("\n--- EXPLAIN AFTER INDEX (expect IXSCAN) ---");
printjson(lab.find(filter).explain("executionStats"));
