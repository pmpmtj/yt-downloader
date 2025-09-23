"""
Application configuration module.

"""

import logging


# Initialize logger for this module
logger = logging.getLogger("app_config")

# Application configuration for Youtube downloader
APP_CONFIG = {
    "audio": {
        "save_to_mp3": "True",
        "remove_original": "False"
    },
    "download": {
        "download_to_remote_location": "false"
    },
    "public_access": {
        "enable_cookie_auth": True,
        "rotate_user_agents": True,
        "rate_limit_per_ip": 10,  # downloads per hour per IP
        "max_concurrent_downloads": 3,
        "use_mobile_fallback": True  # Use mobile user agent as primary anti-bot method
    },
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ]
}

