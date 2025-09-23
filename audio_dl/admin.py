from django.contrib import admin
from .models import DownloadJob, JobMetadata


@admin.register(DownloadJob)
class DownloadJobAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'user', 'download_type', 'status', 'filename', 'created_at', 'download_source']
    list_filter = ['status', 'download_type', 'download_source', 'created_at']
    search_fields = ['job_id', 'user__email', 'url', 'filename']
    readonly_fields = ['job_id', 'created_at', 'started_at', 'completed_at', 'duration_seconds']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(JobMetadata)
class JobMetadataAdmin(admin.ModelAdmin):
    list_display = ['job', 'title', 'uploader', 'duration', 'ext', 'is_deleted']
    list_filter = ['ext', 'is_deleted', 'job__download_type']
    search_fields = ['title', 'uploader', 'job__job_id', 'job__user__email']
    readonly_fields = ['job', 'raw_metadata']
