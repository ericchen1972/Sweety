# Reply Language Following Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Sweety reply in the other party’s latest conversational language while preserving original-language summaries and identical App/server prompt behavior.

**Architecture:** Add one shared Chinese-language contract section to the bundled system prompt and the SQL server seed, without passing App locale into the AI request. Existing prompt parity tests keep both sources identical, while message-construction tests prove the rule reaches the actual model system message.

**Tech Stack:** Python 3.11, pytest, MySQL seed SQL, PyInstaller, macOS codesign.

---

### Task 1: Define failing App and server prompt contracts

**Files:**
- Modify: `app/desktop/tests/test_prompt_contract.py`
- Modify: `app/desktop/tests/test_ai.py`

- [ ] **Step 1: Add a prompt-section extractor and language contract test**

Add to `test_prompt_contract.py`:

```python
def _reply_language(prompt: str) -> str:
    match = re.search(r"回覆語言：\n(.*?)\n\n歷史紀錄：", prompt, flags=re.DOTALL)
    assert match is not None, "prompt is missing the reply-language section"
    return match.group(1)


def test_reply_language_follows_latest_meaningful_message_without_translating_summary(prompt):
    language = _reply_language(prompt)
    for required in (
        "msg_reply",
        "最新一則",
        "主要語言",
        "混用多種語言",
        "最下方",
        "貼圖、圖片、影片、語音",
        "最近對話的主要語言",
        "專有名詞",
        "incoming_summary",
        "原始語言",
        "不要翻譯",
    ):
        assert required in language


def test_bundled_and_sql_prompts_share_the_same_reply_language_contract():
    assert _reply_language(DEFAULT_SYSTEM_PROMPT_TEMPLATE) == _reply_language(_sql_catalog_prompt())
```

- [ ] **Step 2: Require the built model message to contain the contract**

In `test_prompt_isolates_persona_and_sends_role_preserving_history_with_image()`, assert:

```python
assert "回覆語言：" in system_prompt
assert "msg_reply 必須使用對方最新一則" in system_prompt
assert "incoming_summary" in system_prompt
assert "不要翻譯" in system_prompt
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
cd app/desktop
uv run pytest tests/test_prompt_contract.py tests/test_ai.py::test_prompt_isolates_persona_and_sends_role_preserving_history_with_image -q
```

Expected: failures state that both bundled and SQL prompts lack the reply-language section.

### Task 2: Add identical language rules to App and server prompts

**Files:**
- Modify: `app/desktop/src/sweety_app/catalog.py`
- Modify: `app/tools/base_catalog.sql`
- Test: `app/desktop/tests/test_prompt_contract.py`
- Test: `app/desktop/tests/test_ai.py`

- [ ] **Step 1: Insert the same contract before `歷史紀錄：` in both prompt sources**

Insert this exact section in both files:

```text
回覆語言：
- msg_reply 必須使用對方最新一則可辨識實質文字訊息的主要語言；對方用日文就以自然日文回覆，用英文就以英文回覆，用中文就以中文回覆。App 介面語言與人設說明使用的語言都不能取代這項判斷。
- 同一批訊息混用多種語言時，以畫面中最下方、時間最新的實質文字為準。
- 最新內容只有貼圖、圖片、影片、語音或其他沒有可辨識文字的媒體時，沿用最近對話的主要語言；歷史也不足以判斷時，才沿用目前對話可合理推定的語言。
- 人名、品牌、帳號顯示名稱、專有名詞與對方原本用詞可以保留，不要為了統一語言而強制翻譯。
- incoming_summary 必須保留對方的原始語言、字句與順序，不要翻譯成系統提示、App 介面或人設說明的語言。
```

- [ ] **Step 2: Run focused tests and verify GREEN**

```bash
cd app/desktop
uv run pytest tests/test_prompt_contract.py tests/test_ai.py::test_prompt_isolates_persona_and_sends_role_preserving_history_with_image -q
```

Expected: all focused tests pass, including bundled/SQL full prompt identity.

- [ ] **Step 3: Commit the behavior change**

```bash
git add app/desktop/src/sweety_app/catalog.py app/tools/base_catalog.sql app/desktop/tests/test_prompt_contract.py app/desktop/tests/test_ai.py
git commit -m "feat: follow counterpart reply language"
```

### Task 3: Full verification and logging-enabled test build

**Files:**
- Verify: `app/desktop/src/sweety_app/catalog.py`
- Verify: `app/tools/base_catalog.sql`
- Preserve: `videos/`

- [ ] **Step 1: Run full desktop and server-related regression**

```bash
cd app/desktop
uv run pytest
cd ../..
php web/tests/sweety_catalog_contract_test.php
git diff --check
```

Expected: all commands exit 0; existing AI, safety, catalog, database, panel, and API tests remain green.

- [ ] **Step 2: Build the test App**

```bash
cd app/desktop
./build_app.sh
```

Expected: `dist/Sweety.app` is rebuilt with `SWEETY_LOG_ENABLED=1` and the script exits 0.

- [ ] **Step 3: Verify signature, logging flag, prompt contents, and Git scope**

```bash
codesign --verify --deep --strict dist/Sweety.app
/usr/libexec/PlistBuddy -c "Print :LSEnvironment:SWEETY_LOG_ENABLED" dist/Sweety.app/Contents/Info.plist
cd ../..
rg -n "msg_reply 必須使用對方最新一則" app/desktop/src/sweety_app/catalog.py app/tools/base_catalog.sql
git status --short --branch
```

Expected: codesign exits 0, logging prints `1`, both prompt sources match, and only `videos/` remains untracked. Do not create a DMG, deploy the server, or push unless the user separately requests it.
