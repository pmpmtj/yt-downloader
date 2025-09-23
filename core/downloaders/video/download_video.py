# save as: download_video.py
import sys
from ..shared_downloader import download_video as shared_download_video

def download_video(url: str, output_dir: str = None, user=None, user_ip=None, user_agent=None, download_source='api', task_id=None, user_cookies: str = None) -> dict:
    """
    Download video from YouTube URL using shared downloader.
    
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
            'job_id': str,
            'filepath': str or None,
            'filename': str or None,
            'error': str or None,
            'metadata': dict
        }
    """
    result = shared_download_video(url, output_dir, user=user, user_ip=user_ip, user_agent=user_agent, download_source=download_source, task_id=task_id, user_cookies=user_cookies)
    
    # Return in the original format for backward compatibility
    return {
        'success': result['success'],
        'job_id': result.get('job_id'),
        'filepath': result['filepath'],
        'filename': result['filename'],
        'error': result['error'],
        'metadata': result.get('metadata', {})
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python download_video.py <YouTube URL>")
        sys.exit(1)
    
    result = download_video(sys.argv[1])
    if result['success']:
        print(f"Downloaded: {result['filename']}")
    else:
        print(f"Error: {result['error']}")
        sys.exit(1)
