# YouTube Trimmer with AI Hook Detection

A powerful YouTube video trimmer that can automatically detect engaging "hook moments" using AI analysis. Trim videos manually or let AI find the most compelling 15-30 second clips for you.

## Features

- **Manual Trimming**: Trim YouTube videos with precise timestamps
- **AI Hook Detection**: Automatically find engaging moments using OpenAI GPT-4 or Anthropic Claude
- **Audio Transcription**: Uses OpenAI Whisper for accurate transcription
- **Multiple Formats**: Support for various timestamp formats (HH:MM:SS, MM:SS, seconds)
- **Fast Processing**: Optimized for quick video processing and streaming

## Prerequisites

### System Requirements
- **Python 3.8+**
- **Node.js 16+**
- **FFmpeg** (required for video processing)

### Install FFmpeg
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### API Keys (for AI features)
You need at least one of the following:
- **OpenAI API Key** (recommended - provides both transcription and analysis)
- **Anthropic API Key** (for Claude analysis, still needs OpenAI for Whisper transcription)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd youtube-trimmer
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
```

### 4. Configure Environment Variables
Edit `backend/.env` and add your API keys:
```env
# Required for AI hook detection
OPENAI_API_KEY=your_openai_api_key_here

# Optional alternative (still needs OpenAI for transcription)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Running the Application

### Start Backend Server
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python main.py
```
Server will run at: http://localhost:8000

### Start Frontend Development Server
```bash
cd frontend
npm run dev
```
Frontend will run at: http://localhost:5173

## Usage

### Manual Trimming
1. Enter a YouTube URL
2. Specify start and end times (HH:MM:SS, MM:SS, or seconds)
3. Click "Trim Video"
4. Download the trimmed video

### AI Hook Detection
1. Enter a YouTube URL
2. Choose AI provider (OpenAI recommended)
3. Click "Auto-Generate Hooks"
4. Review AI-suggested hook moments
5. Click "Use This Hook" on any suggestion
6. The timestamps will auto-populate in the manual trim form
7. Click "Trim Video" to process

## API Endpoints

### Core Endpoints
- `GET /` - API status and health check
- `GET /health` - Detailed system health check
- `POST /trim` - Manual video trimming
- `POST /auto-hooks` - AI hook detection
- `GET /download/{download_id}` - Download processed video
- `DELETE /cleanup/{download_id}` - Manual cleanup

### Hook Detection Workflow
1. **Download**: Video is downloaded using yt-dlp
2. **Audio Extraction**: FFmpeg extracts audio for transcription
3. **Transcription**: OpenAI Whisper transcribes the audio
4. **Analysis**: AI analyzes transcript for engaging moments
5. **Response**: Returns 3-5 hook suggestions with timestamps

## Configuration

### Supported AI Providers
- **OpenAI**: Uses GPT-4 for analysis + Whisper for transcription
- **Anthropic**: Uses Claude for analysis + OpenAI Whisper for transcription

### Video Processing Limits
- Maximum resolution: 720p (for faster processing)
- Automatic cleanup after 1 hour (trimmed videos) or 10 minutes (temp files)
- Concurrent processing supported

### Error Handling
- Comprehensive error messages for missing dependencies
- API rate limit handling
- Graceful fallbacks for AI failures
- Automatic temporary file cleanup

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   ```bash
   # Verify FFmpeg installation
   ffmpeg -version
   ```

2. **API key errors**
   - Ensure your API keys are valid and have sufficient credits
   - Check that .env file is in the backend directory
   - Restart the backend server after adding keys

3. **Transcription fails**
   - Audio files over 25MB may fail with OpenAI Whisper
   - Try shorter videos or different formats

4. **Hook detection returns empty results**
   - Video may be too short (< 1 minute)
   - Content may not have clear engaging moments
   - Try different AI provider

### Performance Tips
- Use shorter videos (< 10 minutes) for faster processing
- OpenAI provider is generally faster than Anthropic
- Manual trimming is much faster than AI hook detection

## Development

### Backend Structure
```
backend/
├── main.py           # FastAPI application
├── utils.py          # Video processing & AI utilities  
├── requirements.txt  # Python dependencies
├── .env.example     # Environment template
└── venv/           # Virtual environment
```

### Frontend Structure
```
frontend/
├── src/
│   ├── App.jsx      # Main React component
│   └── main.jsx     # React entry point
├── package.json     # Node dependencies
└── vite.config.js   # Vite configuration
```

### Adding New Features
1. Backend functions go in `utils.py`
2. API endpoints go in `main.py`
3. Frontend components go in `App.jsx`
4. Update requirements/dependencies as needed

## License

This project is for educational and personal use. Ensure you comply with YouTube's Terms of Service and respect content creators' rights.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Verify all prerequisites are installed
3. Check API key configuration
4. Review server logs for detailed error messages