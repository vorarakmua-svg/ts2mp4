import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def _env_flag(name: str, default: str) -> bool:
    return os.getenv(name, default) not in ("0", "false", "False")


class Config:
    # All settings can be overridden via environment variables (see _read_environment)

    MODES = ("auto", "remux", "encode")

    @classmethod
    def _read_environment(cls):
        # Paths
        cls.INPUT_DIR = Path(os.getenv("TS2MP4_INPUT_DIR", r"C:\input")).expanduser()
        cls.OUTPUT_DIR = Path(os.getenv("TS2MP4_OUTPUT_DIR", r"C:\output")).expanduser()
        cls.LOG_DIR = Path(os.getenv("TS2MP4_LOG_DIR", "logs")).expanduser()

        # Extensions
        cls.INPUT_EXT = os.getenv("TS2MP4_INPUT_EXT", ".ts")
        cls.OUTPUT_EXT = os.getenv("TS2MP4_OUTPUT_EXT", ".mp4")

        # FFmpeg Settings
        cls.FFMPEG_BIN = os.getenv("TS2MP4_FFMPEG_BIN", "ffmpeg")
        cls.FFPROBE_BIN = os.getenv("TS2MP4_FFPROBE_BIN", "ffprobe")

        # Conversion mode: auto (remux when codecs allow, else re-encode), remux, or encode
        mode = os.getenv("TS2MP4_MODE", "auto").lower()
        cls.MODE = mode if mode in cls.MODES else "auto"

        # Encoding Settings
        cls.CRF_VALUE = int(os.getenv("TS2MP4_CRF_VALUE", "21"))
        cls.PRESET = os.getenv("TS2MP4_NVENC_PRESET", "p4")  # p1 (fastest) to p7 (slowest/best quality)
        cls.GPU_MAX_ATTEMPTS = int(os.getenv("TS2MP4_GPU_MAX_ATTEMPTS", "1"))
        cls.ENABLE_GPU = _env_flag("TS2MP4_ENABLE_GPU", "1")
        cls.FORCE_GPU = os.getenv("TS2MP4_FORCE_GPU", "0") in ("1", "true", "True")

        # Output Handling
        cls.DELETE_ORIGINALS = _env_flag("TS2MP4_DELETE_ORIGINALS", "1")
        cls.OVERWRITE_EXISTING = os.getenv("TS2MP4_OVERWRITE", "0") in ("1", "true", "True")

        # Resource Management
        cls.MAX_CONCURRENT_CONVERSIONS = int(os.getenv("TS2MP4_MAX_CONCURRENT", "1"))
        cls.SLEEP_BETWEEN_FILES = float(os.getenv("TS2MP4_SLEEP_BETWEEN", "2"))

    @classmethod
    def load_env_file(cls, path: Path) -> bool:
        """Load settings from a .env file. Variables already set in the environment take precedence."""
        if not Path(path).is_file():
            return False
        load_dotenv(path, override=False)
        cls._read_environment()
        return True

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
        delete_originals: Optional[bool] = None,
        overwrite_existing: Optional[bool] = None,
        mode: Optional[str] = None,
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
        if delete_originals is not None:
            cls.DELETE_ORIGINALS = delete_originals
        if overwrite_existing is not None:
            cls.OVERWRITE_EXISTING = overwrite_existing
        if mode is not None:
            if mode not in cls.MODES:
                raise ValueError(f"Invalid mode {mode!r}; expected one of {', '.join(cls.MODES)}")
            cls.MODE = mode
        cls.ensure_dirs()


Config._read_environment()
