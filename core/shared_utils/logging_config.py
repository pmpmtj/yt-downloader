import logging
import logging.config
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Ensure logs directory exists
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },

    'handlers': {
        # Console handler with simple formatting
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'level': 'INFO',
        },
        
        # Main application log with detailed formatting
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'app.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 10,
            'formatter': 'standard',
            'mode': 'a',
            'encoding': 'utf-8',
        },
        
        # Error-only log
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'error.log'),
            'maxBytes': 5 * 1024 * 1024,  # 5MB
            'backupCount': 5,
            'formatter': 'standard',
            'mode': 'a',
            'level': 'ERROR',
            'encoding': 'utf-8',
        }
    },
    
    'loggers': {
        # Root logger
        'root': {
            'handlers': ['console', 'app_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        }
    },
}

def setup_logging(debug_mode: bool = False):
    """
    Setup logging configuration.
    
    Args:
        debug_mode: If True, enables debug logging and adds debug handler
    """
   
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # Log the startup message
    logger = logging.getLogger('app_config')
    logger.info(f"Logging initialized. Debug mode: {debug_mode}")
    logger.info(f"Log directory: {LOG_DIR}")


def get_logger(name: str, level: str = None) -> logging.Logger:
    """
    Get a configured logger for a specific module.
    
    Args:
        name: Logger name (usually module name)
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    return logger


# Convenience function to get the standard datetime timestamp
def get_log_timestamp() -> str:
    """Get standardized timestamp for logging."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]