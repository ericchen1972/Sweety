# macOS LINE Contact List Scroll-to-Top Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return the macOS LINE contact list to the top before every unread-contact screenshot, then build a logging-enabled local Sweety.app.

**Architecture:** Add one focused `LineMacAdapter.scroll_main_window_to_top()` helper that activates LINE, positions the pointer in the contact list, scrolls upward twice, and reports success without raising. `unread_contacts()` calls it before capture and writes the result through the existing global diagnostics pipeline.

**Tech Stack:** Python 3.11+, pytest, PyAutoGUI, Pillow, PyInstaller, macOS codesign

---

## File Map

- Modify `app/desktop/src/sweety_app/line_mac.py`: implement scroll normalization, call it before capture, and emit diagnostic events.
- Modify `app/desktop/tests/test_line_mac.py`: cover scroll geometry, operation order, and non-fatal failure.
- Build `app/desktop/dist/Sweety.app`: local generated artifact with diagnostics enabled; do not commit it.

### Task 1: Add failing adapter behavior tests

**Files:**
- Test: `app/desktop/tests/test_line_mac.py`

- [ ] **Step 1: Write the failing scroll helper test**

```python
def test_scroll_main_window_to_top_moves_into_contact_list_and_scrolls_twice(tmp_path: Path):
    mouse = FakeMouse()
    sleeps = []
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=mouse,
        sleeper=sleeps.append,
    )
    adapter._activate_line = lambda: None
    main = {"name": "LINE", "x": 20, "y": 80, "width": 360, "height": 800}

    assert adapter.scroll_main_window_to_top(main) is True
    assert mouse.clicks == [(170, 480, 0.3)]
    assert mouse.keys == [("scroll", 2000), ("scroll", 2000)]
    assert sleeps == [0.5]
```

- [ ] **Step 2: Write the failing capture-order and fallback tests**

```python
@pytest.mark.parametrize("scroll_result", [True, False])
def test_unread_contacts_scrolls_before_capture_even_when_scroll_fails(tmp_path: Path, scroll_result: bool):
    events = []
    adapter = LineMacAdapter(cache_dir=tmp_path, runner=lambda *_args, **_kwargs: Result())
    adapter._main_window = lambda: {"name": "LINE", "x": 20, "y": 80, "width": 360, "height": 800}
    adapter.scroll_main_window_to_top = lambda _main: events.append("scroll") or scroll_result
    adapter._capture = lambda _main, path: (events.append("capture"), Image.new("RGB", (360, 800)).save(path))
    adapter._run_ocr = lambda _path: []

    assert adapter.unread_contacts() == []
    assert events == ["scroll", "capture"]
```

- [ ] **Step 3: Run `cd app/desktop && .venv/bin/python -m pytest tests/test_line_mac.py -q`**

Expected: failure because `LineMacAdapter.scroll_main_window_to_top` does not exist and `unread_contacts()` does not call it.

### Task 2: Implement the safe scroll normalization

**Files:**
- Modify: `app/desktop/src/sweety_app/line_mac.py:1-10`
- Modify: `app/desktop/src/sweety_app/line_mac.py:117-132`
- Modify: `app/desktop/src/sweety_app/line_mac.py` immediately before `prepare_next_chat`

- [ ] **Step 1: Add diagnostics imports**

```python
import logging

from .diagnostics import log_event
```

- [ ] **Step 2: Add the minimal helper**

```python
def scroll_main_window_to_top(self, main: dict[str, Any]) -> bool:
    try:
        self._activate_line()
        self._mouse().moveTo(
            int(main["x"]) + CONTACT_CLICK_X_OFFSET,
            int(main["y"]) + int(main["height"]) // 2,
            duration=0.3,
        )
        self._mouse().scroll(2000)
        self._mouse().scroll(2000)
        self.sleeper(0.5)
        return True
    except Exception:
        return False
```

- [ ] **Step 3: Call the helper before capture and log its result**

Replace the direct `_activate_line()` call in `unread_contacts()` with:

```python
scrolled = self.scroll_main_window_to_top(main)
log_event(
    logging.getLogger("sweety.line"),
    "contact_list_scroll_top_succeeded" if scrolled else "contact_list_scroll_top_failed",
)
self._capture(main, self.contact_list_path)
```

The capture remains unconditional so scroll failure is non-fatal.

- [ ] **Step 4: Run `cd app/desktop && .venv/bin/python -m pytest tests/test_line_mac.py -q`**

Expected: all `test_line_mac.py` tests pass.

- [ ] **Step 5: Run focused diff checks**

```bash
git diff --check
git diff -- app/desktop/src/sweety_app/line_mac.py app/desktop/tests/test_line_mac.py
```

Expected: no whitespace errors; only the planned adapter and test changes appear.

### Task 3: Verify and build the local macOS App

**Files:**
- Generated: `app/desktop/dist/Sweety.app`

- [ ] **Step 1: Run `cd app/desktop && .venv/bin/python -m pytest -q`**

Expected: zero failures.

- [ ] **Step 2: Run `app/desktop/build_app.sh`**

Expected: frontend build, dependency sync, PyInstaller build, and codesign verification succeed; final output is `app/desktop/dist/Sweety.app`.

- [ ] **Step 3: Verify the artifact and logging contract**

```bash
test -d app/desktop/dist/Sweety.app
codesign --verify --deep --strict --verbose=2 app/desktop/dist/Sweety.app
plutil -extract LSEnvironment.SWEETY_LOG_ENABLED raw app/desktop/dist/Sweety.app/Contents/Info.plist
```

Expected: directory check and codesign exit zero; `plutil` prints `1`.

- [ ] **Step 4: Commit only source, tests, and the plan**

```bash
git add app/desktop/src/sweety_app/line_mac.py app/desktop/tests/test_line_mac.py docs/superpowers/plans/2026-08-05-macos-line-contact-list-scroll-top.md
git commit -m "fix: reset LINE contact list before unread scan"
```

Do not add `videos/`, `app/desktop/build/`, or `app/desktop/dist/`.
