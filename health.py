"""
Health check and system monitoring for TS2MP4 converter
Provides system resource monitoring and health status reporting
"""
import json
import time
import psutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from threading import Lock

logger = logging.getLogger("TS2MP4")


class HealthMonitor:
    """Monitors system health and provides status information"""

    def __init__(self, status_file: Optional[Path] = None):
        """
        Initialize health monitor

        Args:
            status_file: Path to status file (default: logs/health_status.json)
        """
        self.status_file = status_file or Path("logs/health_status.json")
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

        # Health status
        self.start_time = datetime.now()
        self.is_healthy = True
        self.last_update = datetime.now()
        self.errors = []
        self.warnings = []

        # Thresholds
        self.cpu_threshold = 95.0  # %
        self.memory_threshold = 90.0  # %
        self.disk_threshold = 95.0  # %

        logger.info("Health monitor initialized")

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get current system information

        Returns:
            Dictionary with system metrics
        """
        try:
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Memory info
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024 ** 3)
            memory_total_gb = memory.total / (1024 ** 3)

            # Disk info
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024 ** 3)
            disk_total_gb = disk.total / (1024 ** 3)

            # Process info
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 ** 2)
            process_cpu_percent = process.cpu_percent(interval=0.1)

            # GPU info (if available)
            gpu_info = self._get_gpu_info()

            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "cpu": {
                    "usage_percent": round(cpu_percent, 2),
                    "count": cpu_count,
                    "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True)
                },
                "memory": {
                    "usage_percent": round(memory_percent, 2),
                    "available_gb": round(memory_available_gb, 2),
                    "total_gb": round(memory_total_gb, 2),
                    "used_gb": round((memory.total - memory.available) / (1024 ** 3), 2)
                },
                "disk": {
                    "usage_percent": round(disk_percent, 2),
                    "free_gb": round(disk_free_gb, 2),
                    "total_gb": round(disk_total_gb, 2),
                    "used_gb": round(disk.used / (1024 ** 3), 2)
                },
                "process": {
                    "memory_mb": round(process_memory_mb, 2),
                    "cpu_percent": round(process_cpu_percent, 2),
                    "threads": process.num_threads(),
                    "pid": process.pid
                },
                "gpu": gpu_info
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"error": str(e)}

    def _get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """
        Get GPU information if available

        Returns:
            Dictionary with GPU metrics or None
        """
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                return {
                    "name": gpu.name,
                    "load_percent": round(gpu.load * 100, 2),
                    "memory_used_mb": round(gpu.memoryUsed, 2),
                    "memory_total_mb": round(gpu.memoryTotal, 2),
                    "memory_percent": round((gpu.memoryUsed / gpu.memoryTotal) * 100, 2),
                    "temperature_c": round(gpu.temperature, 2)
                }
        except ImportError:
            # GPUtil not available
            pass
        except Exception as e:
            logger.debug(f"Could not get GPU info: {e}")

        return None

    def check_health(self) -> Dict[str, Any]:
        """
        Perform health check

        Returns:
            Dictionary with health status
        """
        with self._lock:
            self.last_update = datetime.now()
            system_info = self.get_system_info()

            # Check thresholds
            issues = []
            warnings = []

            if "error" not in system_info:
                # Check CPU
                cpu_usage = system_info["cpu"]["usage_percent"]
                if cpu_usage > self.cpu_threshold:
                    issues.append(f"CPU usage critical: {cpu_usage}%")
                elif cpu_usage > self.cpu_threshold * 0.8:
                    warnings.append(f"CPU usage high: {cpu_usage}%")

                # Check memory
                memory_usage = system_info["memory"]["usage_percent"]
                if memory_usage > self.memory_threshold:
                    issues.append(f"Memory usage critical: {memory_usage}%")
                elif memory_usage > self.memory_threshold * 0.8:
                    warnings.append(f"Memory usage high: {memory_usage}%")

                # Check disk
                disk_usage = system_info["disk"]["usage_percent"]
                if disk_usage > self.disk_threshold:
                    issues.append(f"Disk usage critical: {disk_usage}%")
                elif disk_usage > self.disk_threshold * 0.8:
                    warnings.append(f"Disk usage high: {disk_usage}%")

            self.is_healthy = len(issues) == 0
            self.errors = issues
            self.warnings = warnings

            health_status = {
                "status": "healthy" if self.is_healthy else "unhealthy",
                "timestamp": self.last_update.isoformat(),
                "uptime_seconds": (self.last_update - self.start_time).total_seconds(),
                "checks": {
                    "cpu": "ok" if cpu_usage <= self.cpu_threshold else "critical",
                    "memory": "ok" if memory_usage <= self.memory_threshold else "critical",
                    "disk": "ok" if disk_usage <= self.disk_threshold else "critical",
                },
                "issues": issues,
                "warnings": warnings,
                "system": system_info
            }

            # Write to status file
            try:
                self.status_file.write_text(json.dumps(health_status, indent=2))
            except Exception as e:
                logger.error(f"Failed to write health status file: {e}")

            return health_status

    def record_error(self, error: str):
        """Record an error"""
        with self._lock:
            self.errors.append({
                "timestamp": datetime.now().isoformat(),
                "message": error
            })
            self.is_healthy = False
            logger.error(f"Health error recorded: {error}")

    def record_warning(self, warning: str):
        """Record a warning"""
        with self._lock:
            self.warnings.append({
                "timestamp": datetime.now().isoformat(),
                "message": warning
            })
            logger.warning(f"Health warning recorded: {warning}")

    def get_status_summary(self) -> str:
        """
        Get a formatted status summary

        Returns:
            Formatted status string
        """
        health = self.check_health()
        system = health.get("system", {})

        summary = []
        summary.append(f"Status: {health['status'].upper()}")
        summary.append(f"Uptime: {health['uptime_seconds']:.0f}s")

        if "error" not in system:
            summary.append(f"CPU: {system['cpu']['usage_percent']}%")
            summary.append(f"Memory: {system['memory']['usage_percent']}% ({system['memory']['used_gb']:.1f}/{system['memory']['total_gb']:.1f} GB)")
            summary.append(f"Disk: {system['disk']['usage_percent']}% ({system['disk']['used_gb']:.1f}/{system['disk']['total_gb']:.1f} GB)")

            if system.get("gpu"):
                gpu = system["gpu"]
                summary.append(f"GPU: {gpu['load_percent']}% ({gpu['memory_used_mb']:.0f}/{gpu['memory_total_mb']:.0f} MB)")

        if health["issues"]:
            summary.append(f"Issues: {', '.join(health['issues'])}")

        if health["warnings"]:
            summary.append(f"Warnings: {', '.join(health['warnings'])}")

        return " | ".join(summary)

    def export_health_report(self, output_path: Optional[Path] = None) -> Path:
        """
        Export detailed health report

        Args:
            output_path: Custom output path (default: logs/health_report_TIMESTAMP.json)

        Returns:
            Path to exported report
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path("logs") / f"health_report_{timestamp}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        health_data = self.check_health()
        health_data["report_type"] = "detailed_health_report"
        health_data["generated_at"] = datetime.now().isoformat()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(health_data, f, indent=2)

        logger.info(f"Health report exported to {output_path}")
        return output_path
