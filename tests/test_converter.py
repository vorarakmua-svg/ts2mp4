"""Tests for converter.py module"""
import io
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


@pytest.fixture
def fake_successful_ffmpeg(mocker):
    """Make conversions succeed without FFmpeg: write the output file and pass validation"""
    def run_ffmpeg(self, cmd, **kwargs):
        Path(cmd[-1]).write_bytes(b"CONVERTED")
        return True, False, 100.0, None

    mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
    mocker.patch.object(VideoConverter, '_check_disk_space')
    mocker.patch('converter.VideoValidator.get_video_info', return_value={"format": {"duration": "10"}})
    mocker.patch('converter.VideoValidator.validate_conversion', return_value=True)
    return mocker.patch.object(VideoConverter, '_run_ffmpeg', autospec=True, side_effect=run_ffmpeg)


class TestConvertFileOutputHandling:
    """Test what happens to originals and existing outputs"""

    def test_success_deletes_original_by_default(self, input_dir, output_dir, fake_successful_ffmpeg):
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)

        result = VideoConverter().convert_file(input_file)

        assert result.success is True
        assert (output_dir / "video.mp4").read_bytes() == b"CONVERTED"
        assert not input_file.exists()

    def test_success_keeps_original_when_configured(self, input_dir, output_dir, fake_successful_ffmpeg, monkeypatch):
        monkeypatch.setattr(Config, 'DELETE_ORIGINALS', False, raising=False)
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)

        result = VideoConverter().convert_file(input_file)

        assert result.success is True
        assert (output_dir / "video.mp4").exists()
        assert input_file.exists()

    def test_existing_output_is_skipped(self, input_dir, output_dir, fake_successful_ffmpeg):
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)
        existing = output_dir / "video.mp4"
        existing.write_bytes(b"EXISTING")

        result = VideoConverter().convert_file(input_file)

        assert result.success is False
        assert result.skipped is True
        assert existing.read_bytes() == b"EXISTING"
        assert input_file.exists()
        fake_successful_ffmpeg.assert_not_called()

    def test_existing_output_is_overwritten_when_configured(self, input_dir, output_dir, fake_successful_ffmpeg, monkeypatch):
        monkeypatch.setattr(Config, 'OVERWRITE_EXISTING', True, raising=False)
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)
        existing = output_dir / "video.mp4"
        existing.write_bytes(b"EXISTING")

        result = VideoConverter().convert_file(input_file)

        assert result.success is True
        assert existing.read_bytes() == b"CONVERTED"


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

    def test_convert_file_input_is_directory(self, input_dir, mocker):
        """Test conversion fails with a clear message when input is a directory"""
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        converter = VideoConverter()
        input_path = input_dir / "folder.ts"
        input_path.mkdir()

        result = converter.convert_file(input_path)

        assert result.success is False
        assert "not a file" in result.error

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


def probe_info(video="h264", *audio):
    """Build ffprobe-style metadata with the given codecs"""
    streams = [{"codec_type": "video", "codec_name": video}] if video else []
    streams += [{"codec_type": "audio", "codec_name": codec} for codec in audio]
    return {"format": {"duration": "10"}, "streams": streams}


def value_after(opts, flag):
    return opts[opts.index(flag) + 1]


class TestRemuxPlan:
    """Test choosing stream copy (remux) versus re-encoding"""

    @pytest.fixture
    def cpu_converter(self, mocker):
        mocker.patch.object(VideoConverter, '_detect_hardware', return_value='cpu')
        return VideoConverter()

    def test_default_mode_is_auto(self):
        assert Config.MODE == "auto"

    def test_h264_aac_is_remuxed_first_then_encoded(self, cpu_converter):
        attempts = cpu_converter._build_attempt_plan(probe_info("h264", "aac"))

        label, use_hw, encoder, opts = attempts[0]
        assert encoder == "copy"
        assert value_after(opts, "-c:v") == "copy"
        assert value_after(opts, "-c:a") == "copy"
        assert "+faststart" in opts
        assert attempts[-1][2] == "libx264"

    def test_remux_maps_only_video_and_audio(self, cpu_converter):
        _, _, _, opts = cpu_converter._build_attempt_plan(probe_info("h264", "aac"))[0]

        maps = [opts[i + 1] for i, flag in enumerate(opts) if flag == "-map"]
        assert maps == ["0:v:0", "0:a?"]

    def test_incompatible_audio_is_converted_while_video_is_copied(self, cpu_converter):
        _, _, encoder, opts = cpu_converter._build_attempt_plan(probe_info("h264", "aac", "mp2"))[0]

        assert encoder == "copy"
        assert value_after(opts, "-c:v") == "copy"
        assert value_after(opts, "-c:a") == "aac"

    def test_hevc_is_tagged_for_apple_players(self, cpu_converter):
        _, _, encoder, opts = cpu_converter._build_attempt_plan(probe_info("hevc", "aac"))[0]

        assert encoder == "copy"
        assert value_after(opts, "-tag:v") == "hvc1"

    def test_unsupported_video_codec_is_encoded(self, cpu_converter):
        attempts = cpu_converter._build_attempt_plan(probe_info("mpeg2video", "mp2"))

        assert [a[2] for a in attempts] == ["libx264"]

    def test_missing_metadata_is_encoded(self, cpu_converter):
        attempts = cpu_converter._build_attempt_plan(None)

        assert [a[2] for a in attempts] == ["libx264"]

    def test_encode_mode_never_remuxes(self, cpu_converter, monkeypatch):
        monkeypatch.setattr(Config, 'MODE', "encode")

        attempts = cpu_converter._build_attempt_plan(probe_info("h264", "aac"))

        assert [a[2] for a in attempts] == ["libx264"]

    def test_remux_mode_never_encodes(self, cpu_converter, monkeypatch):
        monkeypatch.setattr(Config, 'MODE', "remux")

        attempts = cpu_converter._build_attempt_plan(probe_info("h264", "aac"))

        assert [a[2] for a in attempts] == ["copy"]

    def test_describe_plan(self, cpu_converter, monkeypatch):
        assert cpu_converter.describe_plan(probe_info("h264", "aac")) == "remux (stream copy)"
        assert cpu_converter.describe_plan(probe_info("mpeg2video", "mp2")) == "re-encode using CPU (libx264)"
        monkeypatch.setattr(Config, 'MODE', "remux")
        assert cpu_converter.describe_plan(probe_info("mpeg2video")) is None


class TestRemuxConversion:
    """Test convert_file behavior around remuxing"""

    def test_failed_remux_falls_back_to_encoding(self, input_dir, output_dir, fake_successful_ffmpeg, mocker):
        mocker.patch('converter.VideoValidator.get_video_info', return_value=probe_info("h264", "aac"))
        def run_ffmpeg(self, cmd, **kwargs):
            if "copy" in cmd:
                return False, False, 0.0, "Non-monotonic DTS"
            Path(cmd[-1]).write_bytes(b"ENCODED")
            return True, False, 100.0, None
        fake_successful_ffmpeg.side_effect = run_ffmpeg
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)

        result = VideoConverter().convert_file(input_file)

        assert result.success is True
        assert result.encoder == "libx264"
        assert (output_dir / "video.mp4").read_bytes() == b"ENCODED"

    def test_remux_success_reports_copy_encoder(self, input_dir, fake_successful_ffmpeg, mocker):
        mocker.patch('converter.VideoValidator.get_video_info', return_value=probe_info("h264", "aac"))
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)

        result = VideoConverter().convert_file(input_file)

        assert result.success is True
        assert result.encoder == "copy"
        assert fake_successful_ffmpeg.call_count == 1

    def test_remux_mode_with_unsupported_codec_fails_clearly(self, input_dir, fake_successful_ffmpeg, mocker, monkeypatch):
        monkeypatch.setattr(Config, 'MODE', "remux")
        mocker.patch('converter.VideoValidator.get_video_info', return_value=probe_info("mpeg2video", "mp2"))
        input_file = input_dir / "video.ts"
        input_file.write_bytes(b"DATA" * 1000)

        result = VideoConverter().convert_file(input_file)

        assert result.success is False
        assert "cannot be remuxed" in result.error
        assert input_file.exists()
        fake_successful_ffmpeg.assert_not_called()


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
        mock_proc.stderr = io.StringIO("".join([
            "Duration: 00:00:10.00\n",
            "time=00:00:05.00 fps=30\n",
            "time=00:00:10.00 fps=30\n",
        ]))

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
        mock_proc.stderr = io.StringIO("".join([
            "Duration: 00:00:10.00\n",
            "time=00:00:05.00\n",  # 50% progress
            "time=00:00:10.00\n",  # 100% progress
        ]))

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
        mock_proc.stderr = io.StringIO("".join([
            "Duration: 00:00:10.00\n",
            "time=00:00:05.00 fps=30 bitrate=5000.0kbits/s speed=2.0x\n",
        ]))

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
