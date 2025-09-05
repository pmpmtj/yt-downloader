"""
path_utils.py

Path resolution and file/directory utilities for cross-platform compatibility.
Handles both frozen (PyInstaller) and regular Python execution.
"""

import sys
import uuid
import re
from pathlib import Path
from typing import Union, Optional, Dict, Any
import json
import platform

# Initialize paths - handling both frozen (PyInstaller) and regular Python execution
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    SCRIPT_DIR = Path(sys._MEIPASS)
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as regular Python script
    SCRIPT_DIR = Path(__file__).resolve().parent.parent
    BASE_DIR = SCRIPT_DIR

def resolve_path(path_input: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """
    Resolve a path input to an absolute Path object.
    
    Args:
        path_input: String or Path object to resolve
        base_dir: Base directory to resolve relative paths against (defaults to SCRIPT_DIR)
    
    Returns:
        Resolved absolute Path object
    """
    if base_dir is None:
        base_dir = SCRIPT_DIR
    
    path = Path(path_input)
    
    # If already absolute, return as-is
    if path.is_absolute():
        return path
    
    # Resolve relative to base_dir
    return (base_dir / path).resolve()


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
    
    Returns:
        Path object of the created/existing directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def generate_session_uuid() -> str:
    """Generate a unique session identifier."""
    return str(uuid.uuid4())


def generate_video_uuid() -> str:
    """Generate a unique video identifier."""
    return str(uuid.uuid4())


def create_download_structure(base_dir: Union[str, Path], session_uuid: str, 
                            video_uuid: str, media_type: str) -> Path:
    """
    Create the download directory structure.
    
    Args:
        base_dir: Base downloads directory
        session_uuid: Session identifier
        video_uuid: Video identifier  
        media_type: Media type (audio, video, transcripts)
    
    Returns:
        Path to the created directory
    """
    download_path = Path(base_dir) / session_uuid / video_uuid / media_type
    return ensure_directory(download_path)


def load_config(config_file: Union[str, Path] = None) -> Dict[str, Any]:
    """
    Load application configuration from JSON file.
    
    Args:
        config_file: Path to config file (defaults to app_config.json in project)
    
    Returns:
        Configuration dictionary
    """
    if config_file is None:
        # Look for config in the package location
        config_file = Path(__file__).parent.parent / "config" / "app_config.json"
    
    config_path = resolve_path(config_file)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file {config_path}: {e}")


def load_normalized_config(config_file: Union[str, Path] = None) -> Dict[str, Any]:
    """
    Load and normalize application configuration from JSON file.
    
    This function handles schema mismatches and provides consistent configuration
    access regardless of whether the user uses legacy downloads.* or modern
    quality_preferences.* structure.
    
    Args:
        config_file: Path to config file (defaults to app_config.json in project)
    
    Returns:
        Normalized configuration dictionary
    """
    try:
        # Import here to avoid circular imports
        from .config_utils import load_and_normalize_config
        return load_and_normalize_config(config_file)
    except ImportError:
        # Fallback to basic load_config if config_utils not available
        return load_config(config_file)


def sanitize_filename(filename: str, config: Optional[Dict[str, Any]] = None) -> str:
    """
    Sanitize filename for Windows and cross-platform compatibility.
    
    Args:
        filename: Raw filename to sanitize
        config: Configuration dictionary (optional)
    
    Returns:
        Sanitized filename safe for Windows and other platforms
    """
    if config is None:
        try:
            config = load_normalized_config()
        except:
            config = {}
    
    behavior = config.get("behavior", {})
    sanitize_enabled = behavior.get("sanitize_filenames", True)
    max_length = behavior.get("max_filename_length", 255)
    
    if not sanitize_enabled:
        return filename
    
    # Windows reserved names (case insensitive)
    windows_reserved = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # Remove/replace illegal characters for Windows
    # < > : " | ? * are illegal in Windows filenames
    illegal_chars = r'[<>:"|?*]'
    sanitized = re.sub(illegal_chars, '_', filename)
    
    # Replace control characters (0-31)
    sanitized = re.sub(r'[\x00-\x1f]', '_', sanitized)
    
    # Handle Windows reserved names
    name_part = sanitized.split('.')[0].upper()
    if name_part in windows_reserved:
        sanitized = f"_{sanitized}"
    
    # Remove trailing dots and spaces (Windows issue)
    sanitized = sanitized.rstrip('. ')
    
    # Ensure not empty after sanitization
    if not sanitized:
        sanitized = "unnamed_file"
    
    # Truncate to max length while preserving extension
    if len(sanitized) > max_length:
        if '.' in sanitized:
            name, ext = sanitized.rsplit('.', 1)
            max_name_length = max_length - len(ext) - 1  # -1 for the dot
            if max_name_length > 0:
                sanitized = f"{name[:max_name_length]}.{ext}"
            else:
                sanitized = sanitized[:max_length]
        else:
            sanitized = sanitized[:max_length]
    
    return sanitized


def validate_path_length(full_path: Union[str, Path], config: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
    """
    Validate path length for Windows compatibility.
    
    Args:
        full_path: Full file path to validate
        config: Configuration dictionary (optional)
    
    Returns:
        Tuple of (is_valid, warning_message)
    """
    path_str = str(full_path)
    
    # Windows path length limits
    MAX_PATH_WINDOWS = 260
    MAX_FILENAME_WINDOWS = 255
    
    is_windows = platform.system().lower() == 'windows'
    
    if is_windows and len(path_str) > MAX_PATH_WINDOWS:
        return False, f"Path length ({len(path_str)}) exceeds Windows limit ({MAX_PATH_WINDOWS})"
    
    filename = Path(path_str).name
    if is_windows and len(filename) > MAX_FILENAME_WINDOWS:
        return False, f"Filename length ({len(filename)}) exceeds Windows limit ({MAX_FILENAME_WINDOWS})"
    
    return True, ""


def create_safe_path(base_dir: Union[str, Path], *path_parts: str, config: Optional[Dict[str, Any]] = None) -> Path:
    """
    Create a safe file path with proper sanitization and length validation.
    
    Args:
        base_dir: Base directory
        *path_parts: Path components to join
        config: Configuration dictionary (optional)
    
    Returns:
        Safe Path object
    
    Raises:
        ValueError: If path would exceed platform limits
    """
    # Sanitize each path component
    sanitized_parts = []
    for part in path_parts:
        if part:  # Skip empty parts
            sanitized_parts.append(sanitize_filename(part, config))
    
    # Build the full path
    full_path = Path(base_dir)
    for part in sanitized_parts:
        full_path = full_path / part
    
    # Validate path length
    is_valid, warning = validate_path_length(full_path, config)
    if not is_valid:
        # Try to shorten the path by truncating the filename
        if len(sanitized_parts) > 0:
            filename = sanitized_parts[-1]
            max_filename_len = 50  # Conservative limit for deeply nested paths
            if len(filename) > max_filename_len:
                # Preserve extension if present
                if '.' in filename:
                    name, ext = filename.rsplit('.', 1)
                    shortened = f"{name[:max_filename_len-len(ext)-1]}.{ext}"
                else:
                    shortened = filename[:max_filename_len]
                
                sanitized_parts[-1] = shortened
                full_path = Path(base_dir)
                for part in sanitized_parts:
                    full_path = full_path / part
                
                # Re-validate
                is_valid, warning = validate_path_length(full_path, config)
        
        if not is_valid:
            raise ValueError(f"Cannot create safe path: {warning}")
    
    return full_path


def get_downloads_directory(config: Optional[Dict[str, Any]] = None) -> Path:
    """
    Get the configured downloads directory.
    
    Args:
        config: Configuration dictionary (loads from file if None)
    
    Returns:
        Resolved downloads directory path
    """
    if config is None:
        config = load_config()
    
    base_dir = config.get("downloads", {}).get("base_directory", "downloads")
    return resolve_path(base_dir, BASE_DIR)

