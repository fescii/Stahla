## Deploying to Fly.io

This application can be deployed to Fly.io using the provided configuration. Follow these steps to deploy:

### Prerequisites

1. Install the Fly.io CLI (flyctl):

   ```
   # On macOS
   brew install flyctl

   # On Linux
   curl -L https://fly.io/install.sh | sh

   # On Windows (using PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. Sign up and log in to Fly.io:

   ```
   flyctl auth signup
   # OR
   flyctl auth login
   ```

3. **Set up an external MongoDB service** (e.g., MongoDB Atlas):

   - Create a MongoDB Atlas account or use another MongoDB service
   - Create a cluster
   - Set up a database user and password
   - Add your IP address to the network access whitelist (or allow all IP addresses for Fly.io deployment)
   - Get the connection string

   Important: On first deployment, the application will automatically initialize the MongoDB collections and create the required indexes.

4. Ensure you have a valid `.env` file with all required environment variables, including MongoDB connection details.

### Automated Deployment

We've created a deployment script to simplify the process:

1. Make the script executable (if not already):

   ```
   chmod +x deploy-to-fly.sh
   ```

2. Run the deployment script:
   ```
   ./deploy-to-fly.sh
   ```

This script will:

- Check if you're logged in to Fly.io
- Create a new Fly.io application if it doesn't exist
- Set up your environment variables from `.env` as Fly.io secrets
- Create a volume for Redis (MongoDB is external)
- Allocate a shared IPv4 address (free)
- Deploy the application

### Manual Deployment

If you prefer to deploy manually:

1. Create a new Fly.io application:

   ```
   flyctl apps create stahla
   ```

2. Set environment variables for MongoDB and other services:

   ```
   # MongoDB connection details (required)
   flyctl secrets set MONGO_HOST=your-mongodb-host
   flyctl secrets set MONGO_USER=your-mongodb-user
   flyctl secrets set MONGO_PASSWORD=your-mongodb-password
   flyctl secrets set MONGO_DB_NAME=your-mongodb-database

   # Redis URL (using local Redis in container)
   flyctl secrets set REDIS_URL=redis://localhost:6379/0

   # Set other environment variables as needed
   ```

3. Create a volume for Redis:

   ```
   flyctl volumes create redis_data --size 1 --region iad
   ```

4. Allocate a shared IPv4 address:

   ```
   flyctl ips allocate-v4 --shared
   ```

5. Deploy the application:
   ```
   flyctl deploy
   ```

### Monitoring Your Deployment

- View deployment status: `flyctl status -a stahla`
- Check logs: `flyctl logs -a stahla`
- Open the application in a browser: `flyctl open -a stahla`

### Scaling

To scale your application on Fly.io:

```
# Scale to multiple instances
flyctl scale count 3
```

For more information, refer to the [Fly.io documentation](https://fly.io/docs/apps/).

### Architecture

The application deployed to Fly.io has the following components:

1. **FastAPI Application**: The main application running on port 8000.
2. **Nginx**: Acting as a reverse proxy, handling static files and forwarding requests to the FastAPI application.
3. **Redis**: Running in the same container for caching and session management.
4. **MongoDB**: External database service (e.g., MongoDB Atlas) for data storage.

### Service Configuration

#### Nginx

Nginx is configured to:

- Serve static files directly from `/static/`
- Forward all other requests to the FastAPI application
- Handle API requests at `/api/`

The Nginx configuration is at `./nginx/nginx.config` and is included in the deployment.

#### MongoDB Initialization

On startup, the application will:

1. Connect to your external MongoDB service using the provided credentials
2. Create the necessary collections if they don't exist:
   - users
   - sheet_products
   - sheet_generators
   - sheet_branches
   - sheet_config
   - bland_call_logs
   - error_logs
   - dashboard_stats
3. Set up required indexes for optimal performance

You can check if the MongoDB initialization was successful in the logs:

```
flyctl logs -a stahla | grep 'MongoDB initialization'
```

### Important Notes on MongoDB

Due to limitations in Alpine Linux (the base image used for Fly.io), MongoDB Shell (`mongosh`) is not available. Therefore, the MongoDB initialization must be done in one of these ways:

1. **Run the local initialization script** before deploying:

   ```bash
   # Initialize MongoDB collections from your local machine
   ./init-external-mongo.sh
   ```

2. **Have your application initialize MongoDB on startup**:
   Ensure your FastAPI application creates collections and indexes when it starts up if they don't exist.

3. **Use MongoDB Atlas UI**:
   You can also create collections and indexes directly from the MongoDB Atlas web interface.

The MongoDB connection is tested during startup, but collection creation is best handled outside of the Fly.io deployment.

### Troubleshooting MongoDB Connection

If you're experiencing issues with MongoDB connectivity, you can use these steps to diagnose:

1. **Check MongoDB connection variables**:

   ```bash
   flyctl secrets list | grep MONGO
   ```

2. **Check the MongoDB initialization logs**:

   ```bash
   flyctl logs -a stahla | grep "MongoDB initialization"
   ```

3. **Test the MongoDB connection**:
   You can SSH into your Fly machine and test the MongoDB connection directly:

   ```bash
   flyctl ssh console -a stahla
   mongosh "mongodb://your-mongo-host" -u your-mongo-user -p your-mongo-password
   ```

4. **Verify MongoDB collections**:
   After connecting to MongoDB via shell, check if collections were created:

   ```javascript
   use your_database
   show collections
   // Should display: users, sheet_products, sheet_generators, etc.
   ```

5. **If you need to manually run the initialization script**:
   ```bash
   flyctl ssh console -a stahla
   sh /code/fly-init-mongo.sh
   ```

Remember that MongoDB Atlas and other MongoDB services may have network restrictions. Make sure to whitelist all IPs or at least the Fly.io IP range in your MongoDB Atlas network settings.

### Common Deployment Issues

#### TOML Configuration Errors

If you see errors like:

```
Error: failed loading app config from fly.toml: toml: table http_service already exists
```

This means there are duplicate sections in your `fly.toml` file. Check to ensure you don't have multiple sections with the same name (e.g., `[http_service]` appearing twice).

Fix by:

```bash
# Check if the configuration is valid
fly config validate

# If not, edit the fly.toml file to remove duplicates
nano fly.toml
```

#### MongoDB Connection Issues

If the application can't connect to MongoDB:

1. Verify your MongoDB connection secrets are set correctly:

   ```bash
   fly secrets list | grep MONGO
   ```

2. Make sure your MongoDB service allows connections from Fly.io (check network access settings).

3. Try running the MongoDB initialization script manually:
   ```bash
   fly ssh console -C "sh /code/fly-init-mongo.sh"
   ```

### Viewing API Logs

To check the API logs for your deployed application, you can use the following Fly.io commands:

#### View All Logs

```bash
# View all logs in real-time
fly logs -a stahla

# View recent logs (last 100 lines)
fly logs -a stahla --lines 100
```

#### Filter API Logs

You can filter logs to focus on specific components or messages:

```bash
# Filter for FastAPI application logs
fly logs -a stahla | grep "INFO\|ERROR\|WARNING"

# Filter for specific endpoints
fly logs -a stahla | grep "GET\|POST\|PUT\|DELETE"

# Filter for error messages
fly logs -a stahla | grep -i "error\|exception\|failed"
```

#### View Structured Logs

If your application uses structured logging (JSON format):

```bash
# Extract and format JSON logs (requires jq)
fly logs -a stahla | grep -o '{.*}' | jq
```

#### Check Specific Instance Logs

If you have multiple instances running:

```bash
# List all instances
fly status -a stahla

# View logs from a specific instance
fly logs -a stahla -i <instance-id>
```

You can also view logs directly in the Fly.io dashboard by visiting:
https://fly.io/apps/stahla/monitoring
