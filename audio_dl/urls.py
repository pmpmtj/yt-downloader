# audio_dl/urls.py
from django.urls import path
from . import views
from . import api  # DRF-based API

app_name = 'audio_dl'

urlpatterns = [
    path("", views.public_landing, name="public_landing"),
    path("download/", views.index, name="index"),
    # Existing synchronous download endpoint stays intact
    path("api/download-audio/", api.download_audio_api, name="download_audio_api"),
    # New: asynchronous background download API (django-background-tasks)
    path("api/download-audio-async/", api.download_audio_api_async, name="download_audio_api_async"),
    path("api/jobs/<str:job_id>/", api.job_status, name="job_status"),
    path("api/jobs/<str:job_id>/result/", api.job_result, name="job_result"),
]