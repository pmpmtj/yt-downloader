# transcriptions_dl/views.py
import os
from django.http import HttpResponseBadRequest, FileResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.downloaders.transcriptions.dl_transcription import download_transcript_files, get_video_info
from core.shared_utils.security_utils import get_client_ip, log_request_info
from core.shared_utils.rate_limiting import get_download_stats, is_ip_allowed
from cookie_management.cookie_manager import get_user_cookies
from django.conf import settings
from transcriptions_dl.search_utils import TranscriptSearchEngine, get_user_search_stats


@login_required
def download_form(request):
    """Transcript download form view."""
    if request.method == "POST":
        url = (request.POST.get("url") or "").strip()
        if not url:
            return HttpResponseBadRequest("Missing URL.")

        # Get selected formats
        selected_formats = request.POST.getlist('formats')
        if not selected_formats:
            messages.error(request, "Please select at least one transcript format.")
            return redirect('transcriptions_dl:download_form')

        # Get user-specific download directory for transcripts
        user_download_dir = request.user.get_download_directory('transcripts')
        
        # Call the core download function with user-specific directory
        try:
            # Log request and get user tracking information
            log_request_info(request, "transcript_download")
            user_ip = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Get user cookies for authentication
            user_cookies = get_user_cookies(request.user)
            
            # Download transcript files using the core function with selected formats
            success, transcript_data = download_transcript_files(url, output_dir=str(user_download_dir), formats=selected_formats)
            
            if not success:
                return HttpResponseBadRequest("Failed to download transcript files.")
            
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
                
                print(f"✅ Transcript saved to database: {video.video_id}")
                
            except Exception as e:
                print(f"⚠️ Warning: Failed to save transcript to database: {e}")
                # Continue with file-based success message even if DB save fails
            
            # Get video info for response
            video_info = get_video_info(url)
            video_id = video_info.get('id', 'unknown') if video_info else 'unknown'
            
            # Find the generated files
            transcript_files = _find_transcript_files(user_download_dir, video_id)
            
            # Server-only storage - show success message and redirect
            format_names = [_get_format_display_name(fmt) for fmt in selected_formats]
            messages.success(request, f'Transcripts downloaded successfully to server: {", ".join(format_names)}')
            return redirect('transcriptions_dl:download_form')
            
        except Exception as e:
            error_text = str(e)
            if "Sign in to confirm you're not a bot" in error_text or "not a bot" in error_text:
                messages.error(request, (
                    "YouTube requires authentication for this request. "
                    "Please upload your YouTube cookies using the Cookie Management page. "
                    "Go to Dashboard → Manage Cookies to upload your cookies.txt file."
                ))
            else:
                messages.error(request, f"Error: {error_text}")
            return HttpResponseBadRequest(f"Error: {e}")

    # Add rate limiting info to context
    client_ip = get_client_ip(request)
    download_stats = get_download_stats(client_ip)
    
    # Get cookie status
    from cookie_management.cookie_manager import get_cookie_status
    cookie_status = get_cookie_status(request.user)
    
    context = {
        'download_stats': download_stats,
        'ip_allowed': is_ip_allowed(client_ip),
        'cookie_status': cookie_status
    }
    
    return render(request, "transcriptions_dl/download_form.html", context)


def _find_transcript_files(download_dir, video_id):
    """Find generated transcript files in the download directory."""
    import glob
    
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




def _get_format_display_name(format_type):
    """Get display name for format type."""
    format_names = {
        'clean': 'Clean Text',
        'timestamped': 'Timestamped Text',
        'structured': 'Structured JSON'
    }
    return format_names.get(format_type, format_type)


@login_required
def search_transcripts(request):
    """Search transcripts web interface."""
    # Get search parameters
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'full_text')
    page = int(request.GET.get('page', 1))
    page_size = 20
    
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
    
    # Time range filter
    time_range = None
    if request.GET.get('time_start') and request.GET.get('time_end'):
        time_range = (
            float(request.GET.get('time_start')),
            float(request.GET.get('time_end'))
        )
    
    # Other filters
    language = request.GET.get('language')
    if language is not None and not language.strip():
        language = None  # Don't filter by language if empty
        
    is_generated = request.GET.get('is_generated')
    if is_generated is not None and is_generated.strip():
        is_generated = is_generated.lower() == 'true'
    else:
        is_generated = None  # Don't filter by is_generated if empty
    
    sort_by = request.GET.get('sort', 'relevance')
    
    # Perform search
    search_engine = TranscriptSearchEngine(user=request.user)
    search_results = None
    
    if query or any(video_filters.values()):
        try:
            search_results = search_engine.search_transcripts(
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
        except Exception as e:
            messages.error(request, f"Search error: {str(e)}")
            search_results = None
    else:
        # Show recent videos when no search is performed
        try:
            search_results = search_engine.search_transcripts(
                query="",
                search_type="full_text",
                sort_by="date",
                page=page,
                page_size=page_size
            )
        except Exception as e:
            messages.error(request, f"Error loading recent videos: {str(e)}")
            search_results = None
    
    # Get user stats for the sidebar
    try:
        user_stats = get_user_search_stats(request.user)
    except Exception as e:
        user_stats = {
            'total_videos': 0,
            'total_segments': 0,
            'total_chapters': 0,
            'languages': [],
            'date_range': {'earliest': None, 'latest': None},
            'total_duration_s': 0
        }
    
    # Get available languages for filter dropdown
    available_languages = user_stats.get('languages', [])
    
    context = {
        'query': query,
        'search_type': search_type,
        'search_results': search_results,
        'user_stats': user_stats,
        'available_languages': available_languages,
        'current_filters': {
            'title': video_filters.get('title', ''),
            'uploader': video_filters.get('uploader', ''),
            'date_from': video_filters.get('date_from', ''),
            'date_to': video_filters.get('date_to', ''),
            'duration_min': video_filters.get('duration_min', ''),
            'duration_max': video_filters.get('duration_max', ''),
            'time_start': request.GET.get('time_start', ''),
            'time_end': request.GET.get('time_end', ''),
            'language': language or '',
            'is_generated': is_generated,
            'sort': sort_by
        }
    }
    
    return render(request, "transcriptions_dl/search_form.html", context)


def public_landing(request):
    """Public landing page that redirects to login or dashboard."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, "public_landing.html")