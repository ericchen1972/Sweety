# Retain Last Chat Screenshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep one complete LINE chat screenshot between diagnostic cycles while preserving release-mode deletion and privacy cleanup.

**Architecture:** `LineMacAdapter` owns a completed `line-chat.png` and a temporary `line-chat.next.png`. It captures into the temporary path and atomically replaces the completed path only on success; `LOG_ENABLED` controls whether post-AI cleanup retains or deletes the completed image, and `MonitorController` logs the actual result.

**Tech Stack:** Python 3.12, pathlib, PyInstaller macOS App, pytest.

---

### Task 1: Make chat capture replacement safe and retention-aware

**Files:**
- Modify: `app/desktop/tests/test_line_mac.py`
- Modify: `app/desktop/src/sweety_app/line_mac.py`

- [x] **Step 1: Add failing adapter tests**

Add tests that construct diagnostic and release adapters and assert:

```python
def test_diagnostic_capture_replaces_previous_completed_screenshot_atomically(tmp_path: Path):
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        retain_chat_capture=True,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=FakeMouse(),
        sleeper=lambda _seconds: None,
    )
    adapter.chat_path.write_bytes(b"previous complete screenshot")
    adapter._capture = lambda _window, path: path.write_bytes(b"new complete screenshot")

    screenshot = adapter.capture_visible_chat("投資顧問")

    assert screenshot == adapter.chat_path
    assert adapter.chat_path.read_bytes() == b"new complete screenshot"
    assert adapter.chat_next_path.exists() is False


def test_failed_diagnostic_capture_preserves_previous_completed_screenshot(tmp_path: Path):
    adapter = LineMacAdapter(
        cache_dir=tmp_path,
        retain_chat_capture=True,
        runner=lambda *_args, **_kwargs: Result(),
        mouse=FakeMouse(),
        sleeper=lambda _seconds: None,
    )
    adapter.chat_path.write_bytes(b"previous complete screenshot")

    def fail_after_write(_window, path):
        path.write_bytes(b"partial screenshot")
        raise RuntimeError("screen capture failed")

    adapter._capture = fail_after_write

    with pytest.raises(RuntimeError, match="screen capture failed"):
        adapter.capture_visible_chat("投資顧問")

    assert adapter.chat_path.read_bytes() == b"previous complete screenshot"
    assert adapter.chat_next_path.exists() is False


def test_diagnostic_cleanup_retains_only_the_adapter_screenshot(tmp_path: Path):
    adapter = LineMacAdapter(cache_dir=tmp_path, retain_chat_capture=True, runner=lambda *_args, **_kwargs: Result())
    adapter.chat_path.write_bytes(b"sensitive chat screenshot")
    other = tmp_path / "other.png"
    other.write_bytes(b"keep")

    assert adapter.discard_chat_capture(adapter.chat_path) == "retained"
    assert adapter.discard_chat_capture(other) == "ignored"
    assert adapter.chat_path.read_bytes() == b"sensitive chat screenshot"
    assert other.read_bytes() == b"keep"


def test_release_adapter_startup_and_cleanup_remove_chat_screenshots(tmp_path: Path):
    (tmp_path / "line-chat.png").write_bytes(b"old complete screenshot")
    (tmp_path / "line-chat.next.png").write_bytes(b"old partial screenshot")

    adapter = LineMacAdapter(cache_dir=tmp_path, retain_chat_capture=False, runner=lambda *_args, **_kwargs: Result())

    assert adapter.chat_path.exists() is False
    assert adapter.chat_next_path.exists() is False
    adapter.chat_path.write_bytes(b"current screenshot")
    assert adapter.discard_chat_capture(adapter.chat_path) == "discarded"
    assert adapter.chat_path.exists() is False


def test_diagnostic_adapter_startup_preserves_complete_and_removes_partial(tmp_path: Path):
    (tmp_path / "line-chat.png").write_bytes(b"last complete screenshot")
    (tmp_path / "line-chat.next.png").write_bytes(b"stale partial screenshot")

    adapter = LineMacAdapter(cache_dir=tmp_path, retain_chat_capture=True, runner=lambda *_args, **_kwargs: Result())

    assert adapter.chat_path.read_bytes() == b"last complete screenshot"
    assert adapter.chat_next_path.exists() is False
```

- [x] **Step 2: Run focused adapter tests and confirm RED**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q app/desktop/tests/test_line_mac.py
```

Expected: failures for the unknown `retain_chat_capture` argument and missing `chat_next_path`.

- [x] **Step 3: Implement atomic replacement and cleanup results**

Update `LineMacAdapter.__init__`:

```python
def __init__(
    self,
    cache_dir: str | Path,
    *,
    retain_chat_capture: bool = False,
    runner: Callable[..., Any] = subprocess.run,
    mouse: Any | None = None,
    clipboard: Any | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    ocr: Any | None = None,
) -> None:
    self.cache_dir = Path(cache_dir)
    self.cache_dir.mkdir(parents=True, exist_ok=True)
    self.retain_chat_capture = retain_chat_capture
    self.runner = runner
    self.mouse = mouse
    self.clipboard = clipboard
    self.sleeper = sleeper
    self._ocr_engine = ocr
    self.contact_list_path = self.cache_dir / "line-contacts.png"
    self.chat_path = self.cache_dir / "line-chat.png"
    self.chat_next_path = self.cache_dir / "line-chat.next.png"
    self.chat_next_path.unlink(missing_ok=True)
    if not self.retain_chat_capture:
        self.chat_path.unlink(missing_ok=True)
```

Capture into the temporary path and replace only after success:

```python
try:
    self._capture(chat, self.chat_next_path)
    self.chat_next_path.replace(self.chat_path)
except Exception:
    self.chat_next_path.unlink(missing_ok=True)
    raise
return self.chat_path
```

Report cleanup behavior:

```python
def discard_chat_capture(self, screenshot_path: str | Path) -> str:
    path = Path(screenshot_path)
    if path != self.chat_path:
        return "ignored"
    if self.retain_chat_capture:
        return "retained"
    path.unlink(missing_ok=True)
    return "discarded"
```

- [x] **Step 4: Run focused adapter tests and confirm GREEN**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q app/desktop/tests/test_line_mac.py
```

Expected: all adapter tests pass.

### Task 2: Wire the global diagnostic switch and truthful monitor events

**Files:**
- Modify: `app/desktop/tests/test_monitor.py`
- Modify: `app/desktop/tests/test_metrics_integration_contract.py`
- Modify: `app/desktop/src/sweety_app/monitor.py`
- Modify: `app/desktop/src/sweety_app/__main__.py`

- [x] **Step 1: Add failing monitor and entrypoint tests**

Change `FakeLine` to accept `capture_cleanup_result: str = "discarded"` and return it from `discard_chat_capture()`. Add a test whose fake returns `"retained"` and assert the event list contains `screenshot_retained` but not `screenshot_discarded`.

In `test_packaging_injects_build_credentials_without_defaults()`, load the
entrypoint source and add this contract assertion:

```python
main_source = (SOURCE_DIR / "__main__.py").read_text()
assert "LineMacAdapter(CACHE_DIR, retain_chat_capture=LOG_ENABLED)" in main_source
```

- [x] **Step 2: Run focused tests and confirm RED**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q app/desktop/tests/test_monitor.py app/desktop/tests/test_metrics_integration_contract.py
```

Expected: monitor still logs `screenshot_discarded`, and the entrypoint does not pass `LOG_ENABLED`.

- [x] **Step 3: Implement event and entrypoint wiring**

Update the adapter protocol:

```python
def discard_chat_capture(self, screenshot_path: Path) -> str: ...
```

Replace unconditional cleanup logging with:

```python
capture_cleanup = self.line.discard_chat_capture(screenshot_path)
if capture_cleanup == "retained":
    self._log("screenshot_retained", target=target_name, path=str(screenshot_path))
else:
    self._log("screenshot_discarded", target=target_name)
```

Pass the global diagnostic flag in the desktop entrypoint:

```python
line = LineMacAdapter(CACHE_DIR, retain_chat_capture=LOG_ENABLED)
```

- [x] **Step 4: Run focused tests and confirm GREEN**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q app/desktop/tests/test_monitor.py app/desktop/tests/test_metrics_integration_contract.py
```

Expected: all focused tests pass.

### Task 3: Verify, commit, rebuild, and sync canonical main

**Files:**
- Modify: `docs/superpowers/plans/2026-07-31-retain-last-chat-screenshot.md` for checkbox tracking

- [x] **Step 1: Run the complete desktop test suite and diff checks**

```bash
rtk .venv/bin/python -m pytest -q
```

Run from `app/desktop`. Then run from the repository root:

```bash
rtk git diff --check
rtk git status --short
```

Expected: every desktop test passes, diff checks are clean, and `videos/` remains untouched.

- [x] **Step 2: Commit the implementation files**

```bash
rtk git add app/desktop/src/sweety_app/line_mac.py app/desktop/src/sweety_app/monitor.py app/desktop/src/sweety_app/__main__.py app/desktop/tests/test_line_mac.py app/desktop/tests/test_monitor.py app/desktop/tests/test_metrics_integration_contract.py docs/superpowers/plans/2026-07-31-retain-last-chat-screenshot.md
rtk git commit -m "fix: retain last diagnostic chat screenshot"
```

- [x] **Step 3: Stop the idle local App and rebuild a logging-enabled test App**

Confirm the monitor is stopped through `/api/monitor/status`, quit the local test App, then run:

```bash
rtk app/desktop/build_app.sh
```

Expected: the App builds with `SWEETY_LOG_ENABLED=1` and passes code-sign verification. Do not start monitoring or send a LINE message as part of build verification.

- [x] **Step 4: Verify the built diagnostic contract without external messaging**

Verify the built App's `Info.plist` has `SWEETY_LOG_ENABLED=1`. Run the focused adapter tests against an isolated temporary directory to prove that a completed screenshot survives cleanup and a failed replacement preserves the previous image.

- [ ] **Step 5: Push canonical main and confirm final state**

```bash
rtk git push origin main
rtk git status --short --branch
```

Expected: local and remote `main` match; only the unrelated `videos/` directory remains untracked.
