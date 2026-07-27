# Multimodal LINE Reply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send the current LINE screenshot and recent history to the selected multimodal model, then persist the extracted latest incoming item and generated reply only after successful delivery.

**Architecture:** `LineMacAdapter` captures and returns the screenshot path without OCRing chat content. `AiClient` owns image encoding, the immutable left/right extraction contract, response validation, and history normalization through a typed `ReplyDecision`; `MonitorController` remains the delivery and atomic persistence coordinator.

**Tech Stack:** Python 3.11, requests, Pillow/mss, AGNES/OpenAI-compatible Chat Completions, SQLite, pytest

---

### Task 1: Define and validate the multimodal AI contract

**Files:**
- Modify: `app/desktop/src/sweety_app/ai.py`
- Test: `app/desktop/tests/test_ai.py`

- [ ] **Step 1: Write failing contract tests**

Add tests that create a temporary PNG, call `AiClient.generate_reply()`, and assert the request includes a Base64 `image_url`, role-preserving history, and the left/right latest-incoming rule. Add parse tests for plain and fenced JSON covering `text`, `sticker`, `image`, and `emoji`, plus rejection of empty fields and unknown types.

```python
decision = client.generate_reply(
    target=target,
    screenshot_path=png_path,
    history=[{"role": "scammer", "content": "之前的訊息"}],
    total_messages=1,
    settings=settings,
)
assert decision.message_type == "sticker"
assert decision.incoming_for_history == "[貼圖] 無奈的卡通角色"
content = session.calls[0]["json"]["messages"][-1]["content"]
assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
cd app/desktop
uv run pytest tests/test_ai.py -q
```

Expected: failures because `screenshot_path` and `ReplyDecision` do not exist.

- [ ] **Step 3: Implement the typed decision and image request**

Add a frozen `ReplyDecision` dataclass with `message_type`, `last_msg`, `msg_reply`, and an `incoming_for_history` property. Replace `visible_text` with `screenshot_path`, Base64-encode PNG/JPEG/WEBP images into the final user content block, append an immutable extraction contract, and parse prompt-requested JSON after stripping optional Markdown fences.

Use these history labels:

```python
MEDIA_HISTORY_LABELS = {
    "sticker": "貼圖",
    "image": "照片",
    "emoji": "表情符號",
}
```

Reject types outside `{"text", "sticker", "image", "emoji"}`, blank `last_msg`, blank `msg_reply`, and unsafe-link replies. Retry the complete request once for invalid output or unsafe links, then raise `AiError`.

- [ ] **Step 4: Run the focused tests**

Run:

```bash
cd app/desktop
uv run pytest tests/test_ai.py -q
```

Expected: all `test_ai.py` tests pass.

### Task 2: Make chat capture return the screenshot

**Files:**
- Modify: `app/desktop/src/sweety_app/line_mac.py`
- Modify: `app/desktop/src/sweety_app/monitor.py`
- Test: `app/desktop/tests/test_line_mac.py`
- Test: `app/desktop/tests/test_monitor.py`

- [ ] **Step 1: Write failing adapter and controller tests**

Change `FakeLine` to expose `capture_visible_chat()` and return a test path. Assert the monitor passes that path to AI. Add an adapter test with injected capture behavior proving chat OCR is not invoked.

```python
def capture_visible_chat(self, target_name: str) -> Path:
    self.events.append("capture")
    return Path("/tmp/test-line-chat.png")
```

Update `FakeAi` to return `ReplyDecision("image", "一張超商繳費單", "這是要我做什麼？")`, then assert persistence contains `[照片] 一張超商繳費單`.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
cd app/desktop
uv run pytest tests/test_line_mac.py tests/test_monitor.py -q
```

Expected: failures because the protocol and controller still call `read_visible_chat()`.

- [ ] **Step 3: Implement screenshot capture and controller wiring**

Rename `read_visible_chat()` to `capture_visible_chat()`. Preserve the existing window verification, scroll-to-bottom behavior, and screenshot capture, but return `self.chat_path` immediately without `_run_ocr()`.

Update `LineAdapter`, `AiAdapter`, and `MonitorController` so the controller passes `screenshot_path`, sends `decision.msg_reply`, and calls:

```python
self.repository.record_exchange(
    str(target["id"]),
    decision.incoming_for_history,
    decision.msg_reply,
)
```

Keep the existing stop checks before AI, after AI, after delay, and before send. Persist and report metrics only after `send_message()` succeeds.

- [ ] **Step 4: Run focused controller and adapter tests**

Run:

```bash
cd app/desktop
uv run pytest tests/test_line_mac.py tests/test_monitor.py -q
```

Expected: all focused tests pass.

### Task 3: Verify safety, failure, and regression behavior

**Files:**
- Modify: `app/desktop/tests/test_ai.py`
- Modify: `app/desktop/tests/test_monitor.py`

- [ ] **Step 1: Add failure-path tests**

Cover malformed fenced JSON, unknown `message_type`, missing media description, capture failure, AI failure, stop-after-capture, and send failure. Assert each failure leaves `messages` empty, `round_trips` unchanged, and metrics unreported.

- [ ] **Step 2: Run the desktop suite**

Run:

```bash
cd app/desktop
uv run pytest -q
```

Expected: the complete desktop suite passes.

- [ ] **Step 3: Run static diff checks**

Run:

```bash
git diff --check
rg -n "read_visible_chat|visible_text" app/desktop/src app/desktop/tests
```

Expected: no whitespace errors and no old chat-content pipeline references.

### Task 4: Record macOS 12 release constraints

**Files:**
- Create: `docs/compatibility/macos-12.md`

- [ ] **Step 1: Document the verified blockers**

Record that the current `Info.plist` declares `LSMinimumSystemVersion=13.0`; the current bundle is arm64-only; OpenCV binaries target macOS 13; and bundled NumPy/ONNX Runtime binaries target macOS 14.

- [ ] **Step 2: Document the supported implementation paths**

Recommend either pinning and rebuilding compatible OCR wheels (`opencv-python<=4.10.0.84`, `onnxruntime<=1.19.2`) or replacing RapidOCR with native Vision OCR and removing OpenCV/ONNX/NumPy from the macOS bundle. Require testing on Apple Silicon and Intel macOS 12 before lowering the plist target.

- [ ] **Step 3: Verify documentation and final tests**

Run:

```bash
git diff --check
cd app/desktop
uv run pytest -q
```

Expected: no diff errors and all desktop tests pass.
