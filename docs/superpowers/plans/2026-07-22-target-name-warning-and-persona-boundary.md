# Target Name Warning And Persona Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Traditional Chinese LINE target-name warning and remove duplicated shared policy from all generated base-persona content while retaining that policy in the common system prompt.

**Architecture:** Keep display copy in the existing i18n module. Make the catalog generator produce identity, profile, and persona-specific style only, then regenerate every checked-in catalog representation from the normalized canonical JSON; the bundled and SQL system prompt remain the single policy source.

**Tech Stack:** React, TypeScript, Vitest, Python 3, pytest, JSON, MySQL seed SQL

---

### Task 1: Update The Target-Name Warning

**Files:**
- Modify: `app/frontend/src/i18n.test.ts`
- Modify: `app/frontend/src/i18n.ts`

- [x] **Step 1: Write the failing localization test**

Add this assertion to the existing Traditional Chinese copy test:

```ts
expect(copy.targetNameWarning).toBe(
  "名稱設定後將不能修改，強烈建議在 LINE 上修改對方名稱，以避免對方更名。\n名稱不可包含特殊字元與表情符號，否則 Sweety 將無法正確辨識。",
);
```

- [x] **Step 2: Run the test and verify the old wording fails**

Run: `cd app/frontend && npm test -- src/i18n.test.ts`

Expected: FAIL because `targetNameWarning` still contains the old alias recommendation.

- [x] **Step 3: Replace the Traditional Chinese warning**

Set `zhTW.targetNameWarning` in `app/frontend/src/i18n.ts` to:

```ts
targetNameWarning: "名稱設定後將不能修改，強烈建議在 LINE 上修改對方名稱，以避免對方更名。\n名稱不可包含特殊字元與表情符號，否則 Sweety 將無法正確辨識。",
```

- [x] **Step 4: Run the localization test and verify it passes**

Run: `cd app/frontend && npm test -- src/i18n.test.ts`

Expected: PASS.

- [x] **Step 5: Commit the copy change**

```bash
git add app/frontend/src/i18n.ts app/frontend/src/i18n.test.ts
git commit -m "fix: clarify LINE target name warning"
```

### Task 2: Make Shared Policy Exclusive To The System Prompt

**Files:**
- Create: `app/desktop/tests/test_catalog_content_contract.py`
- Modify: `app/tools/generate_persona_catalogs.py`
- Modify: `app/catalog/base_personas.json`
- Modify: `app/frontend/src/catalog.generated.json`
- Modify: `app/desktop/src/sweety_app/catalog_personas.py`
- Modify: `app/tools/base_personas.generated.sql`

- [x] **Step 1: Write the failing catalog ownership tests**

Create `app/desktop/tests/test_catalog_content_contract.py`:

```python
from sweety_app.catalog import BASE_PERSONAS, DEFAULT_SYSTEM_PROMPT_TEMPLATE


SHARED_ZH = "你只熟悉自己生活與工作經驗內的事情"
SHARED_EN = "Stay within what this person could reasonably know from work and ordinary life"


def test_base_personas_do_not_repeat_shared_system_policy():
    for persona in BASE_PERSONAS:
        assert SHARED_ZH not in persona["content"]["zh-TW"]
        assert SHARED_EN not in persona["content"]["en"]


def test_system_prompt_retains_knowledge_and_financial_boundaries():
    assert "人設知識邊界" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
    assert "職業、年齡、生活經驗" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
    assert "對方提供投資或賺錢理由時，可以表現出興趣" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
    assert "要繼續問細節、風險、流程、能不能晚點" in DEFAULT_SYSTEM_PROMPT_TEMPLATE
```

- [x] **Step 2: Run the ownership tests and verify duplicated persona policy fails**

Run: `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_catalog_content_contract.py`

Expected: the persona-policy test FAILS because every current generated persona contains the shared suffix; the system-prompt test PASSES.

- [x] **Step 3: Remove suffix generation in both locales**

Change `canonical_content()` in `app/tools/generate_persona_catalogs.py` so both locale branches end after persona-specific style:

```python
if locale == "zh-TW":
    return f"人物資料：\n{identity}\n\n{profile}\n\n風格個性：\n{style}".strip()
return f"Character information:\n{identity}\n\n{profile}\n\nPersonality and style:\n{style}".strip()
```

- [x] **Step 4: Normalize the canonical catalog and regenerate derived artifacts**

Use a short, reviewed one-time normalization that removes only the exact existing `SHARED_ZH` and `SHARED_EN` suffixes from both locale fields in `app/catalog/base_personas.json`. Then regenerate all derived files:

```bash
app/desktop/.venv/bin/python app/tools/generate_persona_catalogs.py
```

Expected: `Generated 24 personas`; the frontend JSON, Python module, and generated SQL all update without the shared suffix. `app/tools/base_catalog.sql` retains its existing generated-persona marker and common system prompt.

- [x] **Step 5: Run ownership and prompt-contract tests**

Run: `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_catalog_content_contract.py app/desktop/tests/test_prompt_contract.py`

Expected: PASS with no duplicated shared suffix and all common system-prompt policy assertions intact.

- [x] **Step 6: Commit the catalog change**

```bash
git add app/tools/generate_persona_catalogs.py app/catalog/base_personas.json app/frontend/src/catalog.generated.json app/desktop/src/sweety_app/catalog_personas.py app/tools/base_personas.generated.sql app/desktop/tests/test_catalog_content_contract.py
git commit -m "refactor: centralize persona knowledge policy"
```

### Task 3: Full Verification

**Files:**
- Verify only

- [x] **Step 1: Verify generated content and whitespace**

Run: `rg -n "你只熟悉自己生活與工作經驗內的事情|Stay within what this person could reasonably know from work and ordinary life" app/catalog/base_personas.json app/frontend/src/catalog.generated.json app/desktop/src/sweety_app/catalog_personas.py app/tools/base_personas.generated.sql`

Expected: no matches.

Run: `git diff --check`

Expected: exit code 0.

- [x] **Step 2: Run the complete frontend suite and build**

Run: `cd app/frontend && npm test && npm run build`

Expected: all Vitest tests pass and Vite build exits 0.

- [x] **Step 3: Run the complete desktop suite**

Run: `app/desktop/.venv/bin/pytest -q`

Expected: all pytest tests pass.

- [x] **Step 4: Run the PHP catalog contract test**

Run: `php web/tests/sweety_catalog_contract_test.php`

Expected: `PASS: simplified persona contract`.

- [x] **Step 5: Review final scope**

Run: `git status --short && git diff HEAD~2 --stat`

Expected: only the approved warning, generator, regenerated artifacts, tests, design, and plan are included; no deployment files or unrelated behavior are changed.
