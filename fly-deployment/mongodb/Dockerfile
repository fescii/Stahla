FROM mongo:7

# Copy initialization scripts
COPY init-mongo-fly.js /docker-entrypoint-initdb.d/
COPY init-mongo-fly.sh /docker-entrypoint-initdb.d/

# Make sure scripts are executable
RUN chmod +x /docker-entrypoint-initdb.d/init-mongo-fly.sh

# MongoDB requires these directories
RUN mkdir -p /data/db /data/configdb && \
  chown -R mongodb:mongodb /data/db /data/configdb

# MongoDB port
EXPOSE 27017

# Start MongoDB with authentication
CMD ["mongod", "--auth", "--bind_ip_all"]
