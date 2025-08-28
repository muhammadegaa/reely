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
    check_prerequisites,
    download_youtube_video,
    get_video_duration
)
from job_manager import job_manager, JobStatus
import subprocess

app = FastAPI(title="YouTube Video Trimmer", version="2.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrimResponse(BaseModel):
    message: str
    job_id: str
    status: str
    progress: int
    download_id: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None

class HooksResponse(BaseModel):
    message: str
    job_id: str
    status: str
    progress: int

class PreviewRequest(BaseModel):
    url: str
    start_time: float
    end_time: float
    filters: Optional[dict] = None

@app.get("/")
async def root():
    prerequisites = check_prerequisites()
    return {
        "message": "YouTube Video Trimmer API v2.0 - Async Processing",
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
    Start a video trimming job (async processing) - NO MORE TIMEOUTS!
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
        
        # Start processing in background immediately
        job_manager.start_trim_job(job_id)
        
        return TrimResponse(
            message="Video trimming started! Check progress with /job/{job_id}",
            job_id=job_id,
            status="queued",
            progress=0
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get real-time job progress and status - NEVER TIMES OUT!
    """
    job_data = job_manager.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job_data["id"],
        status=job_data["status"].value,
        progress=job_data["progress"],
        message=job_data["message"],
        result=job_data["result"],
        error=job_data["error"]
    )

@app.post("/auto-hooks", response_model=HooksResponse)
async def auto_generate_hooks(
    url: str = Form(...),
    ai_provider: str = Form("openai")
):
    """
    AI hook detection with async processing - NO MORE TIMEOUTS!
    """
    try:
        # Check prerequisites
        prerequisites = check_prerequisites()
        if not prerequisites['ffmpeg']:
            raise HTTPException(
                status_code=503,
                detail="FFmpeg is not installed."
            )
        
        # Check AI API keys
        if ai_provider.lower() == "openai" and not prerequisites['openai_api_key']:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured."
            )
        elif ai_provider.lower() == "anthropic" and not prerequisites['anthropic_api_key']:
            raise HTTPException(
                status_code=503,
                detail="Anthropic API key not configured."
            )
        
        # Validate input
        if not is_valid_youtube_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        if ai_provider.lower() not in ["openai", "anthropic"]:
            raise HTTPException(
                status_code=400,
                detail="AI provider must be 'openai' or 'anthropic'"
            )
        
        # Create job
        job_id = job_manager.create_job(
            job_type="hooks",
            url=url,
            ai_provider=ai_provider
        )
        
        # Start processing in background
        job_manager.start_hooks_job(job_id)
        
        return HooksResponse(
            message="Hook detection started! Check progress with /job/{job_id}",
            job_id=job_id,
            status="queued",
            progress=0
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/preview")
async def generate_video_preview(
    url: str = Form(...),
    start_time: float = Form(...),
    end_time: float = Form(...),
    brightness: int = Form(100),
    contrast: int = Form(100),
    saturation: int = Form(100)
):
    """
    Generate actual trimmed video preview with filters applied
    """
    try:
        # Validate input
        if not is_valid_youtube_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        if start_time >= end_time:
            raise HTTPException(status_code=400, detail="Start time must be less than end time")
        
        # Create temporary directory for preview
        temp_dir = tempfile.mkdtemp(prefix="preview_")
        preview_id = str(uuid.uuid4())
        
        try:
            # Download video
            print(f"Downloading video for preview: {url}")
            video_path = download_youtube_video(url, temp_dir)
            
            # Generate preview with filters
            preview_filename = f"preview_{preview_id}.mp4"
            preview_path = os.path.join(temp_dir, preview_filename)
            
            # Build FFmpeg filter string for visual adjustments
            filters = []
            if brightness != 100:
                filters.append(f"eq=brightness={(brightness - 100) / 100.0}")
            if contrast != 100:
                filters.append(f"eq=contrast={contrast / 100.0}")
            if saturation != 100:
                filters.append(f"eq=saturation={saturation / 100.0}")
            
            filter_str = ",".join(filters) if filters else None
            
            # FFmpeg command to create preview
            cmd = [
                "ffmpeg", "-i", video_path,
                "-ss", str(start_time),
                "-t", str(end_time - start_time),
                "-c:v", "libx264",
                "-crf", "28",  # Faster encoding for preview
                "-preset", "fast",
                "-movflags", "faststart",
                "-y"  # Overwrite output
            ]
            
            if filter_str:
                cmd.extend(["-vf", filter_str])
            
            cmd.append(preview_path)
            
            print(f"Generating preview: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            if not os.path.exists(preview_path):
                raise Exception("Preview file was not created")
            
            # Store preview path temporarily (cleanup after 10 minutes)
            preview_info = {
                "path": preview_path,
                "temp_dir": temp_dir,
                "created_at": os.path.getmtime(preview_path)
            }
            
            # Simple in-memory storage for previews (in production, use Redis or similar)
            if not hasattr(app.state, 'previews'):
                app.state.previews = {}
            app.state.previews[preview_id] = preview_info
            
            return {
                "preview_id": preview_id,
                "message": "Preview generated successfully",
                "duration": end_time - start_time,
                "filters_applied": {
                    "brightness": brightness,
                    "contrast": contrast,
                    "saturation": saturation
                }
            }
            
        except Exception as e:
            # Cleanup on error
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Preview generation failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preview/{preview_id}")
async def get_video_preview(preview_id: str):
    """
    Serve the generated video preview file
    """
    if not hasattr(app.state, 'previews') or preview_id not in app.state.previews:
        raise HTTPException(status_code=404, detail="Preview not found")
    
    preview_info = app.state.previews[preview_id]
    preview_path = preview_info["path"]
    
    if not os.path.exists(preview_path):
        raise HTTPException(status_code=404, detail="Preview file not found")
    
    return FileResponse(
        preview_path,
        media_type='video/mp4',
        filename=f"preview_{preview_id}.mp4"
    )

@app.get("/download/{job_id}")
async def download_trimmed_video(job_id: str):
    """
    Download the processed video file
    """
    file_path = job_manager.get_file_path(job_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found or job not completed")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type='video/mp4',
        filename=f"trimmed_video_{job_id}.mp4"
    )

@app.delete("/cleanup/{job_id}")
async def cleanup_job(job_id: str):
    """
    Manually cleanup a job and its files
    """
    job_data = job_manager.get_job(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_manager.cleanup_job(job_id)
    return {"message": "Job cleaned up successfully"}

# Background cleanup task
import asyncio
import threading

def start_cleanup_scheduler():
    """Start background cleanup of old jobs and previews"""
    def cleanup_old_jobs():
        import time
        import shutil
        while True:
            try:
                current_time = time.time()
                
                # Clean up jobs older than 1 hour
                jobs_to_clean = []
                for job_id, job in job_manager.jobs.items():
                    if current_time - job.created_at > 3600:  # 1 hour
                        jobs_to_clean.append(job_id)
                
                for job_id in jobs_to_clean:
                    print(f"Auto-cleaning old job: {job_id}")
                    job_manager.cleanup_job(job_id)
                
                # Clean up previews older than 10 minutes
                if hasattr(app.state, 'previews'):
                    previews_to_clean = []
                    for preview_id, preview_info in app.state.previews.items():
                        if current_time - preview_info["created_at"] > 600:  # 10 minutes
                            previews_to_clean.append(preview_id)
                    
                    for preview_id in previews_to_clean:
                        preview_info = app.state.previews[preview_id]
                        try:
                            shutil.rmtree(preview_info["temp_dir"], ignore_errors=True)
                            print(f"Auto-cleaning old preview: {preview_id}")
                        except Exception as e:
                            print(f"Preview cleanup error: {e}")
                        del app.state.previews[preview_id]
                
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                print(f"Cleanup error: {e}")
                time.sleep(60)
    
    thread = threading.Thread(target=cleanup_old_jobs, daemon=True)
    thread.start()

# Start cleanup scheduler when app starts
@app.on_event("startup")
async def startup_event():
    start_cleanup_scheduler()
    print("🚀 Async Video Processor Started - NO MORE TIMEOUTS!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_async:app", host="0.0.0.0", port=8000, reload=True)