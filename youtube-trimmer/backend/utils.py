import os
import re
import subprocess
import tempfile
import yt_dlp
from pathlib import Path
import logging
import shutil
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv
import openai
from anthropic import Anthropic
import hashlib
import time

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple in-memory cache for hook results (expires after 1 hour)
_hook_cache = {}

def get_url_cache_key(url: str) -> str:
    """Generate cache key for URL"""
    return hashlib.md5(url.encode()).hexdigest()

def get_cached_hooks(url: str) -> Optional[List[Dict]]:
    """Get cached hook results if available and not expired"""
    cache_key = get_url_cache_key(url)
    if cache_key in _hook_cache:
        cached_data, timestamp = _hook_cache[cache_key]
        # Check if cache is still valid (1 hour)
        if time.time() - timestamp < 3600:
            logger.info("Using cached hook results")
            return cached_data
        else:
            # Remove expired cache
            del _hook_cache[cache_key]
    return None

def cache_hooks(url: str, hooks: List[Dict]) -> None:
    """Cache hook results for URL"""
    cache_key = get_url_cache_key(url)
    _hook_cache[cache_key] = (hooks, time.time())
    logger.info("Cached hook results")

def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and available in PATH"""
    return shutil.which('ffmpeg') is not None

def check_prerequisites() -> dict:
    """Check all required system prerequisites"""
    return {
        'ffmpeg': check_ffmpeg_installed(),
        'python': True,  # If we're running Python, it's available
        'yt_dlp': True,   # If we imported it, it's available
        'openai_api_key': bool(os.getenv('OPENAI_API_KEY')),
        'anthropic_api_key': bool(os.getenv('ANTHROPIC_API_KEY'))
    }

def is_valid_youtube_url(url: str) -> bool:
    """Validate if the URL is a valid YouTube URL"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\n]{11})'
    )
    return bool(youtube_regex.match(url))

def parse_timestamp(timestamp: str) -> int:
    """Convert HH:MM:SS or MM:SS timestamp to seconds"""
    try:
        parts = timestamp.split(':')
        if len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        else:
            return int(timestamp)  # Just seconds
    except ValueError:
        raise ValueError(f"Invalid timestamp format: {timestamp}")

def get_video_duration(file_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        import json
        data = json.loads(result.stdout)
        
        # Get duration from format or video stream
        duration = None
        if 'format' in data and 'duration' in data['format']:
            duration = float(data['format']['duration'])
        else:
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video' and 'duration' in stream:
                    duration = float(stream['duration'])
                    break
        
        return duration
    except Exception as e:
        logger.error(f"Error getting video duration: {e}")
        return None

def download_youtube_video(url: str, output_dir: str, for_hooks: bool = False) -> str:
    """Download YouTube video and return the file path"""
    try:
        # Use lower quality for hook detection to speed up downloads
        if for_hooks:
            format_selector = 'worst[height<=360]/worst'  # Very low quality for hooks
        else:
            format_selector = 'best[height<=720]'  # Higher quality for final trimming
            
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'format': format_selector,
            'noplaylist': True,
            'age_limit': 99,  # Allow age-restricted content
            'ignoreerrors': False,
            # Add user agent to avoid some blocks
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info first
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')
            
            # Clean title for filename
            clean_title = re.sub(r'[^\w\s-]', '', video_title)
            clean_title = re.sub(r'[-\s]+', '-', clean_title)
            
            # Update output template with clean title
            ydl_opts['outtmpl'] = os.path.join(output_dir, f'{clean_title}.%(ext)s')
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                ydl_download.download([url])
            
            # Find the downloaded file
            for file in os.listdir(output_dir):
                if file.startswith(clean_title):
                    return os.path.join(output_dir, file)
            
            raise Exception("Downloaded file not found")
            
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        raise Exception(f"Failed to download video: {str(e)}")

def get_video_dimensions(file_path: str) -> tuple:
    """Get video width and height using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        data = json.loads(result.stdout)
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = stream.get('width')
                height = stream.get('height')
                if width and height:
                    return width, height
        
        return None, None
    except Exception as e:
        logger.error(f"Error getting video dimensions: {e}")
        return None, None

def create_subtitle_file(transcript_data: Dict, output_path: str, start_time: int, end_time: int) -> str:
    """Create SRT subtitle file from transcript segments within the specified time range"""
    try:
        segments = transcript_data.get("segments", [])
        if not segments:
            # If no segments, create a single subtitle from the full text
            subtitle_content = f"1\n00:00:00,000 --> 00:00:10,000\n{transcript_data.get('text', '')[:100]}...\n\n"
        else:
            # Filter segments within the trim range and adjust timestamps
            subtitle_lines = []
            subtitle_index = 1
            
            for segment in segments:
                seg_start = segment.get('start', 0)
                seg_end = segment.get('end', 0)
                
                # Check if segment overlaps with our trim range
                if seg_end >= start_time and seg_start <= end_time:
                    # Adjust timestamps relative to trim start
                    adjusted_start = max(0, seg_start - start_time)
                    adjusted_end = min(end_time - start_time, seg_end - start_time)
                    
                    # Convert to SRT time format
                    start_srt = seconds_to_srt_time(adjusted_start)
                    end_srt = seconds_to_srt_time(adjusted_end)
                    
                    text = segment.get('text', '').strip()
                    if text:
                        subtitle_lines.append(f"{subtitle_index}\n{start_srt} --> {end_srt}\n{text}\n")
                        subtitle_index += 1
            
            subtitle_content = '\n'.join(subtitle_lines)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(subtitle_content)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error creating subtitle file: {e}")
        raise Exception(f"Failed to create subtitle file: {str(e)}")

def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def trim_video_vertical(input_path: str, output_path: str, start_time: int, end_time: int, 
                       transcript_data: Dict = None, add_subtitles: bool = False) -> str:
    """Trim video and convert to 9:16 vertical format with optional blurred background and subtitles"""
    try:
        duration = end_time - start_time
        temp_dir = os.path.dirname(output_path)
        
        # Get original video dimensions
        width, height = get_video_dimensions(input_path)
        if not width or not height:
            raise Exception("Could not determine video dimensions")
        
        logger.info(f"Original video dimensions: {width}x{height}")
        
        # Target dimensions (9:16 aspect ratio)
        target_width = 1080
        target_height = 1920
        
        # Determine if video is horizontal (wider than tall)
        is_horizontal = width > height
        
        # Build FFmpeg command
        filter_complex_parts = []
        
        if is_horizontal:
            # For horizontal videos: create blurred background + centered original
            
            # Calculate scale for the main video (fit within target while maintaining aspect ratio)
            scale_factor = min(target_width / width, target_height / height)
            scaled_width = int(width * scale_factor)
            scaled_height = int(height * scale_factor)
            
            # Position for centering
            x_offset = (target_width - scaled_width) // 2
            y_offset = (target_height - scaled_height) // 2
            
            filter_complex_parts = [
                # Create blurred background: scale to fill target, blur heavily
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height},gblur=sigma=20[bg]",
                # Scale main video to fit within target
                f"[0:v]scale={scaled_width}:{scaled_height}[fg]",
                # Overlay main video on blurred background
                f"[bg][fg]overlay={x_offset}:{y_offset}[video]"
            ]
        else:
            # For vertical/square videos: simple scale and crop to target
            filter_complex_parts = [
                f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,crop={target_width}:{target_height}[video]"
            ]
        
        # Add subtitle burning if requested
        if add_subtitles and transcript_data:
            subtitle_file = os.path.join(temp_dir, "subtitles.srt")
            create_subtitle_file(transcript_data, subtitle_file, start_time, end_time)
            
            # Add subtitle filter (burn subtitles into video)
            subtitle_style = "FontName=Arial,FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Shadow=1,MarginV=100"
            filter_complex_parts.append(f"[video]subtitles='{subtitle_file}':force_style='{subtitle_style}'[final]")
            final_output = "[final]"
        else:
            final_output = "[video]"
        
        # Combine all filter parts
        filter_complex = ";".join(filter_complex_parts)
        
        cmd = [
            'ffmpeg', '-y',  # Overwrite output file
            '-i', input_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-filter_complex', filter_complex,
            '-map', final_output,
            '-map', '0:a',  # Copy audio
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-crf', '23',  # Good quality
            '-preset', 'medium',  # Balanced speed/quality
            '-r', '30',  # 30 FPS
            output_path
        ]
        
        logger.info("Processing video with vertical format and effects...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if not os.path.exists(output_path):
            raise Exception("Processed video file was not created")
        
        # Clean up subtitle file if created
        if add_subtitles and transcript_data:
            try:
                os.remove(subtitle_file)
            except:
                pass
            
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise Exception(f"Failed to process video: {e.stderr}")
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        raise Exception(f"Failed to process video: {str(e)}")

def trim_video(input_path: str, output_path: str, start_time: int, end_time: int) -> str:
    """Trim video using ffmpeg (original function for backward compatibility)"""
    try:
        duration = end_time - start_time
        
        cmd = [
            'ffmpeg', '-y',  # Overwrite output file
            '-i', input_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c', 'copy',  # Copy streams without re-encoding for speed
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if not os.path.exists(output_path):
            raise Exception("Trimmed video file was not created")
            
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr}")
        raise Exception(f"Failed to trim video: {e.stderr}")
    except Exception as e:
        logger.error(f"Error trimming video: {e}")
        raise Exception(f"Failed to trim video: {str(e)}")

def extract_audio_for_transcription(video_path: str, output_dir: str) -> str:
    """Extract audio from video for transcription"""
    try:
        audio_path = os.path.join(output_dir, "audio_for_transcription.wav")
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '16000',  # 16kHz sample rate for Whisper
            '-ac', '1',  # Mono
            audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if not os.path.exists(audio_path):
            raise Exception("Audio file was not created")
            
        return audio_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio extraction error: {e.stderr}")
        raise Exception(f"Failed to extract audio: {e.stderr}")
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        raise Exception(f"Failed to extract audio: {str(e)}")

def split_audio_for_transcription(audio_path: str, temp_dir: str, max_size_mb: int = 20) -> List[str]:
    """Split large audio files into smaller chunks for transcription"""
    try:
        file_size = os.path.getsize(audio_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size <= max_size_bytes:
            return [audio_path]  # No splitting needed
        
        logger.info(f"Audio file is {file_size / (1024*1024):.1f}MB, splitting into chunks...")
        
        # Get audio duration first
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', audio_path
        ], capture_output=True, text=True, check=True)
        
        total_duration = float(result.stdout.strip())
        
        # Calculate number of chunks needed
        num_chunks = max(2, int((file_size / max_size_bytes) * 1.2))  # Add 20% buffer
        chunk_duration = total_duration / num_chunks
        
        chunk_files = []
        for i in range(num_chunks):
            start_time = i * chunk_duration
            chunk_file = os.path.join(temp_dir, f"audio_chunk_{i:03d}.wav")
            
            # Extract chunk using ffmpeg
            subprocess.run([
                'ffmpeg', '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(chunk_duration),
                '-c', 'copy',
                '-y', chunk_file
            ], capture_output=True, check=True)
            
            chunk_files.append(chunk_file)
            logger.info(f"Created chunk {i+1}/{num_chunks}: {start_time:.1f}s-{start_time+chunk_duration:.1f}s")
        
        return chunk_files
        
    except Exception as e:
        logger.error(f"Error splitting audio: {e}")
        raise Exception(f"Failed to split audio: {str(e)}")

def transcribe_audio_with_openai(audio_path: str, for_hooks: bool = True) -> Dict:
    """Transcribe audio using OpenAI Whisper API with smart sampling for hook detection"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise Exception("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Get video duration first
        video_duration = get_video_duration(audio_path)
        file_size = os.path.getsize(audio_path)
        
        logger.info(f"Audio file: {file_size/(1024*1024):.1f}MB, Duration: {video_duration:.1f}s ({video_duration/60:.1f} minutes)")
        
        # For hook detection, use smart sampling for long videos
        if for_hooks and video_duration > 600:  # 10+ minutes
            logger.info("Long video detected, using smart sampling for hook detection...")
            return transcribe_sampled_segments_for_hooks(client, audio_path, video_duration)
        
        # For shorter videos or full transcription, use existing logic
        max_size = 20 * 1024 * 1024  # 20MB limit for safety
        
        if file_size > max_size:
            logger.info(f"Large audio file detected, using chunking approach...")
            return transcribe_large_audio_with_chunks(client, audio_path)
        else:
            logger.info("Audio file size OK, using direct transcription...")
            return transcribe_single_audio(client, audio_path)
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise Exception(f"Failed to transcribe audio: {str(e)}")

def transcribe_single_audio(client, audio_path: str) -> Dict:
    """Transcribe a single audio file"""
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json"
        )
    
    return {
        "text": transcript.text,
        "segments": [{
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        } for segment in transcript.segments] if hasattr(transcript, 'segments') else []
    }

def transcribe_large_audio_with_chunks(client, audio_path: str) -> Dict:
    """Transcribe large audio files by splitting into chunks"""
    temp_dir = os.path.dirname(audio_path)
    
    # Split audio into chunks
    chunk_files = split_audio_for_transcription(audio_path, temp_dir)
    
    try:
        all_text = []
        all_segments = []
        cumulative_time = 0.0
        
        logger.info(f"Transcribing {len(chunk_files)} audio chunks...")
        
        for i, chunk_file in enumerate(chunk_files):
            logger.info(f"Transcribing chunk {i+1}/{len(chunk_files)}...")
            
            with open(chunk_file, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            all_text.append(transcript.text)
            
            # Adjust segment timestamps for cumulative time
            if hasattr(transcript, 'segments'):
                for segment in transcript.segments:
                    all_segments.append({
                        "start": segment.start + cumulative_time,
                        "end": segment.end + cumulative_time,
                        "text": segment.text
                    })
            
            # Get chunk duration for next iteration
            if i < len(chunk_files) - 1:  # Not the last chunk
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                    '-of', 'csv=p=0', chunk_file
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    chunk_duration = float(result.stdout.strip())
                    cumulative_time += chunk_duration
        
        logger.info(f"Successfully transcribed all chunks. Total segments: {len(all_segments)}")
        
        return {
            "text": " ".join(all_text),
            "segments": all_segments
        }
        
    finally:
        # Clean up chunk files
        for chunk_file in chunk_files:
            try:
                if chunk_file != audio_path:  # Don't delete the original
                    os.remove(chunk_file)
            except:
                pass

def transcribe_sampled_segments_for_hooks(client, audio_path: str, video_duration: float) -> Dict:
    """Transcribe strategic segments for hook detection instead of entire video"""
    temp_dir = os.path.dirname(audio_path)
    
    # Sample key segments for hook detection
    # Beginning (0-2min), middle sections, and any other strategic points
    segments_to_sample = []
    
    # Always sample the beginning (hooks often occur early)
    segments_to_sample.append((0, min(120, video_duration)))  # First 2 minutes
    
    # Sample middle sections based on video length
    if video_duration > 600:  # 10+ minutes
        # Sample 3 middle segments of 1 minute each
        middle_start = video_duration * 0.3
        segments_to_sample.append((middle_start, middle_start + 60))
        
        middle_start = video_duration * 0.5
        segments_to_sample.append((middle_start, middle_start + 60))
        
        middle_start = video_duration * 0.7
        segments_to_sample.append((middle_start, middle_start + 60))
    
    # Sample near the end (sometimes hooks appear late)
    if video_duration > 300:  # 5+ minutes
        end_start = max(video_duration - 120, video_duration * 0.8)
        segments_to_sample.append((end_start, video_duration))
    
    logger.info(f"Sampling {len(segments_to_sample)} strategic segments for hook detection")
    
    all_text = []
    all_segments = []
    
    try:
        for i, (start_time, end_time) in enumerate(segments_to_sample):
            logger.info(f"Transcribing segment {i+1}/{len(segments_to_sample)}: {start_time:.1f}s - {end_time:.1f}s")
            
            # Extract segment audio
            segment_path = os.path.join(temp_dir, f"segment_{i}.wav")
            
            # Use ffmpeg to extract segment
            cmd = [
                'ffmpeg', '-i', audio_path,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-acodec', 'pcm_s16le',
                '-ac', '1',  # mono
                '-ar', '16000',  # 16kHz sample rate
                '-y',  # overwrite
                segment_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Failed to extract segment {i+1}, skipping...")
                continue
            
            # Transcribe segment
            try:
                with open(segment_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json"
                    )
                
                all_text.append(f"[Segment {start_time:.0f}s-{end_time:.0f}s] {transcript.text}")
                
                # Adjust segment timestamps
                if hasattr(transcript, 'segments'):
                    for segment in transcript.segments:
                        all_segments.append({
                            "start": segment.start + start_time,
                            "end": segment.end + start_time,
                            "text": segment.text
                        })
                
                # Clean up segment file
                os.remove(segment_path)
                
            except Exception as e:
                logger.warning(f"Failed to transcribe segment {i+1}: {e}")
                if os.path.exists(segment_path):
                    os.remove(segment_path)
                continue
        
        logger.info(f"Successfully transcribed {len(segments_to_sample)} segments for hook analysis")
        
        return {
            "text": " ".join(all_text),
            "segments": all_segments,
            "sampled": True  # Mark as sampled transcription
        }
        
    except Exception as e:
        logger.error(f"Error in segment transcription: {e}")
        raise Exception(f"Failed to transcribe segments: {str(e)}")

def analyze_hooks_with_ai(transcript_data: Dict, provider: str = "openai") -> List[Dict]:
    """Analyze transcript to find hook moments using AI"""
    try:
        full_text = transcript_data["text"]
        segments = transcript_data.get("segments", [])
        
        # Create a prompt for hook detection
        prompt = f"""Analyze this video transcript and identify 3-5 "hook moments" that would make compelling short clips.

Hook moments should be:
- Emotionally charged, surprising, or curiosity-inducing
- 15-30 seconds long each
- Self-contained and engaging
- Have clear start/end points

Transcript:
{full_text}

Segment timestamps (for reference):
{json.dumps(segments[:20], indent=2) if segments else "No segments available"}

Respond with ONLY a JSON array in this exact format:
[{{
  "start": 120,
  "end": 145,
  "title": "The shocking statistic that changes everything",
  "reason": "Contains surprising data that creates curiosity"
}}]

Ensure timestamps are realistic based on the content length."""
        
        if provider.lower() == "anthropic":
            return _analyze_with_anthropic(prompt)
        else:
            return _analyze_with_openai(prompt)
            
    except Exception as e:
        logger.error(f"Error analyzing hooks: {e}")
        raise Exception(f"Failed to analyze hooks: {str(e)}")

def _analyze_with_openai(prompt: str) -> List[Dict]:
    """Analyze using OpenAI API"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise Exception("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
    
    client = openai.OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert video editor specializing in creating viral short clips. You understand what makes content engaging and shareable."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    result_text = response.choices[0].message.content
    
    # Parse JSON response
    try:
        # Extract JSON from response (in case there's extra text)
        start = result_text.find('[')
        end = result_text.rfind(']') + 1
        json_text = result_text[start:end] if start != -1 and end > start else result_text
        
        hooks = json.loads(json_text)
        
        # Validate and clean up the response
        validated_hooks = []
        for hook in hooks:
            if isinstance(hook, dict) and all(key in hook for key in ['start', 'end', 'title']):
                validated_hooks.append({
                    'start': int(hook['start']),
                    'end': int(hook['end']),
                    'title': str(hook['title'])[:100],  # Limit title length
                    'reason': str(hook.get('reason', ''))[:200]  # Limit reason length
                })
        
        return validated_hooks[:5]  # Limit to 5 hooks max
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {result_text}")
        raise Exception("AI returned invalid JSON response")

def _analyze_with_anthropic(prompt: str) -> List[Dict]:
    """Analyze using Anthropic Claude API"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise Exception("Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable.")
    
    client = Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=1000,
        temperature=0.7,
        messages=[
            {
                "role": "user",
                "content": f"You are an expert video editor specializing in creating viral short clips. You understand what makes content engaging and shareable.\n\n{prompt}"
            }
        ]
    )
    
    result_text = response.content[0].text
    
    # Parse JSON response
    try:
        # Extract JSON from response (in case there's extra text)
        start = result_text.find('[')
        end = result_text.rfind(']') + 1
        json_text = result_text[start:end] if start != -1 and end > start else result_text
        
        hooks = json.loads(json_text)
        
        # Validate and clean up the response
        validated_hooks = []
        for hook in hooks:
            if isinstance(hook, dict) and all(key in hook for key in ['start', 'end', 'title']):
                validated_hooks.append({
                    'start': int(hook['start']),
                    'end': int(hook['end']),
                    'title': str(hook['title'])[:100],  # Limit title length
                    'reason': str(hook.get('reason', ''))[:200]  # Limit reason length
                })
        
        return validated_hooks[:5]  # Limit to 5 hooks max
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {result_text}")
        raise Exception("AI returned invalid JSON response")

def process_video_for_hooks(url: str, temp_dir: str, ai_provider: str = "openai") -> List[Dict]:
    """Complete pipeline: download video, transcribe, and find hooks (optimized for speed)"""
    try:
        logger.info(f"Starting hook detection pipeline for: {url}")
        
        # Check cache first
        cached_hooks = get_cached_hooks(url)
        if cached_hooks:
            return cached_hooks
        
        # Download video with low quality for speed
        logger.info("Downloading video (low quality for speed)...")
        video_path = download_youtube_video(url, temp_dir, for_hooks=True)
        
        # Extract audio
        logger.info("Extracting audio for transcription...")
        audio_path = extract_audio_for_transcription(video_path, temp_dir)
        
        # Transcribe audio
        logger.info("Transcribing audio with OpenAI Whisper...")
        transcript_data = transcribe_audio_with_openai(audio_path, for_hooks=True)
        
        # Analyze for hooks
        logger.info(f"Analyzing transcript with {ai_provider} for hook moments...")
        hooks = analyze_hooks_with_ai(transcript_data, ai_provider)
        
        logger.info(f"Found {len(hooks)} hook moments")
        
        # Cache the results
        cache_hooks(url, hooks)
        
        return hooks
        
    except Exception as e:
        logger.error(f"Error in hook detection pipeline: {e}")
        raise Exception(f"Hook detection failed: {str(e)}")

def cleanup_files(*file_paths):
    """Clean up temporary files"""
    for file_path in file_paths:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")