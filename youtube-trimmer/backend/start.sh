#!/bin/bash

# Reely Backend Startup Script
# This script sets up and starts the Reely backend application

set -e  # Exit on any error

echo "🚀 Starting Reely Backend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install/update dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file with your configuration before running again.${NC}"
    echo -e "${YELLOW}📝 Essential settings to configure:${NC}"
    echo "   - JWT_SECRET_KEY (for security)"
    echo "   - OPENAI_API_KEY or ANTHROPIC_API_KEY (for AI features)"
    echo "   - STRIPE_SECRET_KEY (for payments)"
    echo "   - DATABASE_URL (for production)"
    exit 1
fi

# Check critical environment variables
echo -e "${BLUE}🔍 Checking configuration...${NC}"
source .env

if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "your-super-secret-jwt-key-change-this-in-production" ]; then
    echo -e "${RED}❌ JWT_SECRET_KEY not configured properly!${NC}"
    exit 1
fi

# Initialize database
echo -e "${BLUE}🗄️  Initializing database...${NC}"
python3 -c "
from database import init_db, health_check
try:
    init_db()
    health = health_check()
    if health['status'] == 'healthy':
        print('✅ Database initialized successfully')
    else:
        print(f'⚠️  Database status: {health[\"status\"]}')
        print(f'   Details: {health}')
except Exception as e:
    print(f'❌ Database initialization failed: {e}')
    exit(1)
"

# Check prerequisites
echo -e "${BLUE}🔍 Checking system prerequisites...${NC}"
python3 -c "
from utils import check_prerequisites
import json

prereqs = check_prerequisites()
missing = [k for k, v in prereqs.items() if not v]

print('System Prerequisites:')
for k, v in prereqs.items():
    status = '✅' if v else '❌'
    print(f'  {status} {k}')

if missing:
    critical = [k for k in missing if k in ['ffmpeg', 'python', 'yt_dlp']]
    if critical:
        print(f'\n❌ Critical components missing: {", ".join(critical)}')
        print('Please install missing components before running the server.')
        exit(1)
    else:
        print(f'\n⚠️  Optional components missing: {", ".join(missing)}')
        print('Some features may not be available.')
else:
    print('\n✅ All prerequisites satisfied!')
"

# Start the server
echo -e "${GREEN}🚀 Starting Reely server...${NC}"
echo -e "${GREEN}📡 Server will be available at: http://localhost:8000${NC}"
echo -e "${GREEN}📚 API docs (development): http://localhost:8000/docs${NC}"
echo -e "${GREEN}❤️  Health check: http://localhost:8000/health${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"

# Run the application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload