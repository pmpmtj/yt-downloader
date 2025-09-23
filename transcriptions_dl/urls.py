# transcriptions_dl/urls.py
from django.urls import path
from . import api
from . import views

app_name = 'transcriptions_dl'

urlpatterns = [
    # Web interface
    path("", views.public_landing, name="public_landing"),
    path("download/", views.download_form, name="download_form"),
    path("search/", views.search_transcripts, name="search_transcripts"),
    
    # API endpoints
    path('api/download/', api.download_transcript_api, name='download_transcript'),
    path('api/download-async/', api.download_transcript_api_async, name='download_transcript_async'),
    path('api/status/<str:job_id>/', api.transcript_job_status, name='transcript_job_status'),
    path('api/result/<str:job_id>/', api.transcript_job_result, name='transcript_job_result'),
    path('api/preview/', api.transcript_preview_api, name='transcript_preview'),
    
    # Search API endpoints
    path('api/search/', api.search_transcripts_api, name='search_transcripts_api'),
    path('api/search/chapters/', api.search_chapters_api, name='search_chapters_api'),
    path('api/transcript/<str:video_id>/', api.get_transcript_content_api, name='get_transcript_content_api'),
    path('api/search/suggestions/', api.search_suggestions_api, name='search_suggestions_api'),
    path('api/search/stats/', api.search_stats_api, name='search_stats_api'),
]
