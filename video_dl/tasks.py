"""Background tasks for video downloads (django-background-tasks).

This module defines a single task function that can be enqueued via
django-background-tasks. It downloads the YouTube video to MEDIA_ROOT/downloads/video.
"""

from pathlib import Path
from typing import Dict, Any
from background_task import background

from django.conf import settings

# Reuse your existing core downloader
# (keeps behavior identical between sync and async paths)
from core.downloaders.video.download_video import download_video
from core.shared_utils.url_utils import YouTubeURLSanitizer, YouTubeURLError
from cookie_management.cookie_manager import get_user_cookies


@background(schedule=0)  # Run immediately
def process_youtube_video(url: str, task_id: str = None, output_dir: str = None, user_id: int = None, user_ip: str = None, user_agent: str = None):
    """Download video for the given URL into user-specific directory.
    
    Args:
        url: YouTube URL to download
        task_id: Optional task identifier for tracking
        output_dir: User-specific output directory path
        user_id: User ID for database logging
        user_ip: User's IP address
        user_agent: User's browser/agent string
    """
    try:
        # Validate YouTube URL before processing
        if not YouTubeURLSanitizer.is_youtube_url(url):
            print(f"Background task {task_id} failed: Invalid YouTube URL")
            return
        
        # Get user object for database logging
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            print(f"Background task {task_id} failed: User {user_id} not found")
            return
        
        # Get user cookies for authentication
        user_cookies = get_user_cookies(user) if user else None
        
        # Use the core download function with user-specific directory
        result = download_video(
            url, 
            output_dir=output_dir,
            user=user,
            user_ip=user_ip,
            user_agent=user_agent,
            download_source='api_async',
            task_id=task_id,
            user_cookies=user_cookies
        )
        
        if result['success']:
            print(f"Background task {task_id} completed successfully: {result['filename']}")
        else:
            print(f"Background task {task_id} failed: {result['error']}")
            
    except Exception as e:
        print(f"Background task {task_id} encountered an exception: {str(e)}")
