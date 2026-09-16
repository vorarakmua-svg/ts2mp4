"""Tests for display.py module"""
import re

import pytest

from display import EnhancedDisplay, visible_width

ANSI = re.compile(r"\x1b\[[0-9;]*m")

FILENAMES = {
    "ascii": "MIAB-648 plain name.ts",
    "thai": "DANDY-760 'ฉันควรทำอย่างไรถ้าครูของฉันยิง cum ทางช่องคล.ts",
    "japanese": "SSIS-001 新人デビュー 完全版 高画質.ts",
    "long": "X" * 200 + ".ts",
    "empty": "",
}


@pytest.fixture
def display(mocker):
    mocker.patch.object(EnhancedDisplay, 'update_system_stats')
    d = EnhancedDisplay()
    d.update_stats(total_files=3, completed=0, failed=0, current_progress=90.8,
                   current_speed="394x", encoder="Remux (copy)", fps="0", bitrate="1869.0kbits/s")
    d.stats.cpu_usage, d.stats.memory_usage, d.stats.gpu_usage = 75.2, 88.8, 12.0
    return d


def box_lines(output):
    plain = [ANSI.sub("", line) for line in output.split("\n")]
    return [line for line in plain if line[:1] in ("║", "╔", "╠", "╚")]


class TestVisibleWidth:
    def test_ascii(self):
        assert visible_width("abc") == 3

    def test_ignores_ansi_codes(self):
        assert visible_width("\x1b[32mabc\x1b[0m") == 3

    def test_thai_combining_marks_take_no_space(self):
        # "ที่" = consonant + two combining marks: one column
        assert visible_width("ที่") == 1

    def test_wide_characters_take_two_columns(self):
        assert visible_width("新人") == 4


class TestBoxAlignment:
    @pytest.mark.parametrize("name", FILENAMES.values(), ids=FILENAMES.keys())
    def test_every_box_line_is_80_columns(self, display, name):
        display.update_stats(current_file=name)

        lines = box_lines(display.render_full_display())

        assert lines
        assert {visible_width(line): line for line in lines if visible_width(line) != 80} == {}

    def test_every_line_ends_with_a_border(self, display):
        display.update_stats(current_file=FILENAMES["thai"])

        for line in box_lines(display.render_full_display()):
            assert line.rstrip()[-1] in ("║", "╗", "╣", "╝"), line

    def test_long_filename_is_truncated_with_ellipsis(self, display):
        display.update_stats(current_file=FILENAMES["long"])

        output = ANSI.sub("", display.render_full_display())

        assert "XXX..." in output

    def test_large_counts_stay_aligned(self, display):
        display.update_stats(total_files=12345, completed=9999, failed=1234)

        lines = box_lines(display.render_full_display())

        assert all(visible_width(line) == 80 for line in lines)


class TestOverallProgress:
    def test_includes_current_file_progress(self, display):
        display.update_stats(total_files=3, completed=0, failed=0, current_progress=90.0)
        assert display.overall_progress() == pytest.approx(30.0)

    def test_failed_files_count_as_done(self, display):
        display.update_stats(total_files=2, completed=0, failed=1, current_progress=50.0)
        assert display.overall_progress() == pytest.approx(75.0)

    def test_never_exceeds_100(self, display):
        display.update_stats(total_files=3, completed=3, failed=0, current_progress=100.0)
        assert display.overall_progress() == 100.0

    def test_no_files(self, display):
        display.update_stats(total_files=0, completed=0, failed=0, current_progress=0.0)
        assert display.overall_progress() == 0.0

    def test_batch_section_shows_overall_percentage(self, display):
        display.update_stats(total_files=3, completed=0, failed=0, current_progress=90.0)
        output = ANSI.sub("", "\n".join(display.render_batch_progress()))
        assert "30.0%" in output


class TestEstimatedRemaining:
    def test_calculating_until_progress_is_known(self, display):
        assert display.estimate_remaining(elapsed=60, overall_percentage=0.0) == "Calculating..."

    def test_calculating_during_first_seconds(self, display):
        assert display.estimate_remaining(elapsed=1, overall_percentage=50.0) == "Calculating..."

    def test_estimate_from_elapsed_and_progress(self, display):
        assert display.estimate_remaining(elapsed=60, overall_percentage=25.0) == "00:03:00"

    def test_done(self, display):
        assert display.estimate_remaining(elapsed=60, overall_percentage=100.0) == "00:00:00"

    def test_time_section_shows_estimate(self, display, mocker):
        mocker.patch('display.time.time', return_value=display.start_time + 60)
        display.update_stats(total_files=4, completed=1, failed=0, current_progress=0.0)

        output = ANSI.sub("", "\n".join(display.render_time_info()))

        assert "Estimated Remaining: 00:03:00" in output
