"""
Vercel serverless function handler for Reely FastAPI app
This file adapts the FastAPI app to work with Vercel's serverless environment
"""
import os
import sys

# Add the parent directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import Mangum
from main_vercel import app

# Create the Mangum handler for Vercel
handler = Mangum(app, lifespan="off")

# Export as the default function for Vercel
def handler_func(request, context=None):
    """Vercel handler function"""
    return handler(request, context)

# For Vercel compatibility
def lambda_handler(event, context):
    """AWS Lambda compatible handler"""
    return handler(event, context)

# Main app for development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)