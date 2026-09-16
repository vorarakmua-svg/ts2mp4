"""
TS2MP4 Professional Video Converter - Main Entry Point
Features professional-grade visual display and concurrent processing
"""
import argparse
import sys
import time
import signal
from pathlib import Path
from threading import Event, Lock, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Sequence, Tuple
from colorama import Fore, Style
from config import Config
from utils import setup_logging, get_input_files
from converter import VideoConverter, ConversionResult
from display import get_display
from metrics import MetricsCollector
from health import HealthMonitor
from profiler import PerformanceProfiler

STOP_EVENT = Event()


def signal_handler(signum, frame):
    if not STOP_EVENT.is_set():
        print(f"\n\n{Fore.YELLOW}[!] Stop requested. Cancelling current conversion and exiting...{Style.RESET_ALL}")
    STOP_EVENT.set()


def register_signal_handlers():
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, signal_handler)
        except (ValueError, AttributeError):
            # SIGTERM is not supported on some Windows environments
            pass


def display_update_loop(display, stop_event: Event):
    """Background thread to update display periodically"""
    while not stop_event.is_set():
        try:
            display.display()
            time.sleep(0.5)  # Update every 500ms
        except Exception:
            # Silently continue on display errors
            pass


def health_check_loop(health_monitor, stop_event: Event):
    """Background thread to perform periodic health checks"""
    while not stop_event.is_set():
        try:
            health_monitor.check_health()
            time.sleep(5)  # Check every 5 seconds
        except Exception as e:
            # Silently continue on health check errors
            pass


def determine_worker_count(hw_accel: str, max_concurrent: int) -> int:
    """Number of parallel conversions; GPU is capped at 2 to avoid exhausting encoder sessions/memory."""
    workers = max(1, max_concurrent)
    if hw_accel == "cuda":
        workers = min(workers, 2)
    return workers


def describe_encoder(hw_accel: str) -> str:
    return "GPU (NVENC)" if hw_accel == "cuda" else "CPU (libx264)"


def final_status(failed: int, skipped: int, interrupted: bool) -> Tuple[str, bool]:
    """Returns the end-of-run message and whether the run fully succeeded."""
    if interrupted:
        return "Processing interrupted by user.", False
    if failed:
        return f"Finished with {failed} failed file(s). See the log for details.", False
    message = "All tasks completed successfully!"
    if skipped:
        message += f" ({skipped} file(s) skipped because the output already exists)"
    return message, True


def process_file_worker(
    converter: VideoConverter,
    input_file: Path,
    cancel_event: Event,
    display,
    counts: dict,
    count_lock: Lock,
    metrics_collector=None,
) -> Tuple[Path, ConversionResult]:
    """Worker function with enhanced display integration and metrics collection"""

    # Update display with current file
    display.update_stats(
        current_file=input_file.name,
        encoder=converter.hw_accel.upper() if converter.hw_accel == "cuda" else "CPU",
        current_progress=0.0,
    )

    def stats_callback(stats: dict):
        """Callback to update display with FFmpeg statistics"""
        display.update_stats(
            current_progress=stats.get('progress', 0.0),
            current_speed=stats.get('speed', '0.00x'),
            fps=stats.get('fps', '0'),
            bitrate=stats.get('bitrate', '0 kbits/s'),
        )

    result = converter.convert_file(
        input_file,
        progress_callback=None,
        stats_callback=stats_callback,
        cancel_event=cancel_event,
    )

    # Record metrics (skipped files were never converted)
    if metrics_collector and not result.skipped:
        metrics_collector.record_conversion(
            input_path=input_file,
            output_path=result.output_path,
            success=result.success,
            duration=result.elapsed_seconds,
            encoder=result.encoder or "unknown",
            realtime_factor=result.realtime_factor,
            error=result.error,
            retried_with_cpu=result.retried_with_cpu,
            cancelled=result.cancelled,
        )

    # Update counts
    with count_lock:
        if result.success:
            counts['completed'] += 1
        elif result.skipped:
            counts['skipped'] += 1
        else:
            counts['failed'] += 1

        # The live display has no skipped column; count skipped files as done so progress adds up
        display.update_stats(
            completed=counts['completed'] + counts['skipped'],
            failed=counts['failed'],
        )

    return input_file, result


def parse_args(argv: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser(
        description="TS2MP4 Professional Video Converter - Batch convert .ts files to .mp4 with real-time monitoring.",
        epilog="Experience professional-grade conversion with live statistics and resource monitoring."
    )
    parser.add_argument("--input-dir", type=Path, help="Directory containing input .ts files.")
    parser.add_argument("--output-dir", type=Path, help="Directory where converted files are written.")
    parser.add_argument("--log-dir", type=Path, help="Directory where logs are stored.")
    parser.add_argument("--ffmpeg-bin", type=str, help="Path to ffmpeg executable.")
    parser.add_argument("--ffprobe-bin", type=str, help="Path to ffprobe executable.")
    parser.add_argument("--sleep-between", type=float, help="Seconds to sleep between conversions (deprecated in concurrent mode).")
    parser.add_argument("--profile", action="store_true", help="Enable performance profiling.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate conversion without actually converting files.")
    parser.add_argument("--wizard", action="store_true", help="Run interactive configuration wizard.")
    parser.add_argument("--keep-originals", dest="delete_originals", action="store_false", default=None,
                        help="Keep the original .ts files after a successful conversion.")
    parser.add_argument("--overwrite", action="store_true", default=None,
                        help="Overwrite existing output files instead of skipping them.")
    return parser.parse_args(argv)


def main():
    register_signal_handlers()
    args = parse_args()

    # Handle wizard mode
    if args.wizard:
        from wizard import ConfigurationWizard
        wizard = ConfigurationWizard()
        wizard.run()
        sys.exit(0)

    # Settings saved by the wizard; real environment variables and CLI flags take precedence
    Config.load_env_file(Path.cwd() / ".env")
    Config.apply_overrides(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        ffmpeg_bin=args.ffmpeg_bin,
        ffprobe_bin=args.ffprobe_bin,
        sleep_between=args.sleep_between,
        delete_originals=args.delete_originals,
        overwrite_existing=args.overwrite,
    )

    logger = setup_logging()
    logger.info("TS2MP4 Converter Started")

    # Check for dry-run mode
    if args.dry_run:
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}🔍 DRY-RUN MODE ENABLED{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}No files will be converted. Showing what would happen...{Style.RESET_ALL}\n")
        logger.info("DRY-RUN mode enabled")

    # Initialize profiler if enabled
    profiler = None
    if args.profile:
        profiler = PerformanceProfiler(Config.LOG_DIR)
        profiler.start()
        logger.info("Performance profiling enabled")

    files = get_input_files()
    if not files:
        message = f"No {Config.INPUT_EXT} files found in {Config.INPUT_DIR}"
        logger.warning(message)
        print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
        sys.exit(1)

    print(f"{Fore.CYAN}Found {len(files)} files to convert.{Style.RESET_ALL}")
    logger.info(f"Found {len(files)} files.")

    try:
        converter = VideoConverter()
    except Exception as e:
        logger.critical(f"Failed to initialize converter: {e}")
        sys.exit(1)

    # Handle dry-run mode
    if args.dry_run:
        print(f"\n{Fore.CYAN}{Style.BRIGHT}╔{'═' * 78}╗{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.YELLOW}{Style.BRIGHT}DRY-RUN SIMULATION{Style.RESET_ALL}" + " " * 61 + f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}╠{'═' * 78}╣{Style.RESET_ALL}")

        for idx, input_file in enumerate(files, 1):
            output_filename = input_file.stem + Config.OUTPUT_EXT
            output_path = Config.OUTPUT_DIR / output_filename
            file_size_mb = input_file.stat().st_size / (1024 ** 2)

            print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.GREEN}[{idx}/{len(files)}]{Style.RESET_ALL} {input_file.name}")
            print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}     → Size: {file_size_mb:.2f} MB")
            print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}     → Output: {output_path}")
            if output_path.exists() and not Config.OVERWRITE_EXISTING:
                action = "Would skip (output already exists)"
            else:
                action = f"Would convert using {describe_encoder(converter.hw_accel)}"
                if not Config.DELETE_ORIGINALS:
                    action += ", keeping original"
            print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}     → Action: {action}")

        print(f"{Fore.CYAN}{Style.BRIGHT}╚{'═' * 78}╝{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Dry-run complete. No files were modified.{Style.RESET_ALL}")
        logger.info("Dry-run simulation completed")
        sys.exit(0)

    # Initialize metrics collector
    metrics_collector = MetricsCollector(Config.LOG_DIR)
    logger.info("Metrics collection enabled")

    # Initialize health monitor
    health_monitor = HealthMonitor(Config.LOG_DIR / "health_status.json")
    health_monitor.check_health()  # Initial health check
    logger.info("Health monitoring enabled")

    # Initialize enhanced display
    display = get_display()
    display.update_stats(
        total_files=len(files),
        completed=0,
        failed=0,
        encoder=converter.hw_accel.upper() if converter.hw_accel == "cuda" else "CPU",
    )

    max_workers = determine_worker_count(converter.hw_accel, Config.MAX_CONCURRENT_CONVERSIONS)
    logger.info("Using %s encoding with %d worker(s)", describe_encoder(converter.hw_accel), max_workers)

    # Thread-safe counters
    count_lock = Lock()
    counts = {'completed': 0, 'failed': 0, 'skipped': 0}

    exit_code = 0
    completed_files = []
    failed_files = []
    skipped_files = []

    # Start display update thread
    display_stop = Event()
    display_thread = Thread(target=display_update_loop, args=(display, display_stop), daemon=True)
    display_thread.start()

    # Start health check thread
    health_stop = Event()
    health_thread = Thread(target=health_check_loop, args=(health_monitor, health_stop), daemon=True)
    health_thread.start()

    logger.info("Starting conversion with %d workers...", max_workers)

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(
                    process_file_worker,
                    converter,
                    input_file,
                    STOP_EVENT,
                    display,
                    counts,
                    count_lock,
                    metrics_collector,
                ): input_file
                for input_file in files
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_file):
                if STOP_EVENT.is_set():
                    # Cancel remaining futures
                    for f in future_to_file:
                        f.cancel()
                    break

                input_file = future_to_file[future]

                try:
                    input_file, result = future.result()

                    if result.success:
                        speed = f"{result.realtime_factor:.2f}x" if result.realtime_factor else "N/A"
                        logger.info(
                            "Converted %s in %.2fs (speed: %s) using %s%s",
                            input_file.name,
                            result.elapsed_seconds,
                            speed,
                            result.encoder,
                            " after GPU fallback" if result.retried_with_cpu else "",
                        )
                        completed_files.append(input_file)
                    elif result.skipped:
                        skipped_files.append(input_file)
                    else:
                        exit_code = exit_code or (130 if result.cancelled else 1)
                        reason = result.error or "Unknown error"

                        if not result.cancelled:
                            logger.error("Failed to convert %s: %s", input_file.name, reason)
                            failed_files.append(input_file)

                except Exception as e:
                    logger.error(f"Unexpected error processing {input_file}: {e}", exc_info=True)
                    failed_files.append(input_file)
                    exit_code = 1

                if STOP_EVENT.is_set():
                    break

    finally:
        # Stop display thread
        display_stop.set()
        display_thread.join(timeout=1)

        # Stop health check thread
        health_stop.set()
        health_thread.join(timeout=1)

        # Clear screen and show professional final summary
        display.clear_screen()

    # Print professional final summary
    print(f"\n{Fore.CYAN}{Style.BRIGHT}╔{'═' * 78}╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.GREEN}{Style.BRIGHT}CONVERSION COMPLETE{Style.RESET_ALL}" + " " * 58 + f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}╠{'═' * 78}╣{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.GREEN}✓ Completed:{Style.RESET_ALL} {len(completed_files):3d} files" + " " * 55 + f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.RED}✗ Failed:{Style.RESET_ALL}    {len(failed_files):3d} files" + " " * 55 + f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.BLUE}↷ Skipped:{Style.RESET_ALL}   {len(skipped_files):3d} files" + " " * 55 + f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} {Fore.YELLOW}⊕ Total:{Style.RESET_ALL}     {len(files):3d} files" + " " * 55 + f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}╚{'═' * 78}╝{Style.RESET_ALL}")

    message, ok = final_status(len(failed_files), len(skipped_files), STOP_EVENT.is_set())
    if ok:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ {message}{Style.RESET_ALL}")
        logger.info(message)
    else:
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚠ {message}{Style.RESET_ALL}")
        logger.warning(message)

    # Export metrics
    if metrics_collector.total_conversions > 0:
        try:
            json_path = metrics_collector.export_to_json()
            csv_path = metrics_collector.export_to_csv()
            print(f"\n{Fore.CYAN}📊 Metrics exported:{Style.RESET_ALL}")
            print(f"  • JSON: {json_path}")
            print(f"  • CSV:  {csv_path}")
            logger.info(f"Metrics exported to {json_path} and {csv_path}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

    # Export final health report
    try:
        health_report_path = health_monitor.export_health_report()
        print(f"\n{Fore.CYAN}🏥 Health report: {health_report_path}{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Failed to export health report: {e}")

    # Export profiling data if enabled
    if profiler:
        try:
            profiler.stop()
            profile_txt = profiler.export_stats()
            profile_bin = profiler.export_binary()
            print(f"\n{Fore.CYAN}⚡ Performance profile:{Style.RESET_ALL}")
            print(f"  • Report: {profile_txt}")
            print(f"  • Binary: {profile_bin}")
            logger.info(f"Performance profile exported to {profile_txt}")
        except Exception as e:
            logger.error(f"Failed to export performance profile: {e}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
