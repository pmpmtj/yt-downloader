# video_dl/api.py
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse
from core.downloaders.video.download_video import download_video
from core.shared_utils.url_utils import YouTubeURLSanitizer, YouTubeURLError
from core.downloaders.shared_downloader import get_file_info
from core.shared_utils.app_config import APP_CONFIG
from cookie_management.cookie_manager import get_user_cookies

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_video_api(request):
    """Synchronous video download API endpoint."""
    url = (request.data.get("url") or "").strip()
    if not url:
        return Response({"detail": "Missing 'url'"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate YouTube URL before processing
    try:
        if not YouTubeURLSanitizer.is_youtube_url(url):
            return Response({"detail": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"URL validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # Get user-specific download directory for video
    user_download_dir = request.user.get_download_directory('video')
    
    # Check if user wants to download to remote (from request data)
    download_to_remote = request.data.get('download_to_remote', True)
    
    # Get user tracking information
    user_ip = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Get user cookies for authentication
    user_cookies = get_user_cookies(request.user)
    
    # Use the core download function with user-specific directory
    result = download_video(
        url, 
        output_dir=str(user_download_dir),
        user=request.user,
        user_ip=user_ip,
        user_agent=user_agent,
        download_source='api',
        user_cookies=user_cookies
    )
    
    if not result['success']:
        return Response({"detail": result['error']}, status=status.HTTP_400_BAD_REQUEST)
    
    if download_to_remote:
        # Return the file (current behavior - download dialog)
        fileobj = open(result['filepath'], "rb")
        return FileResponse(fileobj, as_attachment=True, filename=result['filename'])
    else:
        # Return file info as JSON (server-only storage)
        file_info = get_file_info(result['filepath'])
        return Response({
            'success': True,
            'message': 'File downloaded successfully to server',
            'file_info': file_info,
            'job_id': result.get('job_id'),
            'metadata': result.get('metadata', {})
        }, status=status.HTTP_200_OK)

# ---------------------- Async endpoints (django-background-tasks) ----------------------
from django.urls import reverse
from background_task.models import Task
from django.shortcuts import get_object_or_404
import uuid


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_video_api_async(request):
    """Queue a video download job and return a task id (HTTP 202)."""
    url = (request.data.get("url") or "").strip()
    if not url:
        return Response({"detail": "Missing 'url'"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate YouTube URL before queuing
    try:
        if not YouTubeURLSanitizer.is_youtube_url(url):
            return Response({"detail": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"URL validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # Get user-specific download directory for video
    user_download_dir = request.user.get_download_directory('video')
    
    # Create a unique task ID
    task_id = str(uuid.uuid4())
    
    # Get user tracking information
    user_ip = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Queue the background task with user-specific directory
    from video_dl.tasks import process_youtube_video
    process_youtube_video(
        url, 
        task_id=task_id, 
        output_dir=str(user_download_dir),
        user_id=request.user.id,
        user_ip=user_ip,
        user_agent=user_agent,
        repeat=0
    )

    status_url = request.build_absolute_uri(reverse("video_job_status", args=[task_id]))
    result_url = request.build_absolute_uri(reverse("video_job_result", args=[task_id]))

    return Response({
        "task_id": task_id,
        "status": "queued",
        "status_url": status_url,
        "result_url": result_url,
    }, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def job_status(request, job_id: str):
    """Return current task status from database."""
    try:
        from video_dl.models import DownloadJob
        
        # Try to find the job by task_id first, then by job_id
        try:
            job = DownloadJob.objects.get(task_id=job_id)
        except DownloadJob.DoesNotExist:
            try:
                job = DownloadJob.objects.get(job_id=job_id)
            except DownloadJob.DoesNotExist:
                return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has permission to view this job
        if job.user != request.user:
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            "task_id": str(job.task_id) if job.task_id else str(job.job_id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "filename": job.filename,
            "file_size": job.file_size,
            "error_message": job.error_message,
        })
        
    except Exception as e:
        return Response({"detail": f"Error checking job status: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def job_result(request, job_id: str):
    """Return job result - file download or file info."""
    try:
        from video_dl.models import DownloadJob
        
        # Try to find the job by task_id first, then by job_id
        try:
            job = DownloadJob.objects.get(task_id=job_id)
        except DownloadJob.DoesNotExist:
            try:
                job = DownloadJob.objects.get(job_id=job_id)
            except DownloadJob.DoesNotExist:
                return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has permission to view this job
        if job.user != request.user:
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        if job.status != "completed":
            return Response({"detail": f"Job not completed. Current status: {job.status}"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not job.filepath or not os.path.exists(job.filepath):
            return Response({"detail": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Return the file for download
        fileobj = open(job.filepath, "rb")
        return FileResponse(fileobj, as_attachment=True, filename=job.filename)
        
    except Exception as e:
        return Response({"detail": f"Error retrieving job result: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
