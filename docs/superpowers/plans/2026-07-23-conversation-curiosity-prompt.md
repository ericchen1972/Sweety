# Conversation Curiosity Prompt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every persona sustain suspicious conversations with natural curiosity through one synchronized shared prompt, then publish and verify the server catalog and local application.

**Architecture:** Add one prominent conversation-continuation section to the bundled Python prompt and SQL catalog prompt. Protect existing installations with a narrowly scoped schema-v5 migration, enforce source equality through pytest, deploy with the existing catalog helper, and rebuild the macOS app.

**Tech Stack:** Python 3, SQLite, pytest, MySQL seed SQL, PHP deployment helper, PyInstaller/macOS build scripts

---

### Task 1: Lock The Conversation-Continuation Contract

**Files:**
- Modify: `app/desktop/tests/test_prompt_contract.py`
- Modify: `app/desktop/tests/test_database_migrations.py`

- [x] **Step 1: Add a prompt-section extractor and failing shared-policy tests**

Add `_conversation_continuation()` that extracts text between `對話延續與好奇心：` and `人設知識邊界：`. For both bundled and SQL prompt fixtures, assert that the section requires a natural `對話鉤子`, supports `追問` or `好奇`, rejects mechanically questioning every message, covers `不打擾了` and `有空再聊`, and keeps a concrete question open when the persona says they are busy.

- [x] **Step 2: Require complete prompt equality**

Add:

```python
def test_bundled_and_sql_prompts_are_identical():
    assert DEFAULT_SYSTEM_PROMPT_TEMPLATE == _sql_catalog_prompt()
```

- [x] **Step 3: Add schema-v5 migration tests**

Create a version-4 database containing the prior official prompt marker and assert migration replaces it with `DEFAULT_SYSTEM_PROMPT_TEMPLATE` and sets schema version 5. Create another version-4 database containing an unrelated valid remote prompt and assert migration preserves it.

- [x] **Step 4: Run tests and verify RED**

Run: `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_prompt_contract.py app/desktop/tests/test_database_migrations.py`

Expected: FAIL because the new section is absent and the current schema remains version 4.

### Task 2: Implement The Shared Prompt And Local Migration

**Files:**
- Modify: `app/desktop/src/sweety_app/catalog.py`
- Modify: `app/tools/base_catalog.sql`
- Modify: `app/desktop/src/sweety_app/database.py`

- [x] **Step 1: Add identical shared prompt text**

Insert this policy, with identical wording in Python and SQL:

```text
對話延續與好奇心：
- 只要決定回覆，就要盡量留下自然的「對話鉤子」，讓對方很容易接著說下去；可以追問尚未說完的細節、表達真實好奇、對模糊處表示困惑，或簡短反應後請對方補充。
- 好奇心要符合目前人設、雙方熟稔度與最近上下文；不必每則都用問號，也不要機械式反問、連續盤問或重複同一句型。
- 不要只用「你先忙」、「不打擾了」、「有空再聊」、「晚點再說」等話語主動結束對話。即使表示正在忙、現在不方便或需要晚點處理，也要保留一個對方現在就能回答的具體疑問或未完成話題。
- 當對方準備離開、表示等你或讓話題自然中止時，除非安全規則要求停止，應從先前內容挑一個相關且低壓的細節自然追問，不要只是接受對話結束。
```

- [x] **Step 2: Add the schema-v5 migration**

Set `CURRENT_SCHEMA_VERSION = 5`. For databases below version 5, replace the prompt only when it lacks `對話延續與好奇心：` and contains the prior official marker `不要每次都反問，也不要每次都找藉口；依照最近對話自然決定。`. Preserve unrelated remote prompts.

- [x] **Step 3: Run focused tests and verify GREEN**

Run: `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_prompt_contract.py app/desktop/tests/test_database_migrations.py app/desktop/tests/test_catalog_content_contract.py app/desktop/tests/test_remote_catalog.py`

Expected: all tests PASS.

- [x] **Step 4: Commit prompt implementation**

```bash
git add app/desktop/src/sweety_app/catalog.py app/tools/base_catalog.sql app/desktop/src/sweety_app/database.py app/desktop/tests/test_prompt_contract.py app/desktop/tests/test_database_migrations.py
git commit -m "feat: keep AI conversations naturally open"
```

### Task 3: Verify The Local Codebase

**Files:**
- Verify only

- [x] **Step 1: Verify prompt-source equality and formatting**

Run: `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_prompt_contract.py && git diff --check`

Expected: all prompt tests PASS and `git diff --check` exits 0.

- [x] **Step 2: Run the complete desktop suite**

Run: `app/desktop/.venv/bin/pytest -q`

Expected: all pytest tests PASS.

- [x] **Step 3: Run the PHP catalog contract**

Run: `php web/tests/sweety_catalog_contract_test.php`

Expected: the catalog contract reports PASS.

### Task 4: Deploy And Verify The Server Catalog

**Files:**
- Modify: `app/tools/verify_remote_catalog.py`

- [x] **Step 1: Extend live verification**

Read `systemPromptTemplate` from the live response and assert it contains `對話延續與好奇心：`, `對話鉤子`, `不打擾了`, and `有空再聊`, while preserving the existing 24-persona checks.

- [x] **Step 2: Deploy through the existing helper**

Run: `php app/tools/deploy_base_catalog.php`

Expected: remote migration succeeds and reports the expected table counts and checks.

- [x] **Step 3: Verify the live API**

Run: `app/desktop/.venv/bin/python app/tools/verify_remote_catalog.py`

Expected: `Remote catalog OK` and the new prompt assertions pass.

- [x] **Step 4: Commit live-verification coverage**

```bash
git add app/tools/verify_remote_catalog.py
git commit -m "test: verify live conversation prompt"
```

### Task 5: Rebuild And Verify The Local App

**Files:**
- Verify generated artifacts only

- [x] **Step 1: Run the existing macOS application build**

Run: `cd app/desktop && ./build_app.sh`

Expected: the build exits 0 and produces the Sweety application bundle under `dist/`.

- [x] **Step 2: Verify the bundled prompt**

Inspect the built application's packaged Python resources or launch it against a temporary database and assert the cached prompt contains `對話延續與好奇心：`.

- [x] **Step 3: Review final scope**

Run: `git status --short --branch && git log -5 --oneline`

Expected: only the approved design, tests, shared prompts, migration, and live verifier are committed; build artifacts remain ignored.
