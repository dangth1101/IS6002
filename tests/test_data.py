import pytest

from bird_demo.data import require


def test_missing_file_stops_with_one_line_pointing_to_the_readme(tmp_path):
    with pytest.raises(SystemExit) as stop:
        require(tmp_path / "nope.sqlite")

    message = str(stop.value)
    assert "README.md" in message
    assert "\n" not in message


def test_present_file_is_returned(tmp_path):
    path = tmp_path / "dev.json"
    path.write_text("[]")

    assert require(path) == path
