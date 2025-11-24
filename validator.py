import subprocess
import json
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger("TS2MP4")

class VideoValidator:
    @staticmethod
    def get_video_info(file_path: Path):
        """Retrieves video metadata using ffprobe."""
        cmd = [
            Config.FFPROBE_BIN,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to probe file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading video info for {file_path}: {e}")
            return None

    @staticmethod
    def validate_conversion(input_path: Path, output_path: Path) -> bool:
        """
        Validates the converted file.
        Checks:
        1. File exists and size > 0.
        2. Duration matches input (within 1% tolerance).
        3. Has video stream.
        """
        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error(f"Validation failed: Output file missing or empty: {output_path}")
            return False

        input_info = VideoValidator.get_video_info(input_path)
        output_info = VideoValidator.get_video_info(output_path)

        if not input_info or not output_info:
            logger.error("Validation failed: Could not retrieve metadata.")
            return False

        try:
            # Check duration
            input_duration = float(input_info['format'].get('duration', 0))
            output_duration = float(output_info['format'].get('duration', 0))
            
            if input_duration == 0:
                logger.warning(f"Input file {input_path} has 0 duration. Skipping duration check.")
            else:
                diff = abs(input_duration - output_duration)
                percentage_diff = (diff / input_duration) * 100
                
                if percentage_diff > 1.0: # 1% tolerance
                    logger.error(f"Validation failed: Duration mismatch. Input: {input_duration}s, Output: {output_duration}s (Diff: {percentage_diff:.2f}%)")
                    return False

            # Check for video stream
            has_video = any(s['codec_type'] == 'video' for s in output_info['streams'])
            if not has_video:
                logger.error(f"Validation failed: No video stream found in {output_path}")
                return False

            logger.info(f"Validation passed for {output_path}")
            return True

        except Exception as e:
            logger.error(f"Validation error during checks: {e}")
            return False
