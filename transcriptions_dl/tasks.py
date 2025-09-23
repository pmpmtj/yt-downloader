# transcriptions_dl/tasks.py
from background_task import background
from django.contrib.auth import get_user_model
from core.downloaders.transcriptions.dl_transcription import download_transcript_files, get_video_info
from core.shared_utils.security_utils import log_request_info
import os
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@background(schedule=0)
def process_transcript_download(url, task_id, output_dir, user_id, user_ip=None, user_agent=None):
    """
    Background task for processing transcript downloads.
    
    Args:
        url: YouTube video URL
        task_id: Unique task identifier
        output_dir: Directory to save transcript files
        user_id: ID of the user requesting the download
        user_ip: User's IP address
        user_agent: User's browser agent string
    """
    logger.info(f"Starting background transcript download task {task_id} for URL: {url}")
    
    try:
        # Get user object
        user = User.objects.get(id=user_id)
        
        # Log the background task start
        logger.info(f"Processing transcript download for user {user.email} (task: {task_id})")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Download transcript files using the core function
        success = download_transcript_files(url, output_dir=output_dir)
        
        if success:
            # Get video info for logging
            video_info = get_video_info(url)
            video_title = video_info.get('title', 'Unknown') if video_info else 'Unknown'
            
            logger.info(f"Successfully completed transcript download task {task_id} for: {video_title}")
            
            # TODO: Update database with success status when DB integration is added
            # For now, just log the success
            logger.info(f"Transcript files saved to: {output_dir}")
            
        else:
            logger.error(f"Failed to download transcript for task {task_id}")
            # TODO: Update database with failure status when DB integration is added
            
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found for task {task_id}")
    except Exception as e:
        logger.error(f"Error in background transcript download task {task_id}: {str(e)}")
        # TODO: Update database with error status when DB integration is added
