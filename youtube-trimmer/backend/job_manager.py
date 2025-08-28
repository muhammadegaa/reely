import uuid
import time
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import tempfile
from utils import (
    download_youtube_video, 
    trim_video, 
    trim_video_vertical,
    get_video_duration,
    cleanup_files,
    process_video_for_hooks
)

class JobStatus(Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading" 
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    TRIMMING = "trimming"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    id: str
    status: JobStatus
    progress: int  # 0-100
    message: str
    created_at: float
    updated_at: float
    result: Optional[Dict] = None
    error: Optional[str] = None
    
    # Job specific data
    job_type: str = "trim"  # "trim" or "hooks"
    url: str = ""
    start_time: float = 0
    end_time: float = 0
    vertical_format: bool = False
    add_subtitles: bool = False
    ai_provider: str = "openai"
    
    # File paths for cleanup
    temp_dir: Optional[str] = None
    file_paths: list = None

    def __post_init__(self):
        if self.file_paths is None:
            self.file_paths = []

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.background_tasks = {}
    
    def create_job(self, job_type: str, **kwargs) -> str:
        """Create a new job and return its ID"""
        job_id = str(uuid.uuid4())
        current_time = time.time()
        
        job = Job(
            id=job_id,
            status=JobStatus.QUEUED,
            progress=0,
            message="Job created, waiting to start...",
            created_at=current_time,
            updated_at=current_time,
            job_type=job_type,
            **kwargs
        )
        
        self.jobs[job_id] = job
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job status and progress"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return asdict(job)
    
    def update_job(self, job_id: str, status: JobStatus = None, progress: int = None, 
                   message: str = None, result: Dict = None, error: str = None):
        """Update job progress and status"""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        job.updated_at = time.time()
        
        if status:
            job.status = status
        if progress is not None:
            job.progress = progress
        if message:
            job.message = message
        if result:
            job.result = result
        if error:
            job.error = error
            job.status = JobStatus.FAILED
    
    def start_trim_job(self, job_id: str):
        """Start processing a trim job in background"""
        if job_id not in self.jobs:
            return
        
        # Start background thread
        thread = threading.Thread(target=self._process_trim_job, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        self.background_tasks[job_id] = thread
    
    def start_hooks_job(self, job_id: str):
        """Start processing a hooks job in background"""
        if job_id not in self.jobs:
            return
        
        # Start background thread
        thread = threading.Thread(target=self._process_hooks_job, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        self.background_tasks[job_id] = thread
    
    def _process_trim_job(self, job_id: str):
        """Background processing for trim jobs"""
        job = self.jobs[job_id]
        
        try:
            # Update to downloading
            self.update_job(job_id, JobStatus.DOWNLOADING, 10, "Downloading video...")
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            job.temp_dir = temp_dir
            
            # Download video
            downloaded_file = download_youtube_video(job.url, temp_dir, for_hooks=False)
            job.file_paths.append(downloaded_file)
            
            self.update_job(job_id, progress=30, message="Video downloaded, getting duration...")
            
            # Get video duration
            original_duration = get_video_duration(downloaded_file)
            
            # Validate timestamps
            if original_duration and job.end_time > original_duration:
                raise ValueError(f"End time ({job.end_time}s) exceeds video duration ({original_duration}s)")
            
            self.update_job(job_id, JobStatus.PROCESSING, 50, "Processing video...")
            
            # Handle subtitles if needed
            transcript_data = None
            if job.add_subtitles:
                self.update_job(job_id, JobStatus.TRANSCRIBING, 60, "Generating subtitles...")
                # Import here to avoid circular imports
                from utils import extract_audio_for_transcription, transcribe_audio_with_openai
                
                # Extract and transcribe only the segment we need (OPTIMIZATION)
                segment_audio = f"{temp_dir}/segment_audio.wav"
                import subprocess
                
                # Extract only the needed audio segment (much faster!)
                extract_cmd = [
                    'ffmpeg', '-i', downloaded_file, 
                    '-ss', str(job.start_time),
                    '-t', str(job.end_time - job.start_time),
                    '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                    segment_audio, '-y'
                ]
                subprocess.run(extract_cmd, check=True, capture_output=True)
                
                transcript_data = transcribe_audio_with_openai(segment_audio)
                job.file_paths.append(segment_audio)
            
            # Trim video
            self.update_job(job_id, JobStatus.TRIMMING, 80, "Trimming video...")
            
            output_filename = f"trimmed_{job_id}.mp4"
            output_path = f"{temp_dir}/{output_filename}"
            
            if job.vertical_format:
                trimmed_file = trim_video_vertical(
                    downloaded_file, output_path, job.start_time, job.end_time,
                    transcript_data, job.add_subtitles
                )
            else:
                trimmed_file = trim_video(downloaded_file, output_path, job.start_time, job.end_time)
            
            job.file_paths.append(trimmed_file)
            
            # Complete job
            result = {
                "download_id": job_id,
                "message": "Video trimmed successfully",
                "original_duration": original_duration,
                "trimmed_duration": job.end_time - job.start_time,
                "file_path": trimmed_file
            }
            
            self.update_job(job_id, JobStatus.COMPLETED, 100, "Video ready for download!", result)
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            self.update_job(job_id, error=error_msg, message=error_msg)
            
            # Cleanup on error
            if job.temp_dir:
                cleanup_files(job.temp_dir)
    
    def _process_hooks_job(self, job_id: str):
        """Background processing for hooks jobs"""
        job = self.jobs[job_id]
        
        try:
            # Update to downloading
            self.update_job(job_id, JobStatus.DOWNLOADING, 20, "Downloading video for analysis...")
            
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            job.temp_dir = temp_dir
            
            # Process video for hooks
            self.update_job(job_id, JobStatus.PROCESSING, 50, "AI analyzing video content...")
            
            hooks_data = process_video_for_hooks(job.url, temp_dir, job.ai_provider)
            
            # Get video duration for frontend timeline
            try:
                # Download the video to get duration info
                from utils import download_youtube_video, get_video_duration
                video_path = download_youtube_video(job.url, temp_dir, for_hooks=True)
                video_duration = get_video_duration(video_path)
            except Exception as e:
                # If we can't get duration, default to estimating from hooks
                video_duration = max([hook.get('end', 300) for hook in hooks_data], default=300)
            
            # Complete job
            result = {
                "message": f"Found {len(hooks_data)} hook moments using {job.ai_provider.title()}",
                "hooks": hooks_data,
                "total_hooks": len(hooks_data),
                "video_duration": video_duration
            }
            
            self.update_job(job_id, JobStatus.COMPLETED, 100, "Hook analysis complete!", result)
            
        except Exception as e:
            error_msg = f"Hook analysis failed: {str(e)}"
            self.update_job(job_id, error=error_msg, message=error_msg)
            
            # Cleanup on error
            if job.temp_dir:
                cleanup_files(job.temp_dir)
    
    def cleanup_job(self, job_id: str):
        """Clean up job files and remove from memory"""
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        
        # Clean up files
        for file_path in job.file_paths:
            try:
                cleanup_files(file_path)
            except Exception as e:
                print(f"Error cleaning file {file_path}: {e}")
        
        # Clean up temp directory
        if job.temp_dir:
            try:
                import shutil
                shutil.rmtree(job.temp_dir)
            except Exception as e:
                print(f"Error cleaning temp dir {job.temp_dir}: {e}")
        
        # Remove from memory
        del self.jobs[job_id]
        if job_id in self.background_tasks:
            del self.background_tasks[job_id]
    
    def get_file_path(self, job_id: str) -> Optional[str]:
        """Get the output file path for a completed job"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        if job.status != JobStatus.COMPLETED or not job.result:
            return None
        
        return job.result.get("file_path")

# Global job manager instance
job_manager = JobManager()