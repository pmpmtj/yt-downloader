# video_dl/urls.py
from django.urls import path
from . import views
from . import api  # DRF-based API

app_name = 'video_dl'

urlpatterns = [
    path("", views.public_landing, name="video_public_landing"),
    path("download/", views.index, name="video_index"),
    path("status/<str:job_id>/", views.download_status, name="video_download_status"),
    path("result/<str:job_id>/", views.download_result, name="video_download_result"),
    # Existing synchronous download endpoint stays intact
    path("api/download-video/", api.download_video_api, name="download_video_api"),
    # New: asynchronous background download API (django-background-tasks)
    path("api/download-video-async/", api.download_video_api_async, name="download_video_api_async"),
    path("api/jobs/<str:job_id>/", api.job_status, name="video_job_status"),
    path("api/jobs/<str:job_id>/result/", api.job_result, name="video_job_result"),
]
