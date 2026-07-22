# Sweety Live Reply And macOS App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace test-mode drafting with persistent live LINE replies and ship a runnable signed `Sweety.app`.

**Architecture:** `MonitorController` coordinates unread contacts and commits an exchange only after `LineMacAdapter.send_message()` verifies the named chat, pastes, and presses Enter. PyInstaller bundles the local API, React build, OCR runtime, and shared logo under a stable macOS bundle identifier.

**Tech Stack:** Python 3.11, PySide6, FastAPI, SQLite, AppleScript/pyautogui, React/Vite, PyInstaller.

---

### Task 1: Live reply transaction

**Files:**
- Modify: `app/desktop/src/sweety_app/repositories.py`
- Modify: `app/desktop/src/sweety_app/monitor.py`
- Modify: `app/desktop/src/sweety_app/line_mac.py`
- Test: `app/desktop/tests/test_repositories.py`
- Test: `app/desktop/tests/test_monitor.py`
- Test: `app/desktop/tests/test_line_mac.py`

- [ ] Write tests proving Enter is pressed, successful replies persist both roles, and failures persist nothing.
- [ ] Replace draft paste with target-bound `send_message()`.
- [ ] Persist each exchange atomically after successful send.
- [ ] Keep monitoring after processing all currently unread selected targets.
- [ ] Run focused Python tests.

### Task 2: Hour display and production status

**Files:**
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/desktop/src/sweety_app/panel.py`

- [ ] Use `formatDurationHours()` in desktop and mobile target lists.
- [ ] Remove test-mode and draft-ready language.
- [ ] Run frontend tests, typecheck, and production build.

### Task 3: macOS application bundle

**Files:**
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/desktop/pyproject.toml`
- Create: `app/desktop/launcher.py`
- Create: `app/desktop/Sweety.spec`
- Create: `app/desktop/build_app.sh`

- [ ] Make packaged resource lookup PyInstaller-aware.
- [ ] Bundle frontend, logo, OCR models, and macOS frameworks with bundle ID `tw.sweety.app`.
- [ ] Generate `.icns`, build, ad-hoc sign, and verify the `.app` bundle.
- [ ] Launch `dist/Sweety.app` and verify its local health endpoint.

### Task 4: Final verification

- [ ] Run all Python and frontend tests.
- [ ] Confirm no background development runtime remains.
- [ ] Leave the packaged Sweety App running for permission setup and controlled use.
