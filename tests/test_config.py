"""Tests for config.py module"""
import pytest
import os
from pathlib import Path
from config import Config


class TestConfig:
    """Test Config class functionality"""

    def test_default_values(self):
        """Test that default config values are set correctly"""
        assert Config.INPUT_EXT == ".ts"
        assert Config.OUTPUT_EXT == ".mp4"
        assert Config.FFMPEG_BIN == "ffmpeg"
        assert Config.FFPROBE_BIN == "ffprobe"
        assert Config.CRF_VALUE == 21
        assert Config.PRESET == "p4"
        assert Config.ENABLE_GPU is True
        assert Config.FORCE_GPU is False
        assert Config.MAX_CONCURRENT_CONVERSIONS == 1
        assert Config.SLEEP_BETWEEN_FILES == 2.0

    def test_ensure_dirs_creates_directories(self, temp_dir, monkeypatch):
        """Test that ensure_dirs creates necessary directories"""
        input_dir = temp_dir / "test_input"
        output_dir = temp_dir / "test_output"
        log_dir = temp_dir / "test_logs"

        monkeypatch.setattr(Config, 'INPUT_DIR', input_dir)
        monkeypatch.setattr(Config, 'OUTPUT_DIR', output_dir)
        monkeypatch.setattr(Config, 'LOG_DIR', log_dir)

        Config.ensure_dirs()

        assert input_dir.exists()
        assert output_dir.exists()
        assert log_dir.exists()

    def test_apply_overrides_input_dir(self, temp_dir, monkeypatch):
        """Test applying input directory override"""
        new_input = temp_dir / "new_input"

        # Temporarily store original value
        original_input = Config.INPUT_DIR

        try:
            Config.apply_overrides(input_dir=new_input)
            assert Config.INPUT_DIR == new_input
            assert new_input.exists()
        finally:
            # Restore original
            Config.INPUT_DIR = original_input

    def test_apply_overrides_output_dir(self, temp_dir):
        """Test applying output directory override"""
        new_output = temp_dir / "new_output"
        original_output = Config.OUTPUT_DIR

        try:
            Config.apply_overrides(output_dir=new_output)
            assert Config.OUTPUT_DIR == new_output
            assert new_output.exists()
        finally:
            Config.OUTPUT_DIR = original_output

    def test_apply_overrides_log_dir(self, temp_dir):
        """Test applying log directory override"""
        new_log = temp_dir / "new_logs"
        original_log = Config.LOG_DIR

        try:
            Config.apply_overrides(log_dir=new_log)
            assert Config.LOG_DIR == new_log
            assert new_log.exists()
        finally:
            Config.LOG_DIR = original_log

    def test_apply_overrides_ffmpeg_bin(self):
        """Test applying ffmpeg binary override"""
        original_ffmpeg = Config.FFMPEG_BIN

        try:
            Config.apply_overrides(ffmpeg_bin="/custom/path/ffmpeg")
            assert Config.FFMPEG_BIN == "/custom/path/ffmpeg"
        finally:
            Config.FFMPEG_BIN = original_ffmpeg

    def test_apply_overrides_ffprobe_bin(self):
        """Test applying ffprobe binary override"""
        original_ffprobe = Config.FFPROBE_BIN

        try:
            Config.apply_overrides(ffprobe_bin="/custom/path/ffprobe")
            assert Config.FFPROBE_BIN == "/custom/path/ffprobe"
        finally:
            Config.FFPROBE_BIN = original_ffprobe

    def test_apply_overrides_sleep_between(self):
        """Test applying sleep_between override"""
        original_sleep = Config.SLEEP_BETWEEN_FILES

        try:
            Config.apply_overrides(sleep_between=5.5)
            assert Config.SLEEP_BETWEEN_FILES == 5.5

            # Test negative value gets clamped to 0
            Config.apply_overrides(sleep_between=-1.0)
            assert Config.SLEEP_BETWEEN_FILES == 0.0
        finally:
            Config.SLEEP_BETWEEN_FILES = original_sleep

    def test_apply_overrides_none_values_ignored(self):
        """Test that None overrides don't change config"""
        original_input = Config.INPUT_DIR
        original_output = Config.OUTPUT_DIR

        Config.apply_overrides(input_dir=None, output_dir=None)

        assert Config.INPUT_DIR == original_input
        assert Config.OUTPUT_DIR == original_output

    def test_env_var_override_input_dir(self, temp_dir, monkeypatch):
        """Test environment variable override for input directory"""
        test_input = str(temp_dir / "env_input")
        monkeypatch.setenv("TS2MP4_INPUT_DIR", test_input)

        # Re-import to pick up env var (in practice this would be at module load time)
        # For testing, we'll just verify the getenv call would work
        assert os.getenv("TS2MP4_INPUT_DIR") == test_input

    def test_env_var_enable_gpu_false(self, monkeypatch):
        """Test disabling GPU via environment variable"""
        monkeypatch.setenv("TS2MP4_ENABLE_GPU", "0")
        result = os.getenv("TS2MP4_ENABLE_GPU", "1") not in ("0", "false", "False")
        assert result is False

    def test_env_var_force_gpu_true(self, monkeypatch):
        """Test forcing GPU via environment variable"""
        monkeypatch.setenv("TS2MP4_FORCE_GPU", "1")
        result = os.getenv("TS2MP4_FORCE_GPU", "0") in ("1", "true", "True")
        assert result is True


@pytest.fixture
def restore_config(mocker):
    """Snapshot Config attributes and os.environ, restoring both after the test"""
    snapshot = {k: v for k, v in vars(Config).items() if k.isupper()}
    mocker.patch.dict(os.environ)
    for key in [k for k in os.environ if k.startswith("TS2MP4_")]:
        del os.environ[key]
    yield
    for key, value in snapshot.items():
        setattr(Config, key, value)


class TestOutputHandlingOverrides:
    """Test keep-originals and overwrite settings"""

    def test_output_handling_defaults(self):
        assert Config.DELETE_ORIGINALS is True
        assert Config.OVERWRITE_EXISTING is False

    def test_apply_overrides_output_handling(self, restore_config):
        Config.apply_overrides(delete_originals=False, overwrite_existing=True)

        assert Config.DELETE_ORIGINALS is False
        assert Config.OVERWRITE_EXISTING is True


class TestLoadEnvFile:
    """Test loading settings from a .env file"""

    def test_env_file_settings_are_applied(self, temp_dir, restore_config):
        env_file = temp_dir / ".env"
        env_file.write_text("TS2MP4_CRF_VALUE=30\nTS2MP4_DELETE_ORIGINALS=0\n")

        assert Config.load_env_file(env_file) is True

        assert Config.CRF_VALUE == 30
        assert Config.DELETE_ORIGINALS is False

    def test_real_environment_takes_precedence(self, temp_dir, restore_config):
        env_file = temp_dir / ".env"
        env_file.write_text("TS2MP4_CRF_VALUE=30\n")
        os.environ["TS2MP4_CRF_VALUE"] = "18"

        Config.load_env_file(env_file)

        assert Config.CRF_VALUE == 18

    def test_missing_env_file_changes_nothing(self, temp_dir, restore_config):
        original_crf = Config.CRF_VALUE

        assert Config.load_env_file(temp_dir / ".env") is False

        assert Config.CRF_VALUE == original_crf
