"""
Enhanced error handling with helpful suggestions and troubleshooting
Provides user-friendly error messages with actionable solutions
"""
import sys
from colorama import Fore, Style
from typing import Optional


class ErrorCategory:
    """Error categories for better organization"""
    FFMPEG = "ffmpeg"
    FILESYSTEM = "filesystem"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    RESOURCE = "resource"
    GPU = "gpu"
    GENERAL = "general"


ERROR_SOLUTIONS = {
    # FFmpeg errors
    "FFmpeg not found": {
        "category": ErrorCategory.FFMPEG,
        "suggestions": [
            "Install FFmpeg: https://ffmpeg.org/download.html",
            "Add FFmpeg to your system PATH",
            "Or specify FFmpeg location with: --ffmpeg-bin /path/to/ffmpeg",
            "Verify installation: ffmpeg -version"
        ]
    },
    "ffprobe not found": {
        "category": ErrorCategory.FFMPEG,
        "suggestions": [
            "FFprobe usually comes with FFmpeg installation",
            "Add FFprobe to your system PATH",
            "Or specify FFprobe location with: --ffprobe-bin /path/to/ffprobe",
            "Verify installation: ffprobe -version"
        ]
    },
    "FFmpeg process timed out": {
        "category": ErrorCategory.FFMPEG,
        "suggestions": [
            "The input file may be corrupted or very large",
            "Try a smaller test file first",
            "Check if your system has sufficient resources",
            "Consider using CPU encoding if GPU is causing issues"
        ]
    },
    "Validation failed": {
        "category": ErrorCategory.VALIDATION,
        "suggestions": [
            "Output file may be corrupted",
            "Check available disk space",
            "Verify the input file is not corrupted",
            "Try converting with different encoding settings"
        ]
    },

    # Filesystem errors
    "No .ts files found": {
        "category": ErrorCategory.FILESYSTEM,
        "suggestions": [
            "Verify the input directory path",
            "Ensure .ts files are present in the directory",
            "Check file permissions",
            "Use --input-dir to specify the correct directory"
        ]
    },
    "Permission denied": {
        "category": ErrorCategory.FILESYSTEM,
        "suggestions": [
            "Check file and directory permissions",
            "Run with appropriate user privileges",
            "Ensure the output directory is writable",
            "Check if files are locked by another process"
        ]
    },
    "Insufficient disk space": {
        "category": ErrorCategory.RESOURCE,
        "suggestions": [
            "Free up disk space on the output drive",
            "Video files require significant space (often 1-2x input size)",
            "Use a different output directory with more space",
            "Delete temporary or unnecessary files"
        ]
    },
    "File too large": {
        "category": ErrorCategory.VALIDATION,
        "suggestions": [
            "The file exceeds the 50GB limit",
            "Split the file into smaller segments",
            "Process smaller files first",
            "Contact support if you need to process larger files"
        ]
    },

    # GPU errors
    "GPU acceleration failed": {
        "category": ErrorCategory.GPU,
        "suggestions": [
            "Verify NVIDIA GPU drivers are installed and up to date",
            "Check if FFmpeg was compiled with NVENC support",
            "The converter will automatically fallback to CPU encoding",
            "Use --enable-gpu=0 to disable GPU acceleration"
        ]
    },
    "NVENC encoder not found": {
        "category": ErrorCategory.GPU,
        "suggestions": [
            "Your FFmpeg build may not include NVENC support",
            "Download FFmpeg with NVENC: https://ffmpeg.org/download.html",
            "Or install from: https://github.com/BtbN/FFmpeg-Builds/releases",
            "The converter will use CPU encoding instead"
        ]
    },
    "GPU out of memory": {
        "category": ErrorCategory.RESOURCE,
        "suggestions": [
            "Reduce concurrent conversions (use --max-concurrent=1)",
            "Close other GPU-intensive applications",
            "Try CPU encoding instead (--enable-gpu=0)",
            "Process smaller files or lower resolution content"
        ]
    },

    # Configuration errors
    "Invalid configuration": {
        "category": ErrorCategory.CONFIGURATION,
        "suggestions": [
            "Run the configuration wizard: python main.py --wizard",
            "Check your .env file for syntax errors",
            "Verify all paths are absolute and valid",
            "Review the configuration in config.py"
        ]
    },

    # Resource errors
    "System overload": {
        "category": ErrorCategory.RESOURCE,
        "suggestions": [
            "Reduce concurrent conversions",
            "Close other resource-intensive applications",
            "Monitor system resources with the health checker",
            "Add more system RAM or reduce quality settings"
        ]
    },
}


def get_error_message(error: Exception, context: Optional[str] = None) -> str:
    """
    Get enhanced error message with suggestions

    Args:
        error: The exception that occurred
        context: Optional context about where the error occurred

    Returns:
        Formatted error message with suggestions
    """
    error_str = str(error)
    error_type = type(error).__name__

    # Find matching solution
    solution = None
    for key, value in ERROR_SOLUTIONS.items():
        if key.lower() in error_str.lower() or key.lower() in error_type.lower():
            solution = value
            break

    # Build error message
    lines = [
        f"\n{Fore.RED}{Style.BRIGHT}{'═' * 78}{Style.RESET_ALL}",
        f"{Fore.RED}{Style.BRIGHT}ERROR{Style.RESET_ALL}",
        f"{Fore.RED}{Style.BRIGHT}{'═' * 78}{Style.RESET_ALL}\n",
    ]

    if context:
        lines.append(f"{Fore.YELLOW}Context:{Style.RESET_ALL} {context}")

    lines.append(f"{Fore.RED}Error:{Style.RESET_ALL} {error_str}")
    lines.append(f"{Fore.RED}Type:{Style.RESET_ALL} {error_type}\n")

    if solution:
        lines.append(f"{Fore.CYAN}{Style.BRIGHT}💡 SUGGESTIONS{Style.RESET_ALL}")
        lines.append(f"{Fore.CYAN}{'─' * 78}{Style.RESET_ALL}")
        for i, suggestion in enumerate(solution["suggestions"], 1):
            lines.append(f"{Fore.GREEN}{i}.{Style.RESET_ALL} {suggestion}")
        lines.append("")

    lines.extend([
        f"{Fore.CYAN}{'─' * 78}{Style.RESET_ALL}",
        f"{Fore.CYAN}For more help:{Style.RESET_ALL}",
        f"  • Documentation: https://github.com/yourrepo/ts2mp4/docs",
        f"  • Issues: https://github.com/yourrepo/ts2mp4/issues",
        f"  • Run with --help for usage information",
        f"{Fore.RED}{Style.BRIGHT}{'═' * 78}{Style.RESET_ALL}\n",
    ])

    return '\n'.join(lines)


def handle_error(error: Exception, context: Optional[str] = None, exit_code: int = 1):
    """
    Handle error by printing enhanced message and exiting

    Args:
        error: The exception that occurred
        context: Optional context about where the error occurred
        exit_code: Exit code to use (default: 1)
    """
    message = get_error_message(error, context)
    print(message, file=sys.stderr)
    sys.exit(exit_code)


def print_warning(message: str, suggestions: Optional[list] = None):
    """
    Print a formatted warning message

    Args:
        message: Warning message
        suggestions: Optional list of suggestions
    """
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚠ WARNING{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'─' * 78}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

    if suggestions:
        print(f"\n{Fore.CYAN}Suggestions:{Style.RESET_ALL}")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")

    print(f"{Fore.YELLOW}{'─' * 78}{Style.RESET_ALL}\n")


def print_info(message: str, details: Optional[list] = None):
    """
    Print a formatted info message

    Args:
        message: Info message
        details: Optional list of details
    """
    print(f"\n{Fore.CYAN}{Style.BRIGHT}ℹ INFO{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'─' * 78}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{message}{Style.RESET_ALL}")

    if details:
        for detail in details:
            print(f"  • {detail}")

    print(f"{Fore.CYAN}{'─' * 78}{Style.RESET_ALL}\n")


def suggest_common_fixes():
    """Print common troubleshooting steps"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'═' * 78}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}COMMON TROUBLESHOOTING STEPS{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * 78}{Style.RESET_ALL}\n")

    steps = [
        ("Verify FFmpeg Installation", [
            "Run: ffmpeg -version",
            "Run: ffprobe -version",
            "Ensure both commands work"
        ]),
        ("Check File Permissions", [
            "Verify input directory is readable",
            "Verify output directory is writable",
            "Check file ownership and permissions"
        ]),
        ("Verify Disk Space", [
            "Check available space in output directory",
            "Ensure at least 2x input file size is available",
            "Clean up old files if needed"
        ]),
        ("Test Configuration", [
            "Run: python main.py --wizard",
            "Or use: python main.py --dry-run",
            "Verify paths and settings"
        ]),
        ("Check System Resources", [
            "Monitor CPU and memory usage",
            "Close other applications",
            "Reduce concurrent conversions if needed"
        ])
    ]

    for title, items in steps:
        print(f"{Fore.GREEN}{Style.BRIGHT}{title}:{Style.RESET_ALL}")
        for item in items:
            print(f"  • {item}")
        print()

    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * 78}{Style.RESET_ALL}\n")
