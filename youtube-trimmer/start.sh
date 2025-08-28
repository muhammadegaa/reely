#!/bin/bash

# YouTube Trimmer Startup Script

echo "🚀 Starting YouTube Trimmer Application..."
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+"
    exit 1
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg is not installed. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Homebrew not found. Please install FFmpeg manually:"
        echo "   macOS: brew install ffmpeg"
        echo "   Ubuntu: sudo apt install ffmpeg"
        echo "   Windows: choco install ffmpeg"
        exit 1
    fi
fi

echo "✅ Prerequisites check complete!"
echo ""

# Start backend
echo "🐍 Starting FastAPI backend server..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"
echo ""

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Start frontend
echo "⚛️  Starting React frontend server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"
echo ""

echo "🎉 Application started successfully!"
echo ""
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Function to handle cleanup
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for user input to keep script running
wait