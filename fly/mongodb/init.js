// MongoDB initialization script for Fly.io deployment
// This script runs as part of the MongoDB container initialization

print("Starting MongoDB JavaScript initialization...");

// Get database name from environment variable
const dbName = process.env.MONGO_INITDB_DATABASE;
const appUser = process.env.MONGO_USER;
const appPassword = process.env.MONGO_PASSWORD;

// Switch to the application database
db = db.getSiblingDB(dbName);

print(`Working with database: ${dbName}`);

// Create sample data if needed
try {
  // Insert sample pricing data
  const samplePricing = [
    {
      service_type: "residential_moving",
      base_rate: 100.0,
      hourly_rate: 50.0,
      location: "general",
      effective_date: new Date(),
      created_at: new Date(),
    },
    {
      service_type: "commercial_moving",
      base_rate: 200.0,
      hourly_rate: 75.0,
      location: "general",
      effective_date: new Date(),
      created_at: new Date(),
    },
  ];

  db.pricing.insertMany(samplePricing);
  print("Sample pricing data inserted");

  // Insert sample location data
  const sampleLocations = [
    {
      zip_code: "90210",
      city: "Beverly Hills",
      state: "CA",
      country: "USA",
      coordinates: {
        type: "Point",
        coordinates: [-118.4065, 34.0901],
      },
      service_area: true,
      created_at: new Date(),
    },
  ];

  db.locations.insertMany(sampleLocations);
  print("Sample location data inserted");
} catch (e) {
  print("Note: Sample data might already exist or error occurred: " + e);
}

// Create a system status collection
try {
  db.system_status.insertOne({
    initialized: true,
    version: "1.0.0",
    initialized_at: new Date(),
    environment: "fly.io",
  });
  print("System status document created");
} catch (e) {
  print("System status document creation failed or already exists: " + e);
}

print("MongoDB JavaScript initialization completed successfully!");
