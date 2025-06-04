# Multi-service Dockerfile for Stahla application
# Includes MongoDB, Redis, FastAPI, and Nginx in a single container

FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
  wget \
  gnupg \
  lsb-release \
  software-properties-common \
  curl \
  build-essential \
  supervisor \
  nginx \
  python3 \
  python3-pip \
  python3-venv \
  && rm -rf /var/lib/apt/lists/*

# Install MongoDB
RUN wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - && \
  echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
  apt-get update && \
  apt-get install -y mongodb-org && \
  rm -rf /var/lib/apt/lists/*

# Install Redis
RUN add-apt-repository ppa:redislabs/redis && \
  apt-get update && \
  apt-get install -y redis-server && \
  rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy application files
COPY app ./app
COPY requirements.txt ./requirements.txt

# Copy static files to nginx directory
COPY app/static /usr/share/nginx/html

# Copy configuration files
COPY fly/nginx/nginx.conf /etc/nginx/nginx.conf
COPY fly/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy MongoDB initialization files
COPY fly/mongodb/init.js ./init-mongo.js
COPY fly/mongodb/init.sh ./init-mongo.sh

# Create Python virtual environment and install dependencies
RUN python3 -m venv /app/venv && \
  . /app/venv/bin/activate && \
  pip install --upgrade pip && \
  pip install -r requirements.txt

# Create necessary directories
RUN mkdir -p /data/mongodb /data/redis /data/logs /var/log/nginx && \
  chown -R mongodb:mongodb /data/mongodb && \
  chown -R redis:redis /data/redis && \
  chown -R www-data:www-data /var/log/nginx

# Copy service initialization script
COPY startup.sh ./startup.sh
COPY fly/init.sh ./init.sh
RUN chmod +x ./startup.sh ./init-mongo.sh ./init.sh

# Remove default nginx site
RUN rm -f /etc/nginx/sites-enabled/default

# Expose ports
EXPOSE 80 443 8000 27017 6379

# Set environment variables
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Default command - will be overridden by fly.toml processes
CMD ["./startup.sh"]
