"""
yt_downloads_utils.py

Utility functions for YouTube download formatting and file/path handling.
Includes sanitization, naming, extension mapping, etc.
"""

from yt_dlp import YoutubeDL
from typing import Optional, Dict, List, Any
import time
from pathlib import Path

# Import logging  
from .logger_utils.logger_utils import setup_logger

# Setup logger for this module
logger = setup_logger("yt_downloads_utils")

def get_filename_template(save_path: Optional[str] = None) -> str:
    """Get filename template from config with fallback to default."""
    if save_path:
        return save_path
    
    try:
        from .utils.path_utils import load_config
        config = load_config()
        template = config.get("downloads", {}).get("filename_template", "%(title)s [%(id)s].%(ext)s")
        logger.debug(f"Using filename template from config: {template}")
        return template
    except Exception as e:
        logger.warning(f"Failed to load filename template from config: {e}")
        fallback_template = "%(title)s [%(id)s].%(ext)s"
        logger.debug(f"Using fallback filename template: {fallback_template}")
        return fallback_template

def download_audio(url: str, format_id: str, save_path: Optional[str] = None, max_retries: int = 3, retry_delay: int = 2):
    """Download audio with retry logic and error handling."""
    outtmpl = get_filename_template(save_path)
    logger.info(f"Starting audio download: format_id={format_id}, save_path={save_path}")
    
    opts = {
        'format': format_id,
        'quiet': False,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': outtmpl,
        'retries': max_retries,
    }
    
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Audio download attempt {attempt + 1}/{max_retries + 1}")
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            logger.info(f"✅ Audio download successful on attempt {attempt + 1}")
            return True
            
        except Exception as e:
            logger.warning(f"❌ Audio download attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"💥 Audio download failed after {max_retries + 1} attempts")
                raise Exception(f"Audio download failed after {max_retries + 1} attempts: {str(e)}")
    
    return False


def download_video(url: str, format_id: str, save_path: Optional[str] = None, max_retries: int = 3, retry_delay: int = 2):
    """Download video with retry logic and error handling."""
    outtmpl = get_filename_template(save_path)
    logger.info(f"Starting video download: format_id={format_id}, save_path={save_path}")
    
    opts = {
        'format': format_id,
        'quiet': False,
        'outtmpl': outtmpl,
        'retries': max_retries,
    }
    
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Video download attempt {attempt + 1}/{max_retries + 1}")
            with YoutubeDL(opts) as ydl:
                ydl.download([url])
            logger.info(f"✅ Video download successful on attempt {attempt + 1}")
            return True
            
        except Exception as e:
            logger.warning(f"❌ Video download attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"💥 Video download failed after {max_retries + 1} attempts")
                raise Exception(f"Video download failed after {max_retries + 1} attempts: {str(e)}")
    
    return False


def download_video_with_audio(url: str, quality_preference: str = "720p", save_path: Optional[str] = None, max_retries: int = 3, retry_delay: int = 2):
    """Download video with audio using intelligent format selection."""
    outtmpl = get_filename_template(save_path)
    logger.info(f"Starting video+audio download: quality={quality_preference}, save_path={save_path}")
    
    # Create intelligent format selector based on quality preference
    max_height = "1080" if quality_preference == "1080p" else "720" if quality_preference == "720p" else "480" if quality_preference == "480p" else "720"
    
    # Try combined formats first, then merge separate streams as fallback
    format_selectors = [
        f'best[height<={max_height}][ext=mp4]',  # Best combined format with height limit
        f'bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={max_height}]+bestaudio',  # Merge separate streams
        f'best[height<={max_height}]',  # Any best format with height limit
        'best',  # Ultimate fallback
    ]
    
    opts = {
        'quiet': False,
        'outtmpl': outtmpl,
        'retries': max_retries,
        'merge_output_format': 'mp4',  # Ensure final output is mp4
    }
    
    for format_selector in format_selectors:
        opts['format'] = format_selector
        logger.debug(f"Trying format selector: {format_selector}")
        
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"Video+audio download attempt {attempt + 1}/{max_retries + 1} with format: {format_selector}")
                with YoutubeDL(opts) as ydl:
                    ydl.download([url])
                logger.info(f"✅ Video+audio download successful with format: {format_selector}")
                return True
                
            except Exception as e:
                logger.warning(f"❌ Format {format_selector} attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries:
                    logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.warning(f"💥 Format {format_selector} failed after {max_retries + 1} attempts")
                    break  # Try next format selector
    
    logger.error("💥 All video+audio format selectors failed")
    return False


def download_transcript(video_id: str, language_code: str, save_path: Optional[str] = None, 
                      max_retries: int = 3, retry_delay: int = 2, formats: Optional[List[str]] = None,
                      video_metadata: Optional[Dict[str, Any]] = None):
    """
    Download transcript with retry logic, error handling, and multiple format support.
    
    Args:
        video_id: YouTube video ID
        language_code: Language code for transcript
        save_path: Base path for saving (used for backward compatibility)
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries
        formats: List of formats to generate ('clean', 'timestamped', 'structured'). 
                If None, generates 'timestamped' only for backward compatibility.
        video_metadata: Video metadata for enhanced structured format
    
    Returns:
        Dict with format names as keys and file paths as values, or single path for backward compatibility
    """
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    from .transcript_processor import process_transcript_data
    import datetime
    
    logger.info(f"Starting transcript download: video_id={video_id}, language={language_code}, save_path={save_path}")
    
    # Backward compatibility: if no formats specified, use timestamped only
    if formats is None:
        formats = ['timestamped']
        backward_compatible = True
    else:
        backward_compatible = False
    
    logger.debug(f"Generating formats: {formats}")
    
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Transcript download attempt {attempt + 1}/{max_retries + 1}")
            
            # Use the utility function from core.py for API compatibility
            from .core import _get_transcript_list
            transcript_list = _get_transcript_list(video_id)
            
            # Find the transcript for our language and fetch it
            transcript_data = None
            for transcript in transcript_list:
                if hasattr(transcript, 'language_code') and transcript.language_code == language_code:
                    transcript_data = transcript.fetch()
                    logger.debug(f"✅ Found transcript using transcript list method")
                    break
            
            if not transcript_data:
                # Fallback: try direct get_transcript if it exists
                try:
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
                    logger.debug(f"✅ Found transcript using get_transcript fallback method")
                except Exception as fallback_error:
                    logger.warning(f"Fallback method also failed: {fallback_error}")
                    raise Exception(f"No transcript found for language: {language_code}")
            
            if not transcript_data:
                raise Exception(f"No transcript data found for language: {language_code}")

            # Process transcript with new enhanced processor
            try:
                from .utils.path_utils import load_config
                config = load_config()
            except Exception as e:
                logger.warning(f"Could not load config for transcript processing: {e}")
                config = {}
            
            processed_results = process_transcript_data(transcript_data, video_metadata, formats, config)
            
            # Save files and collect paths
            saved_files = {}
            
            for format_name, content in processed_results.items():
                if format_name == 'structured':
                    # Add processing timestamp to structured format
                    content['metadata']['processed_at'] = datetime.datetime.now().isoformat()
                
                # Determine filename
                if save_path and backward_compatible:
                    # Backward compatibility: use provided save_path for timestamped format
                    filename = save_path
                else:
                    # New naming convention: base_path + format suffix
                    base_name = save_path if save_path else f"{video_id}_{language_code}"
                    if base_name.endswith('.txt') or base_name.endswith('.json'):
                        base_name = base_name.rsplit('.', 1)[0]  # Remove extension
                    
                    if format_name == 'structured':
                        filename = f"{base_name}_structured.json"
                    elif format_name == 'clean':
                        filename = f"{base_name}_clean.txt"
                    else:  # timestamped
                        filename = f"{base_name}_timestamped.txt"
                
                # Ensure directory exists
                Path(filename).parent.mkdir(parents=True, exist_ok=True)
                
                # Save file
                if format_name == 'structured':
                    import json
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(content, f, indent=2, ensure_ascii=False, default=str)
                else:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                
                saved_files[format_name] = filename
                logger.debug(f"✅ Saved {format_name} format to: {filename}")

            logger.info(f"✅ Transcript download successful on attempt {attempt + 1}: {len(saved_files)} formats saved")
            
            # Backward compatibility: return single path if only one format
            if backward_compatible and len(saved_files) == 1:
                return list(saved_files.values())[0]
            else:
                return saved_files
            
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logger.error(f"💥 Transcript not available for video {video_id}: {str(e)}")
            raise Exception(f"Transcripts are disabled or not found for this video: {str(e)}")
            
        except Exception as e:
            logger.warning(f"❌ Transcript download attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries:
                logger.info(f"⏳ Retrying transcript download in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"💥 Transcript download failed after {max_retries + 1} attempts")
                raise Exception(f"Transcript download failed after {max_retries + 1} attempts: {str(e)}")
    
    return None
