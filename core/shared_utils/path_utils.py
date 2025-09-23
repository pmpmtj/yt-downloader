# my_project/path_utils/path_utils.py
"""
path_utils.py

Generic path resolution and file/directory utilities for cross-platform compatibility.
Handles both frozen (PyInstaller) and regular Python execution.
"""

import sys
import logging
from pathlib import Path
from typing import Union, Optional

# Initialize logger for this module
logger = logging.getLogger("path_utils")

def get_script_directories() -> tuple[Path, Path]:
    """
    Get SCRIPT_DIR and BASE_DIR handling both frozen (PyInstaller) and regular Python execution.
    
    Returns:
        Tuple of (SCRIPT_DIR, BASE_DIR)
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        script_dir = Path(sys._MEIPASS)
        base_dir = Path(sys.executable).parent
        logger.debug("Running as compiled executable (PyInstaller)")
    else:
        # Running as regular Python script
        script_dir = Path(__file__).resolve().parent.parent
        base_dir = script_dir
        logger.debug("Running as regular Python script")
    
    logger.debug(f"Script directories: SCRIPT_DIR={script_dir}, BASE_DIR={base_dir}")
    return script_dir, base_dir


def resolve_path(path_input: Union[str, Path], base_dir: Optional[Path] = None) -> Path:
    """
    Resolve a path input to an absolute Path object.

    Args:
        path_input: String or Path object to resolve
        base_dir: Base directory to resolve relative paths against (defaults to current working directory)

    Returns:
        Resolved absolute Path object
    """
    if base_dir is None:
        base_dir = Path.cwd()

    path = Path(path_input)

    # If already absolute, return as-is
    if path.is_absolute():
        return path

    # Resolve relative to base_dir
    return (base_dir / path).resolve()


def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists
        log_creation: Whether to log directory creation

    Returns:
        Path object of the created/existing directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

