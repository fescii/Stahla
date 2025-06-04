#!/bin/bash
set -e

echo "Starting MongoDB initialization for Fly.io deployment..."

# Wait for MongoDB to be ready
until mongosh --eval "print(\"MongoDB is ready\")" > /dev/null 2>&1; do
    echo "Waiting for MongoDB to start..."
    sleep 2
done

echo "MongoDB is running, proceeding with initialization..."

# Get environment variables with defaults
MONGO_ROOT_USER="${MONGO_INITDB_ROOT_USERNAME}"
MONGO_ROOT_PASSWORD="${MONGO_INITDB_ROOT_PASSWORD}"
MONGO_DB_NAME="${MONGO_INITDB_DATABASE}"
MONGO_APP_USER="${MONGO_USER}"
MONGO_APP_PASSWORD="${MONGO_PASSWORD}"

echo "Creating root user and application user..."

# Create the root user and application user
mongosh <<EOF
use admin;

// Create root user if it doesn't exist
try {
  db.createUser({
    user: "${MONGO_ROOT_USER}",
    pwd: "${MONGO_ROOT_PASSWORD}",
    roles: [
      { role: "userAdminAnyDatabase", db: "admin" },
      { role: "readWriteAnyDatabase", db: "admin" },
      { role: "dbAdminAnyDatabase", db: "admin" },
      { role: "clusterAdmin", db: "admin" }
    ]
  });
  print("Root user created successfully");
} catch (e) {
  if (e.code === 51003) {
    print("Root user already exists");
  } else {
    print("Error creating root user: " + e);
    throw e;
  }
}

// Create application user in admin database with permissions for the app database
try {
  db.createUser({
    user: "${MONGO_APP_USER}",
    pwd: "${MONGO_APP_PASSWORD}",
    roles: [
      { role: "readWrite", db: "admin" },
      { role: "dbAdmin", db: "admin" },
      { role: "readWrite", db: "${MONGO_DB_NAME}" },
      { role: "dbAdmin", db: "${MONGO_DB_NAME}" }
    ]
  });
  print("Application user created successfully in admin database");
} catch (e) {
  if (e.code === 51003) {
    print("Application user already exists");
  } else {
    print("Error creating application user: " + e);
    throw e;
  }
}

// Switch to the application database
use ${MONGO_DB_NAME};

// Create collections and indexes
print("Creating collections and indexes...");

// Collections
db.createCollection("users");
db.createCollection("quotes");
db.createCollection("locations");
db.createCollection("pricing");
db.createCollection("classifications");
db.createCollection("emails");
db.createCollection("hubspot_contacts");
db.createCollection("bland_logs");
db.createCollection("webhooks");

// Indexes for better performance
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "created_at": 1 });

db.quotes.createIndex({ "quote_id": 1 }, { unique: true });
db.quotes.createIndex({ "user_id": 1 });
db.quotes.createIndex({ "created_at": 1 });
db.quotes.createIndex({ "status": 1 });

db.locations.createIndex({ "zip_code": 1 });
db.locations.createIndex({ "state": 1 });
db.locations.createIndex({ "coordinates": "2dsphere" });

db.pricing.createIndex({ "service_type": 1 });
db.pricing.createIndex({ "location": 1 });
db.pricing.createIndex({ "effective_date": 1 });

db.classifications.createIndex({ "call_id": 1 }, { unique: true });
db.classifications.createIndex({ "classification": 1 });
db.classifications.createIndex({ "created_at": 1 });

db.emails.createIndex({ "email": 1 });
db.emails.createIndex({ "sent_at": 1 });
db.emails.createIndex({ "status": 1 });

db.hubspot_contacts.createIndex({ "hubspot_id": 1 }, { unique: true });
db.hubspot_contacts.createIndex({ "email": 1 });
db.hubspot_contacts.createIndex({ "last_sync": 1 });

db.bland_logs.createIndex({ "call_id": 1 }, { unique: true });
db.bland_logs.createIndex({ "created_at": 1 });
db.bland_logs.createIndex({ "status": 1 });

db.webhooks.createIndex({ "webhook_id": 1 }, { unique: true });
db.webhooks.createIndex({ "source": 1 });
db.webhooks.createIndex({ "created_at": 1 });

print("Collections and indexes created successfully");
print("MongoDB initialization completed successfully");

EOF

echo "MongoDB initialization script completed!"
