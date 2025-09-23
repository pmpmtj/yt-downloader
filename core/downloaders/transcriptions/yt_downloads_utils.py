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
try:
    from .logger_utils.logger_utils import setup_logger
except ImportError:
    from logger_utils.logger_utils import setup_logger

# Setup logger for this module
logger = setup_logger("yt_downloads_utils")


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
    try:
        from .transcript_processor import process_transcript_data
    except ImportError:
        from transcript_processor import process_transcript_data
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
            from .dl_transcription import _get_transcript_list
            transcript_list = _get_transcript_list(video_id)
            
            # Find the transcript for our language and fetch it
            transcript_data = None
            for transcript in transcript_list:
                if hasattr(transcript, 'language_code') and transcript.language_code == language_code:
                    fetched_transcript = transcript.fetch()
                    # Extract the actual segments from the FetchedTranscript object and convert to dicts
                    transcript_data = [
                        {
                            'text': snippet.text,
                            'start': snippet.start,
                            'duration': snippet.duration
                        }
                        for snippet in fetched_transcript.snippets
                    ]
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
            # Use minimal config for standalone operation
            config = {
                "transcripts": {
                    "processing": {
                        "output_formats": {
                            "clean": True,
                            "timestamped": True,
                            "structured": True
                        },
                        "text_cleaning": {
                            "enabled": True,
                            "remove_filler_words": True,
                            "normalize_whitespace": True,
                            "fix_transcription_artifacts": True,
                            "filler_words": ["um", "uh", "like", "you know", "so", "well", "actually", "basically", "literally"]
                        }
                    }
                }
            }
            
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
