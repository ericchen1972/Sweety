from __future__ import annotations

from pathlib import Path

from sweety_app.line_mac import (
    LineMacAdapter,
    contact_click_point,
    contacts_from_ocr,
    parse_line_windows,
)


def test_parse_line_windows_keeps_names_with_symbols():
    raw = "name:LINE, position:23, 87, size:364, 870|name:💖✨Lilian✨💖, position:410, 87, size:700, 870|"
    windows = parse_line_windows(raw)

    assert windows[0] == {"name": "LINE", "x": 23, "y": 87, "width": 364, "height": 870}
    assert windows[1]["name"] == "💖✨Lilian✨💖"


def test_main_window_exists_requires_window_named_line(tmp_path: Path):
    adapter = LineMacAdapter(cache_dir=tmp_path, runner=lambda *_args, **_kwargs: Result())

    assert adapter.main_window_exists() is True


def test_window_scan_forces_position_and_size_values_before_string_concat(tmp_path: Path):
    captured = {}

    def runner(args, **_kwargs):
        captured["script"] = args[2]
        return Result()

    adapter = LineMacAdapter(cache_dir=tmp_path, runner=runner)

    assert adapter.main_window_exists() is True
    assert "item 1 of (get position of w)" in captured["script"]
    assert "item 1 of (get size of w)" in captured["script"]
    assert "ERROR:" in captured["script"]


def test_contact_click_point_uses_whomai_geometry():
    assert contact_click_point({"x": 23, "y": 87, "width": 364, "height": 870}, 1) == (173, 235)
    assert contact_click_point({"x": 23, "y": 87, "width": 364, "height": 870}, 3) == (173, 379)


def test_contacts_from_ocr_requires_green_badge_and_filters_times():
    ocr = [
        {"text": "Lilian", "bbox": [[10, 10], [60, 10], [60, 30], [10, 30]]},
        {"text": "10:30", "bbox": [[70, 10], [110, 10], [110, 30], [70, 30]]},
        {"text": "沒有未讀", "bbox": [[10, 82], [90, 82], [90, 102], [10, 102]]},
    ]
    contacts = contacts_from_ocr(ocr, image_height=300, has_badge=lambda index: index == 0)

    assert [(item.index, item.name) for item in contacts] == [(1, "Lilian")]


class FakeClipboard:
    def __init__(self) -> None:
        self.value = "原本內容"

    def paste(self) -> str:
        return self.value

    def copy(self, value: str) -> None:
        self.value = value


class FakeMouse:
    def __init__(self) -> None:
        self.clicks = []
        self.keys = []

    def click(self, x, y):
        self.clicks.append((x, y))

    def hotkey(self, *keys):
        self.keys.append(keys)

    def press(self, key):
        self.keys.append((key,))


class Result:
    returncode = 0
    stdout = "name:LINE, position:20, 80, size:360, 800|name:投資顧問, position:100, 200, size:500, 700|"
    stderr = ""


def test_send_message_clears_pastes_and_presses_enter_then_restores_clipboard(tmp_path: Path):
    clipboard = FakeClipboard()
    mouse = FakeMouse()
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=mouse,
        clipboard=clipboard,
        sleeper=lambda _seconds: None,
    )

    assert adapter.send_message("投資顧問", "AI 回覆") is True
    assert mouse.keys == [("command", "a"), ("backspace",), ("command", "v"), ("enter",)]
    assert clipboard.value == "原本內容"


def test_send_message_refuses_a_different_chat_window(tmp_path: Path):
    mouse = FakeMouse()
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=mouse,
        clipboard=FakeClipboard(),
        sleeper=lambda _seconds: None,
    )

    assert adapter.send_message("不存在的對象", "AI 草稿") is False
    assert mouse.clicks == []
    assert mouse.keys == []
