import os
from pathlib import Path
from typing import Optional


class Config:
    # Paths (override via environment variables)
    INPUT_DIR = Path(os.getenv("TS2MP4_INPUT_DIR", r"C:\input")).expanduser()
    OUTPUT_DIR = Path(os.getenv("TS2MP4_OUTPUT_DIR", r"C:\output")).expanduser()
    LOG_DIR = Path(os.getenv("TS2MP4_LOG_DIR", "logs")).expanduser()
    
    # Extensions
    INPUT_EXT = os.getenv("TS2MP4_INPUT_EXT", ".ts")
    OUTPUT_EXT = os.getenv("TS2MP4_OUTPUT_EXT", ".mp4")
    
    # FFmpeg Settings
    FFMPEG_BIN = os.getenv("TS2MP4_FFMPEG_BIN", "ffmpeg")
    FFPROBE_BIN = os.getenv("TS2MP4_FFPROBE_BIN", "ffprobe")
    
    # Encoding Settings
    CRF_VALUE = int(os.getenv("TS2MP4_CRF_VALUE", "21"))
    PRESET = os.getenv("TS2MP4_NVENC_PRESET", "p4") # p1 (fastest) to p7 (slowest/best quality)
    GPU_MAX_ATTEMPTS = int(os.getenv("TS2MP4_GPU_MAX_ATTEMPTS", "1"))
    ENABLE_GPU = os.getenv("TS2MP4_ENABLE_GPU", "1") not in ("0", "false", "False")
    FORCE_GPU = os.getenv("TS2MP4_FORCE_GPU", "0") in ("1", "true", "True")
    
    # Resource Management
    MAX_CONCURRENT_CONVERSIONS = int(os.getenv("TS2MP4_MAX_CONCURRENT", "1"))
    SLEEP_BETWEEN_FILES = float(os.getenv("TS2MP4_SLEEP_BETWEEN", "2"))
    
    @classmethod
    def ensure_dirs(cls):
        cls.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def apply_overrides(
        cls,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        log_dir: Optional[Path] = None,
        ffmpeg_bin: Optional[str] = None,
        ffprobe_bin: Optional[str] = None,
        sleep_between: Optional[float] = None,
    ):
        """Allow CLI overrides to adjust runtime configuration."""
        if input_dir:
            cls.INPUT_DIR = Path(input_dir).expanduser()
        if output_dir:
            cls.OUTPUT_DIR = Path(output_dir).expanduser()
        if log_dir:
            cls.LOG_DIR = Path(log_dir).expanduser()
        if ffmpeg_bin:
            cls.FFMPEG_BIN = ffmpeg_bin
        if ffprobe_bin:
            cls.FFPROBE_BIN = ffprobe_bin
        if sleep_between is not None:
            cls.SLEEP_BETWEEN_FILES = max(0.0, float(sleep_between))
        cls.ensure_dirs()
