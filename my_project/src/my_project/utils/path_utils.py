"""
path_utils.py

Path resolution and file/directory utilities for cross-platform compatibility.
Handles both frozen (PyInstaller) and regular Python execution.
"""

import sys
import uuid
from pathlib import Path
from typing import Union, Optional, Dict, Any
import json

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

