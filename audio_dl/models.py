from django.db import models
from django.contrib.auth import get_user_model
import json
import uuid

User = get_user_model()


class DownloadJob(models.Model):
    """Primary job tracking table for all download operations."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('downloading', 'Downloading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    DOWNLOAD_TYPE_CHOICES = [
        ('audio', 'Audio'),
        ('video', 'Video'),
    ]
    
    # Primary identification
    job_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Job ID")
    task_id = models.UUIDField(null=True, blank=True, verbose_name="Background Task ID")
    
    # Job details
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="User")
    url = models.URLField(max_length=500, verbose_name="YouTube URL")
    download_type = models.CharField(max_length=10, choices=DOWNLOAD_TYPE_CHOICES, verbose_name="Download Type")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Status")
    
    # File information
    filename = models.CharField(max_length=255, null=True, blank=True, verbose_name="Filename")
    filepath = models.TextField(null=True, blank=True, verbose_name="File Path")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="File Size (bytes)")
    
    # Error information
    error_message = models.TextField(null=True, blank=True, verbose_name="Error Message")
    error_details = models.JSONField(null=True, blank=True, verbose_name="Error Details")
    
    # Tracking information
    user_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="User IP Address")
    user_agent = models.TextField(null=True, blank=True, verbose_name="User Agent")
    download_source = models.CharField(max_length=20, default='api', verbose_name="Download Source")  # 'api', 'website', 'api_async'
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Started At")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    
    # Duration calculation
    @property
    def duration_seconds(self):
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    class Meta:
        verbose_name = "Download Job"
        verbose_name_plural = "Download Jobs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['job_id']),
            models.Index(fields=['task_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.download_type} - {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class JobMetadata(models.Model):
    """Detailed metadata table for download jobs."""
    
    job = models.OneToOneField(DownloadJob, on_delete=models.CASCADE, related_name='metadata', verbose_name="Download Job")
    
    # YouTube metadata (from yt-dlp)
    title = models.CharField(max_length=500, null=True, blank=True, verbose_name="Video Title")
    duration = models.IntegerField(null=True, blank=True, verbose_name="Duration (seconds)")
    uploader = models.CharField(max_length=200, null=True, blank=True, verbose_name="Uploader")
    upload_date = models.DateField(null=True, blank=True, verbose_name="Upload Date")
    view_count = models.BigIntegerField(null=True, blank=True, verbose_name="View Count")
    like_count = models.BigIntegerField(null=True, blank=True, verbose_name="Like Count")
    
    # Technical metadata
    format_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="Format ID")
    ext = models.CharField(max_length=10, null=True, blank=True, verbose_name="File Extension")
    vcodec = models.CharField(max_length=50, null=True, blank=True, verbose_name="Video Codec")
    acodec = models.CharField(max_length=50, null=True, blank=True, verbose_name="Audio Codec")
    filesize = models.BigIntegerField(null=True, blank=True, verbose_name="File Size")
    fps = models.FloatField(null=True, blank=True, verbose_name="FPS")
    
    # Complete yt-dlp metadata as JSON
    raw_metadata = models.JSONField(null=True, blank=True, verbose_name="Raw Metadata")
    
    # Additional tracking
    download_speed = models.FloatField(null=True, blank=True, verbose_name="Download Speed (MB/s)")
    retry_count = models.IntegerField(default=0, verbose_name="Retry Count")
    
    # Soft delete tracking
    is_deleted = models.BooleanField(default=False, verbose_name="Is Deleted")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deleted At")
    deletion_reason = models.CharField(max_length=200, null=True, blank=True, verbose_name="Deletion Reason")
    
    class Meta:
        verbose_name = "Job Metadata"
        verbose_name_plural = "Job Metadata"
        ordering = ['-job__created_at']
    
    def __str__(self):
        return f"Metadata for {self.job}"

# Create your models here.
