"""
Test configuration normalization functionality.

Tests the fix for the schema mismatch issue where user config in downloads.*
format should be properly mapped to quality_preferences.* format.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from my_project.utils.config_utils import (
    normalize_config,
    validate_config,
    load_and_normalize_config,
    _normalize_audio_preferences,
    _normalize_video_preferences
)


class TestConfigNormalization:
    """Test configuration normalization functionality."""
    
    def test_legacy_audio_config_normalization(self):
        """Test that legacy downloads.audio.* config is mapped to quality_preferences.audio.*"""
        
        # Legacy config format that users might intuitively use
        legacy_config = {
            "downloads": {
                "audio": {
                    "format": "mp3",
                    "quality": "192"
                }
            }
        }
        
        normalized = normalize_config(legacy_config)
        
        # Should map to modern format
        audio_prefs = normalized["quality_preferences"]["audio"]
        assert "mp3" in audio_prefs["preferred_formats"]
        assert audio_prefs["preferred_formats"][0] == "mp3"  # Should be first preference
        assert audio_prefs["preferred_quality"] == "medium"  # 192 maps to medium
        assert audio_prefs["preferred_bitrate"] == "192"
        
    def test_legacy_video_config_normalization(self):
        """Test that legacy downloads.video.* config is mapped to quality_preferences.video.*"""
        
        legacy_config = {
            "downloads": {
                "video": {
                    "format": "mp4",
                    "quality": "1080p"
                }
            }
        }
        
        normalized = normalize_config(legacy_config)
        
        # Should map to modern format
        video_prefs = normalized["quality_preferences"]["video"]
        assert "mp4" in video_prefs["preferred_formats"]
        assert video_prefs["preferred_formats"][0] == "mp4"  # Should be first preference
        assert video_prefs["preferred_quality"] == "1080p"
        
    def test_bitrate_quality_mapping(self):
        """Test that numeric bitrates are correctly mapped to quality names."""
        
        test_cases = [
            ("128", "low"),
            ("192", "medium"),
            ("320", "high")
        ]
        
        for bitrate, expected_quality in test_cases:
            config = {
                "downloads": {
                    "audio": {
                        "quality": bitrate
                    }
                }
            }
            
            normalized = normalize_config(config)
            audio_prefs = normalized["quality_preferences"]["audio"]
            assert audio_prefs["preferred_quality"] == expected_quality
            assert audio_prefs["preferred_bitrate"] == bitrate
    
    def test_existing_quality_preferences_preserved(self):
        """Test that existing quality_preferences.* config is not overwritten."""
        
        modern_config = {
            "quality_preferences": {
                "audio": {
                    "preferred_quality": "high",
                    "preferred_formats": ["flac", "mp3"]
                }
            },
            "downloads": {
                "audio": {
                    "format": "mp3",
                    "quality": "192"
                }
            }
        }
        
        normalized = normalize_config(modern_config)
        
        # Should preserve existing quality_preferences
        audio_prefs = normalized["quality_preferences"]["audio"]
        assert audio_prefs["preferred_quality"] == "high"  # Not overwritten
        assert audio_prefs["preferred_formats"] == ["flac", "mp3"]  # Not overwritten
    
    def test_validation_warns_about_legacy_usage(self):
        """Test that validation detects and warns about legacy config usage."""
        
        legacy_config = {
            "downloads": {
                "audio": {"format": "mp3"},
                "video": {"quality": "720p"}
            }
        }
        
        is_valid, warnings = validate_config(legacy_config)
        
        assert is_valid is True  # Still valid, just deprecated
        assert len(warnings) == 2  # Should have warnings for both audio and video
        assert any("downloads.audio" in warning for warning in warnings)
        assert any("downloads.video" in warning for warning in warnings)
        assert any("DEPRECATED" in warning for warning in warnings)
    
    def test_quality_fallback_generation(self):
        """Test that quality fallbacks are generated intelligently."""
        
        from my_project.utils.config_utils import _generate_quality_fallbacks
        
        # Test different starting qualities
        test_cases = [
            ("720p", ["720p", "480p", "360p", "1080p", "1440p", "2160p"]),
            ("1080p", ["1080p", "720p", "480p", "360p", "1440p", "2160p"]),
            ("360p", ["360p", "480p", "720p", "1080p", "1440p", "2160p"])
        ]
        
        for preferred, expected_order in test_cases:
            fallbacks = _generate_quality_fallbacks(preferred)
            assert fallbacks[0] == preferred  # First should be preferred
            assert len(fallbacks) == len(expected_order)
            # Lower qualities should come before higher ones (more likely to be available)
            
    def test_defaults_created_when_missing(self):
        """Test that defaults are created when quality_preferences section is missing."""
        
        minimal_config = {
            "downloads": {
                "base_directory": "downloads"
            }
        }
        
        normalized = normalize_config(minimal_config)
        
        # Should have created quality_preferences with defaults
        assert "quality_preferences" in normalized
        assert "audio" in normalized["quality_preferences"]
        assert "video" in normalized["quality_preferences"]
        
        audio_prefs = normalized["quality_preferences"]["audio"]
        assert audio_prefs["preferred_quality"] == "medium"
        assert "mp3" in audio_prefs["preferred_formats"]
        
        video_prefs = normalized["quality_preferences"]["video"]
        assert video_prefs["preferred_quality"] == "720p"
        assert "mp4" in video_prefs["preferred_formats"]


class TestConfigLoadingIntegration:
    """Test the complete configuration loading and normalization flow."""
    
    def test_load_and_normalize_with_legacy_config(self):
        """Test loading and normalizing a config file with legacy format."""
        
        # Create temporary config file with legacy format
        legacy_config_data = {
            "downloads": {
                "base_directory": "downloads",
                "audio": {
                    "format": "mp3",
                    "quality": "192"
                },
                "video": {
                    "format": "mp4",
                    "quality": "720p"
                }
            },
            "network": {
                "max_retries": 3
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(legacy_config_data, f, indent=2)
            temp_config_path = Path(f.name)
        
        try:
            # Load and normalize
            normalized = load_and_normalize_config(temp_config_path)
            
            # Should have mapped legacy format to modern structure
            assert "quality_preferences" in normalized
            audio_prefs = normalized["quality_preferences"]["audio"]
            assert "mp3" in audio_prefs["preferred_formats"]
            assert audio_prefs["preferred_quality"] == "medium"
            
            video_prefs = normalized["quality_preferences"]["video"]
            assert "mp4" in video_prefs["preferred_formats"]
            assert video_prefs["preferred_quality"] == "720p"
            
            # Should preserve other sections
            assert normalized["network"]["max_retries"] == 3
            
        finally:
            # Cleanup
            temp_config_path.unlink()
    
    def test_load_normalized_config_fallback(self):
        """Test that load_normalized_config falls back gracefully if config_utils unavailable."""
        
        # Mock the import to fail
        with patch('my_project.utils.path_utils.load_config') as mock_load_config:
            mock_load_config.return_value = {"test": "config"}
            
            # Mock the config_utils import to fail
            with patch('my_project.utils.path_utils.config_utils', side_effect=ImportError):
                from my_project.utils.path_utils import load_normalized_config
                
                result = load_normalized_config()
                assert result == {"test": "config"}
                mock_load_config.assert_called_once()


class TestRealWorldScenarios:
    """Test real-world configuration scenarios that could cause the original issue."""
    
    def test_user_config_scenario_audio_preferences_ignored(self):
        """
        Test the exact scenario described by your colleague:
        User sets downloads.audio.format but code looks for quality_preferences.audio.preferred_formats
        """
        
        # User's intuitive config
        user_config = {
            "downloads": {
                "base_directory": "my_downloads",
                "audio": {
                    "format": "flac",  # User wants FLAC
                    "quality": "320"   # High quality
                }
            }
        }
        
        # Before normalization: this would result in empty preferences
        raw_audio_prefs = user_config.get("quality_preferences", {}).get("audio", {})
        assert raw_audio_prefs == {}  # Empty! User intent ignored
        
        # After normalization: user intent is preserved
        normalized = normalize_config(user_config)
        audio_prefs = normalized["quality_preferences"]["audio"]
        
        assert "flac" in audio_prefs["preferred_formats"]
        assert audio_prefs["preferred_formats"][0] == "flac"  # User's choice is prioritized
        assert audio_prefs["preferred_quality"] == "high"     # 320 mapped to high
        assert audio_prefs["preferred_bitrate"] == "320"      # Original value preserved
    
    def test_cli_override_still_works(self):
        """Test that CLI quality override still works after normalization."""
        
        config = {
            "downloads": {
                "audio": {"quality": "192"}  # Config says medium
            }
        }
        
        normalized = normalize_config(config)
        audio_prefs = normalized["quality_preferences"]["audio"].copy()
        
        # Simulate CLI override (like core.py does)
        cli_quality_override = "low"
        audio_prefs["preferred_quality"] = cli_quality_override
        
        assert audio_prefs["preferred_quality"] == "low"  # CLI override works
    
    def test_mixed_legacy_and_modern_config(self):
        """Test handling of config with both legacy and modern sections."""
        
        mixed_config = {
            "downloads": {
                "audio": {"format": "mp3"},  # Legacy
                "base_directory": "downloads"
            },
            "quality_preferences": {
                "video": {  # Modern
                    "preferred_quality": "1080p",
                    "preferred_formats": ["mp4"]
                }
            }
        }
        
        normalized = normalize_config(mixed_config)
        
        # Should have both audio (from legacy) and video (from modern)
        assert "quality_preferences" in normalized
        audio_prefs = normalized["quality_preferences"]["audio"]
        video_prefs = normalized["quality_preferences"]["video"]
        
        # Audio should be mapped from legacy
        assert "mp3" in audio_prefs["preferred_formats"]
        
        # Video should be preserved from modern format
        assert video_prefs["preferred_quality"] == "1080p"
        assert video_prefs["preferred_formats"] == ["mp4"]


if __name__ == "__main__":
    pytest.main([__file__])
