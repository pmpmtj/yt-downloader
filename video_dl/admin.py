# video_dl/admin.py
"""
Video download admin configuration.

Note: The DownloadJob and JobMetadata models are already registered
in audio_dl.admin since they support both audio and video downloads.
This file is kept for future video-specific admin customizations.
"""

# The models are already registered in audio_dl.admin
# No additional admin registration needed since we reuse the same models