"""Tests for validator.py module"""
import pytest
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from validator import VideoValidator
from config import Config


class TestGetVideoInfo:
    """Test VideoValidator.get_video_info method"""

    def test_get_video_info_success(self, sample_ts_file, mocker):
        """Test successful video info retrieval"""
        mock_result = Mock()
        mock_result.stdout = json.dumps({
            "format": {"duration": "10.5", "size": "1024000"},
            "streams": [{"codec_type": "video", "codec_name": "h264"}]
        })

        mocker.patch('subprocess.run', return_value=mock_result)

        info = VideoValidator.get_video_info(sample_ts_file)

        assert info is not None
        assert "format" in info
        assert "streams" in info
        assert info["format"]["duration"] == "10.5"

    def test_get_video_info_timeout(self, sample_ts_file, mocker):
        """Test timeout handling in video info retrieval"""
        mocker.patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd=[], timeout=30))

        info = VideoValidator.get_video_info(sample_ts_file)

        assert info is None

    def test_get_video_info_process_error(self, sample_ts_file, mocker):
        """Test handling of subprocess error"""
        mocker.patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, []))

        info = VideoValidator.get_video_info(sample_ts_file)

        assert info is None

    def test_get_video_info_general_exception(self, sample_ts_file, mocker):
        """Test handling of general exceptions"""
        mocker.patch('subprocess.run', side_effect=Exception("Unexpected error"))

        info = VideoValidator.get_video_info(sample_ts_file)

        assert info is None

    def test_get_video_info_invalid_json(self, sample_ts_file, mocker):
        """Test handling of invalid JSON response"""
        mock_result = Mock()
        mock_result.stdout = "INVALID JSON"

        mocker.patch('subprocess.run', return_value=mock_result)

        with pytest.raises(json.JSONDecodeError):
            VideoValidator.get_video_info(sample_ts_file)

    def test_get_video_info_calls_ffprobe_with_correct_args(self, sample_ts_file, mocker):
        """Test that ffprobe is called with correct arguments"""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value.stdout = json.dumps({"format": {}, "streams": []})

        VideoValidator.get_video_info(sample_ts_file)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]

        assert Config.FFPROBE_BIN in call_args
        assert "-v" in call_args
        assert "quiet" in call_args
        assert "-print_format" in call_args
        assert "json" in call_args
        assert str(sample_ts_file) in call_args


class TestExtractDuration:
    """Test VideoValidator._extract_duration method"""

    def test_extract_duration_valid_metadata(self):
        """Test extracting duration from valid metadata"""
        metadata = {"format": {"duration": "123.45"}}

        duration = VideoValidator._extract_duration(metadata)

        assert duration == 123.45

    def test_extract_duration_none_metadata(self):
        """Test extracting duration from None metadata"""
        duration = VideoValidator._extract_duration(None)

        assert duration is None

    def test_extract_duration_missing_format(self):
        """Test extracting duration when format key is missing"""
        metadata = {"streams": []}

        duration = VideoValidator._extract_duration(metadata)

        assert duration is None

    def test_extract_duration_missing_duration_key(self):
        """Test extracting duration when duration key is missing"""
        metadata = {"format": {"size": "1024000"}}

        duration = VideoValidator._extract_duration(metadata)

        assert duration is None

    def test_extract_duration_invalid_value(self):
        """Test extracting duration with non-numeric value"""
        metadata = {"format": {"duration": "invalid"}}

        duration = VideoValidator._extract_duration(metadata)

        assert duration is None

    def test_extract_duration_zero(self):
        """Test extracting zero duration"""
        metadata = {"format": {"duration": "0"}}

        duration = VideoValidator._extract_duration(metadata)

        assert duration == 0.0


class TestHasVideoStream:
    """Test VideoValidator._has_video_stream method"""

    def test_has_video_stream_with_video(self):
        """Test detecting video stream when present"""
        metadata = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"}
            ]
        }

        has_video = VideoValidator._has_video_stream(metadata)

        assert has_video is True

    def test_has_video_stream_without_video(self):
        """Test detecting video stream when absent"""
        metadata = {
            "streams": [
                {"codec_type": "audio", "codec_name": "aac"}
            ]
        }

        has_video = VideoValidator._has_video_stream(metadata)

        assert has_video is False

    def test_has_video_stream_none_metadata(self):
        """Test with None metadata"""
        has_video = VideoValidator._has_video_stream(None)

        assert has_video is False

    def test_has_video_stream_missing_streams(self):
        """Test with missing streams key"""
        metadata = {"format": {}}

        has_video = VideoValidator._has_video_stream(metadata)

        assert has_video is False

    def test_has_video_stream_empty_streams(self):
        """Test with empty streams list"""
        metadata = {"streams": []}

        has_video = VideoValidator._has_video_stream(metadata)

        assert has_video is False

    def test_has_video_stream_none_stream_entry(self):
        """Test with None entry in streams"""
        metadata = {"streams": [None, {"codec_type": "audio"}]}

        has_video = VideoValidator._has_video_stream(metadata)

        assert has_video is False


class TestValidateConversion:
    """Test VideoValidator.validate_conversion method"""

    def test_validate_conversion_success(self, input_dir, output_dir, mocker):
        """Test successful validation"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        # Create files
        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.write_bytes(b"OUTPUT_DATA" * 1000)

        # Mock metadata
        metadata = {
            "format": {"duration": "10.0"},
            "streams": [{"codec_type": "video"}]
        }

        mocker.patch.object(VideoValidator, 'get_video_info', return_value=metadata)

        result = VideoValidator.validate_conversion(input_file, output_file)

        assert result is True

    def test_validate_conversion_output_missing(self, input_dir, output_dir):
        """Test validation failure when output file doesn't exist"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        # output_file intentionally not created

        result = VideoValidator.validate_conversion(input_file, output_file)

        assert result is False

    def test_validate_conversion_output_empty(self, input_dir, output_dir):
        """Test validation failure when output file is empty"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.touch()  # Create empty file

        result = VideoValidator.validate_conversion(input_file, output_file)

        assert result is False

    def test_validate_conversion_duration_mismatch(self, input_dir, output_dir, mocker):
        """Test validation failure on duration mismatch"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.write_bytes(b"OUTPUT_DATA" * 1000)

        # Mock different durations
        input_metadata = {
            "format": {"duration": "100.0"},
            "streams": [{"codec_type": "video"}]
        }
        output_metadata = {
            "format": {"duration": "50.0"},  # 50% different
            "streams": [{"codec_type": "video"}]
        }

        mocker.patch.object(
            VideoValidator,
            'get_video_info',
            side_effect=[input_metadata, output_metadata]
        )

        result = VideoValidator.validate_conversion(
            input_file,
            output_file,
            duration_tolerance_pct=1.0  # Only 1% tolerance
        )

        assert result is False

    def test_validate_conversion_no_video_stream(self, input_dir, output_dir, mocker):
        """Test validation failure when no video stream found"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.write_bytes(b"OUTPUT_DATA" * 1000)

        # Mock metadata without video stream
        metadata = {
            "format": {"duration": "10.0"},
            "streams": [{"codec_type": "audio"}]  # Only audio
        }

        mocker.patch.object(VideoValidator, 'get_video_info', return_value=metadata)

        result = VideoValidator.validate_conversion(input_file, output_file)

        assert result is False

    def test_validate_conversion_metadata_retrieval_failed(self, input_dir, output_dir, mocker):
        """Test validation failure when metadata retrieval fails"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.write_bytes(b"OUTPUT_DATA" * 1000)

        mocker.patch.object(VideoValidator, 'get_video_info', return_value=None)

        result = VideoValidator.validate_conversion(input_file, output_file)

        assert result is False

    def test_validate_conversion_with_provided_metadata(self, input_dir, output_dir):
        """Test validation with pre-provided metadata"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.write_bytes(b"OUTPUT_DATA" * 1000)

        input_info = {
            "format": {"duration": "10.0"},
            "streams": [{"codec_type": "video"}]
        }
        output_info = {
            "format": {"duration": "10.05"},  # Within tolerance
            "streams": [{"codec_type": "video"}]
        }

        result = VideoValidator.validate_conversion(
            input_file,
            output_file,
            input_info=input_info,
            output_info=output_info
        )

        assert result is True

    def test_validate_conversion_missing_durations_logs_warning(self, input_dir, output_dir, mocker, caplog):
        """Test that missing durations log a warning but don't fail validation"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.write_bytes(b"OUTPUT_DATA" * 1000)

        # Mock metadata without durations
        metadata = {
            "format": {},  # No duration
            "streams": [{"codec_type": "video"}]
        }

        mocker.patch.object(VideoValidator, 'get_video_info', return_value=metadata)

        result = VideoValidator.validate_conversion(input_file, output_file)

        # Should still pass (only video stream check is mandatory)
        assert result is True

    def test_validate_conversion_custom_tolerance(self, input_dir, output_dir, mocker):
        """Test validation with custom duration tolerance"""
        input_file = input_dir / "input.ts"
        output_file = output_dir / "output.mp4"

        input_file.write_bytes(b"INPUT_DATA" * 1000)
        output_file.write_bytes(b"OUTPUT_DATA" * 1000)

        input_metadata = {
            "format": {"duration": "100.0"},
            "streams": [{"codec_type": "video"}]
        }
        output_metadata = {
            "format": {"duration": "104.0"},  # 4% different
            "streams": [{"codec_type": "video"}]
        }

        mocker.patch.object(
            VideoValidator,
            'get_video_info',
            side_effect=[input_metadata, output_metadata]
        )

        # Should fail with 1% tolerance
        result_strict = VideoValidator.validate_conversion(
            input_file,
            output_file,
            duration_tolerance_pct=1.0
        )
        assert result_strict is False

        # Reset mock
        mocker.patch.object(
            VideoValidator,
            'get_video_info',
            side_effect=[input_metadata, output_metadata]
        )

        # Should pass with 5% tolerance
        result_lenient = VideoValidator.validate_conversion(
            input_file,
            output_file,
            duration_tolerance_pct=5.0
        )
        assert result_lenient is True
