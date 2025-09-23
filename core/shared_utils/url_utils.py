"""
URL utilities for YouTube URL sanitization and parsing.

This module provides utilities for cleaning and validating YouTube URLs,
extracting metadata, and handling various URL formats consistently.
"""

import re
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass

# Initialize logger
logger = logging.getLogger("url_utils")


@dataclass
class YouTubeURLInfo:
    """Information extracted from a YouTube URL."""
    video_id: str
    clean_url: str
    timestamp: Optional[int] = None  # timestamp in seconds
    playlist_id: Optional[str] = None
    playlist_index: Optional[int] = None
    original_url: str = ""
    url_type: str = "standard"  # standard, short, embed, mobile


class YouTubeURLError(Exception):
    """Exception raised for invalid YouTube URLs."""
    pass


class YouTubeURLSanitizer:
    """
    YouTube URL sanitizer and parser.
    
    Handles various YouTube URL formats and extracts clean URLs with metadata.
    Supports standard, short, embed, mobile, and playlist URLs.
    """
    
    # YouTube URL patterns (order matters - more specific patterns first)
    PATTERNS = {
        'mobile': [
            r'(?:https?://)?m\.youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})',
        ],
        'embed': [
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ],
        'short': [
            r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        ],
        'standard': [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})',
        ]
    }
    
    @classmethod
    def sanitize_url(cls, url: str, preserve_metadata: bool = True) -> YouTubeURLInfo:
        """
        Sanitize a YouTube URL and extract metadata.
        
        Args:
            url: The YouTube URL to sanitize
            preserve_metadata: Whether to extract and preserve metadata (timestamp, playlist info)
            
        Returns:
            YouTubeURLInfo object with clean URL and metadata
            
        Raises:
            YouTubeURLError: If the URL is not a valid YouTube URL
        """
        if not url or not isinstance(url, str):
            raise YouTubeURLError("URL must be a non-empty string")
        
        original_url = url.strip()
        logger.debug(f"Sanitizing URL: {original_url}")
        
        # Extract video ID and determine URL type
        video_id, url_type = cls._extract_video_id(original_url)
        if not video_id:
            raise YouTubeURLError(f"Could not extract video ID from URL: {original_url}")
        
        # Extract metadata if requested
        metadata = {}
        if preserve_metadata:
            metadata = cls._extract_metadata(original_url, url_type)
        
        # Generate clean URL
        clean_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create YouTubeURLInfo object
        url_info = YouTubeURLInfo(
            video_id=video_id,
            clean_url=clean_url,
            timestamp=metadata.get('timestamp'),
            playlist_id=metadata.get('playlist_id'),
            playlist_index=metadata.get('playlist_index'),
            original_url=original_url,
            url_type=url_type
        )
        
        logger.debug(f"Sanitized URL: {clean_url} (type: {url_type})")
        if metadata:
            logger.debug(f"Extracted metadata: {metadata}")
        
        return url_info
    
    @classmethod
    def get_clean_url(cls, url: str) -> str:
        """
        Get just the clean URL without metadata.
        
        Args:
            url: The YouTube URL to sanitize
            
        Returns:
            Clean YouTube URL
            
        Raises:
            YouTubeURLError: If the URL is not a valid YouTube URL
        """
        url_info = cls.sanitize_url(url, preserve_metadata=False)
        return url_info.clean_url
    
    @classmethod
    def _extract_video_id(cls, url: str) -> Tuple[Optional[str], str]:
        """
        Extract video ID from various YouTube URL formats.
        
        Args:
            url: YouTube URL
            
        Returns:
            Tuple of (video_id, url_type)
        """
        # Try each pattern type
        for url_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    video_id = match.group(1)
                    # Validate video ID format
                    if re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                        return video_id, url_type
        
        return None, "unknown"
    
    @classmethod
    def _extract_metadata(cls, url: str, url_type: str) -> Dict[str, Any]:
        """
        Extract metadata from YouTube URL.
        
        Args:
            url: YouTube URL
            url_type: Type of URL (standard, short, embed, mobile)
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}
        
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Extract timestamp
            timestamp = cls._extract_timestamp(query_params, parsed.fragment, url_type)
            if timestamp is not None:
                metadata['timestamp'] = timestamp
            
            # Extract playlist information
            if 'list' in query_params:
                playlist_id = query_params['list'][0]
                if playlist_id:
                    metadata['playlist_id'] = playlist_id
            
            if 'index' in query_params:
                try:
                    playlist_index = int(query_params['index'][0])
                    metadata['playlist_index'] = playlist_index
                except (ValueError, IndexError):
                    pass
            
        except Exception as e:
            logger.warning(f"Error extracting metadata from URL {url}: {e}")
        
        return metadata
    
    @classmethod
    def _extract_timestamp(cls, query_params: Dict, fragment: str, url_type: str) -> Optional[int]:
        """
        Extract timestamp from URL parameters or fragment.
        
        Args:
            query_params: Parsed query parameters
            fragment: URL fragment
            url_type: Type of URL
            
        Returns:
            Timestamp in seconds, or None if not found
        """
        timestamp = None
        
        # Check query parameters for timestamp
        for param in ['t', 'start']:
            if param in query_params:
                timestamp_str = query_params[param][0]
                timestamp = cls._parse_timestamp(timestamp_str)
                if timestamp is not None:
                    break
        
        # Check fragment for timestamp (e.g., #t=30s)
        if timestamp is None and fragment:
            fragment_match = re.search(r't=(\d+[smh]?)', fragment)
            if fragment_match:
                timestamp = cls._parse_timestamp(fragment_match.group(1))
        
        return timestamp
    
    @classmethod
    def _parse_timestamp(cls, timestamp_str: str) -> Optional[int]:
        """
        Parse timestamp string to seconds.
        
        Args:
            timestamp_str: Timestamp string (e.g., "30", "30s", "1m30s", "1h2m30s")
            
        Returns:
            Timestamp in seconds, or None if invalid
        """
        if not timestamp_str:
            return None
        
        try:
            # Handle simple numeric timestamp
            if timestamp_str.isdigit():
                return int(timestamp_str)
            
            # Check for invalid characters first
            if re.search(r'[^0-9hms]', timestamp_str):
                return None
            
            # Check for invalid patterns (like starting with units)
            if re.search(r'^[hms]', timestamp_str):
                return None
            
            # Initialize total seconds
            total_seconds = 0
            
            # Parse hours
            hours_match = re.search(r'(\d+)h', timestamp_str)
            if hours_match:
                total_seconds += int(hours_match.group(1)) * 3600
            
            # Parse minutes - look for number followed by 'm'
            minutes_match = re.search(r'(\d+)m', timestamp_str)
            if minutes_match:
                total_seconds += int(minutes_match.group(1)) * 60
            
            # Parse seconds - look for number followed by 's' or at the end
            seconds_match = re.search(r'(\d+)s', timestamp_str)
            if seconds_match:
                total_seconds += int(seconds_match.group(1))
            else:
                # Check for trailing number without 's' (only if no other units found)
                if not hours_match and not minutes_match:
                    trailing_match = re.search(r'(\d+)$', timestamp_str)
                    if trailing_match:
                        total_seconds += int(trailing_match.group(1))
            
            return total_seconds if total_seconds > 0 else None
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse timestamp '{timestamp_str}': {e}")
            return None
    
    @classmethod
    def is_youtube_url(cls, url: str) -> bool:
        """
        Check if a URL is a valid YouTube URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if it's a valid YouTube URL, False otherwise
        """
        try:
            video_id, _ = cls._extract_video_id(url)
            return video_id is not None
        except Exception:
            return False
    
    @classmethod
    def extract_video_id(cls, url: str) -> Optional[str]:
        """
        Extract just the video ID from a YouTube URL.
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID or None if not found
        """
        try:
            video_id, _ = cls._extract_video_id(url)
            return video_id
        except Exception:
            return None


# Convenience functions for easy imports
def sanitize_youtube_url(url: str, preserve_metadata: bool = True) -> YouTubeURLInfo:
    """
    Sanitize a YouTube URL and extract metadata.
    
    Args:
        url: The YouTube URL to sanitize
        preserve_metadata: Whether to extract and preserve metadata
        
    Returns:
        YouTubeURLInfo object with clean URL and metadata
        
    Raises:
        YouTubeURLError: If the URL is not a valid YouTube URL
    """
    return YouTubeURLSanitizer.sanitize_url(url, preserve_metadata)


def get_clean_youtube_url(url: str) -> str:
    """
    Get a clean YouTube URL without parameters.
    
    Args:
        url: YouTube URL to clean
        
    Returns:
        Clean YouTube URL
        
    Raises:
        YouTubeURLError: If the URL is not a valid YouTube URL
    """
    return YouTubeURLSanitizer.get_clean_url(url)


def is_youtube_url(url: str) -> bool:
    """
    Check if a URL is a valid YouTube URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if it's a valid YouTube URL, False otherwise
    """
    return YouTubeURLSanitizer.is_youtube_url(url)


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from a YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID or None if not found
    """
    return YouTubeURLSanitizer.extract_video_id(url)
