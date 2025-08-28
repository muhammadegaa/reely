"""
Enhanced API documentation configuration for Reely
"""

# API Documentation Metadata
API_TITLE = "Reely API"
API_DESCRIPTION = """
## Transform YouTube videos into viral-ready content with AI

Reely is an AI-powered video trimmer that helps content creators extract the most engaging moments from YouTube videos and convert them to viral-ready formats for TikTok, Instagram Reels, and YouTube Shorts.

### Key Features

🎯 **AI Hook Detection** - Automatically identify the most engaging moments in your videos using advanced AI analysis

✂️ **Smart Video Trimming** - Precise video trimming with timestamp validation and duration checks

📱 **Viral Format Conversion** - Convert videos to vertical format optimized for TikTok and Instagram Reels

💬 **Auto Subtitles** - Generate accurate subtitles using OpenAI's Whisper API

🔐 **User Authentication** - Secure JWT-based authentication with subscription management

💳 **Stripe Integration** - Seamless payment processing with Pro and Premium tiers

📊 **Usage Tracking** - Monitor your monthly usage and subscription limits

### Subscription Tiers

| Feature | Free | Pro | Premium |
|---------|------|-----|---------|
| Video Trims | 5/month | 100/month | Unlimited |
| AI Hook Detection | ❌ | 50/month | Unlimited |
| Max Video Duration | 5 minutes | 30 minutes | 2 hours |
| Vertical Format | ❌ | ✅ | ✅ |
| Auto Subtitles | ❌ | ✅ | ✅ |
| API Access | ❌ | ✅ | ✅ |
| Priority Processing | ❌ | ❌ | ✅ |

### Getting Started

1. **Sign Up** - Create your free account using `/auth/register`
2. **Authenticate** - Get your JWT tokens with `/auth/login`
3. **Trim Videos** - Submit YouTube URLs to `/trim` endpoint
4. **Download Results** - Use the provided download ID to get your processed video

### Rate Limiting

All endpoints are rate-limited to ensure fair usage:
- Authentication endpoints: 10 requests per 15 minutes
- Video processing: 20 requests per hour (free tier)
- Payment endpoints: 5 requests per hour

### API Keys

Premium subscribers can access the API programmatically using API keys instead of JWT tokens.

### Support

For support, feature requests, or bug reports, contact us at support@reely.app
"""

API_VERSION = "2.0.0"

# Tags for organizing endpoints
TAGS_METADATA = [
    {
        "name": "Authentication",
        "description": "User registration, login, and account management operations."
    },
    {
        "name": "Video Processing", 
        "description": "Core video trimming and AI hook detection functionality."
    },
    {
        "name": "Payments",
        "description": "Stripe integration for subscription management and billing."
    },
    {
        "name": "User Management",
        "description": "User profile and usage statistics endpoints."
    },
    {
        "name": "System",
        "description": "Health checks and system status endpoints."
    }
]

# Example responses for documentation
EXAMPLE_RESPONSES = {
    "trim_success": {
        "message": "Video trimmed successfully",
        "download_id": "123e4567-e89b-12d3-a456-426614174000",
        "original_duration": 180.5,
        "trimmed_duration": 30.0
    },
    "hooks_success": {
        "message": "Found 3 hook moments using OpenAI",
        "hooks": [
            {
                "start": 15,
                "end": 25,
                "title": "Surprising revelation",
                "reason": "Sudden change in speaker tone and unexpected information"
            },
            {
                "start": 45,
                "end": 55,
                "title": "Emotional peak",
                "reason": "High emotional intensity and audience engagement markers"
            },
            {
                "start": 120,
                "end": 130,
                "title": "Call to action",
                "reason": "Strong directive language and urgency indicators"
            }
        ],
        "total_hooks": 3
    },
    "user_profile": {
        "id": 123,
        "email": "user@example.com",
        "full_name": "John Doe",
        "is_active": True,
        "is_verified": True,
        "subscription_tier": "pro",
        "monthly_trim_count": 15,
        "monthly_hook_count": 8,
        "created_at": "2024-01-15T10:30:00Z"
    },
    "usage_stats": {
        "monthly_trims_used": 15,
        "monthly_hooks_used": 8,
        "monthly_trims_limit": 100,
        "monthly_hooks_limit": 50,
        "subscription_tier": "pro",
        "days_until_reset": 12
    },
    "subscription_status": {
        "has_subscription": True,
        "tier": "pro",
        "status": "active",
        "current_period_start": "2024-01-01T00:00:00Z",
        "current_period_end": "2024-02-01T00:00:00Z"
    },
    "rate_limit_error": {
        "error": "Rate limit exceeded",
        "message": "Too many requests. Limit: 20 per 3600 seconds",
        "retry_after": 3600
    },
    "authentication_error": {
        "detail": "Authentication required. Please register or login to use Reely."
    },
    "usage_limit_error": {
        "detail": "Monthly trim limit reached (5). Upgrade your subscription for more usage."
    }
}

# OpenAPI Schema Extensions
OPENAPI_SCHEMA_EXTRA = {
    "info": {
        "contact": {
            "name": "Reely Support",
            "email": "support@reely.app",
            "url": "https://reely.app/support"
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        },
        "termsOfService": "https://reely.app/terms"
    },
    "servers": [
        {
            "url": "https://api.reely.app",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.reely.app", 
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ],
    "externalDocs": {
        "description": "Find more info here",
        "url": "https://docs.reely.app"
    }
}

# Security schemes
SECURITY_SCHEMES = {
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    },
    "apiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key"
    }
}

# Custom CSS for documentation
CUSTOM_CSS = """
.swagger-ui .topbar {
    background-color: #6366f1;
}
.swagger-ui .topbar-wrapper .link {
    color: white;
}
"""

# API Examples and Code Samples
CODE_EXAMPLES = {
    "python": """
import requests

# Authentication
auth_response = requests.post(
    "https://api.reely.app/auth/login",
    data={
        "username": "your-email@example.com",
        "password": "your-password"
    }
)
token = auth_response.json()["access_token"]

# Trim a video
headers = {"Authorization": f"Bearer {token}"}
trim_response = requests.post(
    "https://api.reely.app/trim",
    headers=headers,
    data={
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "start_time": "0:30",
        "end_time": "1:00",
        "vertical_format": True
    }
)
download_id = trim_response.json()["download_id"]

# Download the result
download_url = f"https://api.reely.app/download/{download_id}"
video_file = requests.get(download_url, headers=headers)
with open("trimmed_video.mp4", "wb") as f:
    f.write(video_file.content)
""",
    "javascript": """
// Authentication
const authResponse = await fetch('https://api.reely.app/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: 'username=your-email@example.com&password=your-password'
});
const { access_token } = await authResponse.json();

// Trim a video
const formData = new FormData();
formData.append('url', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
formData.append('start_time', '0:30');
formData.append('end_time', '1:00');
formData.append('vertical_format', 'true');

const trimResponse = await fetch('https://api.reely.app/trim', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${access_token}`
    },
    body: formData
});
const { download_id } = await trimResponse.json();

// Download the result
const downloadResponse = await fetch(
    `https://api.reely.app/download/${download_id}`,
    {
        headers: { 'Authorization': `Bearer ${access_token}` }
    }
);
const videoBlob = await downloadResponse.blob();
""",
    "curl": """
# Authentication
curl -X POST "https://api.reely.app/auth/login" \\
    -H "Content-Type: application/x-www-form-urlencoded" \\
    -d "username=your-email@example.com&password=your-password"

# Extract the access_token from response, then:

# Trim a video
curl -X POST "https://api.reely.app/trim" \\
    -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
    -F "url=https://www.youtube.com/watch?v=dQw4w9WgXcQ" \\
    -F "start_time=0:30" \\
    -F "end_time=1:00" \\
    -F "vertical_format=true"

# Download the result (replace DOWNLOAD_ID with actual ID)
curl -X GET "https://api.reely.app/download/DOWNLOAD_ID" \\
    -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
    -o "trimmed_video.mp4"
"""
}