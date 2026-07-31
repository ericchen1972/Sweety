# AI Timeout Panel Alert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the current LINE timeout recovery while showing a localized, transient AI timeout alert above the panel Start/Stop button.

**Architecture:** Classify provider timeouts at the AI client boundary with a dedicated `AiTimeoutError`, then let `MonitorController` own the alert lifecycle and expose it through its existing snapshot. The native AppKit panel remains a passive snapshot consumer and toggles a prebuilt warning card during its existing one-second refresh.

**Tech Stack:** Python 3.12, OpenAI Python SDK, PyObjC/AppKit, pytest

---

## File map

- `app/desktop/src/sweety_app/ai.py`: define and raise the timeout-specific AI exception while preserving current retries.
- `app/desktop/src/sweety_app/monitor.py`: own the transient alert state and keep existing LINE close/recovery behavior.
- `app/desktop/src/sweety_app/panel.py`: render localized warning copy from the snapshot.
- `app/desktop/tests/test_ai.py`: verify timeout classification and retry behavior.
- `app/desktop/tests/test_monitor.py`: verify alert lifecycle, no send/persist, and chat close behavior.
- `app/desktop/tests/test_panel_bridge.py`: verify localized copy and snapshot-driven visibility.

### Task 1: Classify exhausted provider timeouts

**Files:**
- Modify: `app/desktop/src/sweety_app/ai.py:10,50-52,176-192,224-253`
- Test: `app/desktop/tests/test_ai.py:1-150,380-404`

- [ ] **Step 1: Write failing timeout tests**

Import `httpx`, `APITimeoutError`, and the new exception, then add tests proving that two failed outer attempts surface the timeout type while a successful second attempt returns normally:

```python
import httpx
from openai import APITimeoutError

from sweety_app.ai import AiClient, AiError, AiTimeoutError, build_messages, contains_external_link


def provider_timeout() -> APITimeoutError:
    return APITimeoutError(request=httpx.Request("POST", "https://example.test/v1/chat/completions"))


def test_generate_reply_surfaces_timeout_after_existing_retries_are_exhausted(tmp_path):
    factory = FakeStructuredClientFactory([provider_timeout(), provider_timeout()])
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    with pytest.raises(AiTimeoutError, match="timed out"):
        client.generate_reply(
            target=target_payload(), screenshot_path=screenshot_path(tmp_path),
            history=[], total_messages=0, settings=settings(),
        )

    assert len(factory.parse_calls) == 2


def test_generate_reply_hides_transient_timeout_when_retry_succeeds(tmp_path):
    result = ai_module.ReplyDecision(incoming_summary="新訊息", msg_reply="正常回覆")
    factory = FakeStructuredClientFactory([provider_timeout(), result])
    client = AiClient(client_factory=factory, agnes_key="agnes-test")

    assert client.generate_reply(
        target=target_payload(), screenshot_path=screenshot_path(tmp_path),
        history=[], total_messages=0, settings=settings(),
    ) == result
    assert len(factory.parse_calls) == 2
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
cd app/desktop
uv run pytest tests/test_ai.py::test_generate_reply_surfaces_timeout_after_existing_retries_are_exhausted tests/test_ai.py::test_generate_reply_hides_transient_timeout_when_retry_succeeds -v
```

Expected: collection fails because `AiTimeoutError` does not exist.

- [ ] **Step 3: Implement the timeout exception boundary**

Update `ai.py`:

```python
from openai import APITimeoutError, OpenAI


class AiError(RuntimeError):
    pass


class AiTimeoutError(AiError):
    pass
```

In `_request_decision`, place the timeout handler before the general handler:

```python
        except AiError:
            raise
        except APITimeoutError as exc:
            raise AiTimeoutError("AI request timed out") from exc
        except Exception as exc:
            raise AiError("AI request failed") from exc
```

Do not change the two-attempt loop in `generate_reply`; it will preserve `AiTimeoutError` as `last_error` and raise it only if the existing retries do not recover.

- [ ] **Step 4: Run the AI tests**

Run: `cd app/desktop && uv run pytest tests/test_ai.py -v`

Expected: all `test_ai.py` tests pass.

- [ ] **Step 5: Commit the AI boundary**

```bash
git add app/desktop/src/sweety_app/ai.py app/desktop/tests/test_ai.py
git commit -m "feat: classify AI request timeouts"
```

### Task 2: Add the monitor alert lifecycle

**Files:**
- Modify: `app/desktop/src/sweety_app/monitor.py:10,80-87,148-170,258-275,335-356`
- Test: `app/desktop/tests/test_monitor.py:8-12,420-470`

- [ ] **Step 1: Write failing monitor lifecycle tests**

Import `AiTimeoutError` and add a controllable fake which records the snapshot at the instant each AI execution begins:

```python
from sweety_app.ai import AiError, AiTimeoutError, ReplyDecision


def test_ai_timeout_shows_alert_closes_chat_and_persists_nothing(repo):
    target = repo.create_target(target_payload("Rose"))
    line = FakeLine([UnreadContact(index=1, name="Rose")])

    class TimeoutAi:
        def generate_reply(self, **_kwargs):
            raise AiTimeoutError("AI request timed out")

    controller = MonitorController(repo, line, TimeoutAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)

    assert controller.run_cycle() is False
    assert controller.snapshot()["aiTimeoutAlert"] is True
    assert line.closed == 1
    assert line.sent == []
    assert repo.list_messages(target["id"]) == []


def test_non_timeout_ai_failure_does_not_show_alert(repo):
    repo.create_target(target_payload("Rose"))
    line = FakeLine([UnreadContact(index=1, name="Rose")])

    class FailingAi:
        def generate_reply(self, **_kwargs):
            raise AiError("AI returned an invalid reply")

    controller = MonitorController(repo, line, FailingAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)
    controller.run_cycle()

    assert controller.snapshot()["aiTimeoutAlert"] is False


def test_stop_and_next_ai_execution_hide_previous_timeout_alert(repo):
    repo.create_target(target_payload("Rose"))
    line = FakeLine([UnreadContact(index=1, name="Rose")])
    states_at_request: list[bool] = []

    class TimeoutAi:
        def generate_reply(self, **_kwargs):
            states_at_request.append(controller.snapshot()["aiTimeoutAlert"])
            raise AiTimeoutError("AI request timed out")

    controller = MonitorController(repo, line, TimeoutAi(), sleeper=lambda _seconds: None)
    controller.start(background=False)
    controller.run_cycle()
    assert controller.snapshot()["aiTimeoutAlert"] is True

    controller.run_cycle()
    assert states_at_request == [False, False]
    assert controller.snapshot()["aiTimeoutAlert"] is True

    controller.stop()
    assert controller.snapshot()["aiTimeoutAlert"] is False
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
cd app/desktop
uv run pytest tests/test_monitor.py::test_ai_timeout_shows_alert_closes_chat_and_persists_nothing tests/test_monitor.py::test_non_timeout_ai_failure_does_not_show_alert tests/test_monitor.py::test_stop_and_next_ai_execution_hide_previous_timeout_alert -v
```

Expected: failures because `aiTimeoutAlert` is absent and the monitor does not classify the caught error.

- [ ] **Step 3: Implement thread-safe alert state**

Update the import and initialization:

```python
from .ai import AiTimeoutError, ReplyDecision

# in __init__
self._ai_timeout_alert = False
```

Expose and clear it from `snapshot()` and `stop()`:

```python
# in stop(), regardless of was_enabled
self._ai_timeout_alert = False

# in snapshot()
"aiTimeoutAlert": self._ai_timeout_alert,
```

Immediately before `self.ai.generate_reply(...)`, clear the alert under the existing lock:

```python
with self._lock:
    self._ai_timeout_alert = False
decision = self.ai.generate_reply(...)
```

In the existing target exception handler, set it only for the dedicated type before retaining the current status, diagnostic log, and `_close_chat(..., "processing_failed")` flow:

```python
except Exception as exc:
    if isinstance(exc, AiTimeoutError):
        with self._lock:
            self._ai_timeout_alert = True
    self._set_status("error", f"processing_failed: {exc}", target_name)
    # existing log and close recovery remain unchanged
```

- [ ] **Step 4: Run monitor tests**

Run: `cd app/desktop && uv run pytest tests/test_monitor.py -v`

Expected: all `test_monitor.py` tests pass, including the existing close-on-failure assertions.

- [ ] **Step 5: Commit monitor lifecycle**

```bash
git add app/desktop/src/sweety_app/monitor.py app/desktop/tests/test_monitor.py
git commit -m "feat: expose transient AI timeout alert state"
```

### Task 3: Render the localized native panel alert

**Files:**
- Modify: `app/desktop/src/sweety_app/panel.py:40-105,225-292,375-386`
- Test: `app/desktop/tests/test_panel_bridge.py:5-14,55-80`

- [ ] **Step 1: Write failing panel copy and visibility tests**

Add the helper import and tests:

```python
from sweety_app.panel import ai_timeout_alert_copy


def test_ai_timeout_alert_copy_is_localized():
    assert ai_timeout_alert_copy("zh-TW") == "AI 目前沒有回應，請切換 AI 模型或稍後再試。"
    assert ai_timeout_alert_copy("en") == "AI is not responding. Switch AI models or try again later."
    assert ai_timeout_alert_copy("unsupported") == "AI is not responding. Switch AI models or try again later."


def test_bridge_preserves_monitor_timeout_alert_snapshot(tmp_path):
    database = Database(tmp_path / "panel-timeout.sqlite3")
    database.migrate()
    repo = Repository(database)
    monitor = FakeMonitor()
    monitor.ai_timeout_alert = True
    bridge = PanelBridge(repo, monitor, quit_callback=lambda: None)

    assert bridge.snapshot()["aiTimeoutAlert"] is True
```

Extend `FakeMonitor.snapshot()` so it returns `"aiTimeoutAlert": self.ai_timeout_alert`, initialized to `False`.

- [ ] **Step 2: Run focused panel tests and verify they fail**

Run:

```bash
cd app/desktop
uv run pytest tests/test_panel_bridge.py::test_ai_timeout_alert_copy_is_localized tests/test_panel_bridge.py::test_bridge_preserves_monitor_timeout_alert_snapshot -v
```

Expected: collection fails because `ai_timeout_alert_copy` does not exist.

- [ ] **Step 3: Add localized copy and the warning card**

Add the copy helper:

```python
AI_TIMEOUT_ALERT_COPY = {
    "zh-TW": "AI 目前沒有回應，請切換 AI 模型或稍後再試。",
    "en": "AI is not responding. Switch AI models or try again later.",
}


def ai_timeout_alert_copy(locale: str) -> str:
    return AI_TIMEOUT_ALERT_COPY["zh-TW" if locale == "zh-TW" else "en"]
```

Reserve a non-overlapping area above the primary button by moving the selected-target label to `y=364`, count to `y=312`, and status to `y=278`. In `build()`, create a hidden card at `(32, 224, 356, 48)`:

```python
self.ai_timeout_alert = NSView.alloc().initWithFrame_(NSMakeRect(32, 224, 356, 48))
self.ai_timeout_alert.setWantsLayer_(True)
self.ai_timeout_alert.layer().setCornerRadius_(8.0)
self.ai_timeout_alert.layer().setBorderWidth_(1.0)
warning_color = NSColor.systemOrangeColor()
self.ai_timeout_alert.layer().setBorderColor_(warning_color.colorWithAlphaComponent_(0.65).CGColor())
self.ai_timeout_alert.layer().setBackgroundColor_(warning_color.colorWithAlphaComponent_(0.14).CGColor())
warning_label = _label(ai_timeout_alert_copy(self.locale), (12, 6, 332, 36), 12, True)
warning_label.setLineBreakMode_(NSLineBreakByWordWrapping)
warning_label.setMaximumNumberOfLines_(2)
self.ai_timeout_alert.addSubview_(warning_label)
self.ai_timeout_alert.setHidden_(True)
content.addSubview_(self.ai_timeout_alert)
```

At the end of `refresh_`, drive visibility only from the monitor snapshot:

```python
self.ai_timeout_alert.setHidden_(not bool(snapshot.get("aiTimeoutAlert")))
```

- [ ] **Step 4: Run panel tests**

Run: `cd app/desktop && uv run pytest tests/test_panel_bridge.py -v`

Expected: all `test_panel_bridge.py` tests pass.

- [ ] **Step 5: Commit the panel alert**

```bash
git add app/desktop/src/sweety_app/panel.py app/desktop/tests/test_panel_bridge.py
git commit -m "feat: show AI timeout warning in panel"
```

### Task 4: Verify the integrated desktop App

**Files:**
- Verify only; no source changes expected.

- [ ] **Step 1: Run the complete desktop test suite**

Run: `cd app/desktop && uv run pytest`

Expected: all tests pass; existing warnings may remain unchanged.

- [ ] **Step 2: Check formatting and worktree scope**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors and only the pre-existing untracked `videos/` remains.

- [ ] **Step 3: Rebuild the local logging App**

Run: `cd app/desktop && ./build_app.sh`

Expected: the test App rebuild succeeds with `SWEETY_LOG_ENABLED=1` and code signing succeeds.

- [ ] **Step 4: Launch and visually inspect the panel**

Launch the rebuilt App, use a controlled timeout fake or test harness to set `aiTimeoutAlert`, and verify the alert is directly above Start/Stop, readable in the current macOS appearance, and hidden again by Stop. Stop the App after inspection so no background monitor remains active.

- [ ] **Step 5: Confirm canonical main history**

Run: `git log -4 --oneline --decorate`

Expected: the design, plan, and three implementation commits are on `main`; no feature branch or worktree was created.

