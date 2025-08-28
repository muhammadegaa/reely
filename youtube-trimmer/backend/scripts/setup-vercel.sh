#!/bin/bash

# Reely - Vercel Deployment Setup Script
# This script helps set up your Vercel deployment for the Reely SaaS platform

set -e

echo "🚀 Setting up Reely for Vercel deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    print_error "Vercel CLI not found. Installing..."
    npm install -g vercel
    print_status "Vercel CLI installed"
else
    print_status "Vercel CLI found"
fi

# Login to Vercel (if not already logged in)
print_info "Checking Vercel authentication..."
if ! vercel whoami &> /dev/null; then
    print_warning "Not logged into Vercel. Please log in:"
    vercel login
else
    print_status "Already logged into Vercel as $(vercel whoami)"
fi

# Initialize Vercel project
print_info "Setting up Vercel project..."
if [ ! -f ".vercel/project.json" ]; then
    vercel --confirm
    print_status "Vercel project initialized"
else
    print_status "Vercel project already exists"
fi

# Set up environment variables
print_info "Setting up environment variables..."
print_warning "You'll need to set up the following environment variables in Vercel:"
echo ""
echo "=== REQUIRED ENVIRONMENT VARIABLES ==="
echo "DATABASE_URL - Your PostgreSQL database URL"
echo "REDIS_URL - Your Upstash Redis URL"
echo "JWT_SECRET_KEY - Your JWT secret key"
echo "OPENAI_API_KEY - Your OpenAI API key"
echo "STRIPE_SECRET_KEY - Your Stripe secret key"
echo "CORS_ORIGINS - Your frontend domain(s)"
echo ""

# Create environment variables from template
if [ -f ".env.production" ]; then
    print_info "Environment template found. Setting variables in Vercel..."
    
    # Read environment variables and set them
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ $key =~ ^[[:space:]]*# ]] || [[ -z $key ]]; then
            continue
        fi
        
        # Remove quotes if present
        value=$(echo "$value" | sed 's/^"//' | sed 's/"$//')
        
        # Set non-sensitive variables automatically
        case $key in
            "ENVIRONMENT"|"DEBUG"|"APP_NAME"|"APP_VERSION"|"CORS_ORIGINS"|"RATE_LIMIT_REQUESTS_PER_MINUTE"|"RATE_LIMIT_BURST")
                if [[ ! -z $value && $value != *"your-"* && $value != *"password"* ]]; then
                    echo "Setting $key..."
                    vercel env add "$key" production <<< "$value" 2>/dev/null || echo "Variable $key may already exist"
                fi
                ;;
        esac
    done < .env.production
    
    print_status "Basic environment variables set"
    print_warning "Please manually set sensitive variables (API keys, database URLs, etc.) in Vercel dashboard"
else
    print_error ".env.production not found. Please copy from .env.production.example"
fi

# Deploy to Vercel
print_info "Ready to deploy to Vercel!"
echo ""
print_info "To deploy your app:"
echo "1. Set up your database (Vercel Postgres, Supabase, or PlanetScale)"
echo "2. Set up Upstash Redis"
echo "3. Configure environment variables in Vercel dashboard"
echo "4. Run: vercel --prod"
echo ""

read -p "Would you like to deploy now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Deploying to Vercel..."
    vercel --prod
    print_status "Deployment complete! 🎉"
    
    # Get deployment URL
    DEPLOYMENT_URL=$(vercel --prod 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
    if [ ! -z "$DEPLOYMENT_URL" ]; then
        print_status "Your app is live at: $DEPLOYMENT_URL"
        print_info "API endpoints:"
        echo "  - Health Check: $DEPLOYMENT_URL/health"
        echo "  - API Docs: $DEPLOYMENT_URL/docs"
        echo "  - OpenAPI: $DEPLOYMENT_URL/openapi.json"
    fi
else
    print_info "Deployment skipped. Run 'vercel --prod' when ready."
fi

echo ""
print_status "Setup complete! 🚀"
print_info "Next steps:"
echo "1. Set up your database schema by running migrations"
echo "2. Configure your frontend to use the new API URL"
echo "3. Set up domain and SSL in Vercel dashboard"
echo "4. Configure webhooks for Stripe payments"
echo ""
print_info "For support, check the deployment guide or GitHub issues."