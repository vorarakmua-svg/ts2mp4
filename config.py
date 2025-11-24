import os
from pathlib import Path

class Config:
    # Paths
    INPUT_DIR = Path(r"C:\input")
    OUTPUT_DIR = Path(r"C:\output")
    LOG_DIR = Path("logs")
    
    # Extensions
    INPUT_EXT = ".ts"
    OUTPUT_EXT = ".mp4"
    
    # FFmpeg Settings
    FFMPEG_BIN = "ffmpeg"
    FFPROBE_BIN = "ffprobe"
    
    # Encoding Settings
    # CRF: Lower is better quality. 23 is default, 18-28 is sane range.
    # For NVENC, -cq is used for VBR quality control.
    CRF_VALUE = 21 
    PRESET = "p4" # NVENC preset: p1 (fastest) to p7 (slowest/best quality)
    
    # Resource Management
    MAX_CONCURRENT_CONVERSIONS = 1 # Sequential to save resources as requested
    SLEEP_BETWEEN_FILES = 2 # Seconds to sleep between files to let system cool down
    
    @classmethod
    def ensure_dirs(cls):
        cls.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
