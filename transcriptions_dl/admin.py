# transcriptions_dl/admin.py
from django.contrib import admin
from .models import Video, Chapter, TranscriptSegment, RawAsset


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['video_id', 'title', 'user', 'duration_s', 'language_code', 'processed_at']
    list_filter = ['language_code', 'is_generated', 'processed_at']
    search_fields = ['video_id', 'title', 'uploader']
    readonly_fields = ['processed_at']
    raw_id_fields = ['user']


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['video', 'start_time_s', 'end_time_s', 'text']
    list_filter = ['video__user']
    search_fields = ['text', 'video__title']
    raw_id_fields = ['video']


@admin.register(TranscriptSegment)
class TranscriptSegmentAdmin(admin.ModelAdmin):
    list_display = ['video', 'start_time_s', 'duration_s', 'text_preview', 'is_generated']
    list_filter = ['is_generated', 'source', 'video__user']
    search_fields = ['text', 'video__title']
    raw_id_fields = ['video']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text Preview'


@admin.register(RawAsset)
class RawAssetAdmin(admin.ModelAdmin):
    list_display = ['video', 'kind', 'stored_at']
    list_filter = ['kind', 'stored_at', 'video__user']
    search_fields = ['video__title', 'video__video_id']
    raw_id_fields = ['video']