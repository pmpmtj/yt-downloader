# save as: download_audio.py
import sys
import os
import django
from pathlib import Path

# Initialize Django settings for standalone execution
def setup_django():
    """Initialize Django settings for standalone module execution."""
    try:
        # Get the project root directory
        current_dir = Path(__file__).resolve()
        project_root = current_dir.parent.parent.parent.parent
        
        # Add project root to Python path
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Set Django settings module
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youtube_downloader.settings')
        
        # Configure Django
        django.setup()
        
        return True
    except Exception as e:
        print(f"Warning: Could not initialize Django settings: {e}")
        print("Running without database logging capabilities.")
        return False

from ..shared_downloader import download_audio as shared_download_audio

def download_audio(url: str, output_dir: str = None, user=None, user_ip=None, user_agent=None, download_source='api', task_id=None, user_cookies: str = None) -> dict:
    """
    Download audio from YouTube URL using shared downloader.
    
    Args:
        url: YouTube URL to download
        output_dir: Directory to save file (defaults to current working directory)
        user: Django User instance for database logging
        user_ip: User's IP address
        user_agent: User's browser/agent string
        download_source: Source of download ('api', 'website', 'api_async')
        task_id: Background task ID for async jobs
        user_cookies: User's YouTube cookies for authentication
    
    Returns:
        dict: {
            'success': bool,
            'filepath': str or None,
            'filename': str or None,
            'error': str or None,
            'job_id': str,
            'metadata': dict
        }
    """
    result = shared_download_audio(url, output_dir, user=user, user_ip=user_ip, user_agent=user_agent, download_source=download_source, task_id=task_id, user_cookies=user_cookies)
    
    # Return in the original format for backward compatibility
    return {
        'success': result['success'],
        'filepath': result['filepath'],
        'filename': result['filename'],
        'error': result['error'],
        'job_id': result.get('job_id'),
        'metadata': result.get('metadata', {})
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_audio.py <YouTube URL>")
        sys.exit(1)
    
    # Initialize Django for standalone execution
    django_initialized = setup_django()
    
    try:
        result = download_audio(sys.argv[1])
        if result['success']:
            print(f"Downloaded: {result['filename']}")
            print(f"File saved to: {result['filepath']}")
        else:
            print(f"Error: {result['error']}")
            sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
