"""
config_utils.py

Configuration normalization and validation utilities.
Handles schema mismatches and provides consistent configuration access.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

# Import logging
from ..logger_utils.logger_utils import setup_logger

# Setup logger for this module
logger = setup_logger("config_utils")


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize configuration to ensure consistent schema.
    
    Maps legacy/intuitive config paths to expected internal structure.
    
    Args:
        config: Raw configuration dictionary
    
    Returns:
        Normalized configuration dictionary
    """
    logger.debug("Starting configuration normalization")
    normalized = config.copy()
    
    # Normalize audio preferences
    normalized = _normalize_audio_preferences(normalized)
    
    # Normalize video preferences  
    normalized = _normalize_video_preferences(normalized)
    
    # Validate critical sections exist
    normalized = _ensure_quality_preferences_structure(normalized)
    
    logger.debug("Configuration normalization complete")
    return normalized


def _normalize_audio_preferences(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize audio configuration from various possible sources."""
    
    # Check if quality_preferences.audio already exists (preferred structure)
    if config.get("quality_preferences", {}).get("audio"):
        logger.debug("Using existing quality_preferences.audio configuration")
        return config
    
    # Check for legacy downloads.audio structure
    downloads_audio = config.get("downloads", {}).get("audio", {})
    if downloads_audio:
        logger.info("Mapping legacy downloads.audio to quality_preferences.audio")
        
        # Ensure quality_preferences section exists
        if "quality_preferences" not in config:
            config["quality_preferences"] = {}
        if "audio" not in config["quality_preferences"]:
            config["quality_preferences"]["audio"] = {}
        
        audio_prefs = config["quality_preferences"]["audio"]
        
        # Map legacy format → preferred_formats
        if "format" in downloads_audio and "preferred_formats" not in audio_prefs:
            format_value = downloads_audio["format"]
            audio_prefs["preferred_formats"] = [format_value, "mp3", "m4a", "ogg"]
            logger.debug(f"Mapped downloads.audio.format='{format_value}' to preferred_formats")
        
        # Map legacy quality → preferred_quality
        if "quality" in downloads_audio and "preferred_quality" not in audio_prefs:
            quality_value = downloads_audio["quality"]
            # Map bitrate numbers to quality names
            if quality_value in ["128", "192", "320"]:
                if quality_value == "128":
                    audio_prefs["preferred_quality"] = "low"
                elif quality_value == "192":
                    audio_prefs["preferred_quality"] = "medium"
                elif quality_value == "320":
                    audio_prefs["preferred_quality"] = "high"
                audio_prefs["preferred_bitrate"] = quality_value
            else:
                audio_prefs["preferred_quality"] = quality_value
            logger.debug(f"Mapped downloads.audio.quality='{quality_value}' to preferred_quality")
        
        # Set reasonable defaults if not specified
        if "preferred_codec" not in audio_prefs:
            audio_prefs["preferred_codec"] = downloads_audio.get("format", "mp3")
        if "fallback_qualities" not in audio_prefs:
            audio_prefs["fallback_qualities"] = ["medium", "low", "high"]
        if "max_fallback_attempts" not in audio_prefs:
            audio_prefs["max_fallback_attempts"] = 3
    
    return config


def _normalize_video_preferences(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize video configuration from various possible sources."""
    
    # Check if quality_preferences.video already exists (preferred structure)
    if config.get("quality_preferences", {}).get("video"):
        logger.debug("Using existing quality_preferences.video configuration")
        return config
    
    # Check for legacy downloads.video structure
    downloads_video = config.get("downloads", {}).get("video", {})
    if downloads_video:
        logger.info("Mapping legacy downloads.video to quality_preferences.video")
        
        # Ensure quality_preferences section exists
        if "quality_preferences" not in config:
            config["quality_preferences"] = {}
        if "video" not in config["quality_preferences"]:
            config["quality_preferences"]["video"] = {}
        
        video_prefs = config["quality_preferences"]["video"]
        
        # Map legacy format → preferred_formats
        if "format" in downloads_video and "preferred_formats" not in video_prefs:
            format_value = downloads_video["format"]
            video_prefs["preferred_formats"] = [format_value, "mp4", "webm", "mkv"]
            logger.debug(f"Mapped downloads.video.format='{format_value}' to preferred_formats")
        
        # Map legacy quality → preferred_quality
        if "quality" in downloads_video and "preferred_quality" not in video_prefs:
            quality_value = downloads_video["quality"]
            video_prefs["preferred_quality"] = quality_value
            logger.debug(f"Mapped downloads.video.quality='{quality_value}' to preferred_quality")
        
        # Set reasonable defaults if not specified
        if "fallback_qualities" not in video_prefs:
            current_quality = video_prefs.get("preferred_quality", "720p")
            video_prefs["fallback_qualities"] = _generate_quality_fallbacks(current_quality)
        if "max_fallback_attempts" not in video_prefs:
            video_prefs["max_fallback_attempts"] = 3
    
    return config


def _generate_quality_fallbacks(preferred_quality: str) -> list:
    """Generate sensible quality fallback list based on preferred quality."""
    quality_order = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]
    
    if preferred_quality not in quality_order:
        return ["720p", "480p", "360p", "1080p"]  # Safe defaults
    
    # Create fallback list starting with preferred, then nearby qualities
    preferred_index = quality_order.index(preferred_quality)
    fallbacks = [preferred_quality]
    
    # Add lower qualities (more likely to be available)
    for i in range(preferred_index - 1, -1, -1):
        fallbacks.append(quality_order[i])
    
    # Add higher qualities
    for i in range(preferred_index + 1, len(quality_order)):
        fallbacks.append(quality_order[i])
    
    return fallbacks


def _ensure_quality_preferences_structure(config: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure quality_preferences section has required structure."""
    
    if "quality_preferences" not in config:
        config["quality_preferences"] = {}
    
    # Ensure audio section exists with defaults
    if "audio" not in config["quality_preferences"]:
        config["quality_preferences"]["audio"] = {
            "preferred_quality": "medium",
            "preferred_codec": "mp3",
            "preferred_bitrate": "192",
            "fallback_qualities": ["medium", "low", "high"],
            "preferred_formats": ["mp3", "m4a", "ogg"],
            "max_fallback_attempts": 3
        }
        logger.debug("Created default audio preferences")
    
    # Ensure video section exists with defaults
    if "video" not in config["quality_preferences"]:
        config["quality_preferences"]["video"] = {
            "preferred_quality": "720p",
            "fallback_qualities": ["720p", "480p", "360p", "1080p"],
            "preferred_formats": ["mp4", "webm", "mkv"],
            "max_fallback_attempts": 3
        }
        logger.debug("Created default video preferences")
    
    return config


def validate_config(config: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate configuration and return warnings for deprecated usage.
    
    Args:
        config: Configuration dictionary to validate
    
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    is_valid = True
    
    # Check for legacy downloads.audio usage
    if config.get("downloads", {}).get("audio"):
        warnings.append(
            "DEPRECATED: downloads.audio.* configuration detected. "
            "Please migrate to quality_preferences.audio.* format. "
            "See documentation for details."
        )
    
    # Check for legacy downloads.video usage
    if config.get("downloads", {}).get("video"):
        warnings.append(
            "DEPRECATED: downloads.video.* configuration detected. "
            "Please migrate to quality_preferences.video.* format. "
            "See documentation for details."
        )
    
    # Check for missing critical sections
    if not config.get("quality_preferences"):
        warnings.append(
            "INFO: No quality_preferences section found. Using defaults."
        )
    
    return is_valid, warnings


def load_and_normalize_config(config_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration file and apply normalization.
    
    Args:
        config_file: Path to config file (uses default if None)
    
    Returns:
        Normalized configuration dictionary
    """
    logger.debug(f"Loading and normalizing config from: {config_file}")
    
    # Load raw config
    from .path_utils import load_config
    try:
        raw_config = load_config(config_file)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise
    
    # Validate and warn about deprecated usage
    is_valid, warnings = validate_config(raw_config)
    for warning in warnings:
        logger.warning(warning)
    
    # Normalize configuration
    normalized_config = normalize_config(raw_config)
    
    logger.info("Configuration loaded and normalized successfully")
    return normalized_config
