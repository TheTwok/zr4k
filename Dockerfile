# Stage 1: Build the frontend dashboard
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the python app
FROM python:3.10-slim
WORKDIR /usr/src/app

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code and runner scripts
COPY backend/ ./backend/
COPY run.py .
COPY run_tunnel.py .

# Copy the compiled frontend static files from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Ensure the persistent data directory exists and is writable
USER root
RUN mkdir -p /app/data && chmod 777 /app/data

# Command to launch the services
CMD ["python", "run.py"]
