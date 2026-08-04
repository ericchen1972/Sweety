# Japanese App and Catalog Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add end-to-end Japanese localization to the Sweety desktop App and its 24-persona remote catalog without changing AI or automation behavior.

**Architecture:** Treat `ja` as a first-class locale from the canonical persona JSON through generated artifacts, MySQL/PHP catalog responses, SQLite caching, the local API, React, and AppKit. Keep `content_zh_tw` as the sole AI prompt source, use bundled three-language data for clean installs and offline fallback, and require complete three-language remote payloads before atomically replacing SQLite data.

**Tech Stack:** React 19, TypeScript, Vitest, Python 3.11+, FastAPI, SQLite, pytest, PHP, MySQL, PyInstaller, macOS AppKit.

---

## File map

- `app/catalog/base_personas.json`: canonical 24-persona content in `zh-TW`, `en`, and `ja`.
- `app/tools/generate_persona_catalogs.py`: validates locales and generates frontend, Python, and MySQL artifacts.
- `app/frontend/src/catalog.generated.json`: generated bundled React catalog.
- `app/desktop/src/sweety_app/catalog_personas.py`: generated bundled Python catalog.
- `app/tools/base_personas.generated.sql`: generated MySQL persona upsert.
- `app/tools/base_catalog.sql`: remote MySQL schema and seed contract.
- `web/sweety-catalog-lib.php`: remote catalog serialization.
- `web/tests/sweety_catalog_contract_test.php`: PHP response contract.
- `app/tools/verify_remote_catalog.py`: post-deployment three-locale verifier.
- `app/desktop/src/sweety_app/database.py`: SQLite schema and migration.
- `app/desktop/src/sweety_app/repositories.py`: SQLite seed, replace, lookup, and API mapping.
- `app/desktop/src/sweety_app/remote_catalog.py`: remote payload validation and atomic refresh.
- `app/frontend/src/domain.ts`: locale type, detection, and localized formatters.
- `app/frontend/src/i18n.ts`: React UI copy dictionaries.
- `app/frontend/src/App.tsx`: presentation wiring and remaining inline strings.
- `app/frontend/src/storage.ts`: state normalization and bundled fallback.
- `app/desktop/src/sweety_app/config.py`: macOS locale normalization.
- `app/desktop/src/sweety_app/panel.py`: native panel, menu, update, and timeout copy.
- `app/desktop/src/sweety_app/__main__.py`: native permission copy and locale-aware About loader wiring.
- `app/desktop/src/sweety_app/about.py`: locale-aware sanitized About content loading.
- `web/about_sweety_ja.html`: remote Japanese About content.
- `app/tools/deploy_base_catalog.php`: schema/catalog/About deployment inputs.

### Task 1: Canonical Japanese persona catalog and generated artifacts

**Files:**
- Modify: `app/catalog/base_personas.json`
- Modify: `app/tools/generate_persona_catalogs.py`
- Modify: `app/desktop/tests/test_catalog_content_contract.py`
- Modify: `app/desktop/tests/test_catalog_generator.py`
- Modify: `app/frontend/src/catalog.test.ts`
- Regenerate: `app/frontend/src/catalog.generated.json`
- Regenerate: `app/desktop/src/sweety_app/catalog_personas.py`
- Regenerate: `app/tools/base_personas.generated.sql`

- [ ] **Step 1: Write failing three-locale catalog tests**

Add assertions that the canonical and generated catalogs contain exactly 24 personas and that every `name.ja` and `content.ja` is non-empty. Require at least 180 Japanese characters per persona, verify the first persona name is `慎重な経理アシスタント`, and assert its content contains `王筱蘭`, `70万台湾ドル`, and a natural Japanese anti-fraud hesitation line. Add a generator test asserting `name_ja` and `content_ja` appear in generated SQL while `BASE_PERSONA_TEXT` still selects `content["zh-TW"]`.

```python
assert len(BASE_PERSONAS) == 24
for persona in BASE_PERSONAS:
    assert persona["name"]["ja"].strip()
    assert len(persona["content"]["ja"].strip()) >= 180
assert BASE_PERSONAS[0]["name"]["ja"] == "慎重な経理アシスタント"
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd app/desktop
uv run pytest tests/test_catalog_content_contract.py tests/test_catalog_generator.py -q
cd ../frontend
npm test -- --run src/catalog.test.ts
```

Expected: failures report missing `ja` keys and missing SQL columns.

- [ ] **Step 3: Add complete Japanese persona content**

For each of the existing 24 IDs, add a natural Japanese display name and full Japanese `content` preserving the same facts, age, occupation, family situation, caution level, reply length, interruptions, emoji frequency, and conversational boundaries as the canonical Chinese content. Preserve all IDs, images, sort order, gender, and age groups. Do not translate Taiwanese personal names into unrelated Japanese identities.

Update the generator to validate `SUPPORTED_LOCALES = ("zh-TW", "en", "ja")`, pass all three localized values through generated JSON/Python, and emit `name_ja` and `content_ja` in the MySQL upsert. Keep:

```python
BASE_PERSONA_TEXT = {
    persona["id"]: persona["content"]["zh-TW"]
    for persona in BASE_PERSONAS
}
```

- [ ] **Step 4: Regenerate and verify GREEN**

Run:

```bash
python app/tools/generate_persona_catalogs.py
cd app/desktop
uv run pytest tests/test_catalog_content_contract.py tests/test_catalog_generator.py -q
cd ../frontend
npm test -- --run src/catalog.test.ts
```

Expected: all pass and generated artifacts contain three locales.

- [ ] **Step 5: Commit**

```bash
git add app/catalog/base_personas.json app/tools/generate_persona_catalogs.py app/desktop/tests/test_catalog_content_contract.py app/desktop/tests/test_catalog_generator.py app/frontend/src/catalog.test.ts app/frontend/src/catalog.generated.json app/desktop/src/sweety_app/catalog_personas.py app/tools/base_personas.generated.sql
git commit -m "feat: add Japanese persona catalog"
```

### Task 2: Remote MySQL and PHP catalog contract

**Files:**
- Modify: `app/tools/base_catalog.sql`
- Modify: `app/tools/deploy_base_catalog.php`
- Modify: `web/sweety-catalog-lib.php`
- Modify: `web/tests/sweety_catalog_contract_test.php`
- Modify: `app/tools/verify_remote_catalog.py`

- [ ] **Step 1: Write failing server contract tests**

Extend the PHP fixture row with `name_ja` and `content_ja`, then require:

```php
assert_same('慎重な経理アシスタント', $payload['basePersonas'][0]['name']['ja']);
assert_same('日本語の人物設定', $payload['basePersonas'][0]['content']['ja']);
```

Extend the remote verifier to require exactly `{'zh-TW', 'en', 'ja'}` for both localized objects and non-empty Japanese values across all 24 personas.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
php web/tests/sweety_catalog_contract_test.php
```

Expected: missing `ja` response keys.

- [ ] **Step 3: Implement additive server schema and serialization**

Add non-null `name_ja` and `content_ja` columns to fresh schema creation and provide an idempotent existing-table upgrade in the catalog deployment path before generated data is applied. Extend insert/upsert column lists and `sweety_catalog_text()` so every response contains:

```php
'name' => [
    'zh-TW' => (string) $row['name_zh_tw'],
    'en' => (string) $row['name_en'],
    'ja' => (string) $row['name_ja'],
],
'content' => [
    'zh-TW' => (string) $row['content_zh_tw'],
    'en' => (string) $row['content_en'],
    'ja' => (string) $row['content_ja'],
],
```

The deployment preflight must stop if any of the 24 generated Japanese names or contents is empty.

- [ ] **Step 4: Run contract tests and SQL static checks**

Run the PHP contract test and search the generated/base SQL for the new columns. Expected: PHP PASS; both schema and upsert contain `name_ja` and `content_ja`.

- [ ] **Step 5: Commit**

```bash
git add app/tools/base_catalog.sql app/tools/deploy_base_catalog.php web/sweety-catalog-lib.php web/tests/sweety_catalog_contract_test.php app/tools/verify_remote_catalog.py
git commit -m "feat: serve Japanese persona catalog"
```

### Task 3: SQLite Japanese columns and repository mappings

**Files:**
- Modify: `app/desktop/src/sweety_app/database.py`
- Modify: `app/desktop/src/sweety_app/repositories.py`
- Modify: `app/desktop/tests/test_database_migrations.py`
- Modify: `app/desktop/tests/test_repositories.py`
- Modify: `app/desktop/tests/test_api.py`

- [ ] **Step 1: Write failing migration and repository tests**

Add tests for a clean database and the immediately previous schema. Require `name_ja` and `content_ja` columns, preserved targets/settings, Japanese values seeded by persona ID, Japanese values accepted by `replace_remote_catalog()`, and `/api/state` returning `name.ja` and `content.ja`.

```python
assert {"name_ja", "content_ja"} <= column_names
assert persona["name"]["ja"] == "慎重な経理アシスタント"
assert persona["content"]["ja"]
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
cd app/desktop
uv run pytest tests/test_database_migrations.py tests/test_repositories.py tests/test_api.py -q
```

Expected: missing SQLite columns and missing API keys.

- [ ] **Step 3: Implement migration and mappings**

Increment `CURRENT_SCHEMA_VERSION`. Rebuild or alter `base_personas` using the project’s existing migration pattern, preserve current rows, and fill Japanese values from bundled `BASE_PERSONAS` by ID. Extend clean seed, remote replacement, and `_base_persona_for_api()` with `name_ja`/`content_ja`. Keep `get_base_persona_text()` selecting `content_zh_tw`.

- [ ] **Step 4: Verify GREEN**

Rerun the three focused test modules. Expected: all pass, including the explicit Chinese AI-source assertion.

- [ ] **Step 5: Commit**

```bash
git add app/desktop/src/sweety_app/database.py app/desktop/src/sweety_app/repositories.py app/desktop/tests/test_database_migrations.py app/desktop/tests/test_repositories.py app/desktop/tests/test_api.py
git commit -m "feat: persist Japanese persona content"
```

### Task 4: Three-locale remote synchronization

**Files:**
- Modify: `app/desktop/src/sweety_app/remote_catalog.py`
- Modify: `app/desktop/tests/test_remote_catalog.py`

- [ ] **Step 1: Write failing parser tests**

Use a complete three-language payload and assert sync succeeds and stores Japanese. Add separate cases where `name.ja` or `content.ja` is absent/blank; assert sync returns `False` and the repository replacement method is not called.

- [ ] **Step 2: Run test and verify RED**

```bash
cd app/desktop
uv run pytest tests/test_remote_catalog.py -q
```

Expected: Japanese values are discarded or incomplete payloads are accepted.

- [ ] **Step 3: Require Japanese atomically**

Change:

```python
REQUIRED_LOCALES = ("zh-TW", "en", "ja")
```

Keep parsing complete before `replace_remote_catalog()` so a missing Japanese value cannot partially update SQLite.

- [ ] **Step 4: Verify GREEN and commit**

Rerun the focused test, then commit:

```bash
git add app/desktop/src/sweety_app/remote_catalog.py app/desktop/tests/test_remote_catalog.py
git commit -m "feat: sync Japanese catalog locale"
```

### Task 5: React locale foundation and Japanese copy

**Files:**
- Modify: `app/frontend/src/domain.ts`
- Modify: `app/frontend/src/domain.test.ts`
- Modify: `app/frontend/src/i18n.ts`
- Modify: `app/frontend/src/i18n.test.ts`
- Modify: `app/frontend/src/UpdateNotice.test.ts`

- [ ] **Step 1: Write failing locale and copy tests**

Require `detectLocale("ja")`, `detectLocale("ja-JP")`, and `detectLocale("ja-JP-u-ca-japanese")` to return `ja`. Assert `getCopy("ja")` contains Japanese representative values for navigation, start/stop, target editor, AI settings, errors, update notice, and About; assert all three dictionaries have identical recursive key paths.

- [ ] **Step 2: Run tests and verify RED**

```bash
cd app/frontend
npm test -- --run src/domain.test.ts src/i18n.test.ts src/UpdateNotice.test.ts
```

Expected: `ja` is rejected by the type or falls back to English.

- [ ] **Step 3: Implement locale and complete copy**

Use:

```ts
export type Locale = "zh-TW" | "en" | "ja";

export function detectLocale(language?: string): Locale {
  const normalized = language?.toLowerCase() ?? "";
  if (normalized === "zh-tw" || normalized.startsWith("zh-hant")) return "zh-TW";
  if (normalized === "ja" || normalized.startsWith("ja-")) return "ja";
  return "en";
}
```

Add a complete `ja` copy object matching the English/Chinese structure. Use natural Japanese product terms consistently: `開始`, `停止`, `対象`, `ペルソナ`, `返信`, `設定`, `Sweetyについて`. Extend localized duration/persona-style formatters rather than treating every non-Chinese locale as English.

- [ ] **Step 4: Verify GREEN and commit**

Run focused tests and `npm run typecheck`, then commit the five files.

### Task 6: React presentation and server catalog consumption

**Files:**
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/storage.ts`
- Modify: `app/frontend/src/storage.test.ts`
- Modify: `app/frontend/src/personaPreview.test.ts`

- [ ] **Step 1: Write failing presentation tests**

Add state normalization tests proving server-returned `name.ja`/`content.ja` remain authoritative, legacy `text` remains compatible, and bundled catalog is used only when the API has no base personas. Add Japanese persona preview/label expectations.

- [ ] **Step 2: Run tests and verify RED**

```bash
cd app/frontend
npm test -- --run src/storage.test.ts src/personaPreview.test.ts
```

Expected: Japanese typing or fallback assertions fail.

- [ ] **Step 3: Remove binary locale branches**

Move loading, retry, save/export errors, sidebar subtitle, navigation labels, and other inline Chinese/English strings into `getCopy(locale)`. Set:

```ts
document.documentElement.lang = locale === "zh-TW" ? "zh-Hant" : locale;
```

Read persona labels and previews from `persona.name[locale]` and `persona.content[locale]`, with English fallback only for defensive compatibility. Do not merge bundled Japanese over a valid server payload.

- [ ] **Step 4: Verify GREEN and commit**

Run the full frontend suite, typecheck, and build. Commit only frontend source/tests touched by this task.

### Task 7: macOS locale, AppKit panel, and permission prompts

**Files:**
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/desktop/src/sweety_app/panel.py`
- Modify: `app/desktop/src/sweety_app/__main__.py`
- Modify: `app/desktop/tests/test_config.py`
- Modify: `app/desktop/tests/test_panel_bridge.py`
- Modify: `app/desktop/tests/test_permissions.py`

- [ ] **Step 1: Write failing native Japanese tests**

Change the old `ja-JP -> en` expectation to `ja`. Add Japanese expectations for idle/running/paused/error status, current target punctuation, Start/Stop, management, quit, update notice, AI timeout, missing permission names, title, explanatory text, and buttons.

- [ ] **Step 2: Run tests and verify RED**

```bash
cd app/desktop
uv run pytest tests/test_config.py tests/test_panel_bridge.py tests/test_permissions.py -q
```

Expected: Japanese normalizes to or renders as English.

- [ ] **Step 3: Implement dictionary-based native copy**

Normalize Japanese in `config.py`. Replace `"zh-TW" if ... else "en"` branches with a locale helper that returns `zh-TW`, `ja`, or `en`. Add `ja` entries to status, update, timeout, panel/menu, and permission mappings without changing callbacks or state transitions.

- [ ] **Step 4: Verify GREEN and commit**

Rerun focused tests, then commit native implementation and tests.

### Task 8: Japanese About content

**Files:**
- Create: `web/about_sweety_ja.html`
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/desktop/src/sweety_app/about.py`
- Modify: `app/desktop/src/sweety_app/__main__.py`
- Modify: `app/desktop/tests/test_about.py`
- Modify: `app/tools/deploy_base_catalog.php`
- Modify: `web/tests/about.test.mjs`

- [ ] **Step 1: Write failing locale-aware About tests**

Require Japanese locale to request the Japanese URL, sanitize scripts/styles/forms exactly as before, preserve allowed HTTPS links/images, and return Japanese headings. Extend the web test to require `<html lang="ja">`, Japanese metadata, `Sweetyについて`, safety notice, GitHub, author contact, and no missing local image asset references.

- [ ] **Step 2: Run tests and verify RED**

```bash
cd app/desktop
uv run pytest tests/test_about.py -q
cd ../../
node --test web/tests/about.test.mjs
```

Expected: no Japanese URL/content exists.

- [ ] **Step 3: Implement Japanese About selection and content**

Add `ABOUT_SWEETY_JA_URL` defaulting to `https://sweety.tw/about_sweety_ja.html`. Select it once from the detected startup locale and pass it through the existing `AboutContentClient`; keep sanitizer behavior unchanged. Create a complete Japanese page covering what Sweety is, design principles, safety disclaimer, open source, Eric’s projects/contact, and the footer. Add the Japanese page to catalog deployment uploads.

- [ ] **Step 4: Verify GREEN and commit**

Run Python and Node About tests, then commit all seven files.

### Task 9: Full regression, App build, and final Git delivery

**Files:**
- Verify: all changed files
- Preserve: `videos/`

- [ ] **Step 1: Run complete automated suites**

```bash
cd app/frontend
npm test
npm run typecheck
npm run build
cd ../desktop
uv run pytest
cd ../../
php web/tests/sweety_catalog_contract_test.php
node --test web/tests/about.test.mjs web/tests/homepage.test.mjs
git diff --check
```

Expected: every command exits 0 with no new warnings or failures.

- [ ] **Step 2: Build and verify the macOS App**

```bash
cd app/desktop
./build_app.sh
codesign --verify --deep --strict dist/Sweety.app
```

Expected: build completes and codesign verification exits 0. This is a logging-enabled local test build, not a DMG/release build.

- [ ] **Step 3: Review scope and repository status**

Confirm AI persona lookup still selects `content_zh_tw`, only expected localization/schema/test files changed, and `videos/` remains untracked and untouched.

- [ ] **Step 4: Commit any final generated or verification adjustments**

```bash
git add -u
git commit -m "test: verify Japanese app localization"
```

Skip this commit if the worktree has no tracked changes after verification.

- [ ] **Step 5: Push canonical main and verify remote**

```bash
git push origin main
git ls-remote origin refs/heads/main
git rev-parse HEAD
```

Expected: the remote `refs/heads/main` SHA equals local `HEAD`. Do not deploy the production catalog server or publish a DMG in this task.
