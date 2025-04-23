# Use an official Python runtime as a parent image
FROM python:3.13-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed (uncomment and adapt for Alpine if necessary)
# Alpine uses apk, not apt-get. Example:
# RUN apk update && apk add --no-cache build-base

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# This includes the 'app' directory and potentially others like 'assets', 'info'
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run the application
# This will be overridden by the command in docker-compose.yml for development,
# but serves as a default for running the container directly.
# Adjust 'app.main:app' if your FastAPI app instance is located differently.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
