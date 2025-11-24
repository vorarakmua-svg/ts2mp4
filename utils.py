import logging
import sys
from pathlib import Path
from datetime import datetime
from config import Config

def setup_logging():
    """Configures the logging system."""
    Config.ensure_dirs()
    
    log_filename = Config.LOG_DIR / f"conversion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("TS2MP4")

def get_input_files():
    """Scans the input directory for .ts files."""
    if not Config.INPUT_DIR.exists():
        return []
    return list(Config.INPUT_DIR.glob(f"*{Config.INPUT_EXT}"))

def format_size(size_bytes):
    """Formats bytes into human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
