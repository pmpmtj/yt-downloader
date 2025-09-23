from django.db import models
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import MinValueValidator
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector


class Video(models.Model):
    """Main video information and metadata."""
    video_id = models.CharField(max_length=50, primary_key=True, help_text="YouTube video ID (e.g., '_L1JbzDnEMk')")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transcript_videos')
    title = models.TextField(help_text="Video title")
    duration_s = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0)],
        help_text="Duration in seconds"
    )
    upload_date = models.DateField(null=True, blank=True, help_text="Video upload date")
    uploader = models.TextField(null=True, blank=True, help_text="Channel/uploader name")
    language_code = models.CharField(max_length=10, null=True, blank=True, help_text="Language code (e.g., 'en')")
    is_generated = models.BooleanField(null=True, blank=True, help_text="Auto-generated captions?")
    metadata = models.JSONField(default=dict, help_text="Raw video metadata")
    processed_at = models.DateTimeField(auto_now_add=True, help_text="When transcript was processed")
    text_word_count = models.PositiveIntegerField(null=True, blank=True, help_text="Total word count")
    text_char_count = models.PositiveIntegerField(null=True, blank=True, help_text="Total character count")
    
    class Meta:
        db_table = 'transcriptions_video'
        indexes = [
            models.Index(fields=['user', 'video_id']),
            models.Index(fields=['user', 'processed_at']),
            models.Index(fields=['language_code']),
        ]
    
    def __str__(self):
        return f"{self.video_id}: {self.title[:50]}"


class Chapter(models.Model):
    """Video chapters for navigation."""
    id = models.BigAutoField(primary_key=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='chapters')
    start_time_s = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        validators=[MinValueValidator(0)],
        help_text="Chapter start time in seconds"
    )
    end_time_s = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Chapter end time in seconds"
    )
    text = models.TextField(help_text="Chapter title/text")
    summary = models.TextField(null=True, blank=True, help_text="Chapter summary")
    
    class Meta:
        db_table = 'transcriptions_chapter'
        indexes = [
            models.Index(fields=['video', 'start_time_s']),
        ]
        ordering = ['start_time_s']
    
    def __str__(self):
        return f"Chapter {self.start_time_s}s: {self.text[:30]}"


class TranscriptSegment(models.Model):
    """Individual transcript segments for search and playback."""
    id = models.BigAutoField(primary_key=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='segments')
    start_time_s = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        validators=[MinValueValidator(0)],
        help_text="Segment start time in seconds"
    )
    duration_s = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        validators=[MinValueValidator(0)],
        help_text="Segment duration in seconds"
    )
    text = models.TextField(help_text="Segment text content")
    is_generated = models.BooleanField(null=True, blank=True, help_text="Auto-generated segment?")
    source = models.CharField(max_length=50, default='youtube', help_text="Source of transcript")
    text_hash = models.CharField(max_length=64, help_text="SHA256 hash of text for deduplication")
    extra = models.JSONField(default=dict, help_text="Additional segment metadata")
    search_vector = SearchVectorField(null=True, blank=True, help_text="Full-text search vector")
    
    class Meta:
        db_table = 'transcriptions_segment'
        indexes = [
            models.Index(fields=['video', 'start_time_s']),
            GinIndex(fields=['search_vector'], name='seg_tsv_idx'),
        ]
        ordering = ['start_time_s']
    
    def __str__(self):
        return f"Segment {self.start_time_s}s: {self.text[:50]}"


class RawAsset(models.Model):
    """Original transcript files stored as text/JSON."""
    ASSET_TYPES = [
        ('clean_text', 'Clean Text'),
        ('timestamped', 'Timestamped Text'),
        ('structured_json', 'Structured JSON'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='raw_assets')
    kind = models.CharField(max_length=20, choices=ASSET_TYPES, help_text="Type of asset")
    content_text = models.TextField(null=True, blank=True, help_text="Text content")
    content_json = models.JSONField(null=True, blank=True, help_text="JSON content")
    stored_at = models.DateTimeField(auto_now_add=True, help_text="When asset was stored")
    
    class Meta:
        db_table = 'transcriptions_rawasset'
        indexes = [
            models.Index(fields=['video', 'kind']),
        ]
        unique_together = ['video', 'kind']  # One asset per type per video
    
    def __str__(self):
        return f"{self.video.video_id} - {self.get_kind_display()}"


# Signal to automatically update search vector
@receiver(post_save, sender=TranscriptSegment)
def update_search_vector(sender, instance, **kwargs):
    """Update the search vector when a transcript segment is saved."""
    if instance.text:
        instance.search_vector = SearchVector('text', config='english')
        # Update without triggering the signal again
        TranscriptSegment.objects.filter(pk=instance.pk).update(
            search_vector=SearchVector('text', config='english')
        )
