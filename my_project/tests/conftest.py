"""
Shared pytest configuration and fixtures for YouTube Downloader tests.

This module provides common fixtures and configuration used across all test modules.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary directory with test configuration files."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # Create test app_config.json
    test_config = {
        "downloads": {
            "base_directory": "downloads",
            "create_session_folders": True,
            "create_video_folders": True,
            "folder_structure": "{session_uuid}/{video_uuid}/{media_type}"
        },
        "quality_preferences": {
            "video": {
                "preferred_quality": "720p",
                "fallback_qualities": ["720p", "480p", "360p", "1080p"],
                "preferred_formats": ["mp4", "webm", "mkv"],
                "max_fallback_attempts": 3
            },
            "audio": {
                "preferred_quality": "medium",
                "preferred_codec": "mp3",
                "preferred_bitrate": "192",
                "fallback_qualities": ["medium", "low", "high"],
                "preferred_formats": ["mp3", "m4a", "ogg"],
                "max_fallback_attempts": 3
            }
        },
        "transcripts": {
            "preferred_languages": ["en", "en-US", "en-GB"],
            "include_timestamps": True,
            "fallback_to_auto_generated": True,
            "max_fallback_attempts": 3,
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
                    "filler_words": ["um", "uh", "like", "you know", "so", "well"]
                }
            }
        },
        "metadata_collection": {
            "enabled": True,
            "content_analysis": {
                "extract_topics": True,
                "extract_keywords": True,
                "content_categorization": True
            },
            "quality_assessment": {
                "content_quality_score": True,
                "transcript_confidence": True
            }
        },
        "network": {
            "max_retries": 3,
            "retry_delay_seconds": 2,
            "timeout_seconds": 30
        }
    }
    
    with open(config_dir / "app_config.json", "w") as f:
        json.dump(test_config, f, indent=2)
    
    return config_dir


@pytest.fixture
def mock_video_info():
    """Mock yt-dlp video info response for a typical video."""
    return {
        "id": "dQw4w9WgXcQ",
        "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
        "uploader": "Rick Astley",
        "uploader_id": "@RickAstleyYT",
        "duration": 212,
        "view_count": 1400000000,
        "like_count": 15000000,
        "upload_date": "20091025",
        "description": "The official video for 'Never Gonna Give You Up' by Rick Astley.",
        "categories": ["Music"],
        "tags": ["rick astley", "never gonna give you up", "80s", "pop"],
        "webpage_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "formats": [
            {
                "format_id": "140",
                "format": "m4a audio only",
                "ext": "m4a",
                "acodec": "mp4a.40.2",
                "abr": 128,
                "filesize": 3400000,
                "quality": "medium"
            },
            {
                "format_id": "136", 
                "format": "mp4 720p",
                "ext": "mp4",
                "width": 1280,
                "height": 720,
                "vcodec": "avc1.4d401f",
                "filesize": 45000000,
                "quality": "720p"
            }
        ]
    }


@pytest.fixture
def sample_transcript_data():
    """Sample transcript data for testing transcript processing."""
    return [
        {"text": "We're no strangers to love", "start": 0.0, "duration": 2.5},
        {"text": "You know the rules and so do I", "start": 2.5, "duration": 3.0},
        {"text": "A full commitment's what I'm thinking of", "start": 5.5, "duration": 3.5},
        {"text": "You wouldn't get this from any other guy", "start": 9.0, "duration": 4.0},
        {"text": "I just wanna tell you how I'm feeling", "start": 13.0, "duration": 3.0},
        {"text": "Gotta make you understand", "start": 16.0, "duration": 2.5},
        {"text": "Never gonna give you up", "start": 18.5, "duration": 2.5},
        {"text": "Never gonna let you down", "start": 21.0, "duration": 2.5},
        {"text": "Never gonna run around and desert you", "start": 23.5, "duration": 3.5}
    ]


@pytest.fixture
def mock_transcript_response():
    """Mock YouTube transcript API response."""
    mock_transcript = Mock()
    mock_transcript.fetch.return_value = [
        {"text": "We're no strangers to love", "start": 0.0, "duration": 2.5},
        {"text": "You know the rules and so do I", "start": 2.5, "duration": 3.0},
        {"text": "Never gonna give you up", "start": 18.5, "duration": 2.5}
    ]
    return mock_transcript


@pytest.fixture
def mock_transcript_list():
    """Mock transcript list with language options."""
    mock_list = Mock()
    mock_transcript = Mock()
    mock_transcript.language_code = "en"
    mock_transcript.language = "English (auto-generated)"
    mock_transcript.is_generated = True
    mock_transcript.is_translatable = True
    mock_transcript.is_default = True
    
    mock_list.find_transcript.return_value = mock_transcript
    mock_list.__iter__ = Mock(return_value=iter([mock_transcript]))
    
    return mock_list


@pytest.fixture
def temp_download_dir(tmp_path):
    """Create temporary download directory with proper structure."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    
    # Create session directory structure
    session_uuid = "test-session-uuid-12345"
    video_uuid = "test-video-uuid-67890"
    
    session_dir = download_dir / session_uuid
    video_dir = session_dir / video_uuid
    
    # Create media type directories
    (video_dir / "audio").mkdir(parents=True)
    (video_dir / "video").mkdir(parents=True)
    (video_dir / "transcripts").mkdir(parents=True)
    
    return {
        "base_dir": download_dir,
        "session_dir": session_dir,
        "video_dir": video_dir,
        "session_uuid": session_uuid,
        "video_uuid": video_uuid
    }


@pytest.fixture
def mock_logger():
    """Mock logger for testing logging functionality."""
    return Mock()


@pytest.fixture
def sample_export_metadata():
    """Sample metadata for testing export functionality."""
    return {
        "video_metadata": {
            "id": "dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "uploader": "Rick Astley",
            "duration": 212,
            "view_count": 1400000000
        },
        "transcript_analysis": {
            "content_analysis": {
                "keywords": [
                    {"keyword": "love", "frequency": 3},
                    {"keyword": "never", "frequency": 8}
                ],
                "content_type": {
                    "primary_category": "Music",
                    "confidence": 0.95
                }
            },
            "quality_assessment": {
                "quality_score": 92.5,
                "quality_category": "Excellent"
            }
        }
    }


@pytest.fixture
def cli_runner():
    """Pytest fixture for testing CLI commands."""
    from click.testing import CliRunner
    return CliRunner()


# Test data constants
VALID_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
INVALID_YOUTUBE_URL = "https://www.youtube.com/watch?v=INVALID"
PRIVATE_VIDEO_URL = "https://www.youtube.com/watch?v=PrivateVideo"
DELETED_VIDEO_URL = "https://www.youtube.com/watch?v=DeletedVideo"

# Error message constants for consistent testing
ERROR_MESSAGES = {
    "invalid_url": "Invalid YouTube URL format",
    "video_unavailable": "Video unavailable",
    "private_video": "This video is private",
    "deleted_video": "This video has been deleted",
    "network_error": "Network connection failed",
    "permission_denied": "Permission denied",
    "disk_full": "No space left on device"
}


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment before each test to ensure isolation."""
    # This fixture runs automatically before each test
    # Can be used to reset global state, clear caches, etc.
    yield
    # Cleanup after test if needed
