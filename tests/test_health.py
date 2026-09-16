"""Tests for health.py module"""
from health import HealthMonitor


class TestExportHealthReport:
    """Test where health reports are written"""

    def test_report_is_written_next_to_status_file(self, log_dir, mocker):
        mocker.patch.object(HealthMonitor, 'check_health', return_value={"status": "healthy"})
        monitor = HealthMonitor(log_dir / "health_status.json")

        report_path = monitor.export_health_report()

        assert report_path.parent == log_dir
        assert report_path.exists()
