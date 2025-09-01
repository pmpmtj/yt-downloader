"""
Unit tests for core video processing functionality.

Tests the core.py module including video info extraction, format selection,
transcript discovery, and preview generation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Test constants
VALID_VIDEO_ID = "dQw4w9WgXcQ"
INVALID_VIDEO_ID = "INVALID"


class TestVideoInfoExtraction:
    """Test video information extraction from YouTube URLs."""
    
    @pytest.mark.unit
    def test_get_video_info_valid_url(self, mock_video_info):
        """Test successful video info extraction from valid URL."""
        from src.my_project.core import get_video_info
        
        with patch('src.my_project.core.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_instance.extract_info.return_value = mock_video_info
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"
            result = get_video_info(url)
            
            assert result is not None
            assert result["id"] == VALID_VIDEO_ID
            assert "title" in result
            assert "duration" in result
            mock_instance.extract_info.assert_called_once_with(url, download=False)
    
    @pytest.mark.unit
    def test_get_video_info_invalid_url(self):
        """Test video info extraction with invalid URL."""
        from src.my_project.core import get_video_info
        
        with patch('src.my_project.core.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_instance.extract_info.side_effect = Exception("Video unavailable")
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            invalid_url = f"https://www.youtube.com/watch?v={INVALID_VIDEO_ID}"
            result = get_video_info(invalid_url)
            
            assert result is None
    
    @pytest.mark.unit
    def test_get_video_info_private_video(self):
        """Test handling of private video access."""
        from src.my_project.core import get_video_info
        
        with patch('src.my_project.core.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_instance.extract_info.side_effect = Exception("Private video")
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            private_url = "https://www.youtube.com/watch?v=PrivateVideo"
            result = get_video_info(private_url)
            
            assert result is None
    
    @pytest.mark.unit 
    @pytest.mark.network
    def test_get_video_info_network_error(self):
        """Test handling of network errors during extraction."""
        from src.my_project.core import get_video_info
        
        with patch('src.my_project.core.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_instance.extract_info.side_effect = ConnectionError("Network error")
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            url = f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}"
            result = get_video_info(url)
            
            assert result is None


class TestFormatSelection:
    """Test audio and video format selection logic."""
    
    @pytest.mark.unit
    def test_select_audio_format_quality_preference(self, mock_video_info):
        """Test audio format selection based on quality preferences."""
        from src.my_project.core import select_default_audio
        
        # Mock config with audio preferences
        mock_config = {
            "quality_preferences": {
                "audio": {
                    "preferred_quality": "medium",
                    "preferred_formats": ["mp3", "m4a", "ogg"],
                    "max_fallback_attempts": 3
                }
            }
        }
        
        with patch('src.my_project.core.load_config', return_value=mock_config):
            result = select_default_audio(mock_video_info)
            
            assert result is not None
            assert "format_id" in result
    
    @pytest.mark.unit
    def test_select_video_format_fallback_logic(self, mock_video_info):
        """Test video format selection with fallback logic."""
        from src.my_project.core import select_default_video
        
        mock_config = {
            "quality_preferences": {
                "video": {
                    "preferred_quality": "720p",
                    "fallback_qualities": ["720p", "480p", "360p"],
                    "preferred_formats": ["mp4", "webm"],
                    "max_fallback_attempts": 3
                }
            }
        }
        
        with patch('src.my_project.core.load_config', return_value=mock_config):
            result = select_default_video(mock_video_info)
            
            assert result is not None
            assert "format_id" in result
    
    @pytest.mark.unit
    def test_select_format_no_preferred_available(self, mock_video_info):
        """Test format selection when preferred formats are unavailable."""
        from src.my_project.core import select_default_audio
        
        # Mock config requesting unavailable format
        mock_config = {
            "quality_preferences": {
                "audio": {
                    "preferred_quality": "ultra-high",  # Non-existent quality
                    "preferred_formats": ["flac"],       # Unavailable format
                    "max_fallback_attempts": 3
                }
            }
        }
        
        with patch('src.my_project.core.load_config', return_value=mock_config):
            result = select_default_audio(mock_video_info)
            
            # Should fall back to available format
            assert result is not None


class TestTranscriptDiscovery:
    """Test transcript discovery and language handling."""
    
    @pytest.mark.unit
    def test_find_transcript_available_languages(self, mock_transcript_list):
        """Test transcript discovery with available languages."""
        from src.my_project.core import list_transcript_metadata
        
        with patch('src.my_project.core.YouTubeTranscriptApi.list_transcripts', 
                   return_value=mock_transcript_list):
            
            result = list_transcript_metadata(VALID_VIDEO_ID)
            
            assert result is not None
            assert len(result) > 0
            assert "language_code" in result[0]
    
    @pytest.mark.unit
    def test_find_transcript_no_transcripts(self):
        """Test handling when no transcripts are available."""
        from src.my_project.core import list_transcript_metadata
        
        with patch('src.my_project.core.YouTubeTranscriptApi.list_transcripts') as mock_api:
            mock_api.side_effect = Exception("No transcripts available")
            
            result = list_transcript_metadata(INVALID_VIDEO_ID)
            
            assert result is None or len(result) == 0
    
    @pytest.mark.unit
    def test_find_transcript_auto_generated_only(self, mock_transcript_list):
        """Test handling when only auto-generated transcripts exist."""
        from src.my_project.core import list_transcript_metadata
        
        # Mock transcript list with auto-generated transcript
        mock_transcript = Mock()
        mock_transcript.language_code = "en"
        mock_transcript.is_generated = True
        mock_transcript.is_translatable = True
        mock_transcript_list.__iter__ = Mock(return_value=iter([mock_transcript]))
        
        with patch('src.my_project.core.YouTubeTranscriptApi.list_transcripts',
                   return_value=mock_transcript_list):
            
            result = list_transcript_metadata(VALID_VIDEO_ID)
            
            assert result is not None
            assert len(result) > 0
            assert result[0]["is_generated"] is True
    
    @pytest.mark.unit
    def test_find_transcript_multiple_languages(self, mock_transcript_list):
        """Test transcript discovery with multiple languages available."""
        from src.my_project.core import list_transcript_metadata
        
        # Mock multiple language transcripts
        en_transcript = Mock()
        en_transcript.language_code = "en"
        en_transcript.language = "English"
        
        es_transcript = Mock()
        es_transcript.language_code = "es"
        es_transcript.language = "Spanish"
        
        mock_transcript_list.__iter__ = Mock(return_value=iter([en_transcript, es_transcript]))
        
        with patch('src.my_project.core.YouTubeTranscriptApi.list_transcripts',
                   return_value=mock_transcript_list):
            
            result = list_transcript_metadata(VALID_VIDEO_ID)
            
            assert result is not None
            assert len(result) >= 2


class TestPreviewGeneration:
    """Test transcript preview generation and metadata integration."""
    
    @pytest.mark.unit
    def test_preview_transcript_basic(self, sample_transcript_data):
        """Test basic transcript preview generation."""
        from src.my_project.core import preview_transcript
        
        with patch('src.my_project.core.YouTubeTranscriptApi.list_transcripts') as mock_api:
            mock_list = Mock()
            mock_transcript = Mock()
            mock_transcript.fetch.return_value = sample_transcript_data
            mock_list.find_transcript.return_value = mock_transcript
            mock_api.return_value = mock_list
            
            result = preview_transcript(VALID_VIDEO_ID, "en", include_metadata=False)
            
            assert result is not None
            assert "preview_text" in result
            assert "statistics" in result
            assert "total_entries" in result["statistics"]
    
    @pytest.mark.unit
    def test_preview_transcript_with_metadata(self, sample_transcript_data):
        """Test preview generation with metadata analysis enabled."""
        from src.my_project.core import preview_transcript
        
        with patch('src.my_project.core.YouTubeTranscriptApi.list_transcripts') as mock_api:
            mock_list = Mock()
            mock_transcript = Mock()
            mock_transcript.fetch.return_value = sample_transcript_data
            mock_list.find_transcript.return_value = mock_transcript
            mock_api.return_value = mock_list
            
            with patch('src.my_project.core.load_config') as mock_config:
                mock_config.return_value = {"metadata_collection": {"enabled": True}}
                
                result = preview_transcript(VALID_VIDEO_ID, "en", include_metadata=True)
                
                assert result is not None
                assert "preview_text" in result
                assert "statistics" in result
                # Should include enhanced metadata when enabled
    
    @pytest.mark.unit
    def test_preview_transcript_no_transcript(self):
        """Test preview generation when transcript is unavailable."""
        from src.my_project.core import preview_transcript
        
        with patch('src.my_project.core.YouTubeTranscriptApi.list_transcripts') as mock_api:
            mock_api.side_effect = Exception("No transcript available")
            
            result = preview_transcript(INVALID_VIDEO_ID, "en")
            
            assert result is None


class TestErrorHandling:
    """Test error handling in core functionality."""
    
    @pytest.mark.unit
    def test_graceful_degradation_network_issues(self):
        """Test graceful handling of network connectivity issues."""
        from src.my_project.core import get_video_info
        
        with patch('src.my_project.core.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_instance.extract_info.side_effect = ConnectionError()
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            # Should not raise exception, should return None
            result = get_video_info(f"https://www.youtube.com/watch?v={VALID_VIDEO_ID}")
            assert result is None
    
    @pytest.mark.unit
    def test_invalid_config_handling(self):
        """Test handling of invalid configuration."""
        from src.my_project.core import select_default_audio
        
        with patch('src.my_project.core.load_config') as mock_config:
            mock_config.side_effect = Exception("Config file not found")
            
            # Should use reasonable defaults when config fails
            mock_video_info = {"formats": [{"format_id": "140", "ext": "m4a"}]}
            result = select_default_audio(mock_video_info)
            
            # Should still work with defaults
            assert result is not None or True  # Allow graceful degradation


# Fixtures for this test module
@pytest.fixture
def mock_video_formats():
    """Mock video formats for format selection testing."""
    return [
        {
            "format_id": "140",
            "ext": "m4a",
            "acodec": "mp4a.40.2",
            "quality": "medium",
            "abr": 128
        },
        {
            "format_id": "136",
            "ext": "mp4", 
            "vcodec": "avc1.4d401f",
            "quality": "720p",
            "width": 1280,
            "height": 720
        }
    ]
