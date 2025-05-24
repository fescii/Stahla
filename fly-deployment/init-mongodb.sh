#!/bin/bash

# MongoDB Initialization Script for Fly.io
# This script initializes MongoDB and creates the necessary users and collections

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/home/femar/AO3/Stahla"
ENV_FILE="$PROJECT_ROOT/.env"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to load environment variables
load_env() {
    if [ -f "$ENV_FILE" ]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
        print_success "Environment variables loaded"
    else
        print_error ".env file not found at $ENV_FILE"
        exit 1
    fi
}

# Function to check if MongoDB is ready
check_mongodb_ready() {
    print_status "Checking if MongoDB is ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if fly ssh console -a stahla-mongodb -C "mongosh --eval 'print(\"MongoDB ready\")'" >/dev/null 2>&1; then
            print_success "MongoDB is ready"
            return 0
        fi
        
        print_status "Waiting for MongoDB... (attempt $attempt/$max_attempts)"
        sleep 5
        ((attempt++))
    done
    
    print_error "MongoDB is not ready after $max_attempts attempts"
    return 1
}

# Function to initialize MongoDB users and database
initialize_mongodb() {
    print_status "Initializing MongoDB users and database..."
    
    # Get environment variables with defaults
    local mongo_root_user="${MONGO_ROOT_USER:-mongoadmin}"
    local mongo_root_password="${MONGO_ROOT_PASSWORD:-secret}"
    local mongo_db_name="${MONGO_DB_NAME:-stahla_dashboard}"
    local mongo_app_user="${MONGO_USER:-stahla_app}"
    local mongo_app_password="${MONGO_PASSWORD:-app_password}"
    
    # Create initialization script
    local init_script="/tmp/mongo_init.js"
    cat > "$init_script" << EOF
// MongoDB initialization script
print("Starting MongoDB initialization...");

// Create root user
use admin;
try {
  db.createUser({
    user: "${mongo_root_user}",
    pwd: "${mongo_root_password}",
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

// Switch to application database
use ${mongo_db_name};

// Create application user
try {
  db.createUser({
    user: "${mongo_app_user}",
    pwd: "${mongo_app_password}",
    roles: [
      { role: "readWrite", db: "${mongo_db_name}" },
      { role: "dbAdmin", db: "${mongo_db_name}" }
    ]
  });
  print("Application user created successfully");
} catch (e) {
  if (e.code === 51003) {
    print("Application user already exists");
  } else {
    print("Error creating application user: " + e);
    throw e;
  }
}

// Create collections
print("Creating collections...");
db.createCollection("users");
db.createCollection("quotes");
db.createCollection("locations");
db.createCollection("pricing");
db.createCollection("classifications");
db.createCollection("emails");
db.createCollection("hubspot_contacts");
db.createCollection("bland_logs");
db.createCollection("webhooks");

// Create indexes
print("Creating indexes...");
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

// Insert sample data
print("Inserting sample data...");
try {
  db.pricing.insertMany([
    {
      service_type: "residential_moving",
      base_rate: 100.00,
      hourly_rate: 50.00,
      location: "general",
      effective_date: new Date(),
      created_at: new Date()
    },
    {
      service_type: "commercial_moving",
      base_rate: 200.00,
      hourly_rate: 75.00,
      location: "general",
      effective_date: new Date(),
      created_at: new Date()
    }
  ]);
  
  db.locations.insertMany([
    {
      zip_code: "90210",
      city: "Beverly Hills",
      state: "CA",
      country: "USA",
      coordinates: {
        type: "Point",
        coordinates: [-118.4065, 34.0901]
      },
      service_area: true,
      created_at: new Date()
    }
  ]);
  
  db.system_status.insertOne({
    initialized: true,
    version: "1.0.0",
    initialized_at: new Date(),
    environment: "fly.io"
  });
  
  print("Sample data inserted successfully");
} catch (e) {
  print("Sample data insertion error (might already exist): " + e);
}

print("MongoDB initialization completed successfully!");
EOF

    # Copy the script to the MongoDB container and execute it
    print_status "Uploading and executing initialization script..."
    
    # Upload the script
    fly sftp shell -a stahla-mongodb << SFTP_EOF
put $init_script /tmp/mongo_init.js
quit
SFTP_EOF

    # Execute the script
    fly ssh console -a stahla-mongodb -C "mongosh < /tmp/mongo_init.js"
    
    print_success "MongoDB initialization completed!"
    
    # Clean up
    rm -f "$init_script"
}

# Function to verify MongoDB initialization
verify_mongodb() {
    print_status "Verifying MongoDB initialization..."
    
    local mongo_db_name="${MONGO_DB_NAME:-stahla}"
    local mongo_app_user="${MONGO_USER:-stahla}"
    local mongo_app_password="${MONGO_PASSWORD}"
    
    # Test connection with application user
    local test_script="/tmp/mongo_test.js"
    cat > "$test_script" << EOF
// Test MongoDB connection and verify setup
try {
  use ${mongo_db_name};
  
  // Authenticate as application user
  db.auth("${mongo_app_user}", "${mongo_app_password}");
  
  // Test basic operations
  print("Testing collections...");
  print("Users collection: " + db.users.countDocuments());
  print("Quotes collection: " + db.quotes.countDocuments());
  print("Locations collection: " + db.locations.countDocuments());
  print("Pricing collection: " + db.pricing.countDocuments());
  
  // Test system status
  var status = db.system_status.findOne();
  if (status && status.initialized) {
    print("System status: INITIALIZED");
    print("Version: " + status.version);
    print("Environment: " + status.environment);
  } else {
    print("WARNING: System status not found or not initialized");
  }
  
  print("MongoDB verification completed successfully!");
} catch (e) {
  print("ERROR: MongoDB verification failed: " + e);
  quit(1);
}
EOF

    # Upload and execute verification script
    fly sftp shell -a stahla-mongodb << SFTP_EOF
put $test_script /tmp/mongo_test.js
quit
SFTP_EOF

    if fly ssh console -a stahla-mongodb -C "mongosh < /tmp/mongo_test.js"; then
        print_success "MongoDB verification passed!"
        
        # Generate MongoDB URL for the application
        local mongo_url="mongodb://${mongo_app_user}:${mongo_app_password}@stahla-mongodb.internal:27017/${mongo_db_name}"
        print_success "MongoDB URL for your application:"
        echo "$mongo_url"
        
        # Save to a file for easy reference
        echo "MONGO_URL=$mongo_url" > "$PROJECT_ROOT/mongodb_url.env"
        print_status "MongoDB URL saved to mongodb_url.env"
    else
        print_error "MongoDB verification failed!"
        return 1
    fi
    
    # Clean up
    rm -f "$test_script"
}

# Main function
main() {
    print_status "Starting MongoDB initialization for Fly.io..."
    
    # Load environment variables
    load_env
    
    # Check if MongoDB is ready
    if ! check_mongodb_ready; then
        print_error "MongoDB is not ready. Please ensure it's deployed and running."
        exit 1
    fi
    
    # Initialize MongoDB
    initialize_mongodb
    
    # Verify initialization
    verify_mongodb
    
    print_success "MongoDB initialization completed successfully!"
    print_status "You can now deploy your API service with the MongoDB URL."
}

# Script options
case "${1:-init}" in
    "init")
        main
        ;;
    "verify")
        load_env
        verify_mongodb
        ;;
    "help")
        echo "Usage: $0 [init|verify|help]"
        echo "  init   - Initialize MongoDB (default)"
        echo "  verify - Verify MongoDB setup"
        echo "  help   - Show this help"
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
