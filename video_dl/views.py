# video_dl/views.py
import os
from django.http import HttpResponseBadRequest, FileResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.downloaders.video.download_video import download_video
from core.downloaders.shared_downloader import get_file_info
from core.shared_utils.app_config import APP_CONFIG
from core.shared_utils.security_utils import get_client_ip, log_request_info
from core.shared_utils.rate_limiting import get_download_stats, is_ip_allowed
from cookie_management.cookie_manager import get_user_cookies


@login_required
def index(request):
    """Video download form view."""
    if request.method == "POST":
        url = (request.POST.get("url") or "").strip()
        if not url:
            return HttpResponseBadRequest("Missing URL.")

        # Get user-specific download directory for video
        user_download_dir = request.user.get_download_directory('video')
        
        # Check if user wants to download to remote (checkbox state)
        download_to_remote = request.POST.get('download_to_remote') == 'on'
        
        # Call the core download function with user-specific directory
        try:
            # Log request and get user tracking information
            log_request_info(request, "video_download")
            user_ip = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Get user cookies for authentication
            user_cookies = get_user_cookies(request.user)
            
            result = download_video(
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
                messages.success(request, f'Video downloaded successfully to server: {result["filename"]}')
                return redirect('video_dl:video_index')
            
        except Exception as e:
            error_text = str(e)
            # Surface helpful guidance if YouTube bot check is triggered
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
    
    return render(request, "video_dl/download_form.html", context)


def public_landing(request):
    """Public landing page that redirects to login or dashboard."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    else:
        return redirect('accounts:login')


@login_required
def download_status(request, job_id):
    """Display download status for a specific job."""
    try:
        from video_dl.models import DownloadJob
        
        # Try to find the job by task_id first, then by job_id
        try:
            job = DownloadJob.objects.get(task_id=job_id)
        except DownloadJob.DoesNotExist:
            try:
                job = DownloadJob.objects.get(job_id=job_id)
            except DownloadJob.DoesNotExist:
                return HttpResponseBadRequest("Job not found")
        
        # Check if user has permission to view this job
        if job.user != request.user:
            return HttpResponseBadRequest("Permission denied")
        
        context = {
            'job': job,
            'job_id': job_id,
        }
        
        return render(request, "video_dl/download_status.html", context)
        
    except Exception as e:
        return HttpResponseBadRequest(f"Error: {e}")


@login_required
def download_result(request, job_id):
    """Download the result file for a completed job."""
    try:
        from video_dl.models import DownloadJob
        
        # Try to find the job by task_id first, then by job_id
        try:
            job = DownloadJob.objects.get(task_id=job_id)
        except DownloadJob.DoesNotExist:
            try:
                job = DownloadJob.objects.get(job_id=job_id)
            except DownloadJob.DoesNotExist:
                return HttpResponseBadRequest("Job not found")
        
        # Check if user has permission to view this job
        if job.user != request.user:
            return HttpResponseBadRequest("Permission denied")
        
        if job.status != "completed":
            return HttpResponseBadRequest(f"Job not completed. Current status: {job.status}")
        
        if not job.filepath or not os.path.exists(job.filepath):
            return HttpResponseBadRequest("File not found")
        
        # Return the file for download
        fileobj = open(job.filepath, "rb")
        return FileResponse(fileobj, as_attachment=True, filename=job.filename)
        
    except Exception as e:
        return HttpResponseBadRequest(f"Error: {e}")