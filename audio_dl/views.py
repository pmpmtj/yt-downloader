# youtube_downloader/audio_dl/views.py
from django.http import HttpResponseBadRequest, FileResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.downloaders.audio.download_audio import download_audio
from core.downloaders.shared_downloader import get_file_info
from core.shared_utils.app_config import APP_CONFIG
from core.shared_utils.security_utils import get_client_ip, log_request_info
from core.shared_utils.rate_limiting import get_download_stats, is_ip_allowed
from cookie_management.cookie_manager import get_user_cookies

@login_required
def index(request):
    if request.method == "POST":
        url = (request.POST.get("url") or "").strip()
        if not url:
            return HttpResponseBadRequest("Missing URL.")

        # Get user-specific download directory for audio
        user_download_dir = request.user.get_download_directory('audio')
        
        # Check if user wants to download to remote (checkbox state)
        download_to_remote = request.POST.get('download_to_remote') == 'on'
        
        # Call the core download function with user-specific directory
        try:
            # Log request and get user tracking information
            log_request_info(request, "audio_download")
            user_ip = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Get user cookies for authentication
            user_cookies = get_user_cookies(request.user)
            
            result = download_audio(
                url, 
                output_dir=str(user_download_dir),
                user=request.user,
                user_ip=user_ip,
                user_agent=user_agent,
                download_source='website',
                user_cookies=user_cookies
            )
            
            if not result['success']:
                return HttpResponseBadRequest(f"Error: {result['error']}")
            
            if download_to_remote:
                # Return the file (current behavior - download dialog)
                fileobj = open(result['filepath'], "rb")
                return FileResponse(fileobj, as_attachment=True, filename=result['filename'])
            else:
                # Server-only storage - show success message and redirect
                messages.success(request, f'Audio downloaded successfully to server: {result["filename"]}')
                return redirect('audio_dl:index')
            
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
    
    return render(request, "audio_dl/download_form.html", context)


def public_landing(request):
    """Public landing page that redirects to login or dashboard."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, "public_landing.html")
