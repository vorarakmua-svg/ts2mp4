"""
Enhanced main entry point with beautiful visual display
Run this for an engaging, colorful conversion experience!
"""
import argparse
import sys
import time
import signal
from pathlib import Path
from threading import Event, Lock, Semaphore, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple
from colorama import Fore, Style
from config import Config
from utils import setup_logging, get_input_files
from converter import VideoConverter, ConversionResult
from display import get_display

STOP_EVENT = Event()


def signal_handler(signum, frame):
    if not STOP_EVENT.is_set():
        print(f"\n\n{Fore.YELLOW}[!] Stop requested. Finishing current files and exiting...{Style.RESET_ALL}")
    STOP_EVENT.set()


def register_signal_handlers():
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, signal_handler)
        except (ValueError, AttributeError):
            pass


def process_file_worker_enhanced(
    converter: VideoConverter,
    input_file: Path,
    cancel_event: Event,
    gpu_semaphore: Semaphore,
    display,
    completed_count: dict,
    failed_count: dict,
    count_lock: Lock,
) -> Tuple[Path, ConversionResult]:
    """Worker function with enhanced display integration"""

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

    # Perform conversion
    if converter.hw_accel == "cuda":
        with gpu_semaphore:
            result = converter.convert_file(
                input_file,
                progress_callback=None,
                stats_callback=stats_callback,
                cancel_event=cancel_event,
            )
    else:
        result = converter.convert_file(
            input_file,
            progress_callback=None,
            stats_callback=stats_callback,
            cancel_event=cancel_event,
        )

    # Update counts
    with count_lock:
        if result.success:
            completed_count['value'] += 1
        else:
            failed_count['value'] += 1

        display.update_stats(
            completed=completed_count['value'],
            failed=failed_count['value'],
        )

    return input_file, result


def display_update_loop(display, stop_event: Event):
    """Background thread to update display periodically"""
    while not stop_event.is_set():
        try:
            display.display()
            time.sleep(0.5)  # Update every 500ms
        except Exception as e:
            # Silently continue on display errors
            pass


def parse_args():
    parser = argparse.ArgumentParser(description="Batch convert .ts files to .mp4 (Enhanced Display).")
    parser.add_argument("--input-dir", type=Path, help="Directory containing input .ts files.")
    parser.add_argument("--output-dir", type=Path, help="Directory where converted files are written.")
    parser.add_argument("--log-dir", type=Path, help="Directory where logs are stored.")
    parser.add_argument("--ffmpeg-bin", type=str, help="Path to ffmpeg executable.")
    parser.add_argument("--ffprobe-bin", type=str, help="Path to ffprobe executable.")
    parser.add_argument("--sleep-between", type=float, help="Seconds to sleep between conversions.")
    return parser.parse_args()


def main():
    register_signal_handlers()
    args = parse_args()
    Config.apply_overrides(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        ffmpeg_bin=args.ffmpeg_bin,
        ffprobe_bin=args.ffprobe_bin,
        sleep_between=args.sleep_between,
    )

    logger = setup_logging()
    logger.info("TS2MP4 Converter Started (Enhanced Display Mode)")

    files = get_input_files()
    if not files:
        message = f"No {Config.INPUT_EXT} files found in {Config.INPUT_DIR}"
        logger.warning(message)
        print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")
        sys.exit(1)

    try:
        converter = VideoConverter()
    except Exception as e:
        logger.critical(f"Failed to initialize converter: {e}")
        sys.exit(1)

    # Initialize enhanced display
    display = get_display()
    display.update_stats(
        total_files=len(files),
        completed=0,
        failed=0,
        encoder=converter.hw_accel.upper() if converter.hw_accel == "cuda" else "CPU",
    )

    # Determine concurrency
    max_workers = Config.MAX_CONCURRENT_CONVERSIONS
    if converter.hw_accel == "cuda":
        max_workers = min(max_workers, 2)
        logger.info(f"GPU detected: limiting concurrency to {max_workers} workers")
    else:
        logger.info(f"Using CPU encoding with {max_workers} workers")

    # GPU semaphore
    gpu_semaphore = Semaphore(1 if converter.hw_accel == "cuda" else max_workers)

    # Thread-safe counters
    count_lock = Lock()
    completed_count = {'value': 0}
    failed_count = {'value': 0}

    exit_code = 0
    completed_files = []
    failed_files = []

    # Start display update thread
    display_stop = Event()
    display_thread = Thread(target=display_update_loop, args=(display, display_stop), daemon=True)
    display_thread.start()

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(
                    process_file_worker_enhanced,
                    converter,
                    input_file,
                    STOP_EVENT,
                    gpu_semaphore,
                    display,
                    completed_count,
                    failed_count,
                    count_lock,
                ): input_file
                for input_file in files
            }

            # Process completed tasks
            for future in as_completed(future_to_file):
                if STOP_EVENT.is_set():
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

        # Clear screen and show final summary
        display.clear_screen()

    # Print final summary
    print(f"\n{Fore.CYAN}╔{'═' * 78}╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.GREEN}{Style.BRIGHT}CONVERSION COMPLETE{Style.RESET_ALL}" + " " * 58 + f"{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}╠{'═' * 78}╣{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.GREEN}Completed:{Style.RESET_ALL} {len(completed_files):3d} files" + " " * 57 + f"{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.RED}Failed:{Style.RESET_ALL}    {len(failed_files):3d} files" + " " * 57 + f"{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}Total:{Style.RESET_ALL}     {len(files):3d} files" + " " * 57 + f"{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}╚{'═' * 78}╝{Style.RESET_ALL}")

    if STOP_EVENT.is_set():
        print(f"\n{Fore.YELLOW}Processing interrupted by user.{Style.RESET_ALL}")
        logger.warning("Processing interrupted by user.")
    else:
        print(f"\n{Fore.GREEN}All tasks completed successfully!{Style.RESET_ALL}")
        logger.info("Batch conversion finished.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
