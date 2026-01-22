# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies (needed for Postgres, etc.)
RUN apt-get update && apt-get install -y netcat

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install gunicorn  # Ensure gunicorn is installed

# Copy project
COPY . /app/

# Copy entrypoint script and give execution permissions
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Run the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]