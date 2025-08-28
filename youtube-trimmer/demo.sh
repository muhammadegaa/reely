#!/bin/bash

# YouTube Trimmer Demo Setup Script

echo "🎥 YouTube Video Trimmer - Demo Setup"
echo "====================================="
echo ""

# Check current directory
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Please run this script from the youtube-trimmer directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "🔍 Checking prerequisites..."
echo ""

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo "✅ Python: $PYTHON_VERSION"
else
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js: $NODE_VERSION"
else
    echo "❌ Node.js not found. Please install Node.js 16+"
    exit 1
fi

# Check FFmpeg
if command_exists ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)
    echo "✅ FFmpeg: $FFMPEG_VERSION"
    FFMPEG_READY=true
else
    echo "⚠️  FFmpeg not found"
    FFMPEG_READY=false
fi

echo ""

# Setup backend
echo "🐍 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment and installing dependencies..."
source venv/bin/activate
pip install -q fastapi uvicorn python-multipart yt-dlp

echo "✅ Backend setup complete"
echo ""

# Setup frontend
echo "⚛️  Setting up frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install --quiet
fi

echo "✅ Frontend setup complete"
echo ""

# FFmpeg installation
if [ "$FFMPEG_READY" = false ]; then
    echo "🔧 FFmpeg Installation Required"
    echo ""
    echo "FFmpeg is required for video processing. You have a few options:"
    echo ""
    echo "1. Run the automated installer (recommended):"
    echo "   ./install_ffmpeg.sh"
    echo ""
    echo "2. Install manually:"
    echo "   macOS:    brew install ffmpeg"
    echo "   Ubuntu:   sudo apt install ffmpeg"
    echo "   Windows:  choco install ffmpeg"
    echo ""
    read -p "Would you like to run the automated installer now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd ..
        ./install_ffmpeg.sh
        if [ $? -eq 0 ]; then
            FFMPEG_READY=true
        fi
    fi
fi

# Final instructions
cd ..
echo ""
echo "🎉 Setup Complete!"
echo ""

if [ "$FFMPEG_READY" = true ]; then
    echo "✅ All dependencies are installed and ready!"
    echo ""
    echo "🚀 To start the application:"
    echo "   ./start.sh"
    echo ""
    echo "Or start manually:"
    echo "1. Backend:  cd backend && source venv/bin/activate && python main.py"
    echo "2. Frontend: cd frontend && npm run dev"
    echo ""
    echo "Then visit: http://localhost:5173"
else
    echo "⚠️  Setup complete, but FFmpeg is still missing."
    echo "Please install FFmpeg before running the application."
    echo ""
    echo "After installing FFmpeg, start with:"
    echo "   ./start.sh"
fi

echo ""
echo "📚 For more information, see README.md"