"""
Asynchronous Video Processing with Celery/Redis
Production-ready solution for handling long video processing tasks
"""
import os
import tempfile
import uuid
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from celery import Celery
from sqlalchemy.orm import sessionmaker
from database import get_db_session
from models import VideoJob, ProcessingStatus
from utils import (
    download_youtube_video, 
    trim_video_vertical, 
    trim_video,
    extract_audio_for_transcription,
    transcribe_audio_with_openai,
    cleanup_files,
    get_video_duration
)
from config import settings

# Configure Celery
celery_app = Celery(
    'reely_processor',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['async_processor']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_routes={
        'async_processor.process_video_trim': {'queue': 'video_processing'},
        'async_processor.process_hook_detection': {'queue': 'hook_detection'},
    },
    worker_pool='prefork',
    worker_concurrency=2,  # Adjust based on server capacity
)

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name='async_processor.process_video_trim')
def process_video_trim_async(
    self, 
    job_id: str, 
    user_id: int, 
    url: str, 
    start_time: int, 
    end_time: int,
    vertical_format: bool = False,
    add_subtitles: bool = False
) -> Dict:
    """
    Asynchronously process video trimming with progress tracking
    """
    db = None
    temp_dir = None
    
    try:
        # Update job status to processing
        db = next(get_db_session())
        video_job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
        
        if not video_job:
            raise Exception(f"Job {job_id} not found")
        
        video_job.status = ProcessingStatus.PROCESSING.value
        video_job.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"reely_job_{job_id}_")
        
        # Step 1: Download video (optimized quality based on format)
        self.update_state(state='PROGRESS', meta={'step': 'downloading', 'progress': 10})
        logger.info(f"Job {job_id}: Downloading video")
        
        downloaded_file = download_youtube_video(url, temp_dir, for_hooks=False)
        
        # Get original video duration
        original_duration = get_video_duration(downloaded_file)
        video_job.original_duration = original_duration
        db.commit()
        
        # Step 2: Handle subtitle generation if needed (optimized approach)
        transcript_data = None
        if add_subtitles:
            self.update_state(state='PROGRESS', meta={'step': 'transcribing', 'progress': 30})
            logger.info(f"Job {job_id}: Processing subtitles")
            
            # Extract only the segment we need for subtitles
            segment_audio_path = extract_segment_audio(
                downloaded_file, temp_dir, start_time, end_time
            )
            
            # Transcribe only the trimmed segment
            transcript_data = transcribe_audio_with_openai(
                segment_audio_path, for_hooks=False
            )
        
        # Step 3: Process video
        self.update_state(state='PROGRESS', meta={'step': 'processing', 'progress': 70})
        logger.info(f"Job {job_id}: Processing video format")
        
        output_filename = f"trimmed_{job_id}.mp4"
        output_path = os.path.join(temp_dir, output_filename)
        
        if vertical_format:
            trimmed_file = trim_video_vertical(
                downloaded_file, output_path, start_time, end_time,
                transcript_data, add_subtitles
            )
        else:
            trimmed_file = trim_video(downloaded_file, output_path, start_time, end_time)
        
        # Step 4: Store processed file information
        self.update_state(state='PROGRESS', meta={'step': 'finalizing', 'progress': 90})
        
        # In production, upload to S3/cloud storage here
        file_info = {
            'file_path': trimmed_file,
            'temp_dir': temp_dir,
            'original_file': downloaded_file,
            'user_id': user_id,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Update job as completed
        video_job.status = ProcessingStatus.COMPLETED.value
        video_job.completed_at = datetime.now(timezone.utc)
        video_job.trimmed_duration = end_time - start_time
        video_job.file_path = trimmed_file  # Store file path
        db.commit()
        
        logger.info(f"Job {job_id}: Processing completed successfully")
        
        return {
            'status': 'completed',
            'job_id': job_id,
            'file_info': file_info,
            'original_duration': original_duration,
            'trimmed_duration': end_time - start_time
        }
        
    except Exception as e:
        # Update job status on error
        if db and video_job:
            try:
                video_job.status = ProcessingStatus.FAILED.value
                video_job.error_message = str(e)
                video_job.completed_at = datetime.now(timezone.utc)
                db.commit()
            except:
                pass
        
        # Cleanup on error
        if temp_dir:
            cleanup_files(temp_dir)
        
        logger.error(f"Job {job_id}: Processing failed - {str(e)}")
        
        # Retry logic for transient failures
        if self.request.retries < self.max_retries:
            if "network" in str(e).lower() or "timeout" in str(e).lower():
                raise self.retry(countdown=60 * (self.request.retries + 1))
        
        raise Exception(f"Video processing failed: {str(e)}")
        
    finally:
        if db:
            db.close()

def extract_segment_audio(video_path: str, temp_dir: str, start_time: int, end_time: int) -> str:
    """
    Extract only the audio segment we need for transcription
    This dramatically reduces transcription time
    """
    import subprocess
    
    segment_audio_path = os.path.join(temp_dir, "segment_audio.wav")
    duration = end_time - start_time
    
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-ss', str(start_time),
        '-t', str(duration),
        '-vn',  # No video
        '-acodec', 'pcm_s16le',
        '-ar', '16000',  # 16kHz sample rate for Whisper
        '-ac', '1',  # Mono
        segment_audio_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    
    if not os.path.exists(segment_audio_path):
        raise Exception("Audio segment extraction failed")
    
    return segment_audio_path

@celery_app.task(bind=True, name='async_processor.process_hook_detection')
def process_hook_detection_async(
    self,
    job_id: str,
    user_id: int,
    url: str,
    ai_provider: str = "openai"
) -> Dict:
    """
    Asynchronously process hook detection with optimized approach
    """
    from utils import process_video_for_hooks
    
    db = None
    temp_dir = None
    
    try:
        # Update job status
        db = next(get_db_session())
        video_job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
        
        if not video_job:
            raise Exception(f"Job {job_id} not found")
        
        video_job.status = ProcessingStatus.PROCESSING.value
        video_job.started_at = datetime.now(timezone.utc)
        db.commit()
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"reely_hooks_{job_id}_")
        
        self.update_state(state='PROGRESS', meta={'step': 'analyzing', 'progress': 50})
        
        # Process hooks (already optimized for long videos)
        hooks_data = process_video_for_hooks(url, temp_dir, ai_provider)
        
        # Update job with results
        video_job.hooks_data = hooks_data
        video_job.status = ProcessingStatus.COMPLETED.value
        video_job.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"Hook detection job {job_id}: Found {len(hooks_data)} hooks")
        
        return {
            'status': 'completed',
            'job_id': job_id,
            'hooks': hooks_data,
            'total_hooks': len(hooks_data)
        }
        
    except Exception as e:
        if db and video_job:
            try:
                video_job.status = ProcessingStatus.FAILED.value
                video_job.error_message = str(e)
                video_job.completed_at = datetime.now(timezone.utc)
                db.commit()
            except:
                pass
        
        if temp_dir:
            cleanup_files(temp_dir)
        
        logger.error(f"Hook detection job {job_id}: Failed - {str(e)}")
        raise Exception(f"Hook detection failed: {str(e)}")
        
    finally:
        if db:
            db.close()

@celery_app.task(name='async_processor.cleanup_expired_files')
def cleanup_expired_files():
    """
    Periodic task to clean up expired temporary files
    """
    import shutil
    from glob import glob
    import time
    
    temp_pattern = "/tmp/reely_*"
    current_time = time.time()
    cleanup_age = 3600  # 1 hour
    
    for temp_path in glob(temp_pattern):
        try:
            if os.path.isdir(temp_path):
                stat = os.stat(temp_path)
                if current_time - stat.st_mtime > cleanup_age:
                    shutil.rmtree(temp_path)
                    logger.info(f"Cleaned up expired directory: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {temp_path}: {e}")

# Periodic task schedule
celery_app.conf.beat_schedule = {
    'cleanup-expired-files': {
        'task': 'async_processor.cleanup_expired_files',
        'schedule': 1800.0,  # Every 30 minutes
    },
}
celery_app.conf.timezone = 'UTC'

if __name__ == '__main__':
    celery_app.start()