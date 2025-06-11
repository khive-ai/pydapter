// MongoDB initialization script
// This script will run when the MongoDB container starts for the first time

// Switch to the tutorial database
db = db.getSiblingDB('tutorial_db');

// Create collections with some initial configuration
db.createCollection('users');
db.createCollection('products');
db.createCollection('orders');

// Add indexes for better performance
db.users.createIndex({ "id": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "username": 1 }, { unique: true });

db.products.createIndex({ "id": 1 }, { unique: true });
db.products.createIndex({ "category": 1 });
db.products.createIndex({ "tags": 1 });

db.orders.createIndex({ "id": 1 }, { unique: true });
db.orders.createIndex({ "user_id": 1 });
db.orders.createIndex({ "order_date": 1 });

print('Database initialization completed successfully!');
