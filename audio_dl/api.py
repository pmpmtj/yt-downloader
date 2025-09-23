# audio_dl/api.py
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse
from core.downloaders.audio.download_audio import download_audio
from core.shared_utils.url_utils import YouTubeURLSanitizer, YouTubeURLError
from core.downloaders.shared_downloader import get_file_info
from core.shared_utils.app_config import APP_CONFIG
from cookie_management.cookie_manager import get_user_cookies

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_audio_api(request):
    url = (request.data.get("url") or "").strip()
    if not url:
        return Response({"detail": "Missing 'url'"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate YouTube URL before processing
    try:
        if not YouTubeURLSanitizer.is_youtube_url(url):
            return Response({"detail": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"URL validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # Get user-specific download directory for audio
    user_download_dir = request.user.get_download_directory('audio')
    
    # Check if user wants to download to remote (from request data)
    download_to_remote = request.data.get('download_to_remote', True)
    
    # Get user tracking information
    user_ip = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Get user cookies for authentication
    user_cookies = get_user_cookies(request.user)
    
    # Use the core download function with user-specific directory
    result = download_audio(
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

# ---------------------- NEW: Async endpoints (django-background-tasks) ----------------------
from django.urls import reverse
from background_task.models import Task
from django.shortcuts import get_object_or_404
import uuid


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_audio_api_async(request):
    """Queue an audio download job and return a task id (HTTP 202)."""
    url = (request.data.get("url") or "").strip()
    if not url:
        return Response({"detail": "Missing 'url'"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate YouTube URL before queuing
    try:
        if not YouTubeURLSanitizer.is_youtube_url(url):
            return Response({"detail": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"URL validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # Get user-specific download directory for audio
    user_download_dir = request.user.get_download_directory('audio')
    
    # Create a unique task ID
    task_id = str(uuid.uuid4())
    
    # Get user tracking information
    user_ip = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Queue the background task with user-specific directory
    from audio_dl.tasks import process_youtube_audio
    process_youtube_audio(
        url, 
        task_id=task_id, 
        output_dir=str(user_download_dir),
        user_id=request.user.id,
        user_ip=user_ip,
        user_agent=user_agent,
        repeat=0
    )

    status_url = request.build_absolute_uri(reverse("job_status", args=[task_id]))
    result_url = request.build_absolute_uri(reverse("job_result", args=[task_id]))

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
        # Import our custom models
        from audio_dl.models import DownloadJob
        
        # Look for job in our database
        job = DownloadJob.objects.filter(job_id=job_id, user=request.user).first()
        
        if not job:
            return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Return job status and details
        return Response({
            "task_id": job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "filename": job.filename,
            "file_size": job.file_size,
            "error_message": job.error_message,
            "download_source": job.download_source,
            "duration_seconds": job.duration_seconds,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"detail": f"Error checking job status: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def job_result(request, job_id: str):
    """If task finished successfully, stream the generated file."""
    try:
        # Import our custom models
        from audio_dl.models import DownloadJob
        
        # Look for job in our database
        job = DownloadJob.objects.filter(job_id=job_id, user=request.user).first()
        
        if not job:
            return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if job is completed
        if job.status != 'completed':
            return Response({"detail": f"Job not completed (status: {job.status})"}, status=status.HTTP_202_ACCEPTED)
        
        # Check if file exists
        if not job.filepath or not os.path.exists(job.filepath):
            return Response({"detail": "File not found on disk"}, status=status.HTTP_410_GONE)
        
        # Check if we should download to remote location (client)
        download_to_remote = APP_CONFIG.get("download", {}).get("download_to_remote_location", "True").lower() == "true"
        
        if download_to_remote:
            # Return the file (current behavior - download dialog)
            try:
                fileobj = open(job.filepath, "rb")
                return FileResponse(fileobj, as_attachment=True, filename=job.filename)
            except OSError:
                return Response({"detail": "File not found on disk"}, status=status.HTTP_410_GONE)
        else:
            # Return file info as JSON (server-only storage)
            file_info = get_file_info(job.filepath)
            return Response({
                'success': True,
                'message': 'File available for download',
                'file_info': file_info,
                'filepath': job.filepath,
                'job_id': job.job_id,
                'metadata': job.metadata.raw_metadata if hasattr(job, 'metadata') and job.metadata else None,
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        return Response({"detail": f"Error retrieving result: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)