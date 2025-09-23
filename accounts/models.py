from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model that uses email as the primary identifier.
    """
    username = None  # Remove username field
    email = models.EmailField(unique=True, verbose_name="Email Address")
    download_uuid = models.UUIDField(unique=True, verbose_name="Download UUID")
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already required, no additional required fields
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.download_uuid:
            self.download_uuid = uuid.uuid4()
        super().save(*args, **kwargs)
    
    def get_download_directory(self, download_type='audio'):
        """Get the user-specific download directory path."""
        from django.conf import settings
        return settings.MEDIA_ROOT / 'downloads' / download_type / str(self.download_uuid)
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
