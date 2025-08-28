#!/bin/bash

# Reely Production Deployment Script
set -e

echo "🚀 Starting Reely production deployment..."

# Check if environment file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create one from .env.example"
    exit 1
fi

# Load environment variables
source .env

# Build and deploy
echo "📦 Building Docker images..."
docker-compose -f docker-compose.prod.yml build

echo "🗃️ Starting services..."
docker-compose -f docker-compose.prod.yml up -d

echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check if services are running
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Services are running!"
    
    # Run database migrations if needed
    echo "🔄 Running database setup..."
    docker-compose -f docker-compose.prod.yml exec api python database.py
    
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📊 Service Status:"
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "📝 Next steps:"
    echo "1. Configure your domain DNS to point to this server"
    echo "2. Set up SSL certificates in ./ssl/"
    echo "3. Update Stripe webhook endpoints"
    echo "4. Configure monitoring alerts"
    
else
    echo "❌ Deployment failed. Check logs:"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi