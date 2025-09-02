#!/usr/bin/env python3
"""
test_yt_downloads_utils.py

Unit tests for yt_downloads_utils module.
Tests download functionality, transcript processing, and file creation.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import json
import os
from datetime import datetime

from src.my_project.yt_downloads_utils import (
    download_audio,
    download_video, 
    download_video_with_audio,
    download_transcript
)

# Import create_download_structure from utils.path_utils instead
from src.my_project.utils.path_utils import create_download_structure


class TestDownloadAudio:
    """Test audio download functionality."""
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YoutubeDL')
    def test_download_audio_success(self, mock_ydl):
        """Test successful audio download."""
        # Setup mock
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0  # Success
        
        url = "https://www.youtube.com/watch?v=test123"
        format_id = "140"
        save_path = "/test/path/audio.m4a"
        
        result = download_audio(url, format_id, save_path)
        
        assert result is True
        mock_instance.download.assert_called_once_with([url])
        
        # Check ydl options
        call_args = mock_ydl.call_args[0][0]
        assert call_args['format'] == format_id
        assert call_args['outtmpl'] == save_path
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YoutubeDL')
    def test_download_audio_failure(self, mock_ydl):
        """Test audio download failure."""
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = Exception("Download failed")
        
        url = "https://www.youtube.com/watch?v=test123"
        format_id = "140"
        save_path = "/test/path/audio.m4a"
        
        result = download_audio(url, format_id, save_path)
        
        assert result is False
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YoutubeDL')
    def test_download_audio_with_custom_options(self, mock_ydl):
        """Test audio download with custom ydl options."""
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0
        
        url = "https://www.youtube.com/watch?v=test123"
        format_id = "251"
        save_path = "/test/path/audio.webm"
        custom_options = {'writesubtitles': True, 'writeautomaticsub': False}
        
        result = download_audio(url, format_id, save_path, ydl_opts=custom_options)
        
        assert result is True
        call_args = mock_ydl.call_args[0][0]
        assert call_args['writesubtitles'] is True
        assert call_args['writeautomaticsub'] is False


class TestDownloadVideo:
    """Test video download functionality."""
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YoutubeDL')
    def test_download_video_success(self, mock_ydl):
        """Test successful video download."""
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0
        
        url = "https://www.youtube.com/watch?v=test123"
        format_id = "22"
        save_path = "/test/path/video.mp4"
        
        result = download_video(url, format_id, save_path)
        
        assert result is True
        mock_instance.download.assert_called_once_with([url])
        
        call_args = mock_ydl.call_args[0][0]
        assert call_args['format'] == format_id
        assert call_args['outtmpl'] == save_path
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YoutubeDL')
    def test_download_video_network_error(self, mock_ydl):
        """Test video download with network error."""
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.side_effect = ConnectionError("Network error")
        
        url = "https://www.youtube.com/watch?v=test123"
        format_id = "22"
        save_path = "/test/path/video.mp4"
        
        result = download_video(url, format_id, save_path)
        
        assert result is False


class TestDownloadVideoWithAudio:
    """Test combined video+audio download functionality."""
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YoutubeDL')
    def test_download_video_with_audio_success(self, mock_ydl):
        """Test successful video+audio download."""
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0
        
        url = "https://www.youtube.com/watch?v=test123"
        quality = "720p"
        save_path = "/test/path/video_audio.%(ext)s"
        
        result = download_video_with_audio(url, quality, save_path)
        
        assert result is True
        mock_instance.download.assert_called_once_with([url])
        
        call_args = mock_ydl.call_args[0][0]
        assert call_args['outtmpl'] == save_path
        # Should use bestvideo+bestaudio format
        assert 'bestvideo' in call_args['format'] or 'best' in call_args['format']
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YoutubeDL')
    def test_download_video_with_audio_quality_preference(self, mock_ydl):
        """Test video+audio download respects quality preference."""
        mock_instance = Mock()
        mock_ydl.return_value.__enter__.return_value = mock_instance
        mock_instance.download.return_value = 0
        
        url = "https://www.youtube.com/watch?v=test123"
        quality = "1080p"
        save_path = "/test/path/video_audio.%(ext)s"
        
        result = download_video_with_audio(url, quality, save_path)
        
        assert result is True
        call_args = mock_ydl.call_args[0][0]
        # Should include height preference in format string
        format_str = call_args['format']
        assert '[height<=1080]' in format_str or '1080' in format_str


class TestDownloadTranscript:
    """Test transcript download functionality."""
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YouTubeTranscriptApi')
    @patch('src.my_project.yt_downloads_utils.process_transcript_data')
    @patch('src.my_project.yt_downloads_utils.Path')
    def test_download_transcript_success(self, mock_path, mock_process, mock_api):
        """Test successful transcript download."""
        # Setup mocks
        mock_transcript_data = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 2.0},
            {'text': 'This is a test', 'start': 2.0, 'duration': 3.0}
        ]
        mock_api.get_transcript.return_value = mock_transcript_data
        
        mock_processed = {
            'timestamped': 'timestamped content',
            'clean': 'clean content',
            'structured': {'metadata': 'structured content'}
        }
        mock_process.return_value = mock_processed
        
        # Mock Path and file operations
        mock_path_instance = Mock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.parent.mkdir = Mock()
        
        video_id = "test123"
        language_code = "en"
        save_path = "/test/path/transcript.txt"
        formats = ["timestamped", "clean"]
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = download_transcript(video_id, language_code, save_path, formats=formats)
        
        assert isinstance(result, dict)
        assert 'timestamped' in result
        assert 'clean' in result
        
        # Verify API call
        mock_api.get_transcript.assert_called_once_with(video_id, languages=[language_code])
        mock_process.assert_called_once_with(mock_transcript_data, None, formats, None)
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YouTubeTranscriptApi')
    def test_download_transcript_api_error(self, mock_api):
        """Test transcript download with API error."""
        from youtube_transcript_api import NoTranscriptFound
        mock_api.get_transcript.side_effect = NoTranscriptFound(
            "test123", ["en"], "No transcript found"
        )
        
        video_id = "test123"
        language_code = "en"
        save_path = "/test/path/transcript.txt"
        
        result = download_transcript(video_id, language_code, save_path)
        
        assert result is None
    
    @pytest.mark.unit
    @patch('src.my_project.yt_downloads_utils.YouTubeTranscriptApi')
    def test_download_transcript_with_retries(self, mock_api):
        """Test transcript download with retry logic."""
        # First call fails, second succeeds
        mock_transcript_data = [{'text': 'Hello', 'start': 0.0, 'duration': 1.0}]
        mock_api.get_transcript.side_effect = [
            ConnectionError("Network error"),
            mock_transcript_data
        ]
        
        with patch('src.my_project.yt_downloads_utils.process_transcript_data') as mock_process:
            mock_process.return_value = {'timestamped': 'content'}
            
            with patch('src.my_project.yt_downloads_utils.Path'):
                with patch('builtins.open', create=True):
                    result = download_transcript("test123", "en", "/test/path", max_retries=3)
        
        assert result is not None
        assert mock_api.get_transcript.call_count == 2


# Removed TestProcessTranscriptData class since that function doesn't exist in yt_downloads_utils
# The transcript processing logic is handled in transcript_processor.py


class TestCreateDownloadStructure:
    """Test download directory structure creation."""
    
    @pytest.mark.unit
    def test_create_download_structure_success(self, tmp_path):
        """Test successful directory structure creation."""
        base_dir = str(tmp_path)
        session_uuid = "session123"
        video_uuid = "video456"
        download_type = "audio"
        
        result_path = create_download_structure(base_dir, session_uuid, video_uuid, download_type)
        
        assert result_path.exists()
        assert result_path.is_dir()
        
        # Check the structure
        expected_path = tmp_path / session_uuid / video_uuid / download_type
        assert result_path == expected_path
    
    @pytest.mark.unit
    def test_create_download_structure_multiple_types(self, tmp_path):
        """Test creating multiple download type directories."""
        base_dir = str(tmp_path)
        session_uuid = "session123"
        video_uuid = "video456"
        
        audio_path = create_download_structure(base_dir, session_uuid, video_uuid, "audio")
        video_path = create_download_structure(base_dir, session_uuid, video_uuid, "video")
        transcript_path = create_download_structure(base_dir, session_uuid, video_uuid, "transcripts")
        
        assert audio_path.exists()
        assert video_path.exists()
        assert transcript_path.exists()
        
        # All should be siblings under same video directory
        assert audio_path.parent == video_path.parent == transcript_path.parent
    
    @pytest.mark.unit
    def test_create_download_structure_existing_directory(self, tmp_path):
        """Test creating structure when directory already exists."""
        base_dir = str(tmp_path)
        session_uuid = "session123"
        video_uuid = "video456"
        download_type = "audio"
        
        # Create directory first
        first_path = create_download_structure(base_dir, session_uuid, video_uuid, download_type)
        
        # Create again - should not error
        second_path = create_download_structure(base_dir, session_uuid, video_uuid, download_type)
        
        assert first_path == second_path
        assert second_path.exists()
    
    @pytest.mark.unit
    def test_create_download_structure_permission_error(self, tmp_path):
        """Test handling permission errors during directory creation."""
        # Create a read-only base directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        
        with pytest.raises(PermissionError):
            create_download_structure(str(readonly_dir), "session123", "video456", "audio")


class TestUtilityFunctions:
    """Test utility functions and edge cases."""
    
    @pytest.mark.unit
    def test_download_functions_with_none_parameters(self):
        """Test download functions handle None parameters gracefully."""
        # These should not crash but return False
        assert download_audio(None, "140", "/test/path") is False
        assert download_video("https://test.com", None, "/test/path") is False
        assert download_video_with_audio("https://test.com", "720p", None) is False
    
    @pytest.mark.unit 
    def test_download_transcript_invalid_parameters(self):
        """Test download_transcript with invalid parameters."""
        # None video_id should return None
        result = download_transcript(None, "en", "/test/path")
        assert result is None
        
        # Empty language_code should return None  
        result = download_transcript("test123", "", "/test/path")
        assert result is None
    
    # Removed test for process_transcript_data as it doesn't exist in yt_downloads_utils
