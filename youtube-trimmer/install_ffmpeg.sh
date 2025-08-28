#!/bin/bash

# FFmpeg Installation Script
echo "🔧 Installing FFmpeg..."

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        echo "📦 Installing FFmpeg on Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v yum &> /dev/null; then
        echo "📦 Installing FFmpeg on CentOS/RHEL..."
        sudo yum install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        echo "📦 Installing FFmpeg on Fedora..."
        sudo dnf install -y ffmpeg
    else
        echo "❌ Unsupported Linux distribution. Please install FFmpeg manually."
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        echo "🍺 Installing FFmpeg via Homebrew..."
        brew install ffmpeg
    else
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "   Then run: brew install ffmpeg"
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    if command -v choco &> /dev/null; then
        echo "🍫 Installing FFmpeg via Chocolatey..."
        choco install ffmpeg
    else
        echo "❌ Chocolatey not found. Please:"
        echo "   1. Install Chocolatey: https://chocolatey.org/install"
        echo "   2. Run: choco install ffmpeg"
        echo "   OR"
        echo "   Download FFmpeg from: https://ffmpeg.org/download.html"
        exit 1
    fi
else
    echo "❌ Unsupported operating system: $OSTYPE"
    echo "Please install FFmpeg manually from: https://ffmpeg.org/download.html"
    exit 1
fi

# Verify installation
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg installed successfully!"
    ffmpeg -version | head -1
else
    echo "❌ FFmpeg installation failed. Please install manually."
    exit 1
fi