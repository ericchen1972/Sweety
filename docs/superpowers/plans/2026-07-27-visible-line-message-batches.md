# Visible LINE Message Batches Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Make one LINE screenshot produce one reply decision based on every currently visible incoming item after the latest visible outgoing item, while safely skipping screenshots with nothing new.

**Architecture:** Keep the existing one-screenshot, one-model-call monitor pipeline. Replace the latest-item AI contract with an `action`, condensed `incoming_summary`, and `msg_reply` contract, then make the monitor branch on `skip` before delay, delivery, persistence, round-trip accounting, and metrics.

**Tech Stack:** Python 3.12, pytest, Pydantic AI/OpenAI-compatible API client, PyObjC/macOS automation, PyInstaller.

---

## Task 1: Replace the screenshot decision contract

**Files:**

- Modify: `app/desktop/tests/test_ai.py`
- Modify: `app/desktop/src/sweety_app/ai.py`

- [ ] **Step 1: Rewrite the AI decision test helper and prompt assertions**

Change the test JSON helper to emit:

```python
def decision_json(
    *,
    action: str = "reply",
    incoming_summary: str = "你還記得那個網站嗎？",
    msg_reply: str = "我有點忘了，是哪個？",
) -> str:
    return json.dumps(
        {
            "action": action,
            "incoming_summary": incoming_summary,
            "msg_reply": msg_reply,
        },
        ensure_ascii=False,
    )
```

Assert that the screenshot instruction explicitly tells the model to:

- find the lowest visible right-side outgoing message;
- collect all visible left-side incoming items below it in top-to-bottom order;
- collect all visible left-side items when no right-side item exists;
- never infer or retrieve content above the visible screenshot;
- return `skip` with empty strings when no new incoming item exists.

- [ ] **Step 2: Add parser tests for reply and skip**

Cover these cases:

```python
decision = client.generate_reply(...)
assert decision.action == "reply"
assert decision.incoming_summary == "先傳文字，再傳貼圖，最後補一張照片"
assert decision.msg_reply == "..."
```

```python
decision = client.generate_reply(...)
assert decision.action == "skip"
assert decision.incoming_summary == ""
assert decision.msg_reply == ""
```

Also assert that invalid actions, blank reply summaries, blank reply text, and nonempty `skip` fields retry once and then raise `ReplyGenerationError`.

- [ ] **Step 3: Run the focused tests and confirm the expected failure**

Run:

```bash
cd app/desktop
uv run pytest tests/test_ai.py -q
```

Expected: failures because `ReplyDecision` and the prompt still use `message_type`, `last_msg`, and `msg_reply`.

- [ ] **Step 4: Implement the new decision model and parser**

Use:

```python
@dataclass(frozen=True)
class ReplyDecision:
    action: str
    incoming_summary: str
    msg_reply: str

    @property
    def should_reply(self) -> bool:
        return self.action == "reply"
```

Validation rules:

- `action` must be `reply` or `skip`;
- `reply` requires nonblank `incoming_summary` and `msg_reply`;
- `skip` requires both fields to be blank;
- strip surrounding whitespace before returning;
- preserve the existing one-retry behavior for malformed or unsafe output.

Remove the obsolete media-type normalization constants and update the screenshot prompt to the approved visible-batch rules.

- [ ] **Step 5: Run the focused tests**

Run:

```bash
cd app/desktop
uv run pytest tests/test_ai.py -q
```

Expected: all AI tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/desktop/tests/test_ai.py app/desktop/src/sweety_app/ai.py
git commit -m "feat: summarize visible LINE message batches"
```

## Task 2: Skip empty batches and persist one condensed exchange

**Files:**

- Modify: `app/desktop/tests/test_monitor.py`
- Modify: `app/desktop/src/sweety_app/monitor.py`

- [ ] **Step 1: Update monitor fixtures and success expectations**

Change `FakeAi` to return the new `ReplyDecision`. Make the successful delivery test use a mixed visible batch summary such as:

```python
ReplyDecision(
    "reply",
    "對方先問網站進度，接著傳了一張貼圖，最後補上一張版面截圖",
    "有看到，我先照截圖調整版面，再跟你回報。",
)
```

Assert that the repository records exactly one condensed incoming history record and one assistant reply after confirmed delivery.

- [ ] **Step 2: Add a skip-path test**

Have the AI return:

```python
ReplyDecision("skip", "", "")
```

Assert:

- the screenshot is discarded;
- the chat is closed;
- no delay is requested;
- no message is sent;
- no exchange is persisted;
- no round-trip count changes;
- no usage metrics are recorded.

- [ ] **Step 3: Run the focused tests and confirm the expected failure**

Run:

```bash
cd app/desktop
uv run pytest tests/test_monitor.py -q
```

Expected: failures because the monitor still always delays, sends, and persists `incoming_for_history`.

- [ ] **Step 4: Implement the monitor branch**

After the decision has been produced, the screenshot deleted, and stop state checked, add:

```python
if not decision.should_reply:
    self.line.close_chat(str(target["display_name"]))
    continue
```

For successful delivery, persist:

```python
self.repository.record_exchange(
    str(target["id"]),
    decision.incoming_summary,
    decision.msg_reply,
)
```

Keep persistence after confirmed LINE delivery.

- [ ] **Step 5: Run the focused tests**

Run:

```bash
cd app/desktop
uv run pytest tests/test_monitor.py -q
```

Expected: all monitor tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/desktop/tests/test_monitor.py app/desktop/src/sweety_app/monitor.py
git commit -m "feat: skip LINE chats without new messages"
```

## Task 3: Verify the application and build the macOS app

**Files:**

- Verify: `app/desktop/tests/`
- Build output: `app/desktop/dist/Sweety.app`

- [ ] **Step 1: Run the complete desktop test suite**

Run:

```bash
cd app/desktop
uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Inspect the final diff**

Run:

```bash
git diff HEAD~2 --check
git diff HEAD~2 -- app/desktop/src/sweety_app/ai.py app/desktop/src/sweety_app/monitor.py
```

Expected: no whitespace errors, no obsolete latest-item contract, and no unrelated files.

- [ ] **Step 3: Build only `Sweety.app`**

Run:

```bash
cd app/desktop
./build_app.sh
```

Expected: `app/desktop/dist/Sweety.app` exists and no DMG is created.

- [ ] **Step 4: Verify the app bundle**

Run:

```bash
test -d app/desktop/dist/Sweety.app
codesign --verify --deep --strict app/desktop/dist/Sweety.app
spctl --assess --type execute app/desktop/dist/Sweety.app || true
```

Expected: ad-hoc code-signature verification succeeds. Gatekeeper assessment may report that the app is not notarized; this is acceptable for the requested local-use build.

- [ ] **Step 5: Make the verified app available in the main workspace**

Place the verified bundle at:

```text
/Users/eric/Documents/SweetyGame/app/desktop/dist/Sweety.app
```

Do not create a DMG and do not deploy or publish the artifact.
