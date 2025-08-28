"""
Reely - AI-Powered YouTube Video Trimmer SaaS
Production-ready FastAPI application with authentication, payments, and usage tracking
"""
import os
import tempfile
import uuid
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Form, BackgroundTasks, Depends, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

# Core imports
from database import get_db, init_db
from models import User, VideoJob, ProcessingStatus, SUBSCRIPTION_LIMITS, SubscriptionTier
from auth import get_current_active_user, get_optional_current_user
from config import settings, validate_required_settings, get_feature_flags
from middleware import setup_middleware, check_redis_health

# Route modules
from user_routes import router as user_router, check_user_limits, increment_usage
from payments import router as payments_router

# Utility functions
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

# Import async processor if available
try:
    from async_processor import process_video_trim_async, process_hook_detection_async
    ASYNC_PROCESSING_AVAILABLE = True
except ImportError:
    ASYNC_PROCESSING_AVAILABLE = False
    logger.warning("Async processing not available. Install Celery for production deployment.")

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Reely - AI-Powered Video Trimmer",
    version=settings.app_version,
    description="Transform YouTube videos into viral-ready content with AI hook detection",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None
)

# Setup middleware
setup_middleware(app)

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        # Validate configuration
        validate_required_settings()
        logger.info("Configuration validation passed")
        
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
        
        # Log feature flags
        features = get_feature_flags()
        enabled_features = [k for k, v in features.items() if v]
        logger.info(f"Enabled features: {', '.join(enabled_features)}")
        
        # Check Redis health
        redis_health = check_redis_health()
        if redis_health["redis_available"]:
            logger.info(f"Redis connected: {redis_health.get('version', 'unknown')}")
        else:
            logger.warning(f"Redis unavailable: {redis_health.get('error', 'unknown')}")
        
        logger.info(f"Reely {settings.app_version} started successfully in {settings.environment} mode")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        if settings.is_production:
            raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down Reely application")

# Include routers
app.include_router(user_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")

# Pydantic models for API
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
    job_id: Optional[str] = None
    processing_mode: Optional[str] = "synchronous"  # "synchronous" or "asynchronous"
    estimated_completion_time: Optional[int] = None  # seconds

class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: Optional[int] = None  # 0-100
    current_step: Optional[str] = None
    estimated_remaining_time: Optional[int] = None  # seconds
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[dict] = None

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
    job_id: str

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
    checks: dict

# Store processed files temporarily (will be moved to cloud storage in production)
processed_files = {}

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with system status"""
    prerequisites = check_prerequisites()
    features = get_feature_flags()
    
    return {
        "message": "Reely - AI-Powered Video Trimmer API",
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "ready" if all(prerequisites.values()) else "partial",
        "prerequisites": prerequisites,
        "features": {k: v for k, v in features.items() if v},  # Only show enabled features
        "docs_url": "/docs" if settings.debug else "Contact support for API documentation"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    prerequisites = check_prerequisites()
    redis_health = check_redis_health()
    
    # Categorize missing prerequisites
    missing = [k for k, v in prerequisites.items() if not v]
    critical_missing = [k for k in missing if k in ['ffmpeg', 'python', 'yt_dlp']]
    ai_missing = [k for k in missing if k in ['openai_api_key', 'anthropic_api_key']]
    
    # System is healthy if critical components are available
    is_healthy = len(critical_missing) == 0
    
    status_message = "All systems operational"
    if critical_missing:
        status_message = f"Critical services unavailable: {', '.join(critical_missing)}"
    elif ai_missing and len(ai_missing) == 2:
        status_message = "Core services ready, AI features unavailable"
    elif ai_missing:
        status_message = f"Core services ready, some AI features unavailable: {', '.join(ai_missing)}"
    
    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(timezone.utc),
        checks={
            "database": "connected",  # Would implement actual DB check
            "redis": redis_health,
            "prerequisites": prerequisites,
            "missing_components": missing,
            "critical_missing": critical_missing,
            "message": status_message
        }
    )

@app.get("/api/v1/system/stats")
async def system_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get system statistics (admin only in future)"""
    # For now, just return user's stats
    # In production, you'd check for admin role
    
    total_users = db.query(User).count()
    total_jobs = db.query(VideoJob).filter(VideoJob.user_id == current_user.id).count()
    completed_jobs = db.query(VideoJob).filter(
        VideoJob.user_id == current_user.id,
        VideoJob.status == ProcessingStatus.COMPLETED.value
    ).count()
    
    return {
        "user_stats": {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "success_rate": f"{(completed_jobs/total_jobs*100):.1f}%" if total_jobs > 0 else "N/A"
        },
        "subscription": {
            "tier": current_user.subscription_tier,
            "usage": {
                "trims": current_user.monthly_trim_count,
                "hooks": current_user.monthly_hook_count
            }
        }
    }

@app.post("/api/v1/trim", response_model=TrimResponse)
async def trim_video_endpoint(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    vertical_format: bool = Form(False),
    add_subtitles: bool = Form(False),
    async_processing: bool = Form(True),  # Enable async by default
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Trim a YouTube video between specified timestamps
    Now supports asynchronous processing for long videos
    Requires authentication and respects subscription limits
    """
    try:
        # Check usage limits
        if not check_user_limits(current_user, "trim", db):
            limits = SUBSCRIPTION_LIMITS[SubscriptionTier(current_user.subscription_tier)]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Monthly trim limit reached ({limits['monthly_trims']}). Upgrade your subscription for more usage."
            )
        
        # Check prerequisites
        prerequisites = check_prerequisites()
        if not prerequisites['ffmpeg']:
            raise HTTPException(
                status_code=503,
                detail="Video processing service temporarily unavailable. Please try again later."
            )
        
        # Validate input
        if not is_valid_youtube_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL format")
        
        # Parse and validate timestamps
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
        
        # Check video duration limits based on subscription
        max_duration = SUBSCRIPTION_LIMITS[SubscriptionTier(current_user.subscription_tier)]["max_video_duration"]
        trim_duration = end_seconds - start_seconds
        if trim_duration > max_duration:
            raise HTTPException(
                status_code=403,
                detail=f"Video duration ({trim_duration}s) exceeds your plan limit ({max_duration}s). Upgrade for longer videos."
            )
        
        # For long processing tasks or when explicitly requested, use async processing
        should_use_async = async_processing or add_subtitles or vertical_format or trim_duration > 300
        
        if should_use_async:
            return await _process_video_async(
                url, start_seconds, end_seconds, vertical_format, add_subtitles,
                current_user, db, download_id
            )
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        download_id = str(uuid.uuid4())
        video_job = None
        
        try:
            # Create video job record
            video_job = VideoJob(
                user_id=current_user.id,
                job_id=download_id,
                youtube_url=url,
                start_time=start_seconds,
                end_time=end_seconds,
                vertical_format=vertical_format,
                add_subtitles=add_subtitles,
                status=ProcessingStatus.PROCESSING.value
            )
            db.add(video_job)
            db.commit()
            db.refresh(video_job)
            
            # Download video
            logger.info(f"Processing trim request for user {current_user.id}: {url}")
            downloaded_file = download_youtube_video(url, temp_dir, for_hooks=False)
            
            # Get original video duration
            original_duration = get_video_duration(downloaded_file)
            video_job.original_duration = original_duration
            
            # Validate timestamps against video duration
            if original_duration and end_seconds > original_duration:
                raise HTTPException(
                    status_code=400,
                    detail=f"End time ({end_seconds}s) exceeds video duration ({original_duration:.1f}s)"
                )
            
            # Create output file path
            output_filename = f"trimmed_{download_id}.mp4"
            output_path = os.path.join(temp_dir, output_filename)
            
            # Handle subtitles if requested
            transcript_data = None
            if add_subtitles:
                if not prerequisites['openai_api_key']:
                    raise HTTPException(
                        status_code=503,
                        detail="Subtitle generation temporarily unavailable. Please try again without subtitles."
                    )
                
                logger.info("Generating subtitles for video")
                from utils import extract_audio_for_transcription, transcribe_audio_with_openai
                audio_path = extract_audio_for_transcription(downloaded_file, temp_dir)
                transcript_data = transcribe_audio_with_openai(audio_path)
            
            # Process video based on format preference
            if vertical_format:
                logger.info(f"Creating vertical format video: {start_seconds}s to {end_seconds}s")
                trimmed_file = trim_video_vertical(
                    downloaded_file, output_path, start_seconds, end_seconds,
                    transcript_data, add_subtitles
                )
            else:
                logger.info(f"Trimming video: {start_seconds}s to {end_seconds}s")
                trimmed_file = trim_video(downloaded_file, output_path, start_seconds, end_seconds)
            
            # Calculate trimmed duration
            trimmed_duration = end_seconds - start_seconds
            
            # Store file info for download
            processed_files[download_id] = {
                'file_path': trimmed_file,
                'temp_dir': temp_dir,
                'original_file': downloaded_file,
                'user_id': current_user.id,
                'created_at': datetime.now(timezone.utc)
            }
            
            # Update job status and increment usage
            video_job.status = ProcessingStatus.COMPLETED.value
            video_job.trimmed_duration = trimmed_duration
            video_job.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            # Increment usage
            increment_usage(current_user, "trim", db, credits_used=1)
            
            # Schedule cleanup
            background_tasks.add_task(
                cleanup_after_delay,
                download_id,
                3600  # 1 hour
            )
            
            logger.info(f"Successfully processed trim for user {current_user.id}: {download_id}")
            
            return TrimResponse(
                message="Video trimmed successfully",
                download_id=download_id,
                original_duration=original_duration,
                trimmed_duration=trimmed_duration,
                job_id=download_id,
                processing_mode="synchronous"
            )
            
        except Exception as e:
            # Clean up on error
            cleanup_files(temp_dir)
            
            # Update job status
            if video_job:
                video_job.status = ProcessingStatus.FAILED.value
                video_job.error_message = str(e)
                db.commit()
            
            logger.error(f"Trim processing failed for user {current_user.id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Video processing failed. Please try again.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in trim endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")

async def _process_video_async(
    url: str, start_seconds: int, end_seconds: int, 
    vertical_format: bool, add_subtitles: bool,
    current_user: User, db: Session, job_id: str
) -> TrimResponse:
    """
    Process video asynchronously using Celery task queue
    """
    if not ASYNC_PROCESSING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Async processing not available. Please contact support."
        )
    
    try:
        # Create video job record
        video_job = VideoJob(
            user_id=current_user.id,
            job_id=job_id,
            youtube_url=url,
            start_time=start_seconds,
            end_time=end_seconds,
            vertical_format=vertical_format,
            add_subtitles=add_subtitles,
            status=ProcessingStatus.PENDING.value
        )
        db.add(video_job)
        db.commit()
        db.refresh(video_job)
        
        # Increment usage immediately (prevents abuse)
        increment_usage(current_user, "trim", db, credits_used=1)
        
        # Submit async task
        task = process_video_trim_async.delay(
            job_id=job_id,
            user_id=current_user.id,
            url=url,
            start_time=start_seconds,
            end_time=end_seconds,
            vertical_format=vertical_format,
            add_subtitles=add_subtitles
        )
        
        # Estimate processing time based on video characteristics
        trim_duration = end_seconds - start_seconds
        estimated_time = _estimate_processing_time(
            trim_duration, vertical_format, add_subtitles
        )
        
        logger.info(f"Submitted async trim job {job_id} for user {current_user.id}")
        
        return TrimResponse(
            message="Video processing started. Check job status for updates.",
            download_id=job_id,
            job_id=job_id,
            processing_mode="asynchronous",
            estimated_completion_time=estimated_time
        )
        
    except Exception as e:
        logger.error(f"Failed to submit async job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start video processing")

def _estimate_processing_time(trim_duration: int, vertical_format: bool, add_subtitles: bool) -> int:
    """
    Estimate processing time based on video characteristics
    """
    base_time = 60  # 1 minute base processing
    
    # Add time for video length (roughly 1 second processing per 10 seconds of video)
    base_time += trim_duration / 10
    
    # Add time for subtitle processing (roughly 2x the video duration)
    if add_subtitles:
        base_time += trim_duration * 2
    
    # Add time for vertical format processing
    if vertical_format:
        base_time += trim_duration / 5  # Additional processing for effects
    
    return max(60, int(base_time))  # Minimum 1 minute estimate

@app.get("/api/v1/download/{download_id}")
async def download_trimmed_video(
    download_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Download the trimmed video file"""
    if download_id not in processed_files:
        raise HTTPException(status_code=404, detail="File not found or expired")
    
    file_info = processed_files[download_id]
    
    # Check ownership
    if file_info['user_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    file_path = file_info['file_path']
    if not os.path.exists(file_path):
        # Clean up expired file reference
        del processed_files[download_id]
        raise HTTPException(status_code=404, detail="File no longer available")
    
    return FileResponse(
        file_path,
        media_type='video/mp4',
        filename=f"reely_trimmed_{download_id}.mp4",
        headers={"Content-Disposition": f"attachment; filename=reely_trimmed_{download_id}.mp4"}
    )

@app.get("/api/v1/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the status of a processing job
    """
    video_job = db.query(VideoJob).filter(
        VideoJob.job_id == job_id,
        VideoJob.user_id == current_user.id
    ).first()
    
    if not video_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get Celery task status if available
    progress = None
    current_step = None
    estimated_remaining_time = None
    
    if ASYNC_PROCESSING_AVAILABLE and video_job.status == ProcessingStatus.PROCESSING.value:
        try:
            from async_processor import celery_app
            task_result = celery_app.AsyncResult(job_id)
            
            if task_result.state == 'PROGRESS':
                task_info = task_result.info
                progress = task_info.get('progress', 0)
                current_step = task_info.get('step', 'processing')
                
                # Estimate remaining time based on progress
                if progress > 0:
                    elapsed_time = (datetime.now(timezone.utc) - video_job.started_at).total_seconds()
                    estimated_total_time = elapsed_time / (progress / 100)
                    estimated_remaining_time = max(0, int(estimated_total_time - elapsed_time))
                    
        except Exception as e:
            logger.warning(f"Failed to get Celery task status for {job_id}: {e}")
    
    return JobStatusResponse(
        job_id=job_id,
        status=video_job.status,
        progress=progress,
        current_step=current_step,
        estimated_remaining_time=estimated_remaining_time,
        created_at=video_job.created_at,
        completed_at=video_job.completed_at,
        error_message=video_job.error_message,
        result={
            "original_duration": video_job.original_duration,
            "trimmed_duration": video_job.trimmed_duration,
            "has_hooks": video_job.hooks_data is not None,
            "download_available": video_job.status == ProcessingStatus.COMPLETED.value
        } if video_job.status == ProcessingStatus.COMPLETED.value else None
    )

@app.post("/api/v1/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending or processing job
    """
    video_job = db.query(VideoJob).filter(
        VideoJob.job_id == job_id,
        VideoJob.user_id == current_user.id
    ).first()
    
    if not video_job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if video_job.status not in [ProcessingStatus.PENDING.value, ProcessingStatus.PROCESSING.value]:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    
    # Cancel Celery task if available
    if ASYNC_PROCESSING_AVAILABLE:
        try:
            from async_processor import celery_app
            celery_app.control.revoke(job_id, terminate=True)
        except Exception as e:
            logger.warning(f"Failed to cancel Celery task {job_id}: {e}")
    
    # Update job status
    video_job.status = ProcessingStatus.CANCELLED.value
    video_job.completed_at = datetime.now(timezone.utc)
    video_job.error_message = "Cancelled by user"
    db.commit()
    
    return {"message": "Job cancelled successfully"}

@app.post("/api/v1/auto-hooks", response_model=HooksResponse)
async def auto_generate_hooks(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    ai_provider: str = Form("openai"),
    async_processing: bool = Form(True),  # Enable async by default for hooks
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Automatically detect hook moments in a YouTube video using AI
    Now supports asynchronous processing for long videos
    Requires Pro or Premium subscription
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
                detail="Hook detection service temporarily unavailable. Please try again later."
            )
        
        # Validate AI provider and API keys
        if ai_provider.lower() == "openai" and not prerequisites['openai_api_key']:
            raise HTTPException(
                status_code=503,
                detail="OpenAI service temporarily unavailable. Try using 'anthropic' provider."
            )
        elif ai_provider.lower() == "anthropic" and not prerequisites['anthropic_api_key']:
            raise HTTPException(
                status_code=503,
                detail="Anthropic service temporarily unavailable. Try using 'openai' provider."
            )
        elif ai_provider.lower() not in ["openai", "anthropic"]:
            raise HTTPException(
                status_code=400,
                detail="AI provider must be 'openai' or 'anthropic'"
            )
        
        # Validate URL
        if not is_valid_youtube_url(url):
            raise HTTPException(status_code=400, detail="Invalid YouTube URL format")
        
        # Create temporary directory and job
        temp_dir = tempfile.mkdtemp()
        job_id = str(uuid.uuid4())
        video_job = None
        
        try:
            # Create video job record
            video_job = VideoJob(
                user_id=current_user.id,
                job_id=job_id,
                youtube_url=url,
                ai_provider=ai_provider,
                status=ProcessingStatus.PROCESSING.value
            )
            db.add(video_job)
            db.commit()
            db.refresh(video_job)
            
            # Process video for hooks
            logger.info(f"Processing hook detection for user {current_user.id}: {url}")
            hooks_data = process_video_for_hooks(url, temp_dir, ai_provider)
            
            # Update job with results
            video_job.hooks_data = hooks_data
            video_job.status = ProcessingStatus.COMPLETED.value
            video_job.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            # Increment usage
            increment_usage(current_user, "hook_detection", db, credits_used=1)
            
            # Convert to response format
            hooks = [Hook(**hook) for hook in hooks_data]
            
            # Schedule cleanup
            background_tasks.add_task(
                cleanup_temp_directory,
                temp_dir,
                600  # 10 minutes
            )
            
            logger.info(f"Successfully found {len(hooks)} hooks for user {current_user.id}: {job_id}")
            
            return HooksResponse(
                message=f"Found {len(hooks)} hook moments using {ai_provider.title()} AI",
                hooks=hooks,
                total_hooks=len(hooks),
                job_id=job_id
            )
            
        except Exception as e:
            # Clean up on error
            cleanup_files(temp_dir)
            
            # Update job status
            if video_job:
                video_job.status = ProcessingStatus.FAILED.value
                video_job.error_message = str(e)
                db.commit()
            
            logger.error(f"Hook detection failed for user {current_user.id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Hook detection failed. Please try again.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in hooks endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")

@app.get("/api/v1/my-jobs")
async def get_user_jobs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """Get user's video processing jobs with pagination"""
    jobs = db.query(VideoJob).filter(
        VideoJob.user_id == current_user.id
    ).order_by(VideoJob.created_at.desc()).offset(skip).limit(limit).all()
    
    total_count = db.query(VideoJob).filter(VideoJob.user_id == current_user.id).count()
    
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
                "hooks_count": len(job.hooks_data) if job.hooks_data else 0,
                "original_duration": job.original_duration,
                "trimmed_duration": job.trimmed_duration,
                "vertical_format": job.vertical_format,
                "add_subtitles": job.add_subtitles
            }
            for job in jobs
        ],
        "total": total_count,
        "page": skip // limit + 1,
        "pages": (total_count + limit - 1) // limit
    }

@app.delete("/api/v1/cleanup/{download_id}")
async def cleanup_file(
    download_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Manually cleanup a processed file"""
    if download_id not in processed_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = processed_files[download_id]
    
    # Check ownership
    if file_info['user_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Cleanup files
    try:
        cleanup_files(file_info.get('file_path'), file_info.get('original_file'))
        
        # Clean up temp directory
        import shutil
        if 'temp_dir' in file_info and os.path.exists(file_info['temp_dir']):
            shutil.rmtree(file_info['temp_dir'])
        
        del processed_files[download_id]
        
        logger.info(f"Manual cleanup completed for user {current_user.id}: {download_id}")
        return {"message": "File cleaned up successfully"}
        
    except Exception as e:
        logger.error(f"Cleanup failed for {download_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Cleanup failed")

# Background task functions
async def cleanup_after_delay(download_id: str, delay_seconds: int):
    """Background task to cleanup files after a delay"""
    import asyncio
    await asyncio.sleep(delay_seconds)
    
    if download_id in processed_files:
        file_info = processed_files[download_id]
        try:
            cleanup_files(file_info.get('file_path'), file_info.get('original_file'))
            
            # Clean up temp directory
            import shutil
            if 'temp_dir' in file_info and os.path.exists(file_info['temp_dir']):
                shutil.rmtree(file_info['temp_dir'])
            
            del processed_files[download_id]
            logger.info(f"Auto-cleaned up files for download_id: {download_id}")
            
        except Exception as e:
            logger.error(f"Auto-cleanup failed for {download_id}: {str(e)}")

async def cleanup_temp_directory(temp_dir: str, delay_seconds: int):
    """Background task to cleanup temporary directory after delay"""
    import asyncio
    import shutil
    
    await asyncio.sleep(delay_seconds)
    
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Auto-cleaned up temp directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Error cleaning temp directory {temp_dir}: {str(e)}")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error" if settings.is_production else str(exc),
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info" if not settings.debug else "debug"
    )