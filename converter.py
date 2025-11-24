import subprocess
import time
import logging
import re
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
    error: Optional[str] = None


class VideoConverter:
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
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
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

    def convert_file(
        self,
        input_path: Path,
        progress_callback=None,
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

        output_filename = input_path.stem + Config.OUTPUT_EXT
        output_path = Config.OUTPUT_DIR / output_filename
        temp_output_path = output_path.with_name(output_path.name + ".partial")
        output_format = Config.OUTPUT_EXT.lstrip(".")

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

            try:
                if output_path.exists():
                    output_path.unlink()
                temp_output_path.replace(output_path)
            except OSError as finalize_err:
                last_error = f"Failed to finalize output file: {finalize_err}"
                logger.error(last_error)
                self._safe_unlink(temp_output_path)
                return ConversionResult(False, source_duration=source_duration, error=last_error)

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
        cancel_event: Optional[Event],
        duration_hint: Optional[float],
    ) -> Tuple[bool, bool, float, Optional[str]]:
        """Executes FFmpeg while streaming progress updates."""
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
        )

        duration = duration_hint
        last_progress = 0.0
        last_line = None

        try:
            if not process.stderr:
                process.wait()
                return process.returncode == 0, False, last_progress, last_line

            for line in process.stderr:
                last_line = line.strip()

                if cancel_event and cancel_event.is_set():
                    logger.info("Termination requested. Stopping FFmpeg...")
                    process.terminate()
                    break

                if duration is None and "Duration" in line:
                    match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                    if match:
                        h, m, s = map(float, match.groups())
                        duration = h * 3600 + m * 60 + s

                if duration and "time=" in line:
                    match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                    if match:
                        h, m, s = map(float, match.groups())
                        current_time = h * 3600 + m * 60 + s
                        percent = min(100.0, (current_time / duration) * 100)
                        if progress_callback:
                            delta = max(0.0, percent - last_progress)
                            if delta:
                                progress_callback(delta)
                                last_progress = percent

            process.wait()
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
