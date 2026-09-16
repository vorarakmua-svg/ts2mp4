"""
Enhanced visual display for TS2MP4 converter
Provides real-time statistics, resource monitoring, and engaging visual feedback
Professional-grade UI for commercial applications
"""
import re
import time
import unicodedata
import psutil
import sys
from dataclasses import dataclass
from typing import Optional, List
from colorama import Fore, Back, Style, init
from threading import RLock
from datetime import datetime

# Initialize colorama
init(autoreset=True)

# Version information
__version__ = "2.0.0"
__app_name__ = "TS2MP4 Professional Video Converter"

BOX_WIDTH = 80                 # Total columns including the border characters
CONTENT_WIDTH = BOX_WIDTH - 4  # "║ " + content + " ║"

_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _char_width(char: str) -> int:
    """Terminal columns used by a character: 0 for combining marks (e.g. Thai vowels), 2 for wide (CJK)."""
    if unicodedata.combining(char) or unicodedata.category(char) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def visible_width(text: str) -> int:
    """Width of text as displayed in a terminal, ignoring ANSI color codes."""
    return sum(_char_width(char) for char in _ANSI_PATTERN.sub("", text))


def fit_to_width(text: str, width: int) -> str:
    """Pad or truncate (with "...") colored text to exactly `width` terminal columns."""
    text_width = visible_width(text)
    if text_width <= width:
        return text + " " * (width - text_width)

    limit = width - 3
    result, used, pos = [], 0, 0
    while pos < len(text):
        match = _ANSI_PATTERN.match(text, pos)
        if match:
            result.append(match.group())
            pos = match.end()
            continue
        char_width = _char_width(text[pos])
        if used + char_width > limit:
            break
        result.append(text[pos])
        used += char_width
        pos += 1
    return "".join(result) + Style.RESET_ALL + "..." + " " * (limit - used)


@dataclass
class ConversionStats:
    """Real-time conversion statistics"""
    current_file: str = ""
    total_files: int = 0
    completed: int = 0
    failed: int = 0
    current_progress: float = 0.0
    current_speed: str = "0.00x"
    encoder: str = "N/A"
    fps: str = "0"
    bitrate: str = "0 kbits/s"
    elapsed_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_usage: Optional[float] = None


class EnhancedDisplay:
    """Enhanced visual display manager"""

    # Animation frames for spinner
    SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    # Progress bar characters
    PROGRESS_FILLED = '█'
    PROGRESS_EMPTY = '░'
    PROGRESS_PARTIAL = ['▏', '▎', '▍', '▌', '▋', '▊', '▉']

    def __init__(self):
        self.stats = ConversionStats()
        self.lock = RLock()  # Use RLock for reentrant locking
        self.spinner_index = 0
        self.start_time = time.time()

    def clear_screen(self):
        """Clear the console screen"""
        # ANSI escape code to clear screen and move cursor to top
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()

    def get_spinner(self) -> str:
        """Get next spinner frame"""
        frame = self.SPINNER_FRAMES[self.spinner_index]
        self.spinner_index = (self.spinner_index + 1) % len(self.SPINNER_FRAMES)
        return frame

    def create_progress_bar(self, percentage: float, width: int = 40, show_percentage: bool = True) -> str:
        """Create a fancy progress bar with colors"""
        filled_width = int(width * percentage / 100)
        empty_width = width - filled_width

        # Determine color based on progress
        if percentage < 33:
            color = Fore.RED
        elif percentage < 66:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN

        # Create the bar
        bar = color + self.PROGRESS_FILLED * filled_width
        bar += Fore.LIGHTBLACK_EX + self.PROGRESS_EMPTY * empty_width

        if show_percentage:
            bar += f" {color}{percentage:5.1f}%{Style.RESET_ALL}"

        return bar

    def format_time(self, seconds: float) -> str:
        """Format seconds into HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def format_size(self, bytes_size: int) -> str:
        """Format bytes into human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"

    def update_system_stats(self):
        """Update CPU and memory usage"""
        with self.lock:
            # Use interval=None for non-blocking call (returns value since last call)
            self.stats.cpu_usage = psutil.cpu_percent(interval=None)
            self.stats.memory_usage = psutil.virtual_memory().percent

            # Try to get GPU usage (NVIDIA only)
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    self.stats.gpu_usage = gpus[0].load * 100
            except (ImportError, Exception):
                self.stats.gpu_usage = None

    def _border(self, left: str, right: str, color: str = Fore.CYAN) -> str:
        return f"{color}{left}{'═' * (BOX_WIDTH - 2)}{right}{Style.RESET_ALL}"

    def _row(self, content: str, color: str = Fore.CYAN) -> str:
        """One box line, padded or truncated so the right border always lines up"""
        return f"{color}║{Style.RESET_ALL} {fit_to_width(content, CONTENT_WIDTH)}{Style.RESET_ALL} {color}║{Style.RESET_ALL}"

    def _section(self, title: str, rows: List[str]) -> List[str]:
        return [
            self._border("╔", "╗"),
            self._row(title),
            self._border("╠", "╣"),
            *[self._row(row) for row in rows],
            self._border("╚", "╝"),
            "",
        ]

    def render_header(self) -> List[str]:
        """Render the professional header section with branding"""
        color = Fore.CYAN + Style.BRIGHT
        version_line = f"v{__version__}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return [
            self._border("╔", "╗", color),
            self._row(f"{Fore.WHITE}{Style.BRIGHT}{__app_name__.center(CONTENT_WIDTH)}", color),
            self._row(f"{Fore.LIGHTBLACK_EX}{version_line.center(CONTENT_WIDTH)}", color),
            self._border("╚", "╝", color),
            "",
        ]

    def overall_progress(self) -> float:
        """Batch percentage: finished and failed files plus the current file's progress."""
        total = self.stats.total_files
        if total <= 0:
            return 0.0
        done = self.stats.completed + self.stats.failed
        partial = self.stats.current_progress / 100 if done < total else 0.0
        return min(100.0, (done + partial) / total * 100)

    def estimate_remaining(self, elapsed: float, overall_percentage: float) -> str:
        """Estimate time left from the average pace so far."""
        if overall_percentage >= 100:
            return self.format_time(0)
        if overall_percentage <= 0 or elapsed < 3:
            return "Calculating..."
        return self.format_time(elapsed * (100 - overall_percentage) / overall_percentage)

    def render_batch_progress(self) -> List[str]:
        """Render overall batch progress"""
        stats = self.stats
        remaining = max(0, stats.total_files - stats.completed - stats.failed)
        return self._section(
            f"{Fore.YELLOW}{Style.BRIGHT}BATCH PROGRESS",
            [
                self.create_progress_bar(self.overall_progress(), width=60),
                f"{Fore.GREEN}Completed: {stats.completed:3d}{Style.RESET_ALL}  "
                f"{Fore.RED}Failed: {stats.failed:3d}{Style.RESET_ALL}  "
                f"{Fore.CYAN}Remaining: {remaining:3d}{Style.RESET_ALL}  "
                f"{Fore.YELLOW}Total: {stats.total_files:3d}",
            ],
        )

    def render_current_file(self) -> List[str]:
        """Render current file conversion progress"""
        stats = self.stats
        return self._section(
            f"{Fore.MAGENTA}{Style.BRIGHT}{self.get_spinner()} CURRENT FILE",
            [
                f"{Fore.WHITE}{stats.current_file}",
                self.create_progress_bar(stats.current_progress, width=60),
                f"{Fore.YELLOW}Encoder:{Style.RESET_ALL} {stats.encoder:15s} "
                f"{Fore.YELLOW}Speed:{Style.RESET_ALL} {stats.current_speed:7s} "
                f"{Fore.YELLOW}FPS:{Style.RESET_ALL} {stats.fps:5s} "
                f"{Fore.YELLOW}Bitrate:{Style.RESET_ALL} {stats.bitrate}",
            ],
        )

    def render_system_resources(self) -> List[str]:
        """Render system resource usage"""
        def usage_row(label: str, value: float) -> str:
            bar = self.create_progress_bar(value, width=40, show_percentage=False)
            return f"{Fore.YELLOW}{label:7s}{Style.RESET_ALL} {bar}{Style.RESET_ALL} {value:5.1f}%"

        rows = [usage_row("CPU:", self.stats.cpu_usage), usage_row("Memory:", self.stats.memory_usage)]
        if self.stats.gpu_usage is not None:
            rows.append(usage_row("GPU:", self.stats.gpu_usage))
        return self._section(f"{Fore.GREEN}{Style.BRIGHT}SYSTEM RESOURCES", rows)

    def render_time_info(self) -> List[str]:
        """Render time information"""
        elapsed = time.time() - self.start_time
        remaining = self.estimate_remaining(elapsed, self.overall_progress())
        return self._section(
            f"{Fore.BLUE}{Style.BRIGHT}TIME INFORMATION",
            [
                f"{Fore.YELLOW}Elapsed:{Style.RESET_ALL} {self.format_time(elapsed):15s} "
                f"{Fore.YELLOW}Estimated Remaining:{Style.RESET_ALL} {remaining}",
            ],
        )

    def render_full_display(self) -> str:
        """Render the complete display"""
        lines = []

        # Update system stats
        self.update_system_stats()

        # Render all sections
        lines.extend(self.render_header())
        lines.extend(self.render_batch_progress())
        lines.extend(self.render_current_file())
        lines.extend(self.render_system_resources())
        lines.extend(self.render_time_info())

        # Footer
        lines.append(f"{Fore.LIGHTBLACK_EX}Press Ctrl+C to cancel...{Style.RESET_ALL}")

        return "\n".join(lines)

    def update_stats(
        self,
        current_file: Optional[str] = None,
        total_files: Optional[int] = None,
        completed: Optional[int] = None,
        failed: Optional[int] = None,
        current_progress: Optional[float] = None,
        current_speed: Optional[str] = None,
        encoder: Optional[str] = None,
        fps: Optional[str] = None,
        bitrate: Optional[str] = None,
    ):
        """Update statistics (thread-safe)"""
        with self.lock:
            if current_file is not None:
                self.stats.current_file = current_file
            if total_files is not None:
                self.stats.total_files = total_files
            if completed is not None:
                self.stats.completed = completed
            if failed is not None:
                self.stats.failed = failed
            if current_progress is not None:
                self.stats.current_progress = current_progress
            if current_speed is not None:
                self.stats.current_speed = current_speed
            if encoder is not None:
                self.stats.encoder = encoder
            if fps is not None:
                self.stats.fps = fps
            if bitrate is not None:
                self.stats.bitrate = bitrate

    def render_frame(self) -> str:
        """
        Full display as one terminal update that overwrites the previous frame in place:
        cursor home, each line followed by erase-to-end-of-line, then erase anything below.
        Never clears the whole screen, which is what causes flicker.
        """
        with self.lock:
            output = self.render_full_display()
        return "\033[H" + "\n".join(f"{line}\033[K" for line in output.split("\n")) + "\033[J"

    def display(self):
        """Display the current state"""
        sys.stdout.write(self.render_frame())
        sys.stdout.flush()

    def start(self):
        """Begin the live display: clear once and hide the cursor."""
        codes = "\033[2J\033[H"
        if sys.stdout.isatty():
            codes += "\033[?25l"
        sys.stdout.write(codes)
        sys.stdout.flush()

    def stop(self):
        """End the live display and restore the cursor."""
        if sys.stdout.isatty():
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()


# Singleton instance for easy access
_display_instance: Optional[EnhancedDisplay] = None

def get_display() -> EnhancedDisplay:
    """Get or create the display singleton"""
    global _display_instance
    if _display_instance is None:
        _display_instance = EnhancedDisplay()
    return _display_instance
