"""
Quick timeout fix for immediate deployment
This provides a temporary solution while implementing the full async processing system
"""
from utils_optimized import (
    download_youtube_video_optimized,
    extract_audio_segment_direct,
    transcribe_segment_optimized,
    trim_video_vertical_optimized,
    TempFileManager,
    ProcessingTimeoutError
)
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

def process_video_with_timeout_handling(
    url: str,
    start_time: int, 
    end_time: int,
    vertical_format: bool = False,
    add_subtitles: bool = False,
    max_processing_time: int = 840  # 14 minutes to stay under 15min timeout
):
    """
    Process video with aggressive timeout handling and optimizations
    Returns result or raises ProcessingTimeoutError
    """
    
    with TempFileManager(prefix="reely_quick_") as temp_manager:
        try:
            logger.info(f"Starting optimized processing with {max_processing_time}s timeout")
            
            # Step 1: Download video with optimized quality (2-3 minutes max)
            logger.info("Step 1/4: Downloading video...")
            temp_dir = temp_manager.temp_dir
            
            # Use lower quality for faster download when vertical format is needed
            quality = "low" if vertical_format else "medium"
            video_path = download_youtube_video_optimized(url, temp_dir, quality)
            temp_manager.add_file(video_path)
            
            # Step 2: Handle subtitles efficiently (3-8 minutes max)
            transcript_data = None
            if add_subtitles:
                logger.info("Step 2/4: Processing subtitles (optimized)...")
                
                # Extract only the segment we need (much faster)
                audio_path = extract_audio_segment_direct(
                    video_path, 
                    temp_manager.get_temp_path("segment_audio.wav"),
                    start_time, 
                    end_time
                )
                temp_manager.add_file(audio_path)
                
                # Transcribe only the segment
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                transcript_data = transcribe_segment_optimized(audio_path, client)
            else:
                logger.info("Step 2/4: Skipping subtitles")
            
            # Step 3: Process video with timeout (5-8 minutes max)
            logger.info("Step 3/4: Processing video format...")
            output_path = temp_manager.get_temp_path("output.mp4")
            
            # Calculate remaining time for processing
            import time
            processing_start = time.time()
            remaining_time = max_processing_time - 300  # Reserve 5 minutes buffer
            
            if vertical_format:
                processed_path = trim_video_vertical_optimized(
                    video_path,
                    output_path,
                    start_time,
                    end_time,
                    transcript_data,
                    add_subtitles,
                    processing_timeout=remaining_time
                )
            else:
                # Quick trim for standard format
                from utils import trim_video
                processed_path = trim_video(video_path, output_path, start_time, end_time)
            
            logger.info("Step 4/4: Finalizing...")
            
            # Verify output
            if not os.path.exists(processed_path) or os.path.getsize(processed_path) < 1024:
                raise Exception("Output file is invalid or too small")
            
            total_time = time.time() - processing_start
            logger.info(f"Processing completed successfully in {total_time:.1f}s")
            
            return {
                'success': True,
                'output_path': processed_path,
                'processing_time': total_time,
                'temp_dir': temp_dir  # Caller is responsible for cleanup
            }
            
        except ProcessingTimeoutError as e:
            logger.error(f"Processing timed out: {e}")
            raise Exception(f"Video processing timed out. Please try with a shorter video segment or disable subtitles.")
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise Exception(f"Video processing failed: {str(e)}")

def should_use_optimized_processing(
    duration: int,
    vertical_format: bool,
    add_subtitles: bool
) -> bool:
    """
    Determine if optimized processing should be used
    """
    # Use for any video longer than 5 minutes
    if duration > 300:
        return True
    
    # Use for any vertical format with subtitles
    if vertical_format and add_subtitles:
        return True
    
    # Use for very long subtitle requests
    if add_subtitles and duration > 120:
        return True
    
    return False

# Monkey patch into existing utils if needed
def apply_quick_fix():
    """
    Apply the quick fix to existing processing functions
    """
    import utils
    
    # Store original function
    utils._original_trim_video_vertical = utils.trim_video_vertical
    
    def patched_trim_video_vertical(input_path, output_path, start_time, end_time, transcript_data=None, add_subtitles=False):
        """Patched version with timeout handling"""
        duration = end_time - start_time
        
        # Use optimized version for longer videos
        if duration > 300 or add_subtitles:
            try:
                return trim_video_vertical_optimized(
                    input_path, output_path, start_time, end_time, 
                    transcript_data, add_subtitles, processing_timeout=600
                )
            except ProcessingTimeoutError:
                raise Exception("Video processing timed out - please try a shorter segment")
        else:
            # Use original for short videos
            return utils._original_trim_video_vertical(
                input_path, output_path, start_time, end_time, transcript_data, add_subtitles
            )
    
    # Apply patch
    utils.trim_video_vertical = patched_trim_video_vertical
    logger.info("Applied quick timeout fix to video processing functions")

if __name__ == "__main__":
    # Test the quick fix
    apply_quick_fix()
    print("Quick timeout fix applied successfully")