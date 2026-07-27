from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

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

    def moveTo(self, x, y, duration=0):
        self.clicks.append((x, y, duration))

    def scroll(self, amount):
        self.keys.append(("scroll", amount))

    def hotkey(self, *keys):
        self.keys.append(keys)

    def press(self, key):
        self.keys.append((key,))


class Result:
    returncode = 0
    stdout = "name:LINE, position:20, 80, size:360, 800|name:投資顧問, position:100, 200, size:500, 700|"
    stderr = ""


def test_capture_visible_chat_returns_screenshot_without_chat_ocr(tmp_path: Path):
    mouse = FakeMouse()
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=mouse,
        sleeper=lambda _seconds: None,
    )
    adapter._capture = lambda _window, path: path.write_bytes(b"\x89PNG\r\n\x1a\n")
    adapter._run_ocr = lambda _path: (_ for _ in ()).throw(AssertionError("chat OCR must not run"))

    screenshot = adapter.capture_visible_chat("投資顧問")

    assert screenshot == tmp_path / "line-chat.png"
    assert screenshot.read_bytes().startswith(b"\x89PNG")


def test_capture_visible_chat_removes_partial_screenshot_when_capture_fails(tmp_path: Path):
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=FakeMouse(),
        sleeper=lambda _seconds: None,
    )

    def fail_after_write(_window, path):
        path.write_bytes(b"partial sensitive screenshot")
        raise RuntimeError("screen capture failed")

    adapter._capture = fail_after_write

    with pytest.raises(RuntimeError, match="screen capture failed"):
        adapter.capture_visible_chat("投資顧問")

    assert adapter.chat_path.exists() is False


def test_discard_chat_capture_removes_only_the_adapter_screenshot(tmp_path: Path):
    adapter = LineMacAdapter(cache_dir=tmp_path, runner=lambda *_args, **_kwargs: Result())
    adapter.chat_path.write_bytes(b"sensitive chat screenshot")
    other = tmp_path / "other.png"
    other.write_bytes(b"keep")

    adapter.discard_chat_capture(adapter.chat_path)
    adapter.discard_chat_capture(other)

    assert adapter.chat_path.exists() is False
    assert other.read_bytes() == b"keep"


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
    captures = 0

    def capture(_window, path):
        nonlocal captures
        image = Image.new("RGB", (500, 700), "white")
        if captures == 0:
            ImageDraw.Draw(image).rectangle((180, 650, 320, 665), fill="black")
        else:
            ImageDraw.Draw(image).rectangle((350, 500, 470, 550), fill="black")
        image.save(path)
        captures += 1

    adapter._capture = capture

    assert adapter.send_message("投資顧問", "AI 回覆") is True
    assert mouse.keys == [("command", "a"), ("backspace",), ("command", "v"), ("enter",)]
    assert clipboard.value == "原本內容"
    assert (tmp_path / "line-send-before.png").exists() is False
    assert (tmp_path / "line-send-after.png").exists() is False


def test_send_message_returns_false_when_no_outgoing_bubble_appears(tmp_path: Path):
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=FakeMouse(),
        clipboard=FakeClipboard(),
        sleeper=lambda _seconds: None,
    )
    adapter._capture = lambda _window, path: Image.new("RGB", (500, 700), "white").save(path)

    assert adapter.send_message("投資顧問", "AI 回覆") is False
    assert (tmp_path / "line-send-before.png").exists() is False
    assert (tmp_path / "line-send-after.png").exists() is False


def test_send_message_rejects_unrelated_right_side_motion_when_input_did_not_clear(tmp_path: Path):
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=FakeMouse(),
        clipboard=FakeClipboard(),
        sleeper=lambda _seconds: None,
    )
    captures = 0

    def capture(_window, path):
        nonlocal captures
        image = Image.new("RGB", (500, 700), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((180, 650, 320, 665), fill="black")
        draw.rectangle((350 + (captures * 10), 500, 470, 550), fill="black")
        image.save(path)
        captures += 1

    adapter._capture = capture

    assert adapter.send_message("投資顧問", "AI 回覆") is False


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


def test_close_chat_clicks_whomai_close_button(tmp_path: Path):
    captured = {}

    def runner(args, **_kwargs):
        captured["script"] = args[2]
        return SimpleNamespace(returncode=0, stdout="success\n", stderr="")

    adapter = LineMacAdapter(cache_dir=tmp_path, runner=runner)

    assert adapter.close_chat("投資顧問") is True
    assert 'set targetWindow to window "投資顧問"' in captured["script"]
    assert "click button 1 of targetWindow" in captured["script"]
    assert "AXClose" not in captured["script"]


def test_close_chat_returns_false_when_applescript_fails(tmp_path: Path):
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="", stderr="denied"),
    )

    assert adapter.close_chat("投資顧問") is False


def test_close_other_chat_windows_closes_every_non_main_window(tmp_path: Path):
    close_scripts = []

    def runner(args, **_kwargs):
        script = args[2]
        if "repeat with w in every window" in script:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "name:LINE, position:20, 80, size:360, 800|"
                    "name:對象 A, position:100, 200, size:500, 700|"
                    "name:對象 B, position:120, 220, size:500, 700|"
                ),
                stderr="",
            )
        close_scripts.append(script)
        return SimpleNamespace(returncode=0, stdout="success\n", stderr="")

    adapter = LineMacAdapter(cache_dir=tmp_path, runner=runner)

    assert adapter.close_other_chat_windows() is True
    assert len(close_scripts) == 2
    assert 'window "對象 A"' in close_scripts[0]
    assert 'window "對象 B"' in close_scripts[1]
