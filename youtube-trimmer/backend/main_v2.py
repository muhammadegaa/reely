import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Form, BackgroundTasks, Depends, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

# Import database and auth
from database import get_db, init_db
from models import User, VideoJob, ProcessingStatus
from auth import get_current_active_user, get_optional_current_user
from user_routes import router as user_router, check_user_limits, increment_usage
from payments import router as payments_router

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

app = FastAPI(
    title="Reely - AI-Powered Video Trimmer", 
    version="2.0.0",
    description="Transform YouTube videos into viral-ready content with AI hook detection"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Include routers
app.include_router(user_router)
app.include_router(payments_router)

# Configure CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
    download_id: str
    original_duration: Optional[float] = None
    trimmed_duration: Optional[float] = None

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
        "message": "Reely - AI-Powered Video Trimmer API",
        "status": "ready" if all(prerequisites.values()) else "missing_prerequisites",
        "prerequisites": prerequisites,
        "version": "2.0.0"
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
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    vertical_format: bool = Form(False),
    add_subtitles: bool = Form(False),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Trim a YouTube video between specified timestamps
    Now requires authentication and respects usage limits
    """
    try:
        # Check authentication for registered users
        if current_user:
            # Check usage limits for authenticated users
            if not check_user_limits(current_user, "trim", db):
                from models import SUBSCRIPTION_LIMITS, SubscriptionTier
                limits = SUBSCRIPTION_LIMITS[SubscriptionTier(current_user.subscription_tier)]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Monthly trim limit reached ({limits['monthly_trims']}). Upgrade your subscription for more usage."
                )
        else:
            # For anonymous users, we require authentication
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please register or login to use Reely."
            )
        
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
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        video_job = None
        
        try:
            # Download video (higher quality if we need to process vertical format)
            print(f"Downloading video from: {url}")
            downloaded_file = download_youtube_video(url, temp_dir, for_hooks=False)
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
            
            # Create video job record for authenticated users
            if current_user:
                video_job = VideoJob(
                    user_id=current_user.id,
                    job_id=download_id,
                    youtube_url=url,
                    start_time=start_seconds,
                    end_time=end_seconds,
                    vertical_format=vertical_format,
                    add_subtitles=add_subtitles,
                    status=ProcessingStatus.PROCESSING.value,
                    original_duration=original_duration
                )
                db.add(video_job)
                db.commit()
            
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
            
            # Update job status and increment usage for authenticated users
            if current_user and video_job:
                video_job.status = ProcessingStatus.COMPLETED.value
                video_job.trimmed_duration = trimmed_duration
                video_job.completed_at = datetime.now(timezone.utc)
                increment_usage(current_user, "trim", db)
                db.commit()
            
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
            
            # Update job status for authenticated users
            if current_user and video_job:
                video_job.status = ProcessingStatus.FAILED.value
                video_job.error_message = str(e)
                db.commit()
            
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
        filename=f"reely_trimmed_{download_id}.mp4"
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

@app.post("/auto-hooks", response_model=HooksResponse)
async def auto_generate_hooks(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    ai_provider: str = Form("openai"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Automatically detect hook moments in a YouTube video using AI
    Requires authentication and Pro/Premium subscription
    """
    try:
        # Check subscription tier for AI features
        from payments import check_subscription_access
        if not check_subscription_access(current_user, ["hook_detection"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hook detection requires Pro or Premium subscription. Upgrade to access AI features."
            )
        
        # Check usage limits
        if not check_user_limits(current_user, "hook_detection", db):
            from models import SUBSCRIPTION_LIMITS, SubscriptionTier
            limits = SUBSCRIPTION_LIMITS[SubscriptionTier(current_user.subscription_tier)]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly hook detection limit reached ({limits['monthly_hooks']}). Upgrade for more usage."
            )
        
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
        video_job = None
        
        try:
            # Create video job record
            job_id = str(uuid.uuid4())
            video_job = VideoJob(
                user_id=current_user.id,
                job_id=job_id,
                youtube_url=url,
                ai_provider=ai_provider,
                status=ProcessingStatus.PROCESSING.value
            )
            db.add(video_job)
            db.commit()
            
            # Process video for hooks
            print(f"Processing video for hook detection: {url}")
            hooks_data = process_video_for_hooks(url, temp_dir, ai_provider)
            
            # Update job with results
            video_job.hooks_data = hooks_data
            video_job.status = ProcessingStatus.COMPLETED.value
            video_job.completed_at = datetime.now(timezone.utc)
            increment_usage(current_user, "hook_detection", db)
            db.commit()
            
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
            
            # Update job status on error
            if video_job:
                video_job.status = ProcessingStatus.FAILED.value
                video_job.error_message = str(e)
                db.commit()
            
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Add new authenticated endpoints
@app.get("/my-jobs")
async def get_user_jobs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """Get user's video processing jobs"""
    jobs = db.query(VideoJob).filter(
        VideoJob.user_id == current_user.id
    ).order_by(VideoJob.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "jobs": [
            {
                "id": job.job_id,
                "url": job.youtube_url,
                "status": job.status,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
                "has_hooks": job.hooks_data is not None,
                "hooks_count": len(job.hooks_data) if job.hooks_data else 0
            }
            for job in jobs
        ],
        "total": len(jobs)
    }

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