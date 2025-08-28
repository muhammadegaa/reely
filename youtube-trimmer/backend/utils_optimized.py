"""
Optimized utility functions for video processing
Production-ready optimizations for handling long videos and reducing processing time
"""
import os
import subprocess
import tempfile
import logging
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import signal

logger = logging.getLogger(__name__)

class ProcessingTimeoutError(Exception):
    """Raised when a processing operation times out"""
    pass

def download_youtube_video_optimized(url: str, output_dir: str, format_preference: str = "medium") -> str:
    """
    Optimized YouTube video download with format selection and timeout handling
    """
    import yt_dlp
    
    # Format selection based on use case
    format_selectors = {
        "low": "worst[height<=360]/worst",  # For hook detection
        "medium": "best[height<=720]/best[height<=480]/best",  # For normal processing  
        "high": "best[height<=1080]/best"  # For high-quality output
    }
    
    format_selector = format_selectors.get(format_preference, format_selectors["medium"])
    
    try:
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title).50s.%(ext)s'),  # Limit filename length
            'format': format_selector,
            'noplaylist': True,
            'age_limit': 99,
            'ignoreerrors': False,
            'retries': 3,
            'fragment_retries': 3,
            # Optimize download speed
            'http_chunk_size': 10485760,  # 10MB chunks
            'concurrent_fragment_downloads': 4,
            # Reduce metadata processing
            'writeinfojson': False,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            # Add timeout to prevent hanging
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        # Use timeout for the entire download process
        def download_with_timeout():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        
        # Execute download with timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(download_with_timeout)
            try:
                # Timeout based on video quality (lower quality = faster download)
                timeout_seconds = 300 if format_preference == "low" else 600
                future.result(timeout=timeout_seconds)
            except FutureTimeoutError:
                future.cancel()
                raise ProcessingTimeoutError(f"Video download timed out after {timeout_seconds} seconds")
        
        # Find the downloaded file
        for file in os.listdir(output_dir):
            if file.endswith(('.mp4', '.webm', '.mkv')):
                return os.path.join(output_dir, file)
        
        raise Exception("Downloaded file not found")
        
    except Exception as e:
        logger.error(f"Optimized download failed: {e}")
        raise Exception(f"Failed to download video: {str(e)}")

def extract_audio_segment_direct(video_path: str, output_path: str, start_time: int, end_time: int) -> str:
    """
    Extract audio segment directly without processing entire video
    This is much faster than extracting full audio then trimming
    """
    try:
        duration = end_time - start_time
        
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_time),  # Seek before input for faster processing
            '-i', video_path,
            '-t', str(duration),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',
            '-ar', '16000',  # 16kHz for Whisper
            '-ac', '1',  # Mono
            '-avoid_negative_ts', 'make_zero',  # Handle timing issues
            output_path
        ]
        
        # Add timeout to prevent hanging
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=duration + 60,  # Allow extra time for processing
            check=True
        )
        
        if not os.path.exists(output_path):
            raise Exception("Audio segment extraction failed")
        
        # Verify file is not empty
        if os.path.getsize(output_path) < 1024:  # Less than 1KB is likely empty
            raise Exception("Audio segment is too small or empty")
            
        return output_path
        
    except subprocess.TimeoutExpired:
        raise ProcessingTimeoutError("Audio extraction timed out")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio extraction error: {e.stderr}")
        raise Exception(f"Failed to extract audio: {e.stderr}")
    except Exception as e:
        logger.error(f"Error extracting audio segment: {e}")
        raise Exception(f"Failed to extract audio: {str(e)}")

def trim_video_vertical_optimized(
    input_path: str, 
    output_path: str, 
    start_time: int, 
    end_time: int,
    transcript_data: Optional[Dict] = None, 
    add_subtitles: bool = False,
    processing_timeout: int = 1800  # 30 minutes max
) -> str:
    """
    Optimized vertical video processing with timeout and quality settings
    """
    try:
        duration = end_time - start_time
        temp_dir = os.path.dirname(output_path)
        
        # Get video dimensions more efficiently
        width, height = get_video_dimensions_fast(input_path)
        if not width or not height:
            raise Exception("Could not determine video dimensions")
        
        logger.info(f"Processing {width}x{height} video to vertical format")
        
        # Optimize target resolution based on input quality
        if width <= 720:
            target_width, target_height = 720, 1280  # Lower quality input
        else:
            target_width, target_height = 1080, 1920  # High quality
        
        # Build optimized FFmpeg command
        filter_parts = []
        
        # Determine processing approach based on aspect ratio
        is_horizontal = width > height
        
        if is_horizontal:
            # Efficient scaling and blurring for horizontal videos
            scale_factor = min(target_width / width, target_height / height)
            scaled_width = int(width * scale_factor)
            scaled_height = int(height * scale_factor)
            x_offset = (target_width - scaled_width) // 2
            y_offset = (target_height - scaled_height) // 2
            
            filter_parts = [
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height},gblur=sigma=15[bg]",
                f"[0:v]scale={scaled_width}:{scaled_height}[fg]",
                f"[bg][fg]overlay={x_offset}:{y_offset}[video]"
            ]
        else:
            # Simple scaling for vertical/square videos
            filter_parts = [
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height}[video]"
            ]
        
        # Add subtitle filter if needed
        final_output = "[video]"
        if add_subtitles and transcript_data:
            subtitle_file = create_optimized_subtitle_file(
                transcript_data, temp_dir, start_time, end_time
            )
            if subtitle_file:
                # Optimized subtitle styling
                subtitle_style = "FontName=Arial,FontSize=20,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=1,Shadow=0,MarginV=80"
                filter_parts.append(f"[video]subtitles='{subtitle_file}':force_style='{subtitle_style}'[final]")
                final_output = "[final]"
        
        filter_complex = ";".join(filter_parts)
        
        # Optimized encoding settings
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_time),  # Seek before input
            '-i', input_path,
            '-t', str(duration),
            '-filter_complex', filter_complex,
            '-map', final_output,
            '-map', '0:a?',  # Copy audio if available (? makes it optional)
            '-c:v', 'libx264',
            '-preset', 'faster',  # Faster encoding
            '-crf', '25',  # Slightly lower quality for speed
            '-maxrate', '2M',  # Limit bitrate
            '-bufsize', '4M',
            '-c:a', 'aac',
            '-b:a', '128k',  # Lower audio bitrate
            '-r', '24',  # Slightly lower framerate
            '-movflags', '+faststart',  # Optimize for streaming
            output_path
        ]
        
        logger.info(f"Starting optimized vertical processing (timeout: {processing_timeout}s)")
        
        # Execute with timeout
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=processing_timeout,
            check=True
        )
        
        if not os.path.exists(output_path):
            raise Exception("Processed video file was not created")
        
        # Verify output file
        output_size = os.path.getsize(output_path)
        if output_size < 1024 * 100:  # Less than 100KB is suspicious
            raise Exception("Output file is too small, processing may have failed")
        
        logger.info(f"Vertical processing completed, output size: {output_size / (1024*1024):.1f}MB")
        return output_path
        
    except subprocess.TimeoutExpired:
        # Clean up partial file
        if os.path.exists(output_path):
            os.remove(output_path)
        raise ProcessingTimeoutError(f"Video processing timed out after {processing_timeout} seconds")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg vertical processing error: {e.stderr}")
        raise Exception(f"Failed to process video: {e.stderr}")
    except Exception as e:
        logger.error(f"Error in vertical processing: {e}")
        raise Exception(f"Failed to process video: {str(e)}")

def get_video_dimensions_fast(file_path: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Get video dimensions quickly using ffprobe with minimal processing
    """
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0:s=x',
            file_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=10,  # Quick timeout
            check=True
        )
        
        dimensions = result.stdout.strip().split('x')
        if len(dimensions) == 2:
            return int(dimensions[0]), int(dimensions[1])
        
        return None, None
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
        logger.warning(f"Failed to get video dimensions: {e}")
        return None, None

def create_optimized_subtitle_file(
    transcript_data: Dict, 
    temp_dir: str, 
    start_time: int, 
    end_time: int
) -> Optional[str]:
    """
    Create optimized subtitle file with better formatting
    """
    try:
        subtitle_path = os.path.join(temp_dir, "optimized_subtitles.srt")
        
        segments = transcript_data.get("segments", [])
        if not segments:
            # Create simple subtitle from text
            text = transcript_data.get('text', '')[:200]  # Limit length
            if text:
                with open(subtitle_path, 'w', encoding='utf-8') as f:
                    f.write(f"1\n00:00:00,000 --> {seconds_to_srt_time(end_time - start_time)}\n{text}\n\n")
                return subtitle_path
            return None
        
        # Process segments efficiently
        subtitle_lines = []
        subtitle_index = 1
        
        for segment in segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', 0)
            
            # Check overlap with trim range
            if seg_end >= start_time and seg_start <= end_time:
                # Adjust timestamps
                adjusted_start = max(0, seg_start - start_time)
                adjusted_end = min(end_time - start_time, seg_end - start_time)
                
                text = segment.get('text', '').strip()
                if text and len(text) > 3:  # Skip very short text
                    # Break long lines for better readability
                    if len(text) > 40:
                        words = text.split()
                        lines = []
                        current_line = []
                        for word in words:
                            current_line.append(word)
                            if len(' '.join(current_line)) > 35:
                                lines.append(' '.join(current_line[:-1]))
                                current_line = [word]
                        if current_line:
                            lines.append(' '.join(current_line))
                        text = '\n'.join(lines)
                    
                    start_srt = seconds_to_srt_time(adjusted_start)
                    end_srt = seconds_to_srt_time(adjusted_end)
                    
                    subtitle_lines.append(f"{subtitle_index}\n{start_srt} --> {end_srt}\n{text}\n")
                    subtitle_index += 1
        
        if subtitle_lines:
            with open(subtitle_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(subtitle_lines))
            return subtitle_path
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to create optimized subtitle file: {e}")
        return None

def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def transcribe_segment_optimized(
    audio_path: str, 
    client, 
    max_retries: int = 3,
    chunk_size: int = 23 * 1024 * 1024  # 23MB to stay under OpenAI's 25MB limit
) -> Dict:
    """
    Optimized transcription with retry logic and chunking
    """
    import time
    
    for attempt in range(max_retries):
        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Transcribing audio file: {file_size / (1024*1024):.1f}MB (attempt {attempt + 1})")
            
            if file_size > chunk_size:
                logger.info("File too large, chunking not implemented for segments yet")
                # For now, refuse to process very large files
                raise Exception(f"Audio file too large ({file_size / (1024*1024):.1f}MB). Consider shorter segments.")
            
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    temperature=0.2  # Lower temperature for more consistent results
                )
            
            result = {
                "text": transcript.text,
                "segments": [{
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                } for segment in transcript.segments] if hasattr(transcript, 'segments') else []
            }
            
            logger.info(f"Transcription completed: {len(result['segments'])} segments")
            return result
            
        except Exception as e:
            logger.warning(f"Transcription attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Transcription failed after {max_retries} attempts: {str(e)}")

# Context manager for cleanup
class TempFileManager:
    """Context manager for automatic cleanup of temporary files"""
    
    def __init__(self, prefix: str = "reely_temp_"):
        self.temp_dir = None
        self.prefix = prefix
        self.files_to_cleanup = []
    
    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix=self.prefix)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def add_file(self, file_path: str):
        """Add file to cleanup list"""
        if file_path and os.path.exists(file_path):
            self.files_to_cleanup.append(file_path)
    
    def get_temp_path(self, filename: str) -> str:
        """Get path for temporary file"""
        return os.path.join(self.temp_dir, filename)
    
    def cleanup(self):
        """Clean up all temporary files and directory"""
        import shutil
        
        # Clean up individual files
        for file_path in self.files_to_cleanup:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")
        
        # Clean up temp directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {self.temp_dir}: {e}")