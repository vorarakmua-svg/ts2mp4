"""
Metrics collection and export system for TS2MP4 converter
Tracks conversion statistics and exports to JSON/CSV formats
"""
import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from threading import Lock
import logging

logger = logging.getLogger("TS2MP4")


@dataclass
class ConversionMetric:
    """Single conversion metric record"""
    timestamp: str
    input_file: str
    output_file: Optional[str]
    success: bool
    duration_seconds: float
    input_size_bytes: int
    output_size_bytes: Optional[int]
    encoder: str
    realtime_factor: Optional[float]
    error_message: Optional[str]
    retried_with_cpu: bool
    cancelled: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class MetricsCollector:
    """Collects and exports conversion metrics"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize metrics collector

        Args:
            output_dir: Directory to save metrics files (default: logs/)
        """
        self.metrics: List[ConversionMetric] = []
        self.output_dir = output_dir or Path("logs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self.session_start = datetime.now()

        # Statistics
        self.total_conversions = 0
        self.successful_conversions = 0
        self.failed_conversions = 0
        self.cancelled_conversions = 0
        self.total_processing_time = 0.0
        self.total_input_size = 0
        self.total_output_size = 0

    def record_conversion(
        self,
        input_path: Path,
        output_path: Optional[Path],
        success: bool,
        duration: float,
        encoder: str,
        realtime_factor: Optional[float] = None,
        error: Optional[str] = None,
        retried_with_cpu: bool = False,
        cancelled: bool = False,
    ):
        """
        Record a conversion attempt

        Args:
            input_path: Path to input file
            output_path: Path to output file (if successful)
            success: Whether conversion succeeded
            duration: Time taken in seconds
            encoder: Encoder used (h264_nvenc, libx264, etc.)
            realtime_factor: Speed factor (optional)
            error: Error message if failed (optional)
            retried_with_cpu: Whether this was a CPU retry after GPU failure
            cancelled: Whether conversion was cancelled
        """
        with self._lock:
            # Get file sizes
            input_size = input_path.stat().st_size if input_path.exists() else 0
            output_size = output_path.stat().st_size if output_path and output_path.exists() else None

            # Create metric
            metric = ConversionMetric(
                timestamp=datetime.now().isoformat(),
                input_file=str(input_path),
                output_file=str(output_path) if output_path else None,
                success=success,
                duration_seconds=duration,
                input_size_bytes=input_size,
                output_size_bytes=output_size,
                encoder=encoder,
                realtime_factor=realtime_factor,
                error_message=error,
                retried_with_cpu=retried_with_cpu,
                cancelled=cancelled,
            )

            self.metrics.append(metric)

            # Update statistics
            self.total_conversions += 1
            if success:
                self.successful_conversions += 1
            elif cancelled:
                self.cancelled_conversions += 1
            else:
                self.failed_conversions += 1

            self.total_processing_time += duration
            self.total_input_size += input_size
            if output_size:
                self.total_output_size += output_size

    def export_to_json(self, filename: Optional[str] = None) -> Path:
        """
        Export metrics to JSON file

        Args:
            filename: Custom filename (default: metrics_TIMESTAMP.json)

        Returns:
            Path to exported file
        """
        with self._lock:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"metrics_{timestamp}.json"

            output_path = self.output_dir / filename

            data = {
                "session_info": {
                    "start_time": self.session_start.isoformat(),
                    "export_time": datetime.now().isoformat(),
                    "total_conversions": self.total_conversions,
                    "successful": self.successful_conversions,
                    "failed": self.failed_conversions,
                    "cancelled": self.cancelled_conversions,
                    "total_processing_time_seconds": round(self.total_processing_time, 2),
                    "total_input_size_bytes": self.total_input_size,
                    "total_output_size_bytes": self.total_output_size,
                    "average_processing_time": round(
                        self.total_processing_time / max(self.total_conversions, 1), 2
                    ),
                    "success_rate_percent": round(
                        (self.successful_conversions / max(self.total_conversions, 1)) * 100, 2
                    ),
                },
                "conversions": [m.to_dict() for m in self.metrics]
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Metrics exported to JSON: {output_path}")
            return output_path

    def export_to_csv(self, filename: Optional[str] = None) -> Path:
        """
        Export metrics to CSV file

        Args:
            filename: Custom filename (default: metrics_TIMESTAMP.csv)

        Returns:
            Path to exported file
        """
        with self._lock:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"metrics_{timestamp}.csv"

            output_path = self.output_dir / filename

            if not self.metrics:
                # Create empty CSV with headers
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        'timestamp', 'input_file', 'output_file', 'success',
                        'duration_seconds', 'input_size_bytes', 'output_size_bytes',
                        'encoder', 'realtime_factor', 'error_message',
                        'retried_with_cpu', 'cancelled'
                    ])
                    writer.writeheader()
            else:
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = list(self.metrics[0].to_dict().keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for metric in self.metrics:
                        writer.writerow(metric.to_dict())

            logger.info(f"Metrics exported to CSV: {output_path}")
            return output_path

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics

        Returns:
            Dictionary with summary statistics
        """
        with self._lock:
            return {
                "total_conversions": self.total_conversions,
                "successful": self.successful_conversions,
                "failed": self.failed_conversions,
                "cancelled": self.cancelled_conversions,
                "success_rate_percent": round(
                    (self.successful_conversions / max(self.total_conversions, 1)) * 100, 2
                ),
                "total_processing_time_seconds": round(self.total_processing_time, 2),
                "average_processing_time_seconds": round(
                    self.total_processing_time / max(self.total_conversions, 1), 2
                ),
                "total_input_size_bytes": self.total_input_size,
                "total_output_size_bytes": self.total_output_size,
                "compression_ratio_percent": round(
                    (self.total_output_size / max(self.total_input_size, 1)) * 100, 2
                ) if self.total_input_size > 0 else 0,
            }

    def print_summary(self):
        """Print formatted summary to console"""
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("CONVERSION METRICS SUMMARY")
        print("=" * 60)
        print(f"Total Conversions:     {summary['total_conversions']}")
        print(f"  ✓ Successful:        {summary['successful']}")
        print(f"  ✗ Failed:            {summary['failed']}")
        print(f"  ⊘ Cancelled:         {summary['cancelled']}")
        print(f"Success Rate:          {summary['success_rate_percent']}%")
        print(f"Total Processing Time: {summary['total_processing_time_seconds']:.2f}s")
        print(f"Average Time:          {summary['average_processing_time_seconds']:.2f}s")
        print(f"Total Input Size:      {self._format_size(summary['total_input_size_bytes'])}")
        print(f"Total Output Size:     {self._format_size(summary['total_output_size_bytes'])}")
        print(f"Compression Ratio:     {summary['compression_ratio_percent']:.2f}%")
        print("=" * 60)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self.metrics.clear()
            self.total_conversions = 0
            self.successful_conversions = 0
            self.failed_conversions = 0
            self.cancelled_conversions = 0
            self.total_processing_time = 0.0
            self.total_input_size = 0
            self.total_output_size = 0
            self.session_start = datetime.now()
