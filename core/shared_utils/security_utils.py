"""
Security utilities for handling multi-user access and IP detection.
"""
import logging
from pathlib import Path

# Initialize logging
SCRIPT_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


def get_client_ip(request):
    """
    Get the real client IP address from request.
    Handles X-Forwarded-For header for proxy/load balancer scenarios.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: Client IP address
    """
    # Check for X-Forwarded-For header (set by proxies/load balancers)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the chain (original client)
        ip = x_forwarded_for.split(',')[0].strip()
        logger.debug(f"Client IP from X-Forwarded-For: {ip}")
        return ip
    
    # Check for X-Real-IP header (set by some proxies)
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        logger.debug(f"Client IP from X-Real-IP: {x_real_ip}")
        return x_real_ip
    
    # Fall back to REMOTE_ADDR
    ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    logger.debug(f"Client IP from REMOTE_ADDR: {ip}")
    return ip


def log_request_info(request, action="request"):
    """
    Log request information for debugging and security monitoring.
    
    Args:
        request: Django HttpRequest object
        action: Description of the action being performed
    """
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    logger.info(f"[{action}] IP: {client_ip} | User: {getattr(request.user, 'email', 'Anonymous')} | UA: {user_agent[:100]}")
    
    # Log potential security concerns
    if 'bot' in user_agent.lower() or 'crawler' in user_agent.lower():
        logger.warning(f"[SECURITY] Bot detected - IP: {client_ip} | UA: {user_agent}")


class SecurityMiddleware:
    """
    Custom middleware for enhanced security and logging.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request for security monitoring
        log_request_info(request, "incoming_request")
        
        # Add real IP to request for easy access
        request.real_ip = get_client_ip(request)
        
        response = self.get_response(request)
        return response
