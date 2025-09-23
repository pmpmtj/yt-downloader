# video_dl/models.py
"""
Video download models.

This module re-exports the shared models from audio_dl since they already
support both audio and video download types through the download_type field.
"""

# Import the shared models from audio_dl
from audio_dl.models import DownloadJob, JobMetadata

# Re-export for convenience and to maintain app independence
__all__ = ['DownloadJob', 'JobMetadata']