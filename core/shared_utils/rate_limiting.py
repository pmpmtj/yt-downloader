"""
Rate limiting utilities for multi-user public access.
"""
import time
import logging
from pathlib import Path
from typing import Dict, Optional
from django.core.cache import cache
from django.http import HttpResponse
from .app_config import APP_CONFIG
from .security_utils import get_client_ip

# Initialize logging
SCRIPT_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Rate limiting middleware for download requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = APP_CONFIG.get("public_access", {}).get("rate_limit_per_ip", 5)
        self.window_seconds = 3600  # 1 hour window
    
    def __call__(self, request):
        # Only apply rate limiting to download endpoints
        if self.should_rate_limit(request):
            if not self.check_rate_limit(request):
                logger.warning(f"Rate limit exceeded for IP: {get_client_ip(request)}")
                return HttpResponse(
                    "Rate limit exceeded. Please wait before trying again.",
                    status=429
                )
        
        response = self.get_response(request)
        return response
    
    def should_rate_limit(self, request) -> bool:
        """Check if this request should be rate limited."""
        rate_limited_paths = ['/download/', '/video/download/', '/api/download-']
        # Only rate limit POST requests (actual downloads), not GET requests (form displays)
        return (any(path in request.path for path in rate_limited_paths) and 
                request.method == 'POST')
    
    def check_rate_limit(self, request) -> bool:
        """
        Check if the request is within rate limits.
        
        Returns:
            bool: True if within limits, False if over limit
        """
        client_ip = get_client_ip(request)
        cache_key = f"rate_limit:{client_ip}"
        
        # Get current request count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= self.rate_limit:
            return False
        
        # Increment counter
        cache.set(cache_key, current_count + 1, self.window_seconds)
        return True


def get_download_stats(ip_address: str) -> Dict[str, int]:
    """
    Get download statistics for an IP address.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        Dict with download stats
    """
    cache_key = f"rate_limit:{ip_address}"
    current_count = cache.get(cache_key, 0)
    
    return {
        "downloads_used": current_count,
        "downloads_remaining": max(0, APP_CONFIG.get("public_access", {}).get("rate_limit_per_ip", 5) - current_count),
        "window_seconds": 3600
    }


def is_ip_allowed(ip_address: str) -> bool:
    """
    Check if an IP address is allowed to download.
    
    Args:
        ip_address: Client IP address
        
    Returns:
        bool: True if allowed, False if blocked
    """
    # Check for blocked IPs (could be extended with a blacklist)
    blocked_ips = cache.get("blocked_ips", set())
    if ip_address in blocked_ips:
        return False
    
    # Check rate limits
    cache_key = f"rate_limit:{ip_address}"
    current_count = cache.get(cache_key, 0)
    rate_limit = APP_CONFIG.get("public_access", {}).get("rate_limit_per_ip", 5)
    
    return current_count < rate_limit


def block_ip(ip_address: str, duration_seconds: int = 3600, reason: str = "Rate limit violation"):
    """
    Temporarily block an IP address.
    
    Args:
        ip_address: IP to block
        duration_seconds: How long to block for
        reason: Reason for blocking
    """
    blocked_ips = cache.get("blocked_ips", set())
    blocked_ips.add(ip_address)
    cache.set("blocked_ips", blocked_ips, duration_seconds)
    
    logger.warning(f"Blocked IP {ip_address} for {duration_seconds}s. Reason: {reason}")
