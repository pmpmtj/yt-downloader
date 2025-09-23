import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any

ENCODING = "utf-8"
DEFAULT_CONFIG_FILE = "logger_config.json"

if getattr(sys, 'frozen', False):
    MODULE_DIR = Path(sys._MEIPASS)
else:
    MODULE_DIR = Path(__file__).parent.absolute()

def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    if config_path is None:
        possible_config_paths = [
            MODULE_DIR / "config" / DEFAULT_CONFIG_FILE,
        ]
        for path in possible_config_paths:
            if path.exists():
                config_path = path
                break
    try:
        with open(config_path, 'r', encoding=ENCODING) as f:
            return json.load(f)
    except Exception:
        return {
            "logging": {
                "file": {"level": "INFO"},
                "console": {"level": "INFO"}
            }
        }

def setup_logger(module_name: str, config_path: Optional[Path] = None, log_dir: Optional[Path] = None) -> logging.Logger:
    config = load_config(config_path)
    logging_config = config.get("logging", {})
    logs_dir = Path(__file__).parent.absolute() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    module_config = logging_config.get("modules", {}).get(
        module_name,
        logging_config.get("modules", {}).get("default", {})
    )

    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

    console_config = logging_config.get("console", {})
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, console_config.get("level", "INFO")))
    console_handler.setFormatter(logging.Formatter(
        console_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        console_config.get("date_format", "%H:%M:%S")
    ))
    logger.addHandler(console_handler)

    file_config = logging_config.get("file", {})
    log_file = logs_dir / module_config.get("log_filename", file_config.get("log_filename", "project.log"))

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=file_config.get("max_size_bytes", 1048576),
        backupCount=file_config.get("backup_count", 5),
        encoding=file_config.get("encoding", ENCODING)
    )
    file_handler.setLevel(getattr(logging, module_config.get("level", file_config.get("level", "INFO"))))
    file_handler.setFormatter(logging.Formatter(
        file_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s"),
        file_config.get("date_format", "%Y-%m-%d %H:%M:%S")
    ))
    logger.addHandler(file_handler)

    logger.info(f"Using log file: {log_file}")
    return logger
