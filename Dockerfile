# Stage 1: Build the React frontend
FROM node:18-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the Python backend
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies for Playwright and Postgres
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its browser dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy the backend code
COPY app/ ./app/

# Copy the built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set environment variables
ENV PIPELINE_MODE=strict
ENV PIPELINE_CATEGORY=vehicles
ENV PORT=10000

# Expose the port
EXPOSE 10000

# Command to run the application
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"
