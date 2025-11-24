import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from config import Config

logger = logging.getLogger("TS2MP4")


class VideoValidator:
    @staticmethod
    def get_video_info(file_path: Path) -> Optional[Dict[str, Any]]:
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
            stderr = (e.stderr or "").strip()
            logger.error(f"Failed to probe file {file_path}: {stderr or e}")
            return None
        except Exception as e:
            logger.error(f"Error reading video info for {file_path}: {e}")
            return None

    @staticmethod
    def _extract_duration(metadata: Optional[Dict[str, Any]]) -> Optional[float]:
        if not metadata:
            return None
        try:
            return float(metadata.get("format", {}).get("duration"))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _has_video_stream(metadata: Optional[Dict[str, Any]]) -> bool:
        if not metadata:
            return False
        streams = metadata.get("streams") or []
        return any((stream or {}).get("codec_type") == "video" for stream in streams)

    @staticmethod
    def validate_conversion(
        input_path: Path,
        output_path: Path,
        *,
        input_info: Optional[Dict[str, Any]] = None,
        output_info: Optional[Dict[str, Any]] = None,
        duration_tolerance_pct: float = 1.0,
    ) -> bool:
        """
        Validates the converted file.
        Checks:
        1. File exists and size > 0.
        2. Duration matches input (within tolerance).
        3. Has video stream.
        """
        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error(f"Validation failed: Output file missing or empty: {output_path}")
            return False

        input_info = input_info or VideoValidator.get_video_info(input_path)
        output_info = output_info or VideoValidator.get_video_info(output_path)

        if not input_info or not output_info:
            logger.error("Validation failed: Could not retrieve metadata.")
            return False

        input_duration = VideoValidator._extract_duration(input_info)
        output_duration = VideoValidator._extract_duration(output_info)

        if input_duration and output_duration:
            diff = abs(input_duration - output_duration)
            percentage_diff = (diff / input_duration) * 100

            if percentage_diff > duration_tolerance_pct:
                logger.error(
                    "Validation failed: Duration mismatch. Input: %.2fs, Output: %.2fs (Diff: %.2f%%)",
                    input_duration,
                    output_duration,
                    percentage_diff,
                )
                return False
        else:
            logger.warning(
                "Unable to compare durations for %s (input: %s, output: %s).",
                output_path.name,
                "missing" if not input_duration else "ok",
                "missing" if not output_duration else "ok",
            )

        if not VideoValidator._has_video_stream(output_info):
            logger.error(f"Validation failed: No video stream found in {output_path}")
            return False

        logger.info(f"Validation passed for {output_path}")
        return True
