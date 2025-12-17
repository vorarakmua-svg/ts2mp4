"""Tests for utils.py module"""
import pytest
import logging
from pathlib import Path
from utils import setup_logging, get_input_files, format_size
from config import Config


class TestSetupLogging:
    """Test logging setup functionality"""

    def test_setup_logging_returns_logger(self, temp_dir, monkeypatch):
        """Test that setup_logging returns a logger instance"""
        log_dir = temp_dir / "logs"
        monkeypatch.setattr(Config, 'LOG_DIR', log_dir)

        logger = setup_logging()

        assert logger is not None
        assert logger.name == "TS2MP4"
        assert logger.level == logging.INFO

    def test_setup_logging_creates_log_dir(self, temp_dir, monkeypatch):
        """Test that setup_logging creates log directory"""
        log_dir = temp_dir / "logs"
        monkeypatch.setattr(Config, 'LOG_DIR', log_dir)
        monkeypatch.setattr(Config, 'INPUT_DIR', temp_dir / "input")
        monkeypatch.setattr(Config, 'OUTPUT_DIR', temp_dir / "output")

        setup_logging()

        assert log_dir.exists()

    def test_setup_logging_creates_log_file(self, temp_dir, monkeypatch):
        """Test that setup_logging creates a log file"""
        log_dir = temp_dir / "logs"
        monkeypatch.setattr(Config, 'LOG_DIR', log_dir)
        monkeypatch.setattr(Config, 'INPUT_DIR', temp_dir / "input")
        monkeypatch.setattr(Config, 'OUTPUT_DIR', temp_dir / "output")

        setup_logging()

        log_files = list(log_dir.glob("conversion_*.log"))
        assert len(log_files) >= 1

    def test_setup_logging_no_duplicate_handlers(self, temp_dir, monkeypatch):
        """Test that calling setup_logging multiple times doesn't create duplicate handlers"""
        log_dir = temp_dir / "logs"
        monkeypatch.setattr(Config, 'LOG_DIR', log_dir)
        monkeypatch.setattr(Config, 'INPUT_DIR', temp_dir / "input")
        monkeypatch.setattr(Config, 'OUTPUT_DIR', temp_dir / "output")

        logger1 = setup_logging()
        handler_count_1 = len(logger1.handlers)

        logger2 = setup_logging()
        handler_count_2 = len(logger2.handlers)

        # Should have same number of handlers
        assert handler_count_1 == handler_count_2
        assert handler_count_2 == 2  # File handler + stream handler


class TestGetInputFiles:
    """Test get_input_files functionality"""

    def test_get_input_files_empty_directory(self, temp_dir, monkeypatch):
        """Test getting files from empty directory"""
        input_dir = temp_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Config, 'INPUT_DIR', input_dir)
        monkeypatch.setattr(Config, 'OUTPUT_DIR', temp_dir / "output")
        monkeypatch.setattr(Config, 'LOG_DIR', temp_dir / "logs")
        monkeypatch.setattr(Config, 'INPUT_EXT', '.ts')

        files = get_input_files()

        assert files == []

    def test_get_input_files_with_ts_files(self, temp_dir, monkeypatch):
        """Test getting .ts files from directory"""
        input_dir = temp_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Config, 'INPUT_DIR', input_dir)
        monkeypatch.setattr(Config, 'OUTPUT_DIR', temp_dir / "output")
        monkeypatch.setattr(Config, 'LOG_DIR', temp_dir / "logs")
        monkeypatch.setattr(Config, 'INPUT_EXT', '.ts')

        # Create test .ts files
        (input_dir / "video1.ts").touch()
        (input_dir / "video2.ts").touch()
        (input_dir / "video3.ts").touch()

        files = get_input_files()

        assert len(files) == 3
        assert all(f.suffix == '.ts' for f in files)

    def test_get_input_files_ignores_other_extensions(self, temp_dir, monkeypatch):
        """Test that get_input_files only returns .ts files"""
        input_dir = temp_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(Config, 'INPUT_DIR', input_dir)
        monkeypatch.setattr(Config, 'OUTPUT_DIR', temp_dir / "output")
        monkeypatch.setattr(Config, 'LOG_DIR', temp_dir / "logs")
        monkeypatch.setattr(Config, 'INPUT_EXT', '.ts')

        # Create mixed file types
        (input_dir / "video1.ts").touch()
        (input_dir / "video2.mp4").touch()
        (input_dir / "video3.avi").touch()
        (input_dir / "readme.txt").touch()

        files = get_input_files()

        assert len(files) == 1
        assert files[0].suffix == '.ts'

    def test_get_input_files_creates_directory_if_missing(self, temp_dir, monkeypatch):
        """Test that get_input_files creates input directory if it doesn't exist"""
        input_dir = temp_dir / "input"
        monkeypatch.setattr(Config, 'INPUT_DIR', input_dir)
        monkeypatch.setattr(Config, 'OUTPUT_DIR', temp_dir / "output")
        monkeypatch.setattr(Config, 'LOG_DIR', temp_dir / "logs")

        assert not input_dir.exists()

        get_input_files()

        assert input_dir.exists()


class TestFormatSize:
    """Test format_size utility function"""

    def test_format_size_bytes(self):
        """Test formatting bytes"""
        assert format_size(500) == "500.00 B"
        assert format_size(1023) == "1023.00 B"

    def test_format_size_kilobytes(self):
        """Test formatting kilobytes"""
        assert format_size(1024) == "1.00 KB"
        assert format_size(1536) == "1.50 KB"
        assert format_size(1024 * 500) == "500.00 KB"

    def test_format_size_megabytes(self):
        """Test formatting megabytes"""
        assert format_size(1024 * 1024) == "1.00 MB"
        assert format_size(1024 * 1024 * 5) == "5.00 MB"
        assert format_size(1024 * 1024 * 100) == "100.00 MB"

    def test_format_size_gigabytes(self):
        """Test formatting gigabytes"""
        assert format_size(1024 * 1024 * 1024) == "1.00 GB"
        assert format_size(1024 * 1024 * 1024 * 5) == "5.00 GB"

    def test_format_size_terabytes(self):
        """Test formatting terabytes"""
        assert format_size(1024 * 1024 * 1024 * 1024) == "1.00 TB"
        assert format_size(1024 * 1024 * 1024 * 1024 * 2.5) == "2.50 TB"

    def test_format_size_zero(self):
        """Test formatting zero bytes"""
        assert format_size(0) == "0.00 B"

    def test_format_size_boundary_values(self):
        """Test boundary values between units"""
        # Just under 1 KB
        assert format_size(1023.9) == "1023.90 B"
        # Just under 1 MB
        assert format_size(1024 * 1023.9) == "1023.90 KB"
