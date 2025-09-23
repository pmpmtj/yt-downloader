# transcriptions_dl/api.py
import os
import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse
from core.shared_utils.url_utils import YouTubeURLSanitizer, YouTubeURLError
from core.shared_utils.app_config import APP_CONFIG
from core.shared_utils.security_utils import get_client_ip, log_request_info
from cookie_management.cookie_manager import get_user_cookies

# Import the transcript downloader
from core.downloaders.transcriptions.dl_transcription import (
    download_transcript_files, 
    preview_transcript,
    get_video_info
)

# Import search utilities
from transcriptions_dl.search_utils import TranscriptSearchEngine, get_user_search_stats


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_transcript_api(request):
    """Synchronous transcript download API endpoint."""
    url = (request.data.get("url") or "").strip()
    if not url:
        return Response({"detail": "Missing 'url'"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate YouTube URL before processing
    try:
        if not YouTubeURLSanitizer.is_youtube_url(url):
            return Response({"detail": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"URL validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # Get user-specific download directory for transcripts
    user_download_dir = request.user.get_download_directory('transcripts')
    
    # Check if user wants to download to remote (from request data)
    download_to_remote = request.data.get('download_to_remote', False)
    
    # Get user tracking information
    user_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Log request
    log_request_info(request, "transcript_download")
    
    # Get user cookies for authentication
    user_cookies = get_user_cookies(request.user)
    
    try:
        # Use the core transcript download function
        success, transcript_data = download_transcript_files(url, output_dir=str(user_download_dir))
        
        if not success:
            return Response({"detail": "Failed to download transcript"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Save to database (mandatory)
        try:
            from .db_utils import save_transcript_to_db
            
            video = save_transcript_to_db(
                user=request.user,
                video_id=transcript_data.get('video_id'),
                video_info=transcript_data.get('video_info', {}),
                structured_data=transcript_data.get('structured_data'),
                segments=transcript_data.get('segments', []),
                chapters=transcript_data.get('chapters', []),
                clean_text=transcript_data.get('clean_text'),
                timestamped_text=transcript_data.get('timestamped_text'),
                source='youtube',
                is_generated=transcript_data.get('is_generated')
            )
            
        except Exception as e:
            # Log error but continue with API response
            print(f"⚠️ Warning: Failed to save transcript to database: {e}")
        
        # Get video info for response
        video_info = get_video_info(url)
        video_id = video_info.get('id', 'unknown') if video_info else 'unknown'
        
        # Find the generated files
        transcript_files = _find_transcript_files(user_download_dir, video_id)
        
        if download_to_remote and transcript_files:
            # Return the first file (clean format) for download
            file_path = transcript_files.get('clean')
            if file_path and os.path.exists(file_path):
                filename = os.path.basename(file_path)
                fileobj = open(file_path, "rb")
                return FileResponse(fileobj, as_attachment=True, filename=filename)
        
        # Return file info as JSON (server-only storage)
        return Response({
            'success': True,
            'message': 'Transcript files downloaded successfully to server',
            'video_info': {
                'title': video_info.get('title', 'Unknown') if video_info else 'Unknown',
                'uploader': video_info.get('uploader', 'Unknown') if video_info else 'Unknown',
                'duration': video_info.get('duration', 0) if video_info else 0,
                'video_id': video_id
            },
            'file_paths': transcript_files,
            'download_source': 'api'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        error_text = str(e)
        if "Sign in to confirm you're not a bot" in error_text or "not a bot" in error_text:
            return Response({
                "detail": "YouTube requires authentication for this request. Please upload your YouTube cookies using the Cookie Management page."
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": f"Error: {error_text}"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def download_transcript_api_async(request):
    """Queue a transcript download job and return a task id (HTTP 202)."""
    url = (request.data.get("url") or "").strip()
    if not url:
        return Response({"detail": "Missing 'url'"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate YouTube URL before queuing
    try:
        if not YouTubeURLSanitizer.is_youtube_url(url):
            return Response({"detail": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"URL validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # Get user-specific download directory for transcripts
    user_download_dir = request.user.get_download_directory('transcripts')
    
    # Create a unique task ID
    task_id = str(uuid.uuid4())
    
    # Get user tracking information
    user_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Queue the background task
    from transcriptions_dl.tasks import process_transcript_download
    process_transcript_download(
        url, 
        task_id=task_id, 
        output_dir=str(user_download_dir),
        user_id=request.user.id,
        user_ip=user_ip,
        user_agent=user_agent,
        repeat=0
    )

    # Build URLs for status and result endpoints
    from django.urls import reverse
    status_url = request.build_absolute_uri(reverse("transcript_job_status", args=[task_id]))
    result_url = request.build_absolute_uri(reverse("transcript_job_result", args=[task_id]))

    return Response({
        "task_id": task_id,
        "status": "queued",
        "status_url": status_url,
        "result_url": result_url,
    }, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transcript_job_status(request, job_id: str):
    """Return current task status (placeholder - no DB integration yet)."""
    # TODO: Implement with database integration
    return Response({
        "detail": "Status checking not implemented yet - requires database integration"
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transcript_job_result(request, job_id: str):
    """Return job result (placeholder - no DB integration yet)."""
    # TODO: Implement with database integration
    return Response({
        "detail": "Result retrieval not implemented yet - requires database integration"
    }, status=status.HTTP_501_NOT_IMPLEMENTED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transcript_preview_api(request):
    """Preview transcript before downloading."""
    url = request.GET.get("url", "").strip()
    if not url:
        return Response({"detail": "Missing 'url' parameter"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate YouTube URL
    try:
        if not YouTubeURLSanitizer.is_youtube_url(url):
            return Response({"detail": "Invalid YouTube URL"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"detail": f"URL validation error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Get video info first
        video_info = get_video_info(url)
        if not video_info:
            return Response({"detail": "Could not extract video information"}, status=status.HTTP_400_BAD_REQUEST)
        
        video_id = video_info.get('id')
        if not video_id:
            return Response({"detail": "Could not extract video ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get transcript preview
        preview_data = preview_transcript(video_id)
        
        if not preview_data:
            return Response({"detail": "No transcript available for this video"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'video_info': {
                'title': video_info.get('title', 'Unknown'),
                'uploader': video_info.get('uploader', 'Unknown'),
                'duration': video_info.get('duration', 0),
                'video_id': video_id
            },
            'transcript_preview': preview_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        error_text = str(e)
        if "Sign in to confirm you're not a bot" in error_text or "not a bot" in error_text:
            return Response({
                "detail": "YouTube requires authentication for this request. Please upload your YouTube cookies using the Cookie Management page."
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": f"Error: {error_text}"}, status=status.HTTP_400_BAD_REQUEST)


def _find_transcript_files(download_dir, video_id):
    """Find generated transcript files in the download directory."""
    import glob
    from pathlib import Path
    
    if not os.path.exists(download_dir):
        return {}
    
    # Look for files with the video_id pattern
    pattern = os.path.join(download_dir, f"{video_id}_*")
    files = glob.glob(pattern)
    
    transcript_files = {}
    
    for file_path in files:
        filename = os.path.basename(file_path)
        if filename.endswith('_clean.txt'):
            transcript_files['clean'] = file_path
        elif filename.endswith('_timestamped.txt'):
            transcript_files['timestamped'] = file_path
        elif filename.endswith('_structured.json'):
            transcript_files['structured'] = file_path
    
    return transcript_files


# ==================== SEARCH API ENDPOINTS ====================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_transcripts_api(request):
    """Search transcripts with advanced filtering and pagination."""
    # Get search parameters
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'full_text')  # full_text, exact, fuzzy
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)  # Max 100 per page
    
    # Video filters
    video_filters = {}
    if request.GET.get('title'):
        video_filters['title'] = request.GET.get('title')
    if request.GET.get('uploader'):
        video_filters['uploader'] = request.GET.get('uploader')
    if request.GET.get('date_from'):
        video_filters['date_from'] = request.GET.get('date_from')
    if request.GET.get('date_to'):
        video_filters['date_to'] = request.GET.get('date_to')
    if request.GET.get('duration_min'):
        video_filters['duration_min'] = int(request.GET.get('duration_min'))
    if request.GET.get('duration_max'):
        video_filters['duration_max'] = int(request.GET.get('duration_max'))
    
    # Time range filter (for segment search)
    time_range = None
    if request.GET.get('time_start') and request.GET.get('time_end'):
        time_range = (
            float(request.GET.get('time_start')),
            float(request.GET.get('time_end'))
        )
    
    # Other filters
    language = request.GET.get('language')
    is_generated = request.GET.get('is_generated')
    if is_generated is not None:
        is_generated = is_generated.lower() == 'true'
    
    sort_by = request.GET.get('sort', 'relevance')  # relevance, date, duration, title
    
    # Perform search
    search_engine = TranscriptSearchEngine(user=request.user)
    
    try:
        results = search_engine.search_transcripts(
            query=query,
            search_type=search_type,
            video_filters=video_filters,
            time_range=time_range,
            language=language,
            is_generated=is_generated,
            sort_by=sort_by,
            page=page,
            page_size=page_size
        )
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "detail": f"Search error: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_chapters_api(request):
    """Search within video chapters."""
    query = request.GET.get('q', '').strip()
    video_id = request.GET.get('video_id')
    page = int(request.GET.get('page', 1))
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    
    search_engine = TranscriptSearchEngine(user=request.user)
    
    try:
        results = search_engine.search_chapters(
            query=query,
            video_id=video_id,
            page=page,
            page_size=page_size
        )
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "detail": f"Chapter search error: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_transcript_content_api(request, video_id):
    """Get full transcript content for a specific video."""
    format_type = request.GET.get('format', 'clean_text')
    
    if format_type not in ['clean_text', 'timestamped', 'structured_json']:
        return Response({
            "detail": "Invalid format. Must be one of: clean_text, timestamped, structured_json"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    search_engine = TranscriptSearchEngine(user=request.user)
    
    try:
        transcript = search_engine.get_video_transcript(video_id, format_type)
        
        if not transcript:
            return Response({
                "detail": "Transcript not found or not accessible"
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(transcript, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "detail": f"Error retrieving transcript: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_suggestions_api(request):
    """Get search suggestions based on partial query."""
    query = request.GET.get('q', '').strip()
    limit = min(int(request.GET.get('limit', 10)), 50)  # Max 50 suggestions
    
    if len(query) < 2:
        return Response({"suggestions": []}, status=status.HTTP_200_OK)
    
    search_engine = TranscriptSearchEngine(user=request.user)
    
    try:
        suggestions = search_engine.get_search_suggestions(query, limit)
        return Response({"suggestions": suggestions}, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "detail": f"Error getting suggestions: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_stats_api(request):
    """Get search statistics for the current user."""
    try:
        stats = get_user_search_stats(request.user)
        return Response(stats, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            "detail": f"Error getting stats: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
