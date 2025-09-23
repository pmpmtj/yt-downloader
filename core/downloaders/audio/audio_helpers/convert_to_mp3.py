"""
Audio conversion utilities for YouTube downloader.

This module provides functions to convert downloaded audio files to MP3 format
using FFmpeg, with integration to the application configuration system.
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Union, Dict, Any

from core.shared_utils.path_utils import resolve_path
from core.shared_utils.app_config import APP_CONFIG

# Initialize logger for this module
logger = logging.getLogger("convert_to_mp3")


def convert_to_mp3(input_file: Union[str, Path], output_dir: Union[str, Path] = None) -> Dict[str, Any]:
    """
    Convert an audio file to MP3 format using FFmpeg.
    Hardcoded settings: 192k quality, saves to specified output directory.
    Original file removal is controlled by configuration.
    
    Args:
        input_file: Path to input audio file
        output_dir: Directory to save MP3 file (defaults to same directory as input)
        
    Returns:
        dict: {
            'success': bool,
            'input_file': str,
            'output_file': str or None,
            'error': str or None
        }
    """
    logger.info(f"Starting MP3 conversion for: {input_file}")
    
    # Resolve input file path
    input_path = resolve_path(input_file)
    
    if not input_path.exists():
        error_msg = f"Input file does not exist: {input_path}"
        logger.error(error_msg)
        return {
            'success': False,
            'input_file': str(input_path),
            'output_file': None,
            'error': error_msg
        }
    
    # Check if conversion is enabled in config
    save_to_mp3 = APP_CONFIG.get("audio", {}).get("save_to_mp3", "False")
    if save_to_mp3.lower() != "true":
        logger.info("MP3 conversion disabled in configuration")
        return {
            'success': False,
            'input_file': str(input_path),
            'output_file': None,
            'error': "MP3 conversion disabled in configuration"
        }
    
    # Get remove_original setting from config
    remove_original = APP_CONFIG.get("audio", {}).get("remove_original", "True")
    should_remove_original = remove_original.lower() == "true"
    
    # Find FFmpeg
    ffmpeg_path = shutil.which('ffmpeg') or shutil.which('ffmpeg.exe')
    if not ffmpeg_path:
        error_msg = "FFmpeg not found in system PATH"
        logger.error(error_msg)
        return {
            'success': False,
            'input_file': str(input_path),
            'output_file': None,
            'error': error_msg
        }
    
    # Create output filename in specified directory (or same directory as input)
    output_dir_path = resolve_path(output_dir) if output_dir else input_path.parent
    output_filename = input_path.stem + ".mp3"
    output_path = output_dir_path / output_filename
    
    logger.debug(f"Output path: {output_path}")
    
    try:
        # Build FFmpeg command with hardcoded settings
        cmd = [
            ffmpeg_path,
            '-i', str(input_path),
            '-codec:a', 'libmp3lame',
            '-b:a', '192k',  # Hardcoded quality
            '-y',  # Overwrite output file if it exists
            str(output_path)
        ]
        
        logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
        
        # Run FFmpeg conversion
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            logger.info(f"Successfully converted to MP3: {output_path}")
            
            # Remove original file if configured to do so
            if should_remove_original:
                try:
                    input_path.unlink()
                    logger.info(f"Removed original file: {input_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove original file: {e}")
            else:
                logger.info(f"Keeping original file: {input_path}")
            
            return {
                'success': True,
                'input_file': str(input_path),
                'output_file': str(output_path),
                'error': None
            }
        else:
            error_msg = f"FFmpeg conversion failed: {result.stderr}"
            logger.error(error_msg)
            return {
                'success': False,
                'input_file': str(input_path),
                'output_file': None,
                'error': error_msg
            }
            
    except subprocess.TimeoutExpired:
        error_msg = "FFmpeg conversion timed out (5 minutes)"
        logger.error(error_msg)
        return {
            'success': False,
            'input_file': str(input_path),
            'output_file': None,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error during conversion: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'input_file': str(input_path),
            'output_file': None,
            'error': error_msg
        }


if __name__ == "__main__":
    # Test the conversion function
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python convert_to_mp3.py <audio_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    result = convert_to_mp3(input_file)
    
    if result['success']:
        print(f"Conversion successful!")
        print(f"Input: {result['input_file']}")
        print(f"Output: {result['output_file']}")
    else:
        print(f"Conversion failed: {result['error']}")
        sys.exit(1)