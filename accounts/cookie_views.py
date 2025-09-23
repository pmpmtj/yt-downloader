"""
Cookie management views for secure cookie upload and management.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from cookie_management.cookie_manager import cookie_manager, get_cookie_status

logger = logging.getLogger("cookie_views")


@login_required
def cookie_management_view(request):
    """Main cookie management page."""
    cookie_status = get_cookie_status(request.user)
    
    context = {
        'cookie_status': cookie_status,
        'user': request.user
    }
    
    return render(request, 'accounts/cookie_management.html', context)


@login_required
@require_http_methods(["POST"])
def upload_cookies_view(request):
    """Handle cookie file upload."""
    try:
        if 'cookie_file' not in request.FILES:
            messages.error(request, "No cookie file provided")
            return redirect('accounts:cookie_management')
        
        cookie_file = request.FILES['cookie_file']
        
        # Validate file size (max 1MB)
        if cookie_file.size > 1024 * 1024:
            messages.error(request, "Cookie file too large (max 1MB)")
            return redirect('accounts:cookie_management')
        
        # Read file content
        cookie_content = cookie_file.read().decode('utf-8')
        
        # Store cookies
        result = cookie_manager.store_user_cookies(
            request.user, 
            cookie_content, 
            source="upload"
        )
        
        if result['success']:
            messages.success(
                request, 
                f"Cookies uploaded successfully! They will expire in 7 days. "
                f"Found {result['validation']['cookie_count']} YouTube/Google cookies."
            )
            logger.info(f"User {request.user.username} uploaded cookies successfully")
        else:
            messages.error(request, f"Failed to upload cookies: {result['error']}")
            logger.warning(f"User {request.user.username} failed to upload cookies: {result['error']}")
        
    except Exception as e:
        messages.error(request, f"Upload failed: {str(e)}")
        logger.error(f"Cookie upload error for user {request.user.username}: {e}")
    
    return redirect('accounts:cookie_management')


@login_required
@require_http_methods(["POST"])
def paste_cookies_view(request):
    """Handle pasted cookie content."""
    try:
        cookie_content = request.POST.get('cookie_content', '').strip()
        
        if not cookie_content:
            messages.error(request, "No cookie content provided")
            return redirect('accounts:cookie_management')
        
        # Store cookies
        result = cookie_manager.store_user_cookies(
            request.user, 
            cookie_content, 
            source="paste"
        )
        
        if result['success']:
            messages.success(
                request, 
                f"Cookies pasted successfully! They will expire in 7 days. "
                f"Found {result['validation']['cookie_count']} YouTube/Google cookies."
            )
            logger.info(f"User {request.user.username} pasted cookies successfully")
        else:
            messages.error(request, f"Failed to paste cookies: {result['error']}")
            logger.warning(f"User {request.user.username} failed to paste cookies: {result['error']}")
        
    except Exception as e:
        messages.error(request, f"Paste failed: {str(e)}")
        logger.error(f"Cookie paste error for user {request.user.username}: {e}")
    
    return redirect('accounts:cookie_management')


@login_required
@require_http_methods(["POST"])
def delete_cookies_view(request):
    """Delete user's stored cookies."""
    try:
        success = cookie_manager.delete_user_cookies(request.user)
        
        if success:
            messages.success(request, "Cookies deleted successfully")
            logger.info(f"User {request.user.username} deleted their cookies")
        else:
            messages.error(request, "Failed to delete cookies")
            logger.warning(f"User {request.user.username} failed to delete cookies")
        
    except Exception as e:
        messages.error(request, f"Delete failed: {str(e)}")
        logger.error(f"Cookie delete error for user {request.user.username}: {e}")
    
    return redirect('accounts:cookie_management')


@method_decorator(csrf_exempt, name='dispatch')
class CookieAPIView(View):
    """API endpoints for cookie management."""
    
    def get(self, request):
        """Get cookie status."""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            cookie_status = get_cookie_status(request.user)
            return JsonResponse(cookie_status)
        except Exception as e:
            logger.error(f"Cookie status API error for user {request.user.username}: {e}")
            return JsonResponse({'error': 'Failed to get cookie status'}, status=500)
    
    def post(self, request):
        """Upload or paste cookies."""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            data = request.json() if hasattr(request, 'json') else {}
            
            # Check for file upload
            if 'cookie_file' in request.FILES:
                cookie_file = request.FILES['cookie_file']
                cookie_content = cookie_file.read().decode('utf-8')
                source = "api_upload"
            elif 'cookie_content' in data:
                cookie_content = data['cookie_content']
                source = "api_paste"
            else:
                return JsonResponse({'error': 'No cookie data provided'}, status=400)
            
            # Store cookies
            result = cookie_manager.store_user_cookies(request.user, cookie_content, source)
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Cookie API error for user {request.user.username}: {e}")
            return JsonResponse({'error': 'Failed to store cookies'}, status=500)
    
    def delete(self, request):
        """Delete cookies."""
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        try:
            success = cookie_manager.delete_user_cookies(request.user)
            return JsonResponse({'success': success})
            
        except Exception as e:
            logger.error(f"Cookie delete API error for user {request.user.username}: {e}")
            return JsonResponse({'error': 'Failed to delete cookies'}, status=500)
