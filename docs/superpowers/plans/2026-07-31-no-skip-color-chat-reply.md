# No-Skip Color-Based Chat Reply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every opened unread LINE chat produce a reply, with the AI identifying green bubbles as the user's messages and gray bubbles as the other person's messages.

**Architecture:** Replace the reply-or-skip schema with a strict two-field reply schema, and rewrite both screenshot prompt layers around communication-app bubble colors. Remove the monitor's skip branch so every valid AI result proceeds through the existing delay, send verification, persistence, and close flow; invalid results continue through the existing retry and failure recovery paths.

**Tech Stack:** Python 3.11, OpenAI-compatible structured outputs, Pydantic, pytest, PyInstaller macOS App.

---

## File map

- `app/desktop/src/sweety_app/ai.py`: owns the structured `ReplyDecision`, communication-screen prompt, screenshot batch extraction instructions, retry, and unsafe-link checks.
- `app/desktop/src/sweety_app/monitor.py`: owns the unread-target processing pipeline and must treat every valid decision as a reply.
- `app/desktop/tests/test_ai.py`: pins the exact schema, color-based prompt contract, retry behavior, raw-response logging, and existing content-safety behavior.
- `app/desktop/tests/test_monitor.py`: pins the no-skip runtime flow, diagnostic screenshot retention, send/persistence behavior, and AI failure recovery.
- `app/desktop/tests/test_metrics_integration_contract.py`: provides a source-level guard that the monitor cannot regain a skip branch.
- `docs/superpowers/plans/2026-07-31-no-skip-color-chat-reply.md`: tracks execution and final verification.

The generic diagnostics serializer test may continue using an arbitrary field named `action`; it tests that arbitrary structured fields are preserved and is not part of the AI reply contract.

### Task 1: Pin the strict color-based AI contract with failing tests

**Files:**
- Modify: `app/desktop/tests/test_ai.py`

- [x] **Step 1: Rewrite the reply fixture and raw JSON helper without `action`**

Use this helper shape:

```python
def decision_json(
    *,
    incoming_summary: str = "你好",
    msg_reply: str = "怎麼了？",
) -> str:
    return json.dumps(
        {
            "incoming_summary": incoming_summary,
            "msg_reply": msg_reply,
        },
        ensure_ascii=False,
    )
```

Update every valid test fixture to construct:

```python
ai_module.ReplyDecision(
    incoming_summary="你好",
    msg_reply="測試回覆",
)
```

Do not leave any valid `ReplyDecision(action="reply", ...)` fixture.

- [x] **Step 2: Replace left/right and skip prompt assertions with the color contract**

In `test_prompt_isolates_persona_and_sends_role_preserving_history_with_image`, assert both the system contract and image instruction include:

```python
system_prompt = messages[0]["content"]
image_instruction = messages[-1]["content"][0]["text"]

for prompt in (system_prompt, image_instruction):
    assert "通訊 App" in prompt
    assert "綠色背景" in prompt
    assert "使用者自己傳出" in prompt
    assert "灰色背景" in prompt
    assert "對方傳來" in prompt
    assert "最下方的綠色" in prompt
    assert "之後所有可見的灰色" in prompt
    assert "沒有綠色" in prompt
    assert "所有可見的灰色" in prompt
    assert "左側" not in prompt
    assert "右側" not in prompt
    assert "skip" not in prompt
```

Keep the existing assertions for stickers, photos, videos, voice/audio messages, emoji-only content, reply-style quoted boxes, visible-only extraction, persona isolation, bounded history, and the image data URL.

- [x] **Step 3: Require exactly two non-empty response fields**

Change the provider/schema assertion to:

```python
schema = request["response_format"].model_json_schema()
assert set(schema["required"]) == {"incoming_summary", "msg_reply"}
assert schema["additionalProperties"] is False
```

Replace the accepted-skip test with strict validation coverage:

```python
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"incoming_summary": "你好"},
        {"msg_reply": "收到"},
        {"incoming_summary": " ", "msg_reply": "收到"},
        {"incoming_summary": "你好", "msg_reply": " "},
        {"action": "reply", "incoming_summary": "你好", "msg_reply": "收到"},
        {"action": "skip", "incoming_summary": "", "msg_reply": ""},
    ],
)
def test_reply_decision_schema_rejects_invalid_or_extra_fields(payload):
    with pytest.raises(ValidationError):
        ai_module.ReplyDecision.model_validate(payload)
```

Update `test_reply_decision_preserves_one_condensed_visible_batch` to assert trimmed values and remove the `should_reply` assertion.

- [x] **Step 4: Run the AI tests and confirm RED**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q app/desktop/tests/test_ai.py
```

Expected: failures show that the current schema still requires/accepts `action`, the prompt still describes left/right ownership and `skip`, and `ReplyDecision` still exposes `should_reply`.

### Task 2: Implement the strict reply schema and color-based prompt

**Files:**
- Modify: `app/desktop/src/sweety_app/ai.py`
- Test: `app/desktop/tests/test_ai.py`

- [x] **Step 1: Simplify `ReplyDecision` to two required non-empty fields**

Remove `Literal` and `model_validator` from the imports. Replace the model with:

```python
class ReplyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    incoming_summary: str
    msg_reply: str

    @field_validator("incoming_summary", "msg_reply")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("reply fields must not be blank")
        return normalized
```

Do not add a replacement action flag or a `should_reply` property.

- [x] **Step 2: Replace `SCREENSHOT_REPLY_CONTRACT` with the approved communication-screen rules**

Use a contract with these exact semantics:

```python
SCREENSHOT_REPLY_CONTRACT = """
LINE 通訊 App 截圖辨識與回覆規則：
1. 這是一張 LINE 通訊 App 的對話畫面。綠色背景的文字氣泡或內容是使用者自己傳出的；灰色背景的文字氣泡或內容是對方傳來的。不要使用左右位置判斷訊息屬於誰。
2. 系統只會在偵測到已監控聯絡人有新訊息後開啟對話，因此每次都必須整理新訊息並產生回覆，不存在略過或不回覆的選項。
3. 找出畫面中最下方的一則綠色背景訊息，依畫面由上到下收集它之後所有可見的灰色背景訊息。若畫面中沒有綠色背景訊息，就收集畫面中所有可見的灰色背景訊息。
4. 「回覆式 box」是 LINE 顯示在新訊息內的引用預覽，box 內可能是引用的使用者舊訊息。它不是對方本次新傳來的內容；只收集 box 外對方本次實際傳來的內容。
5. 文字、貼圖、照片、影片、語音訊息、其他音訊與純表情符號都算訊息。incoming_summary 只保留本次收集到的灰色內容，依原本先後順序記錄；非文字內容使用簡短客觀描述，畫面看得到長度時一併保留。
6. incoming_summary 不要加上「[對方]」、「對方問」、「對方說」或「我方回覆」等標籤，不要改寫成對話敘事，也不要加入任何綠色內容。
7. 只能根據目前可見畫面判斷，不可向上捲動、推測或補入截圖上方看不到的內容。
8. 根據最近歷史、人設和完整 incoming_summary，產生一則自然、簡短、能延續對話的 msg_reply。incoming_summary 與 msg_reply 都不可為空。
""".strip()
```

- [x] **Step 3: Align the image-specific instruction with the same contract**

Replace the text item in the final multimodal user message with:

```python
(
    "這是一張 LINE 通訊 App 的對話畫面。綠色背景代表使用者自己傳出的內容，"
    "灰色背景代表對方傳來的內容；不要使用左右位置判斷訊息屬於誰。"
    "系統已確認這個對話有新訊息，因此必須產生回覆。"
    "請找出畫面中最下方的綠色背景訊息，依畫面由上到下收集它之後所有可見的灰色背景訊息；"
    "若畫面沒有綠色背景訊息，就收集所有可見的灰色背景訊息。"
    "若灰色訊息含有回覆式 box 引用預覽，只收集 box 外的新內容，不要重複收集引用內容。"
    "文字、貼圖、照片、影片、語音、其他音訊與純表情符號都要依順序記錄進 incoming_summary；"
    "非文字內容使用簡短客觀描述，並保留畫面上看得到的長度。"
    "只處理這張截圖目前看得到的內容，不可向上捲動、推測或補入畫面外訊息。"
    "請回傳非空的 incoming_summary 與 msg_reply。"
)
```

- [x] **Step 4: Run focused AI tests and confirm GREEN**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q app/desktop/tests/test_ai.py
```

Expected: every AI test passes, including structured-output retry, raw-response logging, unsafe-link regeneration, persona isolation, and the new color prompt contract.

### Task 3: Remove the monitor skip path and pin the always-reply flow

**Files:**
- Modify: `app/desktop/tests/test_monitor.py`
- Modify: `app/desktop/tests/test_metrics_integration_contract.py`
- Modify: `app/desktop/src/sweety_app/monitor.py`
- Test: `app/desktop/tests/test_ai.py`

- [x] **Step 1: Update monitor fixtures and successful-flow expectations**

Change every valid monitor fixture to omit `action`, including the default:

```python
@dataclass
class FakeAi:
    decision: ReplyDecision = ReplyDecision(
        incoming_summary="你還記得那個網站嗎？",
        msg_reply="我有點忘了，是哪個？",
    )
```

Delete the two tests that intentionally construct an accepted skip decision. Update `test_successful_cycle_logs_stage_events_and_ai_decision` so its AI event assertion is:

```python
assert {key: ai_event[key] for key in ("event", "target", "incoming_summary", "msg_reply")} == {
    "event": "ai_request_succeeded",
    "target": "Rose",
    "incoming_summary": "對方最後一則訊息",
    "msg_reply": "這是我的回覆",
}
assert "action" not in ai_event
```

Change the retained-screenshot test to use a valid reply, expect `run_cycle()` to be `True`, and assert that the reply was sent while `screenshot_retained` contains `/tmp/test-line-chat.png`.

- [x] **Step 2: Add a source-level regression guard against skip returning**

Add to `test_metrics_integration_contract.py`:

```python
def test_monitor_has_no_ai_skip_branch():
    monitor_source = (SOURCE_DIR / "monitor.py").read_text()

    assert "decision.should_reply" not in monitor_source
    assert "ai_decision_skipped" not in monitor_source
    assert "ai_decision_skip" not in monitor_source
```

- [x] **Step 3: Run focused tests and confirm RED**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q \
  app/desktop/tests/test_ai.py \
  app/desktop/tests/test_monitor.py \
  app/desktop/tests/test_metrics_integration_contract.py
```

Expected: monitor tests fail because production logging still accesses `decision.action`, and the source contract finds the old skip branch.

- [x] **Step 4: Remove action logging and the skip branch from the monitor**

Change the successful AI event to:

```python
self._log(
    "ai_request_succeeded",
    target=target_name,
    incoming_summary=decision.incoming_summary,
    msg_reply=decision.msg_reply,
)
```

After the existing stop check, proceed directly to reply-delay calculation. Delete this block completely:

```python
if not decision.should_reply:
    self._log("ai_decision_skipped", target=target_name, action=decision.action)
    self._close_chat(target_name, "ai_decision_skip")
    continue
```

Do not alter delay, send verification, persistence, callback, screenshot cleanup, stop interruption, or exception recovery behavior.

- [x] **Step 5: Run focused tests and confirm GREEN**

```bash
rtk app/desktop/.venv/bin/python -m pytest -q \
  app/desktop/tests/test_ai.py \
  app/desktop/tests/test_monitor.py \
  app/desktop/tests/test_metrics_integration_contract.py
```

Expected: all focused tests pass and no product code or reply-contract test accepts `skip`.

- [x] **Step 6: Commit the implementation**

```bash
rtk git add \
  app/desktop/src/sweety_app/ai.py \
  app/desktop/src/sweety_app/monitor.py \
  app/desktop/tests/test_ai.py \
  app/desktop/tests/test_monitor.py \
  app/desktop/tests/test_metrics_integration_contract.py \
  docs/superpowers/plans/2026-07-31-no-skip-color-chat-reply.md
rtk git commit -m "fix: always reply using chat bubble colors"
```

### Task 4: Verify, rebuild the diagnostic App, and sync canonical main

**Files:**
- Modify: `docs/superpowers/plans/2026-07-31-no-skip-color-chat-reply.md` (checkbox tracking only)
- Verify: `app/desktop/dist/Sweety.app`

- [x] **Step 1: Run the complete desktop suite and repository checks**

From `app/desktop`:

```bash
rtk .venv/bin/python -m pytest -q
```

From the repository root:

```bash
rtk git diff --check
rtk git status --short --branch
rtk rg -n 'action.?=.?"skip"|ai_decision_skipped|ai_decision_skip|decision\.should_reply' \
  app/desktop/src/sweety_app
```

Expected: the complete suite passes; diff checks are clean; the product contract search has no matches; only the unrelated `videos/` directory is untracked.

- [x] **Step 2: Stop an idle local App without starting monitoring or messaging**

Check `http://127.0.0.1:8891/api/monitor/status` if the App is running. If monitoring is active, stop it through the existing local API, then quit the App normally. Do not open a chat or send a LINE message for verification.

- [x] **Step 3: Rebuild the logging-enabled local test App**

```bash
rtk app/desktop/build_app.sh
```

Expected: the build completes with `SWEETY_LOG_ENABLED=1`, PyInstaller produces `app/desktop/dist/Sweety.app`, and the build's signing verification succeeds.

- [x] **Step 4: Verify the built diagnostic contract and signature**

```bash
/usr/libexec/PlistBuddy \
  -c 'Print :LSEnvironment:SWEETY_LOG_ENABLED' \
  app/desktop/dist/Sweety.app/Contents/Info.plist
codesign --verify --deep --strict app/desktop/dist/Sweety.app
```

Expected: `PlistBuddy` prints `1` and `codesign` exits successfully. Leave the App stopped.

- [x] **Step 5: Record rollout completion, commit, and push `main`**

Mark completed checkboxes in this plan, then run:

```bash
rtk git add docs/superpowers/plans/2026-07-31-no-skip-color-chat-reply.md
rtk git commit -m "docs: complete color-based reply rollout"
rtk git push origin main
```

- [x] **Step 6: Confirm the final canonical state**

```bash
rtk git diff --check
rtk git status --short --branch
rtk git rev-parse HEAD
rtk git rev-parse origin/main
```

Expected: local and remote `main` resolve to the same commit; the tree is clean except for the unrelated untracked `videos/`; no feature branch or worktree exists; the rebuilt diagnostic App remains stopped.
