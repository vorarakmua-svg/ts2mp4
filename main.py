import sys
import time
import signal
import logging
from tqdm import tqdm
from config import Config
from utils import setup_logging, get_input_files
from converter import VideoConverter

# Global flag for graceful shutdown
STOP_REQUESTED = False

def signal_handler(signum, frame):
    global STOP_REQUESTED
    print("\n\n[!] Stop requested. Finishing current file and exiting...")
    STOP_REQUESTED = True

def main():
    # Setup signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Setup logging
    logger = setup_logging()
    logger.info("TS2MP4 Converter Started")

    # Check for input files
    files = get_input_files()
    if not files:
        logger.warning(f"No .ts files found in {Config.INPUT_DIR}")
        print(f"No .ts files found in {Config.INPUT_DIR}")
        return

    print(f"Found {len(files)} files to convert.")
    logger.info(f"Found {len(files)} files.")

    # Initialize converter
    try:
        converter = VideoConverter()
    except Exception as e:
        logger.critical(f"Failed to initialize converter: {e}")
        return

    # Overall progress bar
    with tqdm(total=len(files), desc="Total Progress", unit="file") as pbar_total:
        for i, input_file in enumerate(files):
            if STOP_REQUESTED:
                break

            # Create a progress bar for the current file
            # We'll pass a callback to update this bar
            with tqdm(total=100, desc=f"Converting {input_file.name}", unit="%", leave=False) as pbar_file:
                
                def update_progress(percent):
                    pbar_file.n = percent
                    pbar_file.refresh()

                success = converter.convert_file(input_file, progress_callback=update_progress)
            
            if success:
                pbar_total.write(f"[+] Successfully converted: {input_file.name}")
            else:
                pbar_total.write(f"[-] Failed to convert: {input_file.name}")
            
            pbar_total.update(1)

    logger.info("Batch conversion finished.")
    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()
