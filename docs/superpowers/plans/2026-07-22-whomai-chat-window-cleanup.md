# WhomAI-style LINE Chat Window Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reliably close detached LINE chat windows after processing and before each unread scan.

**Architecture:** Keep cleanup inside `LineMacAdapter`, using the same Accessibility close-button click as WhOmAI. Expose one method for a named chat and one best-effort method for all non-main windows; the monitor calls the latter before unread discovery and retains its existing targeted cleanup paths.

**Tech Stack:** Python 3.12, AppleScript/System Events Accessibility, pytest

---

### Task 1: Match WhOmAI's close-button behavior

**Files:**
- Modify: `app/desktop/tests/test_line_mac.py`
- Modify: `app/desktop/src/sweety_app/line_mac.py`

- [ ] **Step 1: Write failing adapter tests**

Add tests that capture the AppleScript passed to the runner, assert `close_chat("投資顧問")` returns `True`, and verify the script contains `click button 1 of targetWindow` but not `AXClose`. Add failure coverage using a runner result whose stdout is `failed`, and add `close_other_chat_windows()` coverage with multiple non-main windows.

- [ ] **Step 2: Run the adapter tests and verify RED**

Run: `.venv/bin/pytest -q tests/test_line_mac.py`

Expected: failures because `close_chat()` returns `None`, uses `AXClose`, and `close_other_chat_windows()` does not exist.

- [ ] **Step 3: Implement minimal adapter cleanup**

Change `close_chat()` to execute this WhOmAI-style script and interpret stdout:

```python
script = f'''tell application "System Events"
tell process "LINE"
  if not (exists window "{safe_name}") then return "already_closed"
  set targetWindow to window "{safe_name}"
  try
    click button 1 of targetWindow
    delay 0.5
    return "success"
  on error
    return "failed"
  end try
end tell
end tell'''
```

Return true for `success` and `already_closed`. Implement `close_other_chat_windows()` by enumerating `_windows()`, excluding the window named `LINE`, and calling `close_chat()` for each remaining name; return true only if every close succeeds.

- [ ] **Step 4: Run the adapter tests and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_line_mac.py`

Expected: all tests pass.

### Task 2: Add pre-scan defensive cleanup

**Files:**
- Modify: `app/desktop/tests/test_monitor.py`
- Modify: `app/desktop/src/sweety_app/monitor.py`

- [ ] **Step 1: Write a failing monitor-order test**

Extend `FakeLine` with `close_other_chat_windows()` and an event list. Add a test asserting the first two events from `run_cycle()` are `cleanup` then `unread_contacts`, including when cleanup returns false.

- [ ] **Step 2: Run the monitor test and verify RED**

Run: `.venv/bin/pytest -q tests/test_monitor.py`

Expected: failure because `run_cycle()` does not invoke pre-scan cleanup.

- [ ] **Step 3: Implement best-effort pre-scan cleanup**

Add `close_other_chat_windows() -> bool` to `LineAdapter`. At the start of `run_cycle()`, immediately before `unread_contacts()`, call it inside a narrow try/except and continue into unread discovery regardless of its result.

- [ ] **Step 4: Run the monitor tests and verify GREEN**

Run: `.venv/bin/pytest -q tests/test_monitor.py`

Expected: all tests pass.

### Task 3: Verify and package

**Files:**
- Verify: `app/desktop/src/sweety_app/monitor.py`
- Verify: `app/desktop/src/sweety_app/line_mac.py`
- Verify: `app/desktop/tests/test_monitor.py`
- Verify: `app/desktop/tests/test_line_mac.py`

- [ ] **Step 1: Run the full desktop test suite**

Run from `app/desktop`: `.venv/bin/pytest -q`

Expected: zero failures.

- [ ] **Step 2: Check the diff**

Run: `git diff --check && git diff -- app/desktop/src/sweety_app/monitor.py app/desktop/src/sweety_app/line_mac.py app/desktop/tests/test_monitor.py app/desktop/tests/test_line_mac.py`

Expected: no whitespace errors and only the scoped cleanup changes.

- [ ] **Step 3: Rebuild and validate the application**

Run from `app/desktop`: `./build_app.sh && codesign --verify --deep --strict dist/Sweety.app`

Expected: build exits zero and code-sign verification emits no error.

- [ ] **Step 4: Commit the implementation**

```bash
git add app/desktop/src/sweety_app/monitor.py app/desktop/src/sweety_app/line_mac.py app/desktop/tests/test_monitor.py app/desktop/tests/test_line_mac.py
git commit -m "fix: close LINE chat windows after replies"
```
