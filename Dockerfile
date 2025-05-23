# Use an official Python runtime as a parent image
FROM python:3.13-alpine

# Install build dependencies required by psutil
RUN apk update && apk add --no-cache gcc python3-dev musl-dev linux-headers

# Set the working directory in the container
WORKDIR /code

# Copy the requirements file into the container at /code
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container at /code/app
COPY ./app /code/app

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable (optional, can be set in docker-compose.yml)
# ENV NAME World

# Command to run the app - for Fly.io deployment
# In production, we don't use --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
