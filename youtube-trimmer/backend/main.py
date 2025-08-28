import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Form, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from utils import (
    is_valid_youtube_url,
    parse_timestamp,
    download_youtube_video,
    trim_video,
    trim_video_vertical,
    get_video_duration,
    cleanup_files,
    check_prerequisites,
    process_video_for_hooks
)
from job_manager import job_manager, JobStatus

app = FastAPI(title="YouTube Video Trimmer", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrimRequest(BaseModel):
    url: str
    start_time: str
    end_time: str
    vertical_format: Optional[bool] = False
    add_subtitles: Optional[bool] = False

class TrimResponse(BaseModel):
    message: str
    job_id: str
    status: str
    progress: int
    download_id: Optional[str] = None
    original_duration: Optional[float] = None
    trimmed_duration: Optional[float] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None

class HooksRequest(BaseModel):
    url: str
    ai_provider: Optional[str] = "openai"

class Hook(BaseModel):
    start: int
    end: int
    title: str
    reason: Optional[str] = None

class HooksResponse(BaseModel):
    message: str
    hooks: List[Hook]
    total_hooks: int

# Store processed files temporarily
processed_files = {}

@app.get("/")
async def root():
    prerequisites = check_prerequisites()
    return {
        "message": "YouTube Video Trimmer API",
        "status": "ready" if all(prerequisites.values()) else "missing_prerequisites",
        "prerequisites": prerequisites
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with system requirements status"""
    prerequisites = check_prerequisites()
    missing = [k for k, v in prerequisites.items() if not v]
    
    # Categorize missing prerequisites
    critical_missing = [k for k in missing if k in ['ffmpeg', 'python', 'yt_dlp']]
    ai_missing = [k for k in missing if k in ['openai_api_key', 'anthropic_api_key']]
    
    # System is healthy if critical components are available
    is_healthy = len(critical_missing) == 0
    
    status_message = "All systems ready"
    if critical_missing:
        status_message = f"Critical missing: {', '.join(critical_missing)}"
    elif ai_missing and len(ai_missing) == 2:
        status_message = "Core ready, but no AI API keys configured"
    elif ai_missing:
        status_message = f"Core ready, missing: {', '.join(ai_missing)}"
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "prerequisites": prerequisites,
        "missing": missing,
        "critical_missing": critical_missing,
        "ai_missing": ai_missing,
        "message": status_message
    }

@app.post("/trim", response_model=TrimResponse)
async def trim_video_endpoint(
    url: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    vertical_format: bool = Form(False),
    add_subtitles: bool = Form(False)
):
    """
    Start a video trimming job (async processing)
    """
    try:
        # Check prerequisites
        prerequisites = check_prerequisites()
        if not prerequisites['ffmpeg']:
            raise HTTPException(
                status_code=503, 
                detail="FFmpeg is not installed. Please install FFmpeg to process videos."
            )
        
        # Validate input
        if not is_valid_youtube_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        # Parse timestamps
        try:
            start_seconds = parse_timestamp(start_time)
            end_seconds = parse_timestamp(end_time)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        if start_seconds >= end_seconds:
            raise HTTPException(
                status_code=400, 
                detail="Start time must be less than end time"
            )
        
        # Check if subtitles requested but no OpenAI key
        if add_subtitles and not prerequisites['openai_api_key']:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key required for subtitle generation."
            )
        
        # Create job
        job_id = job_manager.create_job(
            job_type="trim",
            url=url,
            start_time=start_seconds,
            end_time=end_seconds,
            vertical_format=vertical_format,
            add_subtitles=add_subtitles
        )
        
        # Start processing in background
        job_manager.start_trim_job(job_id)
        
        return TrimResponse(
            message="Video trimming started. Use job_id to check progress.",
            job_id=job_id,
            status="queued",
            progress=0
        )
            print(f"Downloaded to: {downloaded_file}")
            
            # Get original video duration
            original_duration = get_video_duration(downloaded_file)
            
            # Validate timestamps against video duration
            if original_duration and end_seconds > original_duration:
                raise HTTPException(
                    status_code=400,
                    detail=f"End time ({end_seconds}s) exceeds video duration ({original_duration}s)"
                )
            
            # Create output file path
            download_id = str(uuid.uuid4())
            output_filename = f"trimmed_{download_id}.mp4"
            output_path = os.path.join(temp_dir, output_filename)
            
            # Get transcript data if subtitles are requested
            transcript_data = None
            if add_subtitles:
                print("Getting transcript for subtitles...")
                from utils import extract_audio_for_transcription, transcribe_audio_with_openai
                
                # Check if we have OpenAI API key for transcription
                if not check_prerequisites()['openai_api_key']:
                    raise HTTPException(
                        status_code=503,
                        detail="OpenAI API key required for subtitle generation. Please configure OPENAI_API_KEY."
                    )
                
                # Extract and transcribe audio
                audio_path = extract_audio_for_transcription(downloaded_file, temp_dir)
                transcript_data = transcribe_audio_with_openai(audio_path)
            
            # Choose processing method based on format preference
            if vertical_format:
                print(f"Processing video for TikTok/Instagram format: {start_seconds}s to {end_seconds}s")
                trimmed_file = trim_video_vertical(
                    downloaded_file, output_path, start_seconds, end_seconds, 
                    transcript_data, add_subtitles
                )
            else:
                print(f"Trimming video: {start_seconds}s to {end_seconds}s")
                trimmed_file = trim_video(downloaded_file, output_path, start_seconds, end_seconds)
            
            # Get trimmed video duration
            trimmed_duration = end_seconds - start_seconds
            
            # Store file info for download
            processed_files[download_id] = {
                'file_path': trimmed_file,
                'temp_dir': temp_dir,
                'original_file': downloaded_file
            }
            
            # Schedule cleanup after 1 hour
            background_tasks.add_task(
                cleanup_after_delay, 
                download_id, 
                3600  # 1 hour
            )
            
            return TrimResponse(
                message="Video trimmed successfully",
                download_id=download_id,
                original_duration=original_duration,
                trimmed_duration=trimmed_duration
            )
            
        except Exception as e:
            # Clean up on error
            cleanup_files(temp_dir)
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/download/{download_id}")
async def download_trimmed_video(download_id: str):
    """
    Download the trimmed video file
    """
    if download_id not in processed_files:
        raise HTTPException(status_code=404, detail="File not found or expired")
    
    file_info = processed_files[download_id]
    file_path = file_info['file_path']
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type='video/mp4',
        filename=f"trimmed_video_{download_id}.mp4"
    )

@app.delete("/cleanup/{download_id}")
async def cleanup_file(download_id: str):
    """
    Manually cleanup a processed file
    """
    if download_id in processed_files:
        file_info = processed_files[download_id]
        cleanup_files(
            file_info['file_path'],
            file_info['original_file']
        )
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(file_info['temp_dir'])
        except Exception as e:
            print(f"Error cleaning temp dir: {e}")
        
        del processed_files[download_id]
        return {"message": "File cleaned up successfully"}
    
    raise HTTPException(status_code=404, detail="File not found")

async def cleanup_after_delay(download_id: str, delay_seconds: int):
    """
    Background task to cleanup files after a delay
    """
    import asyncio
    await asyncio.sleep(delay_seconds)
    
    if download_id in processed_files:
        file_info = processed_files[download_id]
        cleanup_files(
            file_info['file_path'],
            file_info['original_file']
        )
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(file_info['temp_dir'])
        except Exception as e:
            print(f"Error cleaning temp dir: {e}")
        
        del processed_files[download_id]
        print(f"Auto-cleaned up files for download_id: {download_id}")

@app.post("/auto-hooks", response_model=HooksResponse)
async def auto_generate_hooks(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    ai_provider: str = Form("openai")
):
    """
    Automatically detect hook moments in a YouTube video using AI
    """
    try:
        # Check prerequisites
        prerequisites = check_prerequisites()
        if not prerequisites['ffmpeg']:
            raise HTTPException(
                status_code=503,
                detail="FFmpeg is not installed. Please install FFmpeg to process videos."
            )
        
        # Check AI API keys
        if ai_provider.lower() == "openai" and not prerequisites['openai_api_key']:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )
        elif ai_provider.lower() == "anthropic" and not prerequisites['anthropic_api_key']:
            raise HTTPException(
                status_code=503,
                detail="Anthropic API key not configured. Please set ANTHROPIC_API_KEY environment variable."
            )
        
        # Validate input
        if not is_valid_youtube_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        # Validate AI provider
        if ai_provider.lower() not in ["openai", "anthropic"]:
            raise HTTPException(
                status_code=400,
                detail="AI provider must be 'openai' or 'anthropic'"
            )
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Process video for hooks
            print(f"Processing video for hook detection: {url}")
            hooks_data = process_video_for_hooks(url, temp_dir, ai_provider)
            
            # Convert to response format
            hooks = [Hook(**hook) for hook in hooks_data]
            
            # Schedule cleanup after 10 minutes (shorter than video files since no download needed)
            background_tasks.add_task(
                cleanup_temp_directory,
                temp_dir,
                600  # 10 minutes
            )
            
            return HooksResponse(
                message=f"Found {len(hooks)} hook moments using {ai_provider.title()}",
                hooks=hooks,
                total_hooks=len(hooks)
            )
            
        except Exception as e:
            # Clean up on error
            cleanup_files(temp_dir)
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

async def cleanup_temp_directory(temp_dir: str, delay_seconds: int):
    """
    Background task to cleanup temporary directory after delay
    """
    import asyncio
    import shutil
    
    await asyncio.sleep(delay_seconds)
    
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Auto-cleaned up temp directory: {temp_dir}")
    except Exception as e:
        print(f"Error cleaning temp directory {temp_dir}: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)