#!/bin/bash
set -e

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to start..."
until mongosh --host mongodb --eval "print('MongoDB is ready')" > /dev/null 2>&1; do
  sleep 1
done

# Connect to MongoDB and initialize
echo "MongoDB is ready! Initializing database and users..."

# Create root user if not exists
mongosh --host mongodb << EOF
use admin
if (db.getUser("${MONGO_INITDB_ROOT_USERNAME}") == null) {
  db.createUser({
    user: "${MONGO_INITDB_ROOT_USERNAME}",
    pwd: "${MONGO_INITDB_ROOT_PASSWORD}",
    roles: [ { role: "root", db: "admin" } ]
  })
  print("Root user created")
} else {
  print("Root user already exists")
}
EOF

# Authenticate as root user
mongosh --host mongodb -u "${MONGO_INITDB_ROOT_USERNAME}" -p "${MONGO_INITDB_ROOT_PASSWORD}" --authenticationDatabase admin << EOF
// Create application database
use ${MONGO_DB_NAME}
print("Created database: ${MONGO_DB_NAME}")

// Create application user with permissions
if (db.getUser("${MONGO_USER}") == null) {
  db.createUser({
    user: "${MONGO_USER}",
    pwd: "${MONGO_PASSWORD}",
    roles: [
      { role: "readWrite", db: "${MONGO_DB_NAME}" },
      { role: "dbAdmin", db: "${MONGO_DB_NAME}" }
    ]
  })
  print("Application user created: ${MONGO_USER}")
} else {
  print("Application user already exists")
}

// Initialize collections
db.createCollection("users")
db.createCollection("sheet_products")
db.createCollection("sheet_generators")
db.createCollection("sheet_branches")
db.createCollection("sheet_config")
db.createCollection("bland_call_logs")
db.createCollection("error_logs")
db.createCollection("dashboard_stats")
print("Collections created")

// Create indexes
db.users.createIndex({ "email": 1 }, { unique: true })
db.bland_call_logs.createIndex({ "call_id": 1 }, { unique: true })
db.sheet_products.createIndex({ "product_id": 1 }, { unique: true })
print("Indexes created")

print("MongoDB initialization completed successfully")
EOF

echo "MongoDB initialization script completed"
