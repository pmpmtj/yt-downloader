#!/usr/bin/env python3
"""
Standalone runner for YouTube downloader modules.

This script provides a unified interface for running download modules
outside of the Django web application context.
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to Python path
current_dir = Path(__file__).resolve()
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def setup_django():
    """Initialize Django settings for standalone execution."""
    try:
        import django
        from django.conf import settings
        
        # Set Django settings module
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube_downloader.settings')
        
        # Configure Django
        django.setup()
        
        print("✓ Django settings initialized successfully")
        return True
    except Exception as e:
        print(f"⚠ Warning: Could not initialize Django settings: {e}")
        print("Running without database logging capabilities.")
        return False

def run_audio_download(url: str, output_dir: str = None):
    """Run audio download with proper error handling."""
    try:
        from core.downloaders.audio.download_audio import download_audio
        
        print(f"Starting audio download for: {url}")
        result = download_audio(url, output_dir)
        
        if result['success']:
            print(f"✓ Download successful!")
            print(f"  File: {result['filename']}")
            print(f"  Path: {result['filepath']}")
            if result.get('metadata', {}).get('title'):
                print(f"  Title: {result['metadata']['title']}")
        else:
            print(f"✗ Download failed: {result['error']}")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Unexpected error during audio download: {e}")
        return False

def run_video_download(url: str, output_dir: str = None):
    """Run video download with proper error handling."""
    try:
        from core.downloaders.shared_downloader import download_video
        
        print(f"Starting video download for: {url}")
        result = download_video(url, output_dir)
        
        if result['success']:
            print(f"✓ Download successful!")
            print(f"  File: {result['filename']}")
            print(f"  Path: {result['filepath']}")
            if result.get('metadata', {}).get('title'):
                print(f"  Title: {result['metadata']['title']}")
        else:
            print(f"✗ Download failed: {result['error']}")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Unexpected error during video download: {e}")
        return False

def main():
    """Main entry point for standalone runner."""
    parser = argparse.ArgumentParser(
        description="YouTube Downloader - Standalone Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python standalone_runner.py audio "https://www.youtube.com/watch?v=VIDEO_ID"
  python standalone_runner.py video "https://www.youtube.com/watch?v=VIDEO_ID" --output-dir ./downloads
  python standalone_runner.py audio "https://www.youtube.com/watch?v=VIDEO_ID" --output-dir /path/to/output
        """
    )
    
    parser.add_argument(
        'type',
        choices=['audio', 'video'],
        help='Type of download (audio or video)'
    )
    
    parser.add_argument(
        'url',
        help='YouTube URL to download'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for downloaded files (default: current directory)'
    )
    
    parser.add_argument(
        '--no-django',
        action='store_true',
        help='Skip Django initialization (no database logging)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("YouTube Downloader - Standalone Runner")
    print("=" * 60)
    
    # Initialize Django unless disabled
    if not args.no_django:
        django_initialized = setup_django()
    else:
        print("⚠ Django initialization skipped")
        django_initialized = False
    
    # Validate URL
    if not args.url or not ('youtube.com' in args.url or 'youtu.be' in args.url):
        print("✗ Error: Please provide a valid YouTube URL")
        sys.exit(1)
    
    # Run the appropriate download
    success = False
    if args.type == 'audio':
        success = run_audio_download(args.url, args.output_dir)
    elif args.type == 'video':
        success = run_video_download(args.url, args.output_dir)
    
    # Exit with appropriate code
    if success:
        print("\n✓ Download completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Download failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
