"""
Enhanced visual display for TS2MP4 converter
Provides real-time statistics, resource monitoring, and engaging visual feedback
Professional-grade UI for commercial applications
"""
import time
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
    estimated_remaining: str = "Calculating..."
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

    def render_header(self) -> List[str]:
        """Render the professional header section with branding"""
        lines = []

        # Professional title with version and timestamp
        title = f"{__app_name__}"
        version_text = f"v{__version__}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create wider border for professional look
        border_width = 78
        border = "═" * border_width

        # Header with gradient-style borders
        lines.append(f"{Fore.CYAN}{Style.BRIGHT}╔{border}╗{Style.RESET_ALL}")

        # Title line (centered)
        # Total content should be 76 chars (excluding the 2 border spaces)
        title_padding = (76 - len(title)) // 2
        lines.append(
            f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} "
            f"{' ' * title_padding}{Fore.WHITE}{Style.BRIGHT}{title}{Style.RESET_ALL}"
            f"{' ' * (76 - len(title) - title_padding)} "
            f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}"
        )

        # Version and timestamp line
        version_line = f"{version_text}  |  {timestamp}"
        version_padding = (76 - len(version_line)) // 2
        lines.append(
            f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL} "
            f"{' ' * version_padding}{Fore.LIGHTBLACK_EX}{version_line}{Style.RESET_ALL}"
            f"{' ' * (76 - len(version_line) - version_padding)} "
            f"{Fore.CYAN}{Style.BRIGHT}║{Style.RESET_ALL}"
        )

        lines.append(f"{Fore.CYAN}{Style.BRIGHT}╚{border}╝{Style.RESET_ALL}")
        lines.append("")

        return lines

    def render_batch_progress(self) -> List[str]:
        """Render overall batch progress"""
        lines = []

        # Overall progress
        overall_percentage = (self.stats.completed / self.stats.total_files * 100) if self.stats.total_files > 0 else 0

        lines.append(f"{Fore.CYAN}╔{'═' * 78}╗{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}{Style.BRIGHT}BATCH PROGRESS{Style.RESET_ALL}" + " " * 61 + f" {Fore.CYAN}║{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}╠{'═' * 78}╣{Style.RESET_ALL}")

        # Progress bar
        bar = self.create_progress_bar(overall_percentage, width=60)
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {bar}" + " " * 9 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        # Statistics
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.GREEN}Completed: {self.stats.completed:3d}{Style.RESET_ALL}  "
                    f"{Fore.RED}Failed: {self.stats.failed:3d}{Style.RESET_ALL}  "
                    f"{Fore.CYAN}Remaining: {self.stats.total_files - self.stats.completed - self.stats.failed:3d}{Style.RESET_ALL}  "
                    f"{Fore.YELLOW}Total: {self.stats.total_files:3d}{Style.RESET_ALL}" + " " * 15 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        lines.append(f"{Fore.CYAN}╚{'═' * 78}╝{Style.RESET_ALL}")
        lines.append("")

        return lines

    def render_current_file(self) -> List[str]:
        """Render current file conversion progress"""
        lines = []

        spinner = self.get_spinner()

        lines.append(f"{Fore.CYAN}╔{'═' * 78}╗{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.MAGENTA}{Style.BRIGHT}{spinner} CURRENT FILE{Style.RESET_ALL}" + " " * 60 + f" {Fore.CYAN}║{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}╠{'═' * 78}╣{Style.RESET_ALL}")

        # File name (truncate if too long)
        filename = self.stats.current_file
        if len(filename) > 70:
            filename = filename[:67] + "..."
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}{filename}{Style.RESET_ALL}" + " " * (74 - len(filename)) + f" {Fore.CYAN}║{Style.RESET_ALL}")

        # Progress bar for current file
        bar = self.create_progress_bar(self.stats.current_progress, width=60)
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {bar}" + " " * 9 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        # Encoding details
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}Encoder:{Style.RESET_ALL} {self.stats.encoder:15s} "
                    f"{Fore.YELLOW}Speed:{Style.RESET_ALL} {self.stats.current_speed:8s} "
                    f"{Fore.YELLOW}FPS:{Style.RESET_ALL} {self.stats.fps:6s} "
                    f"{Fore.YELLOW}Bitrate:{Style.RESET_ALL} {self.stats.bitrate:12s}" + " " * 2 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        lines.append(f"{Fore.CYAN}╚{'═' * 78}╝{Style.RESET_ALL}")
        lines.append("")

        return lines

    def render_system_resources(self) -> List[str]:
        """Render system resource usage"""
        lines = []

        lines.append(f"{Fore.CYAN}╔{'═' * 78}╗{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.GREEN}{Style.BRIGHT}SYSTEM RESOURCES{Style.RESET_ALL}" + " " * 58 + f" {Fore.CYAN}║{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}╠{'═' * 78}╣{Style.RESET_ALL}")

        # CPU usage
        cpu_bar = self.create_progress_bar(self.stats.cpu_usage, width=40, show_percentage=False)
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}CPU:   {Style.RESET_ALL} {cpu_bar} {self.stats.cpu_usage:5.1f}%" + " " * 22 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        # Memory usage
        mem_bar = self.create_progress_bar(self.stats.memory_usage, width=40, show_percentage=False)
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}Memory:{Style.RESET_ALL} {mem_bar} {self.stats.memory_usage:5.1f}%" + " " * 22 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        # GPU usage (if available)
        if self.stats.gpu_usage is not None:
            gpu_bar = self.create_progress_bar(self.stats.gpu_usage, width=40, show_percentage=False)
            lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}GPU:   {Style.RESET_ALL} {gpu_bar} {self.stats.gpu_usage:5.1f}%" + " " * 22 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        lines.append(f"{Fore.CYAN}╚{'═' * 78}╝{Style.RESET_ALL}")
        lines.append("")

        return lines

    def render_time_info(self) -> List[str]:
        """Render time information"""
        lines = []

        elapsed = time.time() - self.start_time

        lines.append(f"{Fore.CYAN}╔{'═' * 78}╗{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.BLUE}{Style.BRIGHT}TIME INFORMATION{Style.RESET_ALL}" + " " * 59 + f" {Fore.CYAN}║{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}╠{'═' * 78}╣{Style.RESET_ALL}")

        lines.append(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.YELLOW}Elapsed:{Style.RESET_ALL} {self.format_time(elapsed):15s} "
                    f"{Fore.YELLOW}Estimated Remaining:{Style.RESET_ALL} {self.stats.estimated_remaining:15s}" + " " * 15 + f" {Fore.CYAN}║{Style.RESET_ALL}")

        lines.append(f"{Fore.CYAN}╚{'═' * 78}╝{Style.RESET_ALL}")
        lines.append("")

        return lines

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
        estimated_remaining: Optional[str] = None,
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
            if estimated_remaining is not None:
                self.stats.estimated_remaining = estimated_remaining

    def display(self):
        """Display the current state"""
        with self.lock:
            output = self.render_full_display()

        # Clear screen and show new content
        self.clear_screen()
        print(output)
        sys.stdout.flush()


# Singleton instance for easy access
_display_instance: Optional[EnhancedDisplay] = None

def get_display() -> EnhancedDisplay:
    """Get or create the display singleton"""
    global _display_instance
    if _display_instance is None:
        _display_instance = EnhancedDisplay()
    return _display_instance
