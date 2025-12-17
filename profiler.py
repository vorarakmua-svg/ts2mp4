"""
Performance profiling module for TS2MP4 converter
Provides cProfile integration and performance analysis
"""
import cProfile
import pstats
import io
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger("TS2MP4")


class PerformanceProfiler:
    """Performance profiler using cProfile"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize performance profiler

        Args:
            output_dir: Directory to save profile reports (default: logs/)
        """
        self.output_dir = output_dir or Path("logs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profiler = cProfile.Profile()
        self.is_profiling = False
        self.start_time = None
        logger.info("Performance profiler initialized")

    def start(self):
        """Start profiling"""
        if not self.is_profiling:
            self.profiler.enable()
            self.is_profiling = True
            self.start_time = time.time()
            logger.info("Profiling started")

    def stop(self):
        """Stop profiling"""
        if self.is_profiling:
            self.profiler.disable()
            self.is_profiling = False
            elapsed = time.time() - self.start_time if self.start_time else 0
            logger.info(f"Profiling stopped (duration: {elapsed:.2f}s)")

    def get_stats(self, sort_by: str = 'cumulative', limit: int = 50) -> str:
        """
        Get profiling statistics as string

        Args:
            sort_by: Sort key ('cumulative', 'time', 'calls', etc.)
            limit: Number of entries to show

        Returns:
            Formatted statistics string
        """
        if self.is_profiling:
            self.stop()

        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.sort_stats(sort_by)
        stats.print_stats(limit)
        return stream.getvalue()

    def export_stats(self, filename: Optional[str] = None) -> Path:
        """
        Export profiling statistics to file

        Args:
            filename: Custom filename (default: profile_TIMESTAMP.txt)

        Returns:
            Path to exported file
        """
        if self.is_profiling:
            self.stop()

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"profile_{timestamp}.txt"

        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("TS2MP4 PERFORMANCE PROFILE\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Duration: {time.time() - self.start_time:.2f}s\n" if self.start_time else "")
            f.write("\n" + "=" * 80 + "\n")
            f.write("TOP FUNCTIONS BY CUMULATIVE TIME\n")
            f.write("=" * 80 + "\n\n")
            f.write(self.get_stats(sort_by='cumulative', limit=50))
            f.write("\n" + "=" * 80 + "\n")
            f.write("TOP FUNCTIONS BY INTERNAL TIME\n")
            f.write("=" * 80 + "\n\n")
            f.write(self.get_stats(sort_by='time', limit=50))
            f.write("\n" + "=" * 80 + "\n")
            f.write("TOP FUNCTIONS BY CALL COUNT\n")
            f.write("=" * 80 + "\n\n")
            f.write(self.get_stats(sort_by='calls', limit=50))

        logger.info(f"Profile statistics exported to {output_path}")
        return output_path

    def export_binary(self, filename: Optional[str] = None) -> Path:
        """
        Export binary profile data for visualization tools

        Args:
            filename: Custom filename (default: profile_TIMESTAMP.prof)

        Returns:
            Path to exported file
        """
        if self.is_profiling:
            self.stop()

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"profile_{timestamp}.prof"

        output_path = self.output_dir / filename
        self.profiler.dump_stats(str(output_path))

        logger.info(f"Binary profile data exported to {output_path}")
        logger.info(f"Visualize with: python -m snakeviz {output_path}")
        return output_path

    def reset(self):
        """Reset profiler"""
        self.profiler = cProfile.Profile()
        self.is_profiling = False
        self.start_time = None
        logger.info("Profiler reset")


def profile_function(output_dir: Optional[Path] = None):
    """
    Decorator to profile a function

    Args:
        output_dir: Directory to save profile (default: logs/)

    Example:
        @profile_function()
        def my_function():
            # code to profile
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            profiler = PerformanceProfiler(output_dir)
            profiler.start()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                profiler.stop()
                profile_path = profiler.export_stats(
                    filename=f"profile_{func.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                )
                logger.info(f"Function '{func.__name__}' profiled: {profile_path}")

        return wrapper
    return decorator


class PerformanceTimer:
    """Simple performance timer context manager"""

    def __init__(self, name: str = "Operation", log_result: bool = True):
        """
        Initialize timer

        Args:
            name: Name of the operation being timed
            log_result: Whether to log the result
        """
        self.name = name
        self.log_result = log_result
        self.start_time = None
        self.end_time = None
        self.elapsed = None

    def __enter__(self):
        """Start timer"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and optionally log result"""
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time

        if self.log_result:
            logger.info(f"{self.name} completed in {self.elapsed:.2f}s")

        return False  # Don't suppress exceptions

    def __str__(self):
        """String representation"""
        if self.elapsed is not None:
            return f"{self.name}: {self.elapsed:.2f}s"
        return f"{self.name}: (not completed)"


def benchmark_function(func: Callable, *args, iterations: int = 1, **kwargs) -> dict:
    """
    Benchmark a function by running it multiple times

    Args:
        func: Function to benchmark
        *args: Positional arguments to pass to function
        iterations: Number of times to run the function
        **kwargs: Keyword arguments to pass to function

    Returns:
        Dictionary with benchmark results
    """
    times = []

    for i in range(iterations):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        times.append(elapsed)

    return {
        "function": func.__name__,
        "iterations": iterations,
        "times": times,
        "min": min(times),
        "max": max(times),
        "avg": sum(times) / len(times),
        "total": sum(times)
    }
