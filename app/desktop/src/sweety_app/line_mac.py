from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from .monitor import UnreadContact


CONTACT_HEIGHT = 72
CONTACT_TOP_OFFSET = 112
CONTACT_CLICK_X_OFFSET = 150


def parse_line_windows(raw: str) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    pattern = re.compile(r"name:(.*?), position:\s*(-?\d+),\s*(-?\d+), size:\s*(\d+),\s*(\d+)")
    for entry in raw.split("|"):
        match = pattern.search(entry.strip())
        if not match:
            continue
        windows.append(
            {
                "name": match.group(1).strip(),
                "x": int(match.group(2)),
                "y": int(match.group(3)),
                "width": int(match.group(4)),
                "height": int(match.group(5)),
            }
        )
    return windows


def contact_click_point(window: dict[str, Any], contact_index: int) -> tuple[int, int]:
    return (
        int(window["x"]) + CONTACT_CLICK_X_OFFSET,
        int(window["y"]) + CONTACT_TOP_OFFSET + ((contact_index - 1) * CONTACT_HEIGHT) + CONTACT_HEIGHT // 2,
    )


def is_time_text(text: str) -> bool:
    value = text.strip()
    if not value or re.fullmatch(r"\d{1,2}:\d{2}", value):
        return True
    if any(token in value for token in ("昨天", "今天", "明天", "上午", "下午", "中午", "星期", "週")):
        return True
    return any(
        re.search(pattern, value)
        for pattern in (r"\d{1,2}月\d{1,2}日", r"\d{4}[./-]\d{1,2}[./-]\d{1,2}", r"\d{1,2}[./-]\d{1,2}")
    )


def contacts_from_ocr(
    results: list[dict[str, Any]],
    *,
    image_height: int,
    has_badge: Callable[[int], bool],
) -> list[UnreadContact]:
    groups: dict[int, list[str]] = {}
    for item in results:
        bbox = item.get("bbox") or []
        if not bbox:
            continue
        center_y = sum(float(point[1]) for point in bbox) / len(bbox)
        if center_y > image_height - 60:
            continue
        groups.setdefault(int(center_y // CONTACT_HEIGHT), []).append(str(item.get("text", "")))

    contacts: list[UnreadContact] = []
    for zero_index in sorted(groups):
        if not has_badge(zero_index):
            continue
        name = " ".join(text.strip() for text in groups[zero_index] if not is_time_text(text)).strip()
        if name:
            contacts.append(UnreadContact(index=zero_index + 1, name=name))
    if len(contacts) > 1:
        contacts.reverse()
    return contacts


class LineMacAdapter:
    def __init__(
        self,
        cache_dir: str | Path,
        *,
        runner: Callable[..., Any] = subprocess.run,
        mouse: Any | None = None,
        clipboard: Any | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        ocr: Any | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.runner = runner
        self.mouse = mouse
        self.clipboard = clipboard
        self.sleeper = sleeper
        self._ocr_engine = ocr
        self.contact_list_path = self.cache_dir / "line-contacts.png"
        self.chat_path = self.cache_dir / "line-chat.png"

    def main_window_exists(self) -> bool:
        return self._main_window() is not None

    def unread_contacts(self) -> list[UnreadContact]:
        main = self._main_window()
        if main is None:
            raise RuntimeError("LINE main window not found")
        self._activate_line()
        self._capture(main, self.contact_list_path)
        with Image.open(self.contact_list_path) as image:
            cropped = image.crop((62, CONTACT_TOP_OFFSET, image.width, image.height))
            cropped.save(self.contact_list_path)
            height = cropped.height
        results = self._run_ocr(self.contact_list_path)
        return contacts_from_ocr(
            results,
            image_height=height,
            has_badge=lambda index: self._has_green_badge(self.contact_list_path, index),
        )

    def open_chat(self, contact: UnreadContact) -> bool:
        main = self._main_window()
        if main is None:
            return False
        self._activate_line()
        x, y = contact_click_point(main, contact.index)
        mouse = self._mouse()
        mouse.moveTo(x, y, duration=0.3)
        mouse.doubleClick()
        self.sleeper(1.5)
        return True

    def read_visible_chat(self, target_name: str) -> str:
        windows = self._windows()
        chat = next((item for item in windows if item["name"] != "LINE" and self._same_window_name(item["name"], target_name)), None)
        if chat is None:
            raise RuntimeError(f"LINE chat window not found: {target_name}")
        safe_name = target_name.replace('"', '\\"')
        self._osascript(
            f'''tell application "LINE" to activate
tell application "System Events" to tell process "LINE"
  set frontmost to true
  try
    set frontmost of window "{safe_name}" to true
  end try
  key code 119
  repeat 5 times
    key code 125
  end repeat
end tell'''
        )
        self._mouse().moveTo(chat["x"] + chat["width"] // 2, chat["y"] + chat["height"] // 2, duration=0.2)
        self._mouse().scroll(-2000)
        self._mouse().scroll(-2000)
        self.sleeper(0.5)
        self._capture(chat, self.chat_path)
        results = self._run_ocr(self.chat_path)
        ordered = sorted(results, key=lambda item: min(point[1] for point in item.get("bbox", [[0, 0]])))
        return "\n".join(str(item.get("text", "")).strip() for item in ordered if str(item.get("text", "")).strip())

    def send_message(self, target_name: str, reply: str) -> bool:
        chat = next((item for item in self._windows() if item["name"] == target_name), None)
        if chat is None:
            return False
        clipboard = self._clipboard()
        mouse = self._mouse()
        original = clipboard.paste()
        safe_name = self._safe_window_name(target_name)
        script = f'''tell application "LINE" to activate
tell application "System Events" to tell process "LINE"
set frontmost to true
if not (exists window "{safe_name}") then error "TARGET_WINDOW_NOT_FOUND"
perform action "AXRaise" of window "{safe_name}"
end tell'''
        try:
            self._osascript(script)
            mouse.click(chat["x"] + chat["width"] // 2, chat["y"] + chat["height"] - 50)
            self.sleeper(0.2)
            mouse.hotkey("command", "a")
            mouse.press("backspace")
            clipboard.copy(reply)
            mouse.hotkey("command", "v")
            self.sleeper(0.2)
            mouse.press("enter")
            self.sleeper(0.3)
            return True
        finally:
            clipboard.copy(original)

    def close_chat(self, target_name: str) -> None:
        safe_name = self._safe_window_name(target_name)
        self._osascript(
            f'''tell application "System Events" to tell process "LINE"
if exists window "{safe_name}" then perform action "AXClose" of window "{safe_name}"
end tell'''
        )

    def _windows(self) -> list[dict[str, Any]]:
        script = '''tell application "System Events"
if not (exists process "LINE") then return "PROCESS_NOT_FOUND"
tell process "LINE"
set windowInfo to ""
repeat with w in every window
try
set windowInfo to windowInfo & "name:" & (name of w) & ", position:" & (item 1 of (get position of w)) & ", " & (item 2 of (get position of w)) & ", size:" & (item 1 of (get size of w)) & ", " & (item 2 of (get size of w)) & "|"
on error errMsg
set windowInfo to windowInfo & "ERROR:" & errMsg & "|"
end try
end repeat
return windowInfo
end tell
end tell'''
        result = self._osascript(script)
        return parse_line_windows(result.stdout.strip())

    def _main_window(self) -> dict[str, Any] | None:
        return next((item for item in self._windows() if item["name"] == "LINE"), None)

    def _activate_line(self) -> None:
        self._osascript('tell application "LINE" to activate')
        self.sleeper(0.3)

    def _osascript(self, script: str) -> Any:
        result = self.runner(["/usr/bin/osascript", "-e", script], capture_output=True, text=True, timeout=8)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "AppleScript failed")
        return result

    def _capture(self, window: dict[str, Any], path: Path) -> None:
        import mss
        import mss.tools

        region = {"left": window["x"], "top": window["y"], "width": window["width"], "height": window["height"]}
        with mss.mss() as screen:
            screenshot = screen.grab(region)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=str(path))

    def _run_ocr(self, path: Path) -> list[dict[str, Any]]:
        if self._ocr_engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._ocr_engine = RapidOCR()
        result, _elapsed = self._ocr_engine(str(path))
        if not result:
            return []
        return [{"bbox": item[0], "text": item[1]} for item in result]

    @staticmethod
    def _has_green_badge(path: Path, contact_index: int) -> bool:
        with Image.open(path) as image:
            width, height = image.size
            row_top = contact_index * CONTACT_HEIGHT
            row_bottom = min(height, (contact_index + 1) * CONTACT_HEIGHT)
            if row_top >= height:
                return False
            left, right = (80, min(width, 400)) if width > 500 else (max(0, width - 80), max(0, width - 5))
            region = image.crop((left, row_top + 15, right, max(row_top + 16, row_bottom - 15))).convert("RGB")
            green_count = sum(1 for red, green, blue in region.getdata() if green > red + 20 and green > blue + 20 and green > 80)
            return 100 < green_count < 800

    @staticmethod
    def _same_window_name(found: str, expected: str) -> bool:
        return found == expected or found in expected or expected in found

    @staticmethod
    def _safe_window_name(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _mouse(self) -> Any:
        if self.mouse is None:
            import pyautogui

            self.mouse = pyautogui
        return self.mouse

    def _clipboard(self) -> Any:
        if self.clipboard is None:
            import pyperclip

            self.clipboard = pyperclip
        return self.clipboard
