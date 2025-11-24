import argparse
import sys
import time
import signal
from pathlib import Path
from threading import Event
from colorama import Fore, Style
from tqdm import tqdm
from config import Config
from utils import setup_logging, get_input_files
from converter import VideoConverter

STOP_EVENT = Event()


def signal_handler(signum, frame):
    if not STOP_EVENT.is_set():
        print(f"\n\n{Fore.YELLOW}[!] Stop requested. Finishing current file and exiting...{Style.RESET_ALL}")
    STOP_EVENT.set()


def register_signal_handlers():
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, signal_handler)
        except (ValueError, AttributeError):
            # SIGTERM is not supported on some Windows environments
            pass


def parse_args():
    parser = argparse.ArgumentParser(description="Batch convert .ts files to .mp4.")
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
    logger.info("TS2MP4 Converter Started")

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

    exit_code = 0

    with tqdm(total=len(files), desc="Total Progress", unit="file") as pbar_total:
        for index, input_file in enumerate(files):
            if STOP_EVENT.is_set():
                break

            with tqdm(total=100, desc=f"Converting {input_file.name}", unit="%", leave=False) as pbar_file:

                def update_progress(delta):
                    pbar_file.update(delta)
                    pbar_file.refresh()

                result = converter.convert_file(
                    input_file,
                    progress_callback=update_progress,
                    cancel_event=STOP_EVENT,
                )

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
                pbar_total.write(f"{Fore.GREEN}[+] Successfully converted: {input_file.name}{Style.RESET_ALL}")
            else:
                exit_code = exit_code or (130 if result.cancelled else 1)
                reason = result.error or "Unknown error"
                if result.cancelled:
                    pbar_total.write(f"{Fore.YELLOW}[!] Cancelled: {input_file.name} ({reason}){Style.RESET_ALL}")
                    break
                pbar_total.write(f"{Fore.RED}[-] Failed to convert: {input_file.name} ({reason}){Style.RESET_ALL}")
                logger.error("Failed to convert %s: %s", input_file.name, reason)

            pbar_total.update(1)

            if STOP_EVENT.is_set():
                break

            if index < len(files) - 1 and Config.SLEEP_BETWEEN_FILES > 0:
                time.sleep(Config.SLEEP_BETWEEN_FILES)

    if STOP_EVENT.is_set():
        print(f"\n{Fore.YELLOW}Processing interrupted by user.{Style.RESET_ALL}")
        logger.warning("Processing interrupted by user.")
    else:
        print(f"\n{Fore.GREEN}All tasks completed.{Style.RESET_ALL}")
        logger.info("Batch conversion finished.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
