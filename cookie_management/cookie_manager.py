"""
Secure cookie management for YouTube downloads.

This module provides encrypted per-user cookie storage and retrieval
for YouTube authentication to bypass bot detection.
"""

import os
import json
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User

logger = logging.getLogger("cookie_manager")

class CookieManager:
    """Manages secure storage and retrieval of user cookies."""
    
    def __init__(self):
        self.cookie_storage_dir = Path(settings.BASE_DIR) / "secure_cookies"
        self.cookie_storage_dir.mkdir(exist_ok=True, mode=0o700)  # Secure directory
        self._encryption_key = self._get_or_create_encryption_key()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for cookie storage."""
        key_file = self.cookie_storage_dir / "encryption.key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            key_file.chmod(0o600)  # Secure file permissions
            logger.info("Generated new encryption key for cookie storage")
            return key
    
    def _encrypt_cookies(self, cookies_data: str) -> str:
        """Encrypt cookie data."""
        fernet = Fernet(self._encryption_key)
        encrypted_data = fernet.encrypt(cookies_data.encode())
        return base64.b64encode(encrypted_data).decode()
    
    def _decrypt_cookies(self, encrypted_data: str) -> str:
        """Decrypt cookie data."""
        fernet = Fernet(self._encryption_key)
        decoded_data = base64.b64decode(encrypted_data.encode())
        decrypted_data = fernet.decrypt(decoded_data)
        return decrypted_data.decode()
    
    def store_user_cookies(self, user: User, cookies_content: str, source: str = "upload") -> Dict[str, Any]:
        """
        Store encrypted cookies for a user.
        
        Args:
            user: Django User instance
            cookies_content: Raw cookies.txt content (Netscape format)
            source: Source of cookies ('upload', 'browser', 'manual')
        
        Returns:
            Dict with storage result and metadata
        """
        try:
            # Validate cookie format
            validation_result = self.validate_cookie_format(cookies_content)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Invalid cookie format: {validation_result['error']}"
                }
            
            # Prepare cookie metadata
            cookie_data = {
                "content": cookies_content,
                "source": source,
                "uploaded_at": datetime.now().isoformat(),
                "expires_at": self._calculate_expiry().isoformat(),
                "user_id": user.id,
                "username": user.username
            }
            
            # Encrypt the entire cookie data
            encrypted_data = self._encrypt_cookies(json.dumps(cookie_data))
            
            # Store in user-specific file
            user_cookie_file = self.cookie_storage_dir / f"user_{user.id}_cookies.enc"
            with open(user_cookie_file, 'w') as f:
                f.write(encrypted_data)
            user_cookie_file.chmod(0o600)  # Secure file permissions
            
            # Cache for quick access
            cache_key = f"user_cookies:{user.id}"
            cache.set(cache_key, cookie_data, timeout=3600)  # 1 hour cache
            
            logger.info(f"Stored encrypted cookies for user {user.username} (ID: {user.id})")
            
            return {
                "success": True,
                "expires_at": cookie_data["expires_at"],
                "source": source,
                "validation": validation_result
            }
            
        except Exception as e:
            logger.error(f"Failed to store cookies for user {user.id}: {e}")
            return {
                "success": False,
                "error": f"Storage failed: {str(e)}"
            }
    
    def get_user_cookies(self, user: User) -> Optional[str]:
        """
        Retrieve and decrypt cookies for a user.
        
        Args:
            user: Django User instance
        
        Returns:
            Raw cookies content or None if not found/expired
        """
        try:
            # Check cache first
            cache_key = f"user_cookies:{user.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                # Check if expired
                expires_at = datetime.fromisoformat(cached_data["expires_at"])
                if datetime.now() < expires_at:
                    logger.debug(f"Retrieved cookies from cache for user {user.id}")
                    return cached_data["content"]
                else:
                    # Expired, remove from cache
                    cache.delete(cache_key)
                    logger.info(f"Cookies expired for user {user.id}")
            
            # Load from file
            user_cookie_file = self.cookie_storage_dir / f"user_{user.id}_cookies.enc"
            if not user_cookie_file.exists():
                logger.debug(f"No cookie file found for user {user.id}")
                return None
            
            with open(user_cookie_file, 'r') as f:
                encrypted_data = f.read()
            
            # Decrypt and parse
            decrypted_data = self._decrypt_cookies(encrypted_data)
            cookie_data = json.loads(decrypted_data)
            
            # Check expiry
            expires_at = datetime.fromisoformat(cookie_data["expires_at"])
            if datetime.now() >= expires_at:
                logger.info(f"Cookies expired for user {user.id}, removing file")
                user_cookie_file.unlink()
                return None
            
            # Cache for future use
            cache.set(cache_key, cookie_data, timeout=3600)
            
            logger.debug(f"Retrieved cookies from file for user {user.id}")
            return cookie_data["content"]
            
        except Exception as e:
            logger.error(f"Failed to retrieve cookies for user {user.id}: {e}")
            return None
    
    def validate_cookie_format(self, cookies_content: str) -> Dict[str, Any]:
        """
        Validate Netscape cookie format.
        
        Args:
            cookies_content: Raw cookies.txt content
        
        Returns:
            Dict with validation result and details
        """
        try:
            lines = cookies_content.strip().split('\n')
            
            # Skip comments and empty lines
            cookie_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            
            if not cookie_lines:
                return {
                    "valid": False,
                    "error": "No cookie data found (only comments or empty lines)"
                }
            
            # Check for Netscape format
            valid_cookies = 0
            youtube_domains = set()
            
            for line in cookie_lines:
                parts = line.split('\t')
                if len(parts) >= 7:  # Netscape format has 7 tab-separated fields
                    domain = parts[0]
                    if 'youtube.com' in domain or 'google.com' in domain:
                        youtube_domains.add(domain)
                        valid_cookies += 1
            
            if valid_cookies == 0:
                return {
                    "valid": False,
                    "error": "No valid YouTube/Google cookies found"
                }
            
            return {
                "valid": True,
                "cookie_count": valid_cookies,
                "youtube_domains": list(youtube_domains),
                "format": "netscape"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation failed: {str(e)}"
            }
    
    def get_cookie_status(self, user: User) -> Dict[str, Any]:
        """
        Get cookie status and metadata for a user.
        
        Args:
            user: Django User instance
        
        Returns:
            Dict with cookie status information
        """
        try:
            # Check cache first
            cache_key = f"user_cookies:{user.id}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                expires_at = datetime.fromisoformat(cached_data["expires_at"])
                is_expired = datetime.now() >= expires_at
                
                return {
                    "has_cookies": not is_expired,
                    "expires_at": cached_data["expires_at"],
                    "source": cached_data["source"],
                    "uploaded_at": cached_data["uploaded_at"],
                    "expires_in_hours": max(0, (expires_at - datetime.now()).total_seconds() / 3600)
                }
            
            # Check file
            user_cookie_file = self.cookie_storage_dir / f"user_{user.id}_cookies.enc"
            if not user_cookie_file.exists():
                return {
                    "has_cookies": False,
                    "expires_at": None,
                    "source": None,
                    "uploaded_at": None,
                    "expires_in_hours": 0
                }
            
            # Load and check expiry
            with open(user_cookie_file, 'r') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._decrypt_cookies(encrypted_data)
            cookie_data = json.loads(decrypted_data)
            
            expires_at = datetime.fromisoformat(cookie_data["expires_at"])
            is_expired = datetime.now() >= expires_at
            
            if is_expired:
                # Clean up expired file
                user_cookie_file.unlink()
                return {
                    "has_cookies": False,
                    "expires_at": cookie_data["expires_at"],
                    "source": cookie_data["source"],
                    "uploaded_at": cookie_data["uploaded_at"],
                    "expires_in_hours": 0
                }
            
            return {
                "has_cookies": True,
                "expires_at": cookie_data["expires_at"],
                "source": cookie_data["source"],
                "uploaded_at": cookie_data["uploaded_at"],
                "expires_in_hours": (expires_at - datetime.now()).total_seconds() / 3600
            }
            
        except Exception as e:
            logger.error(f"Failed to get cookie status for user {user.id}: {e}")
            return {
                "has_cookies": False,
                "expires_at": None,
                "source": None,
                "uploaded_at": None,
                "expires_in_hours": 0,
                "error": str(e)
            }
    
    def delete_user_cookies(self, user: User) -> bool:
        """
        Delete stored cookies for a user.
        
        Args:
            user: Django User instance
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from cache
            cache_key = f"user_cookies:{user.id}"
            cache.delete(cache_key)
            
            # Remove file
            user_cookie_file = self.cookie_storage_dir / f"user_{user.id}_cookies.enc"
            if user_cookie_file.exists():
                user_cookie_file.unlink()
            
            logger.info(f"Deleted cookies for user {user.username} (ID: {user.id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete cookies for user {user.id}: {e}")
            return False
    
    def _calculate_expiry(self) -> datetime:
        """Calculate cookie expiry time (7 days from now)."""
        return datetime.now() + timedelta(days=7)
    
    def cleanup_expired_cookies(self) -> int:
        """
        Clean up expired cookie files.
        
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        try:
            for cookie_file in self.cookie_storage_dir.glob("user_*_cookies.enc"):
                try:
                    with open(cookie_file, 'r') as f:
                        encrypted_data = f.read()
                    
                    decrypted_data = self._decrypt_cookies(encrypted_data)
                    cookie_data = json.loads(decrypted_data)
                    
                    expires_at = datetime.fromisoformat(cookie_data["expires_at"])
                    if datetime.now() >= expires_at:
                        cookie_file.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up expired cookie file: {cookie_file}")
                        
                except Exception as e:
                    logger.warning(f"Failed to process cookie file {cookie_file}: {e}")
                    # If we can't decrypt, assume it's corrupted and delete
                    cookie_file.unlink()
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired cookie files")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired cookies: {e}")
        
        return cleaned_count


# Global instance
cookie_manager = CookieManager()


def get_user_cookies(user: User) -> Optional[str]:
    """Convenience function to get user cookies."""
    return cookie_manager.get_user_cookies(user)


def store_user_cookies(user: User, cookies_content: str, source: str = "upload") -> Dict[str, Any]:
    """Convenience function to store user cookies."""
    return cookie_manager.store_user_cookies(user, cookies_content, source)


def get_cookie_status(user: User) -> Dict[str, Any]:
    """Convenience function to get cookie status."""
    return cookie_manager.get_cookie_status(user)
