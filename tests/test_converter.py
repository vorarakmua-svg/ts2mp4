"""Tests for converter.py module"""
import pytest
import subprocess
import time
from pathlib import Path
from threading import Event
from unittest.mock import Mock, MagicMock, patch, call
from converter import VideoConverter, ConversionResult
from config import Config


class TestVideoConverterInit:
    """Test VideoConverter initialization"""

    def test_converter_initialization(self, temp_dir, mocker):
        """Test converter initializes correctly"""
        mocker.patch.object(Config, 'INPUT_DIR', temp_dir / "input")
        mocker.patch.object(Config, 'OUTPUT_DIR', temp_dir / "output")
        mocker.patch.object(Config, 'LOG_DIR', temp_dir / "logs")
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')

        converter = VideoConverter()

        assert converter.hw_accel in ['cpu', 'cuda']

    def test_converter_creates_directories(self, temp_dir, mocker):
        """Test that converter ensures directories exist"""
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        log_dir = temp_dir / "logs"

        mocker.patch.object(Config, 'INPUT_DIR', input_dir)
        mocker.patch.object(Config, 'OUTPUT_DIR', output_dir)
        mocker.patch.object(Config, 'LOG_DIR', log_dir)
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')

        VideoConverter()

        assert input_dir.exists()
        assert output_dir.exists()
        assert log_dir.exists()


class TestDetectHardware:
    """Test hardware detection"""

    def test_detect_hardware_gpu_disabled(self, mocker):
        """Test GPU detection when disabled"""
        mocker.patch.object(Config, 'ENABLE_GPU', False)

        converter = VideoConverter()

        assert converter.hw_accel == 'cpu'

    def test_detect_hardware_gpu_forced(self, mocker):
        """Test GPU detection when forced"""
        mocker.patch.object(Config, 'ENABLE_GPU', True)
        mocker.patch.object(Config, 'FORCE_GPU', True)

        converter = VideoConverter()

        assert converter.hw_accel == 'cuda'

    def test_detect_hardware_nvenc_available(self, mocker):
        """Test GPU detection when NVENC is available"""
        mocker.patch.object(Config, 'ENABLE_GPU', True)
        mocker.patch.object(Config, 'FORCE_GPU', False)

        mock_result = Mock()
        mock_result.stdout = "h264_nvenc encoder available"
        mock_result.stderr = ""

        mocker.patch('subprocess.run', return_value=mock_result)

        converter = VideoConverter()

        assert converter.hw_accel == 'cuda'

    def test_detect_hardware_nvenc_unavailable(self, mocker):
        """Test GPU detection when NVENC is unavailable"""
        mocker.patch.object(Config, 'ENABLE_GPU', True)
        mocker.patch.object(Config, 'FORCE_GPU', False)

        mock_result = Mock()
        mock_result.stdout = "libx264 encoder available"
        mock_result.stderr = ""

        mocker.patch('subprocess.run', return_value=mock_result)

        converter = VideoConverter()

        assert converter.hw_accel == 'cpu'

    def test_detect_hardware_timeout(self, mocker):
        """Test GPU detection timeout handling"""
        mocker.patch.object(Config, 'ENABLE_GPU', True)
        mocker.patch.object(Config, 'FORCE_GPU', False)

        mocker.patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd=[], timeout=10))

        converter = VideoConverter()

        assert converter.hw_accel == 'cpu'

    def test_detect_hardware_ffmpeg_not_found(self, mocker):
        """Test GPU detection when FFmpeg not found"""
        mocker.patch.object(Config, 'ENABLE_GPU', True)
        mocker.patch.object(Config, 'FORCE_GPU', False)

        mocker.patch('subprocess.run', side_effect=FileNotFoundError())

        with pytest.raises(FileNotFoundError):
            VideoConverter()

    def test_detect_hardware_process_error(self, mocker):
        """Test GPU detection with subprocess error"""
        mocker.patch.object(Config, 'ENABLE_GPU', True)
        mocker.patch.object(Config, 'FORCE_GPU', False)

        mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, []))

        converter = VideoConverter()

        assert converter.hw_accel == 'cpu'


class TestValidatePathSafety:
    """Test path safety validation"""

    def test_validate_path_safety_valid_path(self, temp_dir):
        """Test validation of a safe path"""
        safe_path = temp_dir / "video.ts"
        safe_path.touch()

        # Should not raise exception
        VideoConverter._validate_path_safety(safe_path)

    def test_validate_path_safety_dangerous_semicolon(self, temp_dir):
        """Test rejection of path with semicolon"""
        dangerous_path = temp_dir / "video;rm.ts"

        with pytest.raises(ValueError, match="dangerous characters"):
            VideoConverter._validate_path_safety(dangerous_path)

    def test_validate_path_safety_dangerous_ampersand(self, temp_dir):
        """Test rejection of path with ampersand"""
        dangerous_path = temp_dir / "video&test.ts"

        with pytest.raises(ValueError, match="dangerous characters"):
            VideoConverter._validate_path_safety(dangerous_path)

    def test_validate_path_safety_dangerous_pipe(self, temp_dir):
        """Test rejection of path with pipe"""
        dangerous_path = temp_dir / "video|test.ts"

        with pytest.raises(ValueError, match="dangerous characters"):
            VideoConverter._validate_path_safety(dangerous_path)

    def test_validate_path_safety_relative_path(self):
        """Test rejection of relative path"""
        relative_path = Path("../video.ts")

        with pytest.raises(ValueError, match="must be absolute"):
            VideoConverter._validate_path_safety(relative_path)

    @pytest.mark.skipif(not hasattr(Path, 'is_symlink'), reason="Symlinks not supported")
    def test_validate_path_safety_symlink(self, temp_dir):
        """Test rejection of symlink"""
        target = temp_dir / "target.ts"
        target.touch()
        symlink = temp_dir / "link.ts"

        try:
            symlink.symlink_to(target)

            with pytest.raises(ValueError, match="Symlinks not allowed"):
                VideoConverter._validate_path_safety(symlink)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")


class TestValidatePathWithinDirectory:
    """Test path traversal protection"""

    def test_validate_path_within_directory_valid(self, temp_dir):
        """Test validation of path within allowed directory"""
        allowed_dir = temp_dir / "allowed"
        allowed_dir.mkdir()
        valid_path = allowed_dir / "video.ts"

        # Should not raise exception
        VideoConverter._validate_path_within_directory(valid_path, allowed_dir)

    def test_validate_path_within_directory_traversal(self, temp_dir):
        """Test rejection of path traversal attempt"""
        allowed_dir = temp_dir / "allowed"
        allowed_dir.mkdir()
        outside_path = temp_dir / "outside.ts"

        with pytest.raises(ValueError, match="outside allowed directory"):
            VideoConverter._validate_path_within_directory(outside_path, allowed_dir)


class TestValidateFileSize:
    """Test file size validation"""

    def test_validate_file_size_valid(self, temp_dir):
        """Test validation of normal sized file"""
        file_path = temp_dir / "video.ts"
        file_path.write_bytes(b"DATA" * 1000)

        # Should not raise exception
        VideoConverter._validate_file_size(file_path)

    def test_validate_file_size_file_not_found(self, temp_dir):
        """Test validation of non-existent file"""
        file_path = temp_dir / "missing.ts"

        with pytest.raises(FileNotFoundError):
            VideoConverter._validate_file_size(file_path)

    def test_validate_file_size_empty_file(self, temp_dir):
        """Test rejection of empty file"""
        file_path = temp_dir / "empty.ts"
        file_path.touch()

        with pytest.raises(ValueError, match="empty"):
            VideoConverter._validate_file_size(file_path)

    def test_validate_file_size_too_large(self, temp_dir, mocker):
        """Test rejection of file exceeding max size"""
        file_path = temp_dir / "large.ts"
        file_path.write_bytes(b"DATA")

        # Mock stat to return large size
        mock_stat = Mock()
        mock_stat.st_size = 51 * 1024 ** 3  # 51 GB
        mocker.patch.object(Path, 'stat', return_value=mock_stat)

        with pytest.raises(ValueError, match="too large"):
            VideoConverter._validate_file_size(file_path)


class TestCheckDiskSpace:
    """Test disk space checking"""

    def test_check_disk_space_sufficient(self, temp_dir, mocker):
        """Test with sufficient disk space"""
        input_file = temp_dir / "input.ts"
        input_file.write_bytes(b"DATA" * 1000)
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        # Mock disk usage with plenty of space
        mock_usage = Mock()
        mock_usage.free = 100 * 1024 ** 3  # 100 GB free
        mocker.patch('shutil.disk_usage', return_value=mock_usage)

        # Should not raise exception
        VideoConverter._check_disk_space(input_file, output_dir)

    def test_check_disk_space_insufficient(self, temp_dir, mocker):
        """Test with insufficient disk space"""
        input_file = temp_dir / "input.ts"
        input_file.write_bytes(b"DATA" * 1000)
        output_dir = temp_dir / "output"
        output_dir.mkdir()

        # Mock disk usage with minimal space
        mock_usage = Mock()
        mock_usage.free = 100 * 1024  # Only 100 KB free
        mocker.patch('shutil.disk_usage', return_value=mock_usage)

        with pytest.raises(OSError, match="Insufficient disk space"):
            VideoConverter._check_disk_space(input_file, output_dir)


class TestConvertFile:
    """Test file conversion"""

    def test_convert_file_security_validation_fails(self, input_dir, mocker):
        """Test conversion fails on security validation"""
        converter = VideoConverter()
        input_file = input_dir / "test.ts"
        input_file.write_bytes(b"DATA" * 1000)

        # Mock validation to fail
        mocker.patch.object(VideoConverter, '_validate_path_safety', side_effect=ValueError("Unsafe path"))

        result = converter.convert_file(input_file)

        assert result.success is False
        assert "Unsafe path" in result.error

    def test_convert_file_input_not_exists(self, input_dir, mocker):
        """Test conversion fails when input doesn't exist"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()
        input_file = input_dir / "missing.ts"

        result = converter.convert_file(input_file)

        assert result.success is False
        assert "does not exist" in result.error

    def test_convert_file_wrong_extension(self, input_dir, mocker):
        """Test conversion skips wrong file extension"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()
        input_file = input_dir / "video.mp4"
        input_file.write_bytes(b"DATA")

        result = converter.convert_file(input_file)

        assert result.success is False
        assert "non-.ts file" in result.error

    def test_convert_file_cancelled_before_start(self, input_dir, output_dir, mocker):
        """Test conversion cancelled before starting"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        mocker.patch.object(Config, 'INPUT_DIR', input_dir)
        mocker.patch.object(Config, 'OUTPUT_DIR', output_dir)

        converter = VideoConverter()
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)

        cancel_event = Event()
        cancel_event.set()  # Cancel immediately

        # Mock VideoValidator to avoid actual ffprobe calls
        mocker.patch('converter.VideoValidator.get_video_info', return_value={"format": {"duration": "10"}})

        result = converter.convert_file(input_file, cancel_event=cancel_event)

        assert result.success is False
        assert result.cancelled is True


class TestBuildAttemptPlan:
    """Test attempt plan building"""

    def test_build_attempt_plan_cpu_only(self, mocker):
        """Test attempt plan with CPU only"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()

        attempts = converter._build_attempt_plan()

        assert len(attempts) == 1
        label, use_hw, encoder, opts = attempts[0]
        assert use_hw is False
        assert encoder == "libx264"
        assert "CPU" in label

    def test_build_attempt_plan_gpu(self, mocker):
        """Test attempt plan with GPU"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cuda')
        mocker.patch.object(Config, 'GPU_MAX_ATTEMPTS', 2)
        converter = VideoConverter()

        attempts = converter._build_attempt_plan()

        # Should have GPU attempts + CPU fallback
        assert len(attempts) >= 2

        # First attempts should be GPU
        label, use_hw, encoder, opts = attempts[0]
        assert use_hw is True
        assert encoder == "h264_nvenc"
        assert "GPU" in label

        # Last attempt should be CPU
        label, use_hw, encoder, opts = attempts[-1]
        assert use_hw is False
        assert encoder == "libx264"


class TestGetEncodingOptions:
    """Test encoding options generation"""

    def test_get_encoding_options_hardware(self, mocker):
        """Test GPU encoding options"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cuda')
        mocker.patch.object(Config, 'PRESET', 'p5')
        mocker.patch.object(Config, 'CRF_VALUE', 23)

        converter = VideoConverter()
        codec, opts = converter._get_encoding_options(use_hw=True)

        assert codec == "h264_nvenc"
        assert "-c:v" in opts
        assert "h264_nvenc" in opts
        assert "-preset" in opts
        assert "p5" in opts
        assert "-cq:v" in opts
        assert "23" in opts

    def test_get_encoding_options_software(self, mocker):
        """Test CPU encoding options"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        mocker.patch.object(Config, 'CRF_VALUE', 21)

        converter = VideoConverter()
        codec, opts = converter._get_encoding_options(use_hw=False)

        assert codec == "libx264"
        assert "-c:v" in opts
        assert "libx264" in opts
        assert "-crf" in opts
        assert "21" in opts
        assert "-preset" in opts
        assert "medium" in opts


class TestRunFFmpeg:
    """Test FFmpeg execution"""

    def test_run_ffmpeg_success(self, mocker):
        """Test successful FFmpeg execution"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()

        # Mock subprocess
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = iter([
            "Duration: 00:00:10.00\n",
            "time=00:00:05.00 fps=30\n",
            "time=00:00:10.00 fps=30\n",
        ])

        mocker.patch('subprocess.Popen', return_value=mock_proc)

        cmd = ["ffmpeg", "-i", "input.ts", "output.mp4"]
        success, cancelled, progress, last_line = converter._run_ffmpeg(
            cmd,
            progress_callback=None,
            cancel_event=None,
            duration_hint=10.0
        )

        assert success is True
        assert cancelled is False

    def test_run_ffmpeg_timeout(self, mocker):
        """Test FFmpeg timeout handling"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()

        # Mock process that never completes
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = None

        mock_proc.wait.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=10)

        mocker.patch('subprocess.Popen', return_value=mock_proc)

        cmd = ["ffmpeg", "-i", "input.ts", "output.mp4"]
        success, cancelled, progress, last_line = converter._run_ffmpeg(
            cmd,
            progress_callback=None,
            cancel_event=None,
            duration_hint=1.0  # Short duration = short timeout
        )

        assert success is False
        assert "timed out" in last_line.lower()

    def test_run_ffmpeg_progress_callback(self, mocker):
        """Test FFmpeg with progress callback"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = iter([
            "Duration: 00:00:10.00\n",
            "time=00:00:05.00\n",  # 50% progress
            "time=00:00:10.00\n",  # 100% progress
        ])

        mocker.patch('subprocess.Popen', return_value=mock_proc)

        progress_calls = []

        def progress_callback(delta):
            progress_calls.append(delta)

        cmd = ["ffmpeg", "-i", "input.ts", "output.mp4"]
        success, cancelled, progress, last_line = converter._run_ffmpeg(
            cmd,
            progress_callback=progress_callback,
            cancel_event=None,
            duration_hint=10.0
        )

        assert success is True
        assert len(progress_calls) > 0

    def test_run_ffmpeg_stats_callback(self, mocker):
        """Test FFmpeg with stats callback"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = iter([
            "Duration: 00:00:10.00\n",
            "time=00:00:05.00 fps=30 bitrate=5000.0kbits/s speed=2.0x\n",
        ])

        mocker.patch('subprocess.Popen', return_value=mock_proc)

        stats_calls = []

        def stats_callback(stats):
            stats_calls.append(stats)

        cmd = ["ffmpeg", "-i", "input.ts", "output.mp4"]
        success, cancelled, progress, last_line = converter._run_ffmpeg(
            cmd,
            progress_callback=None,
            stats_callback=stats_callback,
            cancel_event=None,
            duration_hint=10.0
        )

        assert success is True
        assert len(stats_calls) > 0
        # Check that stats contain expected keys
        if stats_calls:
            assert any('progress' in s for s in stats_calls)


class TestSafeUnlink:
    """Test safe file deletion"""

    def test_safe_unlink_existing_file(self, temp_dir):
        """Test safe deletion of existing file"""
        file_path = temp_dir / "test.tmp"
        file_path.touch()

        assert file_path.exists()

        VideoConverter._safe_unlink(file_path)

        assert not file_path.exists()

    def test_safe_unlink_nonexistent_file(self, temp_dir):
        """Test safe deletion of non-existent file (should not error)"""
        file_path = temp_dir / "missing.tmp"

        # Should not raise exception
        VideoConverter._safe_unlink(file_path)


class TestConversionResult:
    """Test ConversionResult dataclass"""

    def test_conversion_result_success(self):
        """Test successful conversion result"""
        result = ConversionResult(
            success=True,
            output_path=Path("/output/video.mp4"),
            elapsed_seconds=10.5,
            source_duration=100.0,
            realtime_factor=9.52,
            encoder="h264_nvenc",
            retried_with_cpu=False,
            cancelled=False,
            error=None
        )

        assert result.success is True
        assert result.output_path == Path("/output/video.mp4")
        assert result.elapsed_seconds == 10.5
        assert result.encoder == "h264_nvenc"
        assert result.cancelled is False

    def test_conversion_result_failure(self):
        """Test failed conversion result"""
        result = ConversionResult(
            success=False,
            error="FFmpeg failed"
        )

        assert result.success is False
        assert result.error == "FFmpeg failed"
        assert result.output_path is None
        assert result.cancelled is False
