"""
Database utilities for saving transcript data to PostgreSQL.

This module provides functions to save transcript data from the core
downloaders into the Django database models.
"""
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from django.db import transaction
from django.conf import settings

from .models import Video, Chapter, TranscriptSegment, RawAsset


def sha256_text(text: str) -> str:
    """Generate SHA256 hash of text for deduplication."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def parse_upload_date(upload_date: Any) -> Optional[datetime]:
    """Parse upload date from various formats."""
    if not upload_date:
        return None
    
    if isinstance(upload_date, str):
        if len(upload_date) == 8 and upload_date.isdigit():
            # Format: 20250130 -> 2025-01-30
            return datetime.strptime(upload_date, "%Y%m%d").date()
        try:
            # Try parsing as ISO date
            return datetime.fromisoformat(upload_date).date()
        except ValueError:
            return None
    elif isinstance(upload_date, (int, float)):
        # Unix timestamp
        return datetime.fromtimestamp(upload_date).date()
    
    return None


def save_video_to_db(user, video_id: str, video_info: Dict[str, Any], 
                    structured_data: Dict[str, Any] = None) -> Video:
    """Save video information to database."""
    
    # Extract metadata from structured data or video_info
    metadata = structured_data or {}
    info = metadata.get("metadata") or metadata.get("info") or video_info
    
    # Parse basic video information
    title = (info.get("title") or 
             metadata.get("title") or 
             video_info.get("title") or 
             f"Video {video_id}")
    
    duration_s = (info.get("duration") or 
                  info.get("duration_s") or 
                  video_info.get("duration"))
    
    upload_date = parse_upload_date(
        info.get("upload_date") or 
        video_info.get("upload_date")
    )
    
    uploader = (info.get("uploader") or 
                info.get("channel") or 
                video_info.get("uploader"))
    
    language_code = (info.get("language") or 
                     info.get("language_code") or 
                     video_info.get("language_code"))
    
    is_generated = (info.get("is_generated") or 
                    video_info.get("is_generated"))
    
    # Calculate text statistics
    text_word_count = None
    text_char_count = None
    
    if structured_data:
        # Try to get text from segments or clean text
        segments = structured_data.get("snippets") or structured_data.get("segments") or []
        if segments:
            all_text = " ".join([seg.get("text", "") for seg in segments])
            text_word_count = len(all_text.split())
            text_char_count = len(all_text)
    
    # Create or update video record
    video, created = Video.objects.update_or_create(
        video_id=video_id,
        user=user,
        defaults={
            'title': title,
            'duration_s': int(duration_s) if duration_s else None,
            'upload_date': upload_date,
            'uploader': uploader,
            'language_code': language_code,
            'is_generated': is_generated,
            'metadata': metadata if metadata else {},
            'text_word_count': text_word_count,
            'text_char_count': text_char_count,
        }
    )
    
    return video


def save_chapters_to_db(video: Video, chapters: List[Dict[str, Any]]) -> None:
    """Save video chapters to database."""
    if not chapters:
        return
    
    # Delete existing chapters for this video
    Chapter.objects.filter(video=video).delete()
    
    # Create new chapters
    chapter_objects = []
    for chapter in chapters:
        start_time = float(chapter.get("start") or chapter.get("start_time") or 0.0)
        end_time = (float(chapter.get("end") or chapter.get("end_time")) 
                   if chapter.get("end") or chapter.get("end_time") else None)
        
        chapter_objects.append(Chapter(
            video=video,
            start_time_s=start_time,
            end_time_s=end_time,
            text=str(chapter.get("text") or chapter.get("title") or "").strip(),
            summary=chapter.get("summary"),
        ))
    
    Chapter.objects.bulk_create(chapter_objects)


def save_segments_to_db(video: Video, segments: List[Dict[str, Any]], 
                       source: str = "youtube", is_generated: bool = None) -> None:
    """Save transcript segments to database."""
    if not segments:
        return
    
    # Delete existing segments for this video
    TranscriptSegment.objects.filter(video=video).delete()
    
    # Create new segments
    segment_objects = []
    for segment in segments:
        # Handle both dict and string formats
        if isinstance(segment, str):
            # Skip string segments for now - they need to be parsed differently
            continue
            
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
            
        start_time = float(segment.get("start") or segment.get("start_time") or 0.0)
        duration = float(segment.get("duration") or segment.get("dur") or 0.0)
        
        # Calculate duration if not provided
        if duration <= 0.0 and segment.get("end"):
            duration = max(0.5, float(segment["end"]) - start_time)
        if duration <= 0.0:
            duration = 3.0  # Default duration
        
        # Create extra metadata
        extra = {k: v for k, v in segment.items() 
                if k not in {"text", "start", "start_time", "duration", "dur", "end"}}
        
        segment_objects.append(TranscriptSegment(
            video=video,
            start_time_s=start_time,
            duration_s=duration,
            text=text,
            is_generated=is_generated,
            source=source,
            text_hash=sha256_text(text),
            extra=extra,
        ))
    
    TranscriptSegment.objects.bulk_create(segment_objects)


def save_raw_assets_to_db(video: Video, clean_text: str = None, 
                         timestamped_text: str = None, 
                         structured_json: Dict[str, Any] = None) -> None:
    """Save raw transcript files to database."""
    
    # Save clean text
    if clean_text:
        RawAsset.objects.update_or_create(
            video=video,
            kind='clean_text',
            defaults={'content_text': clean_text}
        )
    
    # Save timestamped text
    if timestamped_text:
        RawAsset.objects.update_or_create(
            video=video,
            kind='timestamped',
            defaults={'content_text': timestamped_text}
        )
    
    # Save structured JSON
    if structured_json:
        RawAsset.objects.update_or_create(
            video=video,
            kind='structured_json',
            defaults={'content_json': structured_json}
        )


@transaction.atomic
def save_transcript_to_db(user, video_id: str, video_info: Dict[str, Any],
                         structured_data: Dict[str, Any] = None,
                         segments: List[Dict[str, Any]] = None,
                         chapters: List[Dict[str, Any]] = None,
                         clean_text: str = None,
                         timestamped_text: str = None,
                         source: str = "youtube",
                         is_generated: bool = None) -> Video:
    """
    Save complete transcript data to database in a single transaction.
    
    Args:
        user: Django user instance
        video_id: YouTube video ID
        video_info: Basic video information from yt-dlp
        structured_data: Structured JSON data from transcript processor
        segments: List of transcript segments
        chapters: List of video chapters
        clean_text: Clean text content
        timestamped_text: Timestamped text content
        source: Source of transcript (default: "youtube")
        is_generated: Whether transcript is auto-generated
    
    Returns:
        Video instance
    """
    
    # Save video information
    video = save_video_to_db(user, video_id, video_info, structured_data)
    
    # Save chapters
    if chapters:
        save_chapters_to_db(video, chapters)
    
    # Save segments
    if segments:
        save_segments_to_db(video, segments, source, is_generated)
    
    # Save raw assets
    save_raw_assets_to_db(
        video, 
        clean_text=clean_text,
        timestamped_text=timestamped_text,
        structured_json=structured_data
    )
    
    return video
