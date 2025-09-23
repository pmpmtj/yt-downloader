# Django YouTube Downloader - Project Structure Guide

## 📁 Complete Project Structure

```
youtube_downloader/
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
├── README.md
├── youtube_downloader/           # Django project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                        # Shared utilities and core functionality
│   ├── __init__.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging_utils.py     # Centralized logging configuration
│   │   └── file_utils.py        # File operations utilities
│   └── downloaders/             # Core download functionality
│       ├── __init__.py
│       ├── base_downloader.py   # Abstract base downloader
│       ├── audio_downloader.py  # Audio-specific download logic
│       ├── video_downloader.py  # Video-specific download logic
│       └── exceptions.py        # Custom exceptions
├── audio_dl/                    # Audio download Django app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py           # For API responses
│   ├── tasks.py                 # Celery tasks (optional)
│   └── tests/
│       ├── __init__.py
│       ├── test_views.py
│       └── test_models.py
├── video_dl/                    # Video download Django app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── serializers.py
│   ├── tasks.py
│   └── tests/
│       ├── __init__.py
│       ├── test_views.py
│       └── test_models.py
├── media/                       # User uploads and downloads
│   └── downloads/
│       ├── audio/
│       └── video/
├── static/                      # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── templates/                   # HTML templates
│   ├── base.html
│   ├── audio_dl/
│   │   ├── download_form.html
│   │   └── download_status.html
│   └── video_dl/
│       ├── download_form.html
│       └── download_status.html
└── logs/                        # Application logs
```

## 🏗️ Architecture Best Practices

### 1. **Separation of Concerns**
- **`core/`**: Contains reusable business logic independent of Django apps
- **`audio_dl/` & `video_dl/`**: Django apps focusing on web interface and database operations
- **`utils/`**: Shared utilities that can be used across the entire project

### 2. **Dependency Flow**
```
Django Apps (audio_dl, video_dl) 
    ↓ (imports from)
Core Modules (downloaders, utils)
    ↓ (uses)
External Libraries (yt-dlp, etc.)
```

## 📝 Key File Examples

### `core/utils/logging_utils.py`
```python
import logging
import os
from logging.handlers import RotatingFileHandler
from django.conf import settings

def setup_logger(name, log_file, level=logging.INFO):
    """Set up a logger with file and console handlers."""
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

### `core/utils/file_utils.py`
```python
import os
import shutil
from pathlib import Path
from django.conf import settings

def ensure_directory_exists(path):
    """Create directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_safe_filename(filename):
    """Remove unsafe characters from filename."""
    import re
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def cleanup_old_files(directory, days_old=7):
    """Remove files older than specified days."""
    import time
    cutoff = time.time() - (days_old * 24 * 60 * 60)
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.getctime(file_path) < cutoff:
                os.remove(file_path)
```

### `core/downloaders/base_downloader.py`
```python
from abc import ABC, abstractmethod
from core.utils.logging_utils import setup_logger

class BaseDownloader(ABC):
    def __init__(self):
        self.logger = setup_logger(
            self.__class__.__name__,
            f'logs/{self.__class__.__name__.lower()}.log'
        )
    
    @abstractmethod
    def download(self, url, output_path):
        """Download content from URL to output path."""
        pass
    
    @abstractmethod
    def get_info(self, url):
        """Get information about the content."""
        pass
    
    def validate_url(self, url):
        """Validate if URL is supported."""
        # Common validation logic
        return 'youtube.com' in url or 'youtu.be' in url
```

### `audio_dl/models.py`
```python
from django.db import models
from django.utils import timezone

class AudioDownload(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('downloading', 'Downloading'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    url = models.URLField()
    title = models.CharField(max_length=255, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"Audio: {self.title or self.url}"
```

## 🔧 Configuration Files

### `requirements.txt`
```txt
Django>=4.2.0
yt-dlp>=2023.7.6
celery>=5.3.0
redis>=4.5.0
python-dotenv>=1.0.0
```

### `settings.py` additions
```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'audio_dl',
    'video_dl',
]

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🚀 Benefits of This Structure

1. **Modularity**: Core functionality is separated from Django-specific code
2. **Reusability**: Utils and downloaders can be used across different apps
3. **Testability**: Each component can be tested independently
4. **Scalability**: Easy to add new download types or apps
5. **Maintainability**: Clear separation makes debugging and updates easier
6. **Django Best Practices**: Follows Django's app-based architecture

## 📋 Next Steps

1. Set up virtual environment and install dependencies
2. Create the folder structure
3. Implement the base classes and utilities
4. Build the Django apps using the core modules
5. Add tests for each component
6. Configure logging and error handling
7. Add API endpoints if needed
8. Set up background tasks with Celery (optional)

This structure provides a solid foundation that's both Django-compliant and follows software engineering best practices for maintainable, scalable applications.