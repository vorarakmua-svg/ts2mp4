"""Tests for main.py helpers"""
from pathlib import Path
from threading import Event, Lock
from unittest.mock import MagicMock

import pytest

import main
from converter import ConversionResult


class TestWorkerCount:
    """Test concurrency selection"""

    def test_gpu_uses_configured_workers(self):
        assert main.determine_worker_count("cuda", 2) == 2

    def test_gpu_is_capped_at_two(self):
        assert main.determine_worker_count("cuda", 8) == 2

    def test_cpu_uses_configured_workers(self):
        assert main.determine_worker_count("cpu", 4) == 4

    def test_at_least_one_worker(self):
        assert main.determine_worker_count("cpu", 0) == 1


class TestFinalStatus:
    """Test the end-of-run message"""

    def test_all_succeeded(self):
        message, ok = main.final_status(failed=0, skipped=0, interrupted=False)
        assert ok is True
        assert "successfully" in message

    def test_failures_are_reported(self):
        message, ok = main.final_status(failed=2, skipped=0, interrupted=False)
        assert ok is False
        assert "successfully" not in message
        assert "2" in message

    def test_skipped_files_are_mentioned(self):
        message, ok = main.final_status(failed=0, skipped=3, interrupted=False)
        assert ok is True
        assert "3" in message and "skipped" in message

    def test_interrupted(self):
        message, ok = main.final_status(failed=0, skipped=0, interrupted=True)
        assert ok is False
        assert "interrupted" in message


class TestDescribeEncoder:
    """Test encoder label shown to users (e.g. in dry-run)"""

    def test_gpu(self):
        assert main.describe_encoder("cuda") == "GPU (NVENC)"

    def test_cpu(self):
        assert main.describe_encoder("cpu") == "CPU (libx264)"


class TestParseArgs:
    """Test command-line flags"""

    def test_output_handling_flags_default_to_none(self):
        args = main.parse_args([])
        assert args.delete_originals is None
        assert args.overwrite is None

    def test_keep_originals_and_overwrite(self):
        args = main.parse_args(["--keep-originals", "--overwrite"])
        assert args.delete_originals is False
        assert args.overwrite is True


class TestProcessFileWorker:
    """Test per-file bookkeeping"""

    def _run(self, result):
        converter = MagicMock(hw_accel="cpu")
        converter.convert_file.return_value = result
        counts = {"completed": 0, "failed": 0, "skipped": 0}
        main.process_file_worker(
            converter, Path("video.ts"), Event(), MagicMock(), counts, Lock()
        )
        return counts

    def test_success_counts_as_completed(self):
        assert self._run(ConversionResult(True)) == {"completed": 1, "failed": 0, "skipped": 0}

    def test_failure_counts_as_failed(self):
        assert self._run(ConversionResult(False, error="boom")) == {"completed": 0, "failed": 1, "skipped": 0}

    def test_skip_counts_as_skipped(self):
        result = ConversionResult(False, skipped=True, error="exists")
        assert self._run(result) == {"completed": 0, "failed": 0, "skipped": 1}


class TestModeFlag:
    """Test --mode flag"""

    def test_mode_defaults_to_none(self):
        assert main.parse_args([]).mode is None

    def test_mode_choice(self):
        assert main.parse_args(["--mode", "remux"]).mode == "remux"

    def test_invalid_mode_rejected(self):
        with pytest.raises(SystemExit):
            main.parse_args(["--mode", "bogus"])
