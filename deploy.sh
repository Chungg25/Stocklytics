#!/bin/bash
# Deployment script for Alphahubiq on Oracle VPS

echo "🚀 Starting Deployment Process..."

# Pull latest code
echo "📦 Pulling latest code from GitHub..."
git pull origin main

# Build and start containers in detached mode
echo "🐳 Building and starting Docker containers..."
docker-compose up --build -d

# Prune old images to save disk space
echo "🧹 Cleaning up unused Docker images..."
docker image prune -f

echo "✅ Deployment Successful!"
echo "Frontend running on Port 3000"
echo "Backend running on Port 8000"
