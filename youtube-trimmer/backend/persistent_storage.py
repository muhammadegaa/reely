"""
Persistent storage system for Reely
Handles video job persistence, file tracking, and cleanup
"""
import os
import json
import shutil
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from sqlalchemy.orm import Session

from models import VideoJob, ProcessingStatus, User
from database import get_db

class ProcessedFileManager:
    """
    Enhanced file manager that replaces in-memory processed_files dict
    with database-persistent storage and proper cleanup
    """
    
    def __init__(self):
        self.temp_base_dir = Path("./temp_files")
        self.temp_base_dir.mkdir(exist_ok=True)
    
    def store_processed_file(
        self,
        job_id: str,
        file_path: str,
        temp_dir: str,
        original_file: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Store processed file information in database and filesystem
        """
        try:
            if db:
                # Update database record with file information
                video_job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
                if video_job:
                    # Store metadata about the processed file
                    file_metadata = {
                        "file_path": file_path,
                        "temp_dir": temp_dir,
                        "original_file": original_file,
                        "stored_at": datetime.now(timezone.utc).isoformat(),
                        **(metadata or {})
                    }
                    
                    # You could add a file_metadata JSON column to VideoJob model
                    # For now, we'll use the existing structure
                    video_job.status = ProcessingStatus.COMPLETED.value
                    video_job.completed_at = datetime.now(timezone.utc)
                    db.commit()
            
            return True
            
        except Exception as e:
            print(f"Error storing processed file {job_id}: {e}")
            return False
    
    def get_processed_file(self, job_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve processed file information from database
        """
        if db:
            video_job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
            if video_job and video_job.status == ProcessingStatus.COMPLETED.value:
                # For backward compatibility with the existing processed_files dict
                # We need to reconstruct the expected file info structure
                # This is a temporary solution until we can add proper file metadata columns
                
                # Try to find the file in temp directories
                temp_dirs = list(Path("./temp_files").glob("*"))
                for temp_dir in temp_dirs:
                    potential_files = list(temp_dir.glob(f"*{job_id}*"))
                    if potential_files:
                        file_path = str(potential_files[0])
                        return {
                            "file_path": file_path,
                            "temp_dir": str(temp_dir),
                            "original_file": None,  # Would need to store this separately
                            "job_id": job_id,
                            "created_at": video_job.created_at,
                            "completed_at": video_job.completed_at
                        }
        
        return None
    
    def cleanup_processed_file(self, job_id: str, db: Optional[Session] = None) -> bool:
        """
        Clean up processed files and update database
        """
        try:
            file_info = self.get_processed_file(job_id, db)
            if file_info:
                # Clean up files
                if file_info.get("file_path") and os.path.exists(file_info["file_path"]):
                    os.remove(file_info["file_path"])
                
                if file_info.get("original_file") and os.path.exists(file_info["original_file"]):
                    os.remove(file_info["original_file"])
                
                # Clean up temp directory
                temp_dir = file_info.get("temp_dir")
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Update database - mark as cleaned up or delete old records
            if db:
                video_job = db.query(VideoJob).filter(VideoJob.job_id == job_id).first()
                if video_job:
                    # Option 1: Mark as cleaned up (keep record for history)
                    # video_job.status = ProcessingStatus.CLEANED.value  # Would need to add this status
                    
                    # Option 2: Delete old completed jobs after cleanup
                    if video_job.completed_at and (
                        datetime.now(timezone.utc) - video_job.completed_at
                    ) > timedelta(days=7):  # Delete jobs older than 7 days
                        db.delete(video_job)
                    
                    db.commit()
            
            return True
            
        except Exception as e:
            print(f"Error cleaning up processed file {job_id}: {e}")
            return False
    
    def cleanup_expired_files(self, db: Optional[Session] = None, max_age_hours: int = 24) -> int:
        """
        Clean up expired files based on age
        Returns number of files cleaned up
        """
        cleaned_count = 0
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        if db:
            # Find completed jobs older than cutoff time
            expired_jobs = db.query(VideoJob).filter(
                VideoJob.status == ProcessingStatus.COMPLETED.value,
                VideoJob.completed_at < cutoff_time
            ).all()
            
            for job in expired_jobs:
                if self.cleanup_processed_file(job.job_id, db):
                    cleaned_count += 1
        
        # Also clean up orphaned temp directories
        temp_dirs = list(self.temp_base_dir.glob("*"))
        for temp_dir in temp_dirs:
            try:
                # Check if directory is old enough to clean up
                dir_mtime = datetime.fromtimestamp(temp_dir.stat().st_mtime, timezone.utc)
                if dir_mtime < cutoff_time:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    cleaned_count += 1
            except Exception as e:
                print(f"Error cleaning temp directory {temp_dir}: {e}")
        
        return cleaned_count
    
    def get_storage_stats(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Get storage usage statistics
        """
        stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "processing_jobs": 0,
            "failed_jobs": 0,
            "temp_directories": 0,
            "total_temp_size_mb": 0
        }
        
        if db:
            # Database stats
            stats["total_jobs"] = db.query(VideoJob).count()
            stats["completed_jobs"] = db.query(VideoJob).filter(
                VideoJob.status == ProcessingStatus.COMPLETED.value
            ).count()
            stats["processing_jobs"] = db.query(VideoJob).filter(
                VideoJob.status == ProcessingStatus.PROCESSING.value
            ).count()
            stats["failed_jobs"] = db.query(VideoJob).filter(
                VideoJob.status == ProcessingStatus.FAILED.value
            ).count()
        
        # Filesystem stats
        if self.temp_base_dir.exists():
            temp_dirs = list(self.temp_base_dir.glob("*"))
            stats["temp_directories"] = len(temp_dirs)
            
            total_size = 0
            for temp_dir in temp_dirs:
                try:
                    for file_path in temp_dir.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                except Exception as e:
                    print(f"Error calculating size for {temp_dir}: {e}")
            
            stats["total_temp_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        return stats

# Global file manager instance
file_manager = ProcessedFileManager()

# Compatibility functions for existing code
def get_processed_file_info(download_id: str) -> Optional[Dict[str, Any]]:
    """
    Get processed file info (replaces processed_files[download_id])
    """
    with next(get_db()) as db:
        return file_manager.get_processed_file(download_id, db)

def store_processed_file_info(download_id: str, file_info: Dict[str, Any]) -> bool:
    """
    Store processed file info (replaces processed_files[download_id] = file_info)
    """
    with next(get_db()) as db:
        return file_manager.store_processed_file(
            download_id,
            file_info.get("file_path", ""),
            file_info.get("temp_dir", ""),
            file_info.get("original_file"),
            file_info,
            db
        )

def cleanup_processed_file_info(download_id: str) -> bool:
    """
    Clean up processed file info (replaces del processed_files[download_id])
    """
    with next(get_db()) as db:
        return file_manager.cleanup_processed_file(download_id, db)

def cleanup_expired_files(max_age_hours: int = 24) -> int:
    """
    Background task to clean up expired files
    """
    with next(get_db()) as db:
        return file_manager.cleanup_expired_files(db, max_age_hours)

# Background cleanup scheduler
import asyncio
import threading

async def scheduled_cleanup_task():
    """
    Scheduled task to run cleanup every hour
    """
    while True:
        try:
            cleaned_count = cleanup_expired_files(24)  # Clean files older than 24 hours
            if cleaned_count > 0:
                print(f"Scheduled cleanup: removed {cleaned_count} expired files/directories")
        except Exception as e:
            print(f"Error in scheduled cleanup: {e}")
        
        # Wait 1 hour before next cleanup
        await asyncio.sleep(3600)

def start_background_cleanup():
    """
    Start background cleanup task
    """
    def run_cleanup():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(scheduled_cleanup_task())
    
    thread = threading.Thread(target=run_cleanup, daemon=True)
    thread.start()
    print("Started background file cleanup task")