import subprocess
import time
import logging
import re
from pathlib import Path
from typing import Optional
from config import Config
from validator import VideoValidator

logger = logging.getLogger("TS2MP4")

class VideoConverter:
    def __init__(self):
        self.hw_accel = self._detect_hardware()

    def _detect_hardware(self) -> str:
        """Checks for NVIDIA GPU availability."""
        try:
            # Simple check: try to encode a dummy frame with nvenc
            # This is a robust way to check if nvenc is actually usable
            cmd = [
                Config.FFMPEG_BIN,
                "-y",
                "-f", "lavfi", "-i", "color=c=black:s=64x64:d=1",
                "-c:v", "h264_nvenc",
                "-f", "null", "-"
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info("NVIDIA GPU detected. Using hardware acceleration (h264_nvenc/hevc_nvenc).")
            return "cuda"
        except subprocess.CalledProcessError:
            logger.warning("NVIDIA GPU not detected or NVENC unavailable. Falling back to CPU.")
            return "cpu"
        except FileNotFoundError:
            logger.critical("FFmpeg not found! Please ensure ffmpeg is in your PATH.")
            raise

    def convert_file(self, input_path: Path, progress_callback=None) -> bool:
        """
        Converts a single file.
        Returns True if successful and validated, False otherwise.
        """
        output_filename = input_path.stem + Config.OUTPUT_EXT
        output_path = Config.OUTPUT_DIR / output_filename
        
        # Determine encoder and options based on hardware
        if self.hw_accel == "cuda":
            # Try HEVC (H.265) first for better quality/size, else H.264
            # For simplicity in this robust version, we'll stick to h264_nvenc as it's widely compatible
            # But user asked for "better output file", so let's try to use hevc_nvenc if possible?
            # Let's stick to h264_nvenc for maximum compatibility unless specified, 
            # but we can add a config option later.
            # Using h264_nvenc with -cq for quality control
            video_codec = "h264_nvenc"
            # -cq:v is for VBR quality in NVENC. 
            # -preset p4 is medium-fast.
            encoding_opts = ["-c:v", video_codec, "-preset", Config.PRESET, "-cq:v", str(Config.CRF_VALUE)]
        else:
            video_codec = "libx264"
            encoding_opts = ["-c:v", video_codec, "-crf", str(Config.CRF_VALUE), "-preset", "medium"]

        # Audio copy is usually safe and preserves quality
        audio_opts = ["-c:a", "aac", "-b:a", "192k"] 

        cmd = [
            Config.FFMPEG_BIN,
            "-y", # Overwrite output
            "-i", str(input_path),
            *encoding_opts,
            *audio_opts,
            str(output_path)
        ]

        logger.info(f"Starting conversion: {input_path.name} -> {output_path.name} [{self.hw_accel}]")
        
        start_time = time.time()
        try:
            # Run conversion
            # We use Popen to capture output for progress parsing if needed
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8' # Ensure encoding is handled
            )
            
            # Simple progress monitoring (reading stderr line by line)
            # FFmpeg writes stats to stderr
            duration = None
            for line in process.stderr:
                # Try to extract duration first
                if "Duration" in line and not duration:
                    match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                    if match:
                        h, m, s = map(float, match.groups())
                        duration = h * 3600 + m * 60 + s
                
                # Extract time to calculate progress
                if "time=" in line and duration:
                    match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                    if match:
                        h, m, s = map(float, match.groups())
                        current_time = h * 3600 + m * 60 + s
                        percent = (current_time / duration) * 100
                        if progress_callback:
                            progress_callback(percent)
            
            process.wait()

            if process.returncode != 0:
                logger.error(f"FFmpeg failed for {input_path.name}")
                # If GPU failed, maybe try CPU fallback?
                if self.hw_accel == "cuda":
                    logger.warning("GPU conversion failed. Attempting CPU failover...")
                    self.hw_accel = "cpu" # Switch to CPU for this and future
                    return self.convert_file(input_path, progress_callback)
                return False

            # Validation
            if VideoValidator.validate_conversion(input_path, output_path):
                # Delete original if validated
                try:
                    input_path.unlink()
                    logger.info(f"Deleted original file: {input_path}")
                    return True
                except OSError as e:
                    logger.error(f"Failed to delete original file {input_path}: {e}")
                    return True # Conversion was still successful
            else:
                # Validation failed, delete output
                if output_path.exists():
                    output_path.unlink()
                return False

        except Exception as e:
            logger.error(f"Error converting {input_path}: {e}")
            return False
        finally:
            # Resource management sleep
            time.sleep(Config.SLEEP_BETWEEN_FILES)
