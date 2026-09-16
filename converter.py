import subprocess
import time
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Optional, List, Tuple
from config import Config
from validator import VideoValidator

logger = logging.getLogger("TS2MP4")


@dataclass
class ConversionResult:
    success: bool
    output_path: Optional[Path] = None
    elapsed_seconds: float = 0.0
    source_duration: Optional[float] = None
    realtime_factor: Optional[float] = None
    encoder: str = ""
    retried_with_cpu: bool = False
    cancelled: bool = False
    skipped: bool = False
    error: Optional[str] = None


class VideoConverter:
    # Compile regex patterns once at class level for performance
    _DURATION_PATTERN = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})")
    _TIME_PATTERN = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
    _FPS_PATTERN = re.compile(r"fps=\s*(\d+\.?\d*)")
    _BITRATE_PATTERN = re.compile(r"bitrate=\s*([\d.]+\s*\w+bits/s)")
    _SPEED_PATTERN = re.compile(r"speed=\s*([\d.]+)x")

    def __init__(self):
        # Ensure required directories exist before any work begins
        Config.ensure_dirs()
        self.hw_accel = self._detect_hardware()

    def _detect_hardware(self) -> str:
        """Checks for NVIDIA GPU availability."""
        if not Config.ENABLE_GPU:
            logger.info("GPU acceleration disabled via configuration.")
            return "cpu"

        if Config.FORCE_GPU:
            logger.info("GPU acceleration forced via configuration override.")
            return "cuda"

        cmd = [Config.FFMPEG_BIN, "-hide_banner", "-encoders"]
        try:
            # Add 10-second timeout for encoder detection
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg encoder detection timed out. Falling back to CPU.")
            return "cpu"
        except FileNotFoundError:
            logger.critical("FFmpeg not found! Please ensure ffmpeg is in your PATH.")
            raise
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            logger.warning("Unable to inspect FFmpeg encoders (stderr: %s). Falling back to CPU.", stderr or "n/a")
            return "cpu"
        except Exception as exc:
            logger.warning("Unexpected error while detecting GPU support: %s. Falling back to CPU.", exc)
            return "cpu"

        encoders_output = (result.stdout or "") + (result.stderr or "")
        if "h264_nvenc" in encoders_output or "hevc_nvenc" in encoders_output:
            logger.info("FFmpeg NVENC encoder detected. GPU acceleration enabled.")
            return "cuda"

        logger.warning("FFmpeg build does not list NVENC encoders. Falling back to CPU.")
        return "cpu"

    @staticmethod
    def _validate_path_safety(path: Path) -> None:
        """Validates path for security concerns (command injection, dangerous characters)."""
        path_str = str(path)
        # Check for potentially dangerous characters that could be used for injection
        dangerous_chars = [';', '&', '|', '`', '$', '>', '<', '\n', '\r']
        if any(char in path_str for char in dangerous_chars):
            raise ValueError(f"Path contains potentially dangerous characters: {path}")

        # Ensure path is absolute to prevent relative path issues
        if not path.is_absolute():
            raise ValueError(f"Path must be absolute: {path}")

        # No symlinks allowed to prevent symlink attacks
        if path.is_symlink():
            raise ValueError(f"Symlinks not allowed: {path}")

    @staticmethod
    def _validate_path_within_directory(path: Path, allowed_dir: Path) -> None:
        """Prevents path traversal attacks by ensuring path is within allowed directory."""
        try:
            resolved_path = path.resolve(strict=False)
            resolved_dir = allowed_dir.resolve(strict=False)

            # Check if path is within allowed directory
            resolved_path.relative_to(resolved_dir)
        except ValueError:
            raise ValueError(f"Path outside allowed directory: {path}")

    @staticmethod
    def _validate_file_size(path: Path, max_size: int = 50 * 1024 ** 3) -> None:
        """Validates file size is within acceptable range (default: 50GB max)."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        size = path.stat().st_size
        if size == 0:
            raise ValueError(f"File is empty: {path}")
        if size > max_size:
            raise ValueError(
                f"File too large: {size / (1024**3):.2f}GB "
                f"(max: {max_size / (1024**3):.2f}GB)"
            )

    @staticmethod
    def _check_disk_space(input_path: Path, output_dir: Path) -> None:
        """Ensures sufficient disk space for conversion."""
        input_size = input_path.stat().st_size
        # Conservative estimate: output might be up to 1.5x input size
        estimated_output = int(input_size * 1.5)
        safety_margin = 2 * 1024 ** 3  # 2GB safety margin
        required_space = estimated_output + safety_margin

        stat = shutil.disk_usage(output_dir)
        if stat.free < required_space:
            raise OSError(
                f"Insufficient disk space. Required: {required_space / (1024**3):.2f}GB, "
                f"Available: {stat.free / (1024**3):.2f}GB"
            )

    def convert_file(
        self,
        input_path: Path,
        progress_callback=None,
        stats_callback=None,
        cancel_event: Optional[Event] = None,
    ) -> ConversionResult:
        """
        Converts a single file and returns a detailed result.
        """
        if not input_path.exists():
            message = f"Input file does not exist: {input_path}"
            logger.error(message)
            return ConversionResult(False, error=message)

        if not input_path.is_file():
            message = f"Input path is not a file: {input_path}"
            logger.error(message)
            return ConversionResult(False, error=message)

        if input_path.suffix.lower() != Config.INPUT_EXT.lower():
            message = f"Skipping non-{Config.INPUT_EXT} file: {input_path.name}"
            logger.warning(message)
            return ConversionResult(False, error=message)

        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # SECURITY VALIDATION BLOCK
        try:
            self._validate_path_safety(input_path)
            self._validate_path_within_directory(input_path, Config.INPUT_DIR)
            self._validate_file_size(input_path)
            self._check_disk_space(input_path, Config.OUTPUT_DIR)
        except (ValueError, FileNotFoundError, OSError) as e:
            logger.error(f"Security validation failed for {input_path}: {e}")
            return ConversionResult(False, error=str(e))

        output_filename = input_path.stem + Config.OUTPUT_EXT
        output_path = Config.OUTPUT_DIR / output_filename
        temp_output_path = output_path.with_name(output_path.name + ".partial")
        output_format = Config.OUTPUT_EXT.lstrip(".")

        if output_path.exists() and not Config.OVERWRITE_EXISTING:
            message = f"Output already exists, skipping: {output_path.name}"
            logger.warning(message)
            return ConversionResult(False, output_path=output_path, skipped=True, error=message)

        audio_opts = ["-c:a", "aac", "-b:a", "192k"]
        input_info = VideoValidator.get_video_info(input_path)
        source_duration = VideoValidator._extract_duration(input_info)

        attempts = self._build_attempt_plan()
        last_error = None
        hardware_failed = False

        for label, use_hw, encoder, encoding_opts in attempts:
            if cancel_event and cancel_event.is_set():
                message = "Conversion cancelled before starting."
                logger.info(message)
                return ConversionResult(False, source_duration=source_duration, cancelled=True, error=message)

            self._safe_unlink(temp_output_path)
            cmd = [
                Config.FFMPEG_BIN,
                "-y",
                "-i", str(input_path),
                *encoding_opts,
                *audio_opts,
            ]
            if output_format:
                cmd.extend(["-f", output_format])
            cmd.append(str(temp_output_path))

            logger.info("Starting %s using %s", input_path.name, label)
            attempt_start = time.time()

            success, cancelled, last_progress, last_line = self._run_ffmpeg(
                cmd,
                progress_callback=progress_callback,
                stats_callback=stats_callback,
                cancel_event=cancel_event,
                duration_hint=source_duration,
            )

            if cancelled:
                self._safe_unlink(temp_output_path)
                message = "Conversion cancelled by user."
                logger.info(message)
                return ConversionResult(False, source_duration=source_duration, cancelled=True, error=message)

            if not success:
                last_error = last_line or "FFmpeg returned a non-zero exit status."
                logger.warning("%s failed for %s: %s", label, input_path.name, last_error)
                self._safe_unlink(temp_output_path)
                if progress_callback and last_progress:
                    progress_callback(-last_progress)
                if not use_hw:
                    break
                hardware_failed = True
                continue

            elapsed = time.time() - attempt_start
            is_valid = VideoValidator.validate_conversion(
                input_path,
                temp_output_path,
                input_info=input_info,
            )

            if not is_valid:
                last_error = f"Validation failed for {temp_output_path.name}"
                logger.error(last_error)
                self._safe_unlink(temp_output_path)
                if progress_callback:
                    progress_callback(-100.0)
                if not use_hw:
                    break
                hardware_failed = True
                continue

            # Atomic file replacement to avoid race conditions
            try:
                # replace() is atomic on most systems - it handles existing files
                temp_output_path.replace(output_path)
            except OSError as finalize_err:
                # If replace failed, try unlinking first and retry once
                try:
                    if output_path.exists():
                        output_path.unlink()
                    temp_output_path.replace(output_path)
                except OSError as retry_err:
                    last_error = f"Failed to finalize output file: {retry_err}"
                    logger.error(last_error)
                    self._safe_unlink(temp_output_path)
                    return ConversionResult(False, source_duration=source_duration, error=last_error)

            if Config.DELETE_ORIGINALS:
                try:
                    input_path.unlink()
                    logger.info(f"Deleted original file: {input_path}")
                except OSError as e:
                    logger.error(f"Failed to delete original file {input_path}: {e}")

            realtime_factor = None
            if elapsed > 0 and source_duration:
                realtime_factor = source_duration / elapsed

            logger.info(
                "Completed %s in %.2fs using %s (x%s realtime).",
                input_path.name,
                elapsed,
                encoder,
                f"{realtime_factor:.2f}" if realtime_factor else "N/A",
            )

            return ConversionResult(
                True,
                output_path=output_path,
                elapsed_seconds=elapsed,
                source_duration=source_duration,
                realtime_factor=realtime_factor,
                encoder=encoder,
                retried_with_cpu=(not use_hw and hardware_failed),
            )

        message = last_error or "Conversion failed after all attempts."
        logger.error(message)
        return ConversionResult(False, source_duration=source_duration, error=message)

    def _build_attempt_plan(self) -> List[Tuple[str, bool, str, List[str]]]:
        """Create an ordered list of encoding attempts."""
        attempts: List[Tuple[str, bool, str, List[str]]] = []
        if self.hw_accel == "cuda":
            retries = max(1, Config.GPU_MAX_ATTEMPTS)
            for attempt_idx in range(retries):
                codec, opts = self._get_encoding_options(use_hw=True)
                label = f"GPU (NVENC) attempt {attempt_idx + 1}/{retries}"
                attempts.append((label, True, codec, opts))

        codec, opts = self._get_encoding_options(use_hw=False)
        attempts.append(("CPU (libx264)", False, codec, opts))
        return attempts

    def _get_encoding_options(self, use_hw: bool) -> Tuple[str, List[str]]:
        """Returns encoder name and ffmpeg options based on hardware availability."""
        if use_hw:
            codec = "h264_nvenc"
            opts = ["-c:v", codec, "-preset", Config.PRESET, "-cq:v", str(Config.CRF_VALUE)]
        else:
            codec = "libx264"
            opts = ["-c:v", codec, "-crf", str(Config.CRF_VALUE), "-preset", "medium"]
        return codec, opts

    def _run_ffmpeg(
        self,
        cmd: List[str],
        *,
        progress_callback,
        stats_callback=None,
        cancel_event: Optional[Event],
        duration_hint: Optional[float],
    ) -> Tuple[bool, bool, float, Optional[str]]:
        """Executes FFmpeg while streaming progress updates and statistics."""
        # Calculate timeout: allow 10x realtime for safety, default 1 hour
        timeout = (duration_hint * 10) if duration_hint else 3600

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
        )

        duration = duration_hint
        last_progress = 0.0
        percent = 0.0  # Initialize to avoid UnboundLocalError
        last_line = None
        start_time = time.time()

        try:
            if not process.stderr:
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.error("FFmpeg process timed out")
                    process.kill()
                    return False, False, last_progress, "Process timed out"
                return process.returncode == 0, False, last_progress, last_line

            for line in process.stderr:
                last_line = line.strip()

                if cancel_event and cancel_event.is_set():
                    logger.info("Termination requested. Stopping FFmpeg...")
                    process.terminate()
                    break

                if duration is None and "Duration:" in line:
                    match = self._DURATION_PATTERN.search(line)
                    if match:
                        h, m, s = map(float, match.groups())
                        duration = h * 3600 + m * 60 + s

                if duration and "time=" in line:
                    match = self._TIME_PATTERN.search(line)
                    if match:
                        h, m, s = map(float, match.groups())
                        current_time = h * 3600 + m * 60 + s
                        percent = min(100.0, (current_time / duration) * 100)
                        if progress_callback:
                            delta = max(0.0, percent - last_progress)
                            if delta:
                                progress_callback(delta)
                                last_progress = percent

                    # Extract and report detailed statistics
                    if stats_callback:
                        stats = {}

                        # FPS
                        fps_match = self._FPS_PATTERN.search(line)
                        if fps_match:
                            stats['fps'] = fps_match.group(1)

                        # Bitrate
                        bitrate_match = self._BITRATE_PATTERN.search(line)
                        if bitrate_match:
                            stats['bitrate'] = bitrate_match.group(1)

                        # Speed
                        speed_match = self._SPEED_PATTERN.search(line)
                        if speed_match:
                            stats['speed'] = f"{speed_match.group(1)}x"

                        # Progress percentage
                        stats['progress'] = percent

                        if stats:
                            stats_callback(stats)

                # Check for timeout during processing
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.error("FFmpeg process exceeded timeout")
                    process.terminate()
                    last_line = "Process timed out"
                    break

            # Wait for process to complete with remaining timeout
            remaining_timeout = max(1, timeout - (time.time() - start_time))
            try:
                process.wait(timeout=remaining_timeout)
            except subprocess.TimeoutExpired:
                logger.error("FFmpeg process timed out during wait")
                process.kill()
                last_line = "Process timed out"
        finally:
            if process.stderr:
                process.stderr.close()

        cancelled = bool(cancel_event and cancel_event.is_set())
        success = process.returncode == 0 and not cancelled

        if success and progress_callback and last_progress < 100.0:
            progress_callback(100.0 - last_progress)
            last_progress = 100.0

        return success, cancelled, last_progress, last_line

    @staticmethod
    def _safe_unlink(path: Path):
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            logger.warning(f"Failed to remove temporary file {path}: {exc}")
