import logging
import sys
from datetime import datetime
from pathlib import Path
from colorama import init as colorama_init, Fore, Style
from config import Config


class _ColorFormatter(logging.Formatter):
    """Adds ANSI color codes to log levels for console output."""

    COLOR_MAP = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record):
        message = super().format(record)
        color = self.COLOR_MAP.get(record.levelno, "")
        if not color:
            return message
        return f"{color}{message}{Style.RESET_ALL}"


def setup_logging():
    """Configures the logging system without duplicating handlers."""
    colorama_init(autoreset=True)
    Config.ensure_dirs()
    logger = logging.getLogger("TS2MP4")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    log_filename = Config.LOG_DIR / f"conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    base_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setFormatter(base_formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(_ColorFormatter("%(asctime)s [%(levelname)s] %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def get_input_files():
    """Scans the input directory for configured input files."""
    Config.ensure_dirs()
    return list(Config.INPUT_DIR.glob(f"*{Config.INPUT_EXT}"))

def format_size(size_bytes):
    """Formats bytes into human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
