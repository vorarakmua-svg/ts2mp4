"""Pytest configuration and shared fixtures"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def input_dir(temp_dir):
    """Create temporary input directory"""
    input_path = temp_dir / "input"
    input_path.mkdir(parents=True, exist_ok=True)
    return input_path


@pytest.fixture
def output_dir(temp_dir):
    """Create temporary output directory"""
    output_path = temp_dir / "output"
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


@pytest.fixture
def log_dir(temp_dir):
    """Create temporary log directory"""
    log_path = temp_dir / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


@pytest.fixture
def sample_ts_file(input_dir):
    """Create a sample .ts file for testing"""
    ts_file = input_dir / "sample.ts"
    # Create a small dummy file with some content
    ts_file.write_bytes(b"SAMPLE_TS_CONTENT" * 1000)
    return ts_file


@pytest.fixture
def mock_ffmpeg_success(mocker):
    """Mock successful FFmpeg execution"""
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = ""
    mock_proc.stderr = "Duration: 00:00:10.00\ntime=00:00:10.00\n"
    return mocker.patch('subprocess.Popen', return_value=mock_proc)


@pytest.fixture
def mock_ffprobe_info(mocker):
    """Mock ffprobe returning valid video info"""
    video_info = {
        "format": {
            "duration": "10.00",
            "size": "1024000"
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080
            },
            {
                "codec_type": "audio",
                "codec_name": "aac"
            }
        ]
    }
    return mocker.patch('validator.VideoValidator.get_video_info', return_value=video_info)
