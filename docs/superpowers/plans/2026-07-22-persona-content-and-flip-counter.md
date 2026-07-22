# Persona Content And Flip Counter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace duplicate persona editorial fields with one canonical localized content field for all twenty-four personas, derive card previews from that content, and ship the requested homepage instructions and split-flap aggregate counter.

**Architecture:** Keep operational catalog metadata but reduce persona copy to localized `name` and `content`. Migrate MySQL and SQLite by rebuilding the persona tables, update the remote contract atomically, and keep one canonical set of detailed fallback content in each runtime. Render card excerpts through a pure helper and implement the homepage flip display with dependency-free digit-state helpers plus CSS flap layers.

**Tech Stack:** MySQL/PHP, Python 3.11/SQLite/pytest, React 19/TypeScript/Vitest, static HTML/CSS/ES modules/Node test runner.

---

The workspace root is not a Git repository, so the normal commit step after each task is replaced by a diff/status checkpoint and fresh tests.

### Task 1: Lock The Simplified Remote And Local Contract

**Files:**
- Modify: `app/desktop/tests/test_remote_catalog.py`
- Modify: `app/desktop/tests/test_repositories.py`
- Modify: `app/desktop/tests/test_database_migrations.py`
- Modify: `app/frontend/src/domain.ts`
- Create: `app/frontend/src/catalog.test.ts`

- [ ] **Step 1: Write the failing remote payload test**

Change the fixture persona to the new shape and assert legacy keys are absent:

```python
{
    "id": "remote-persona",
    "ageGroup": "35-50",
    "gender": "female",
    "name": {"zh-TW": "遠端人設", "en": "Remote Persona"},
    "content": {"zh-TW": "完整人物資料與風格內容", "en": "Complete character and style content"},
    "image": "/images/personas/remote.jpg",
}
```

Assert `get_base_persona_text("remote-persona")` equals the Traditional Chinese `content` and that `summary`, `profile`, `style`, and `text` are not returned by `list_base_personas()`.

- [ ] **Step 2: Write the failing SQLite schema migration test**

Create a version-3 database with the legacy columns, insert one persona, run `Database.migrate()`, and assert:

```python
columns = {row["name"] for row in connection.execute("PRAGMA table_info(base_personas)")}
assert columns == {
    "id", "age_group", "gender", "name_zh_tw", "name_en",
    "content_zh_tw", "content_en", "image", "sort_order", "updated_at",
}
assert migrated["content_zh_tw"] == legacy["text_zh_tw"]
```

- [ ] **Step 3: Write the failing frontend contract test**

Change `BasePersona` expectations to require:

```ts
type BasePersona = {
  id: string;
  ageGroup: AgeGroup;
  gender: Gender;
  name: LocalizedText;
  content: LocalizedText;
  image: string;
};
```

Assert every bundled item has `content` and does not have `summary`, `profile`, `style`, or `text`.

- [ ] **Step 4: Run tests and verify RED**

Run:

```bash
cd app/desktop && .venv/bin/pytest tests/test_remote_catalog.py tests/test_repositories.py tests/test_database_migrations.py -q
cd app/frontend && npm test -- src/catalog.test.ts
```

Expected: failures caused by the current legacy payload and schema fields.

### Task 2: Implement SQLite, Repository, Parser, And API Contract

**Files:**
- Modify: `app/desktop/src/sweety_app/database.py`
- Modify: `app/desktop/src/sweety_app/repositories.py`
- Modify: `app/desktop/src/sweety_app/remote_catalog.py`
- Modify: `app/desktop/src/sweety_app/api.py`
- Modify: `app/frontend/src/domain.ts`

- [ ] **Step 1: Rebuild the SQLite table in schema version 4**

Set `CURRENT_SCHEMA_VERSION = 4`. For databases older than version 4, create `base_personas_v4` with only operational fields plus `name_*` and `content_*`, copy `COALESCE(NULLIF(text_*, ''), prompt_*)`, drop the old table, and rename the replacement. Fresh databases use the same final schema.

- [ ] **Step 2: Update repository writes and reads**

`replace_remote_catalog()` inserts `content_zh_tw` and `content_en`. `_base_persona_for_api()` returns only:

```python
{
    "id": row["id"],
    "ageGroup": row["age_group"],
    "gender": row["gender"],
    "name": {"zh-TW": row["name_zh_tw"], "en": row["name_en"]},
    "content": {"zh-TW": row["content_zh_tw"], "en": row["content_en"]},
    "image": row["image"],
}
```

`get_base_persona_text()` reads `content_zh_tw`.

- [ ] **Step 3: Update payload parsing and TypeScript domain types**

Require localized `content` and remove all reads of `summary`, `profile`, `style`, and `text`. Keep `id`, `ageGroup`, `gender`, `name`, and `image` validation unchanged.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 commands. Expected: all focused desktop and frontend contract tests pass.

- [ ] **Step 5: Run a workspace diff checkpoint**

Run `find app -type f -newer docs/superpowers/plans/2026-07-22-persona-content-and-flip-counter.md` and inspect only expected files because Git metadata is unavailable.

### Task 3: Replace Server Schema And Catalog Endpoint

**Files:**
- Modify: `app/tools/base_catalog.sql`
- Modify: `web/sweety-catalog.php`
- Modify: `app/tools/catalog_remote_runner.template.php`
- Modify: `app/tools/verify_remote_catalog.py`
- Create: `web/tests/sweety_catalog_contract_test.php`

- [ ] **Step 1: Write the failing PHP contract test**

Extract endpoint row mapping into a pure function and test a representative row. Expected payload:

```php
[
    'id' => 'cautious-accounting-assistant',
    'ageGroup' => '20-35',
    'gender' => 'female',
    'name' => ['zh-TW' => '謹慎的會計助理', 'en' => 'Cautious Accounting Assistant'],
    'content' => ['zh-TW' => '人物資料...', 'en' => 'Character information...'],
    'image' => '/images/personas/cautious-accounting-assistant.jpg',
]
```

Assert no legacy editorial keys are present.

- [ ] **Step 2: Run PHP test and verify RED**

Run `php web/tests/sweety_catalog_contract_test.php`.
Expected: mapping helper/content columns are missing.

- [ ] **Step 3: Rebuild the MySQL persona table contract**

The final `base_personas` columns are `id`, `slug`, `age_group_id`, `gender`, localized name/content, `image_path`, `sort_order`, and timestamps. The migration copies legacy `prompt + speech_style` into content only when a row has not yet received the new detailed content, then removes `summary_*`, `prompt_*`, `speech_style_*`, and `is_active`.

- [ ] **Step 4: Update the endpoint and verification script**

Select localized `content` directly, remove `is_active` filtering, return the simplified contract, and verify exactly 24 personas: six per age group and three per gender within each age group.

- [ ] **Step 5: Run PHP and parser tests and verify GREEN**

Run:

```bash
php web/tests/sweety_catalog_contract_test.php
cd app/desktop && .venv/bin/pytest tests/test_remote_catalog.py -q
```

Expected: both pass.

### Task 4: Rewrite All Twenty-Four Personas

**Files:**
- Modify: `app/tools/base_catalog.sql`
- Modify: `app/desktop/src/sweety_app/catalog.py`
- Modify: `app/frontend/src/catalog.ts`
- Modify: `app/desktop/tests/test_repositories.py`
- Create or modify: `app/frontend/src/catalog.test.ts`

- [ ] **Step 1: Add failing completeness assertions**

Assert 24 IDs, six items in each age group, balanced gender, localized names/content, Traditional Chinese content of at least 180 characters, and English content of at least 300 characters. Add exact Wang Xiaolan assertions for `與母親妹妹居住在新北市板橋`, `70萬`, the suspicion sentence, and supplied phrases such as `你幹嘛啦～`, `好窩`, and `母湯啦`.

- [ ] **Step 2: Run catalog tests and verify RED**

Run:

```bash
cd app/desktop && .venv/bin/pytest tests/test_repositories.py -q
cd app/frontend && npm test -- src/catalog.test.ts
```

Expected: item count/content-length and Wang Xiaolan detail assertions fail.

- [ ] **Step 3: Write detailed canonical content**

For each of the 24 existing IDs, write localized `人物資料` and `風格個性` content covering identity, work, home/family, interests, message habits, financial motive, investment tension, characteristic delays/questions, and individualized Taiwanese speech. Preserve each existing persona's age group, gender, name, image, and ordering.

- [ ] **Step 4: Keep the three runtime catalogs identical**

Ensure the server SQL, Python fallback, and TypeScript fallback contain the same localized names and content for every ID. Do not create summaries or separate style fields.

- [ ] **Step 5: Run catalog tests and verify GREEN**

Run the Task 4 focused commands. Expected: all pass with 24 personas.

### Task 5: Derive Card Preview And Update Persona Editor

**Files:**
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/i18n.ts`
- Modify: `app/frontend/src/i18n.test.ts`
- Create: `app/frontend/src/personaPreview.ts`
- Create: `app/frontend/src/personaPreview.test.ts`

- [ ] **Step 1: Write failing preview tests**

Define desired behavior:

```ts
expect(personaPreview("人物資料：\n王筱蘭住在板橋。", 10)).toBe("王筱蘭住在板橋。")
expect(personaPreview("人物資料：\n這是一段超過限制的完整人設內容", 8)).toBe("這是一段超過限...")
```

Also assert the exact Traditional Chinese guidance copy.

- [ ] **Step 2: Run tests and verify RED**

Run `cd app/frontend && npm test -- src/personaPreview.test.ts src/i18n.test.ts`.
Expected: helper and copy are missing.

- [ ] **Step 3: Implement preview and UI changes**

`personaPreview()` strips only leading section headings for compact preview, collapses whitespace, truncates by Unicode code points, and adds `...` only when truncated. `BaseCard` calls it with `item.content[locale]`. `BaseDetailModal` renders `item.content[locale]` unchanged. Clone copies that same value. Add the guidance immediately below the age/gender row.

- [ ] **Step 4: Run frontend tests, typecheck, and build**

Run:

```bash
cd app/frontend && npm test
cd app/frontend && npm run typecheck
cd app/frontend && npm run build
```

Expected: zero failures and a successful Vite build.

### Task 6: Add Homepage Copy And Split-Flap Counter

**Files:**
- Modify: `web/index.html`
- Modify: `web/homepage.js`
- Modify: `web/homepage.css`
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write failing homepage copy and digit-state tests**

Protect the two supplied Chinese strings exactly. Add pure helper assertions:

```js
assert.deepEqual(toFlipDigits({ days: 12, hours: 7 }), { days: ['1', '2'], hours: ['0', '7'] });
assert.deepEqual(changedDigitIndexes(['0', '7'], ['0', '8']), [1]);
```

Assert the HTML contains split-flap groups and the CSS contains a reduced-motion rule.

- [ ] **Step 2: Run homepage tests and verify RED**

Run `node --test web/tests/homepage.test.mjs`.
Expected: missing copy, helpers, markup, and styles.

- [ ] **Step 3: Add instruction introduction**

Insert normal intro copy and an emphasized quote immediately under the `使用說明` section heading. Add a faithful English translation and preserve the exact Traditional Chinese punctuation.

- [ ] **Step 4: Implement dependency-free split flaps**

Render variable day digits and two hour digits with top/bottom faces and a transient flipping layer. On aggregate refresh, compare old/new arrays and animate changed positions only. Keep the existing screen-reader text and no-fake-clock loader behavior.

- [ ] **Step 5: Add responsive and reduced-motion CSS**

Use dark cards, light numbers, center seam, shadows, day/hour labels, responsive digit sizing, and `@media (prefers-reduced-motion: reduce)` to remove flip animation.

- [ ] **Step 6: Run homepage tests and verify GREEN**

Run `node --test web/tests/homepage.test.mjs`.
Expected: all tests pass.

### Task 7: Full Verification, Deployment, Rebuild, And Live Checks

**Files:**
- Modify if required by deployment verification: `app/tools/deploy_base_catalog.php`
- Modify if required by deployment verification: `app/tools/deploy_homepage.php`
- Generated: `app/frontend/dist/`
- Generated: `app/desktop/dist/Sweety.app`

- [ ] **Step 1: Run full local suites**

Run:

```bash
cd app/desktop && .venv/bin/pytest -q
cd app/frontend && npm test && npm run typecheck && npm run build
node --test web/tests/homepage.test.mjs
php web/tests/sweety_catalog_contract_test.php
php web/tests/sweety_metrics_test.php
```

Expected: all tests pass with no failures.

- [ ] **Step 2: Deploy server catalog and homepage**

Run the existing configured helpers without printing credentials:

```bash
php app/tools/deploy_base_catalog.php
php app/tools/deploy_homepage.php
```

Expected: schema/data upload, 24-person catalog verification, homepage asset upload, and remote file verification succeed.

- [ ] **Step 3: Rebuild the macOS application**

Use the repository's existing build path invoked by `deploy_homepage.php`, or run its build command directly when deployment does not rebuild after this change. Expected: `app/desktop/dist/Sweety.app` is freshly produced.

- [ ] **Step 4: Verify remote and local runtime data**

Run `app/tools/verify_remote_catalog.py` and synchronize into a clean temporary SQLite database. Assert 24 rows, six per age group, simplified keys only, detailed content, and Wang Xiaolan's approved text.

- [ ] **Step 5: Visually verify desktop and mobile**

Open the local Persona Editor and live homepage. Check the age/gender guidance, derived excerpts, full-text modal, clone flow, instruction intro, split-flap proportions, mobile wrapping, and reduced-motion state. Capture screenshots only for verification evidence.

- [ ] **Step 6: Record final evidence**

Report exact test counts, deployment output, live catalog count, live homepage copy, rebuilt app path, and any residual compatibility caveat. Do not claim completion unless every required check has fresh evidence.
