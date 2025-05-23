// MongoDB Initialization Script
print("Starting MongoDB initialization process");

// MongoDB automatically executes this script during container initialization
// with MONGO_INITDB_ROOT_USERNAME and MONGO_INITDB_ROOT_PASSWORD credentials

// Get database name and app credentials from environment variables
// Use defaults if not provided
const dbName = process.env.MONGO_DB_NAME || "stahla_dashboard";
const appUser = process.env.MONGO_USER || "stahla_app";
const appPassword = process.env.MONGO_PASSWORD || "app_password";

print("Setting up database: " + dbName);
print("Creating application user: " + appUser);

// Create application database
db = db.getSiblingDB(dbName);
print("Created database: " + dbName);

// Create application user with permissions only to this database
try {
  db.createUser({
    user: appUser,
    pwd: appPassword,
    roles: [
      { role: "readWrite", db: dbName },
      { role: "dbAdmin", db: dbName },
    ],
  });
  print("Created user " + appUser + " for database " + dbName);
} catch (e) {
  print("Error creating user: " + e);
  print("User might already exist, continuing...");
}

// Initialize collections with proper indexes
try {
  db.createCollection("users");
  db.createCollection("sheet_products");
  db.createCollection("sheet_generators");
  db.createCollection("sheet_branches");
  db.createCollection("sheet_config");
  db.createCollection("bland_call_logs");
  db.createCollection("error_logs");
  db.createCollection("dashboard_stats");
  print("Collections created successfully");

  // Create indexes
  db.users.createIndex({ email: 1 }, { unique: true });
  db.bland_call_logs.createIndex({ call_id: 1 }, { unique: true });
  db.sheet_products.createIndex({ product_id: 1 }, { unique: true });
  print("Indexes created successfully");
} catch (e) {
  print("Error creating collections or indexes: " + e);
}

print("MongoDB initialization completed successfully");
