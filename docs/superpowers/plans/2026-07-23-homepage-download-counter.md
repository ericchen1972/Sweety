# Sweety Homepage Download Counter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Count every Windows or macOS download click and show the public total beside the download-section heading.

**Architecture:** A dedicated public PHP endpoint owns a singleton MySQL counter and remains separate from the authenticated desktop metrics endpoint. The static homepage fetches the total on load, posts once from each enabled platform download click with `keepalive`, and renders a responsive localized count without delaying the download.

**Tech Stack:** PHP 8, MysqliDb, MariaDB/MySQL, JavaScript ES modules, static HTML/CSS, Node.js test runner

---

## File structure

- Create `web/sweety-downloads-lib.php`: strict parsing for non-negative database
  and JSON counter values.
- Create `web/sweety-downloads.php`: public GET/POST controller.
- Create `web/tests/sweety_downloads_test.php`: helper, controller, and migration
  contract tests with an isolated fake database.
- Modify `app/tools/sweety_metrics.sql`: create and seed the singleton counter.
- Modify `app/tools/metrics_remote_runner.template.php`: verify the new table and
  return its total after migration.
- Modify `web/homepage.js`: fetch, format, post, and attach platform tracking.
- Modify `web/index.html`: add the localized live counter hook and bump assets.
- Modify `web/homepage.css`: right-align on large screens and stack on mobile.
- Modify `web/tests/homepage.test.mjs`: protect frontend behavior and layout.
- Modify `app/tools/deploy_homepage.php`: publish the endpoint and helper.

### Task 1: Download counter backend

**Files:**
- Create: `web/sweety-downloads-lib.php`
- Create: `web/sweety-downloads.php`
- Create: `web/tests/sweety_downloads_test.php`
- Modify: `app/tools/sweety_metrics.sql`
- Modify: `app/tools/metrics_remote_runner.template.php`

- [ ] **Step 1: Write failing helper and endpoint contract tests**

Create `web/tests/sweety_downloads_test.php` using the assertion helpers and
temporary PHP-server pattern from `sweety_metrics_test.php`. Require
`sweety-downloads-lib.php` and assert:

```php
check_same(0, sweety_downloads_parse_total(0), 'integer zero is valid');
check_same(42, sweety_downloads_parse_total('42'), 'database integer string is valid');
check_same(null, sweety_downloads_parse_total(-1), 'negative integer is invalid');
check_same(null, sweety_downloads_parse_total('1.5'), 'decimal string is invalid');
check_same(null, sweety_downloads_parse_total('18446744073709551615'), 'overflow is invalid');
```

Read the endpoint and migration as strings and require:

```php
check(str_contains($endpoint, "Cache-Control: public, max-age=60"), 'GET is briefly cached');
check(str_contains($endpoint, "Cache-Control: no-store"), 'POST is never cached');
check(str_contains($endpoint, 'total_downloads = total_downloads + 1'), 'POST increments atomically');
check(!str_contains($endpoint, 'REMOTE_ADDR'), 'endpoint does not read client IP');
check((bool) preg_match('/CREATE TABLE(?: IF NOT EXISTS)? sweety_download_totals/i', $migration), 'migration creates download singleton');
check((bool) preg_match('/total_downloads\\s+BIGINT\\s+UNSIGNED/i', $migration), 'download total uses unsigned BIGINT');
check((bool) preg_match('/INSERT INTO sweety_download_totals[\\s\\S]*VALUES\\s*\\(1,\\s*0\\)/i', $migration), 'migration seeds singleton');
```

The fake `MysqliDb` fixture must serve a persisted integer from a temporary JSON
file. Test these HTTP cases:

```php
check_same(200, $get['status'], 'GET succeeds');
check_same(['totalDownloads' => 0], json_decode($get['body'], true), 'GET returns zero');
check_same(200, $post['status'], 'POST succeeds');
check_same(['totalDownloads' => 1], json_decode($post['body'], true), 'POST returns incremented total');
check_same(200, $secondPost['status'], 'second POST succeeds');
check_same(['totalDownloads' => 2], json_decode($secondPost['body'], true), 'repeated click counts again');
check_same(405, $put['status'], 'unsupported method is rejected');
check_same(500, $failure['status'], 'database failure is reported');
```

- [ ] **Step 2: Run the backend test and verify RED**

```bash
php web/tests/sweety_downloads_test.php
```

Expected: FAIL because the helper, endpoint, table, and controller behavior do
not exist.

- [ ] **Step 3: Implement strict total parsing**

Create `web/sweety-downloads-lib.php`:

```php
<?php
declare(strict_types=1);

function sweety_downloads_parse_total(mixed $value): ?int
{
    if (is_int($value)) {
        return $value >= 0 ? $value : null;
    }
    if (!is_string($value) || preg_match('/^[0-9]+$/D', $value) !== 1) {
        return null;
    }
    $normalized = ltrim($value, '0');
    if ($normalized === '') {
        return 0;
    }
    $maximum = (string) PHP_INT_MAX;
    if (strlen($normalized) > strlen($maximum)
        || (strlen($normalized) === strlen($maximum) && strcmp($normalized, $maximum) > 0)) {
        return null;
    }
    return (int) $normalized;
}
```

- [ ] **Step 4: Implement GET and POST**

Create `web/sweety-downloads.php` following the database creation and error
inspection pattern in `sweety-metrics.php`.

GET query:

```sql
SELECT total_downloads FROM sweety_download_totals WHERE id = 1
```

POST queries:

```sql
UPDATE sweety_download_totals
SET total_downloads = total_downloads + 1
WHERE id = 1
```

```sql
SELECT total_downloads FROM sweety_download_totals WHERE id = 1
```

Return `{"totalDownloads":N}` with 200 after valid GET or POST. Set
`Cache-Control: public, max-age=60` for GET and `Cache-Control: no-store` for
POST/errors. Return 405 with `Allow: GET, POST` for other methods and
`{"ok":false,"error":"downloads_unavailable"}` with 500 on failures.

- [ ] **Step 5: Add the schema and migration verification**

Append to `app/tools/sweety_metrics.sql`:

```sql
CREATE TABLE IF NOT EXISTS sweety_download_totals (
    id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    total_downloads BIGINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO sweety_download_totals (id, total_downloads)
VALUES (1, 0)
ON DUPLICATE KEY UPDATE id = VALUES(id);
```

Add `sweety_download_totals` to the required-table list in
`metrics_remote_runner.template.php`. Query its singleton and add
`downloadTotal` to the successful JSON response.

- [ ] **Step 6: Verify backend GREEN**

```bash
php web/tests/sweety_downloads_test.php
php web/tests/sweety_metrics_test.php
php -l web/sweety-downloads-lib.php
php -l web/sweety-downloads.php
php -l app/tools/metrics_remote_runner.template.php
```

Expected: both PHP test suites pass and all syntax checks report no errors.

- [ ] **Step 7: Commit the backend**

```bash
git add web/sweety-downloads-lib.php web/sweety-downloads.php web/tests/sweety_downloads_test.php app/tools/sweety_metrics.sql app/tools/metrics_remote_runner.template.php
git commit -m "feat: add public download counter API"
```

### Task 2: Homepage counter and click tracking

**Files:**
- Modify: `web/homepage.js`
- Modify: `web/index.html`
- Modify: `web/homepage.css`
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write failing frontend behavior tests**

Add tests for:

```js
assert.equal(homepage.parseDownloadTotal({ totalDownloads: 0 }), 0);
assert.equal(homepage.parseDownloadTotal({ totalDownloads: 42 }), 42);
assert.equal(homepage.parseDownloadTotal({ totalDownloads: -1 }), null);
assert.equal(homepage.parseDownloadTotal({ totalDownloads: '42' }), null);
assert.equal(homepage.formatDownloadCount('zh-TW', 42), '已下載 42 次');
assert.equal(homepage.formatDownloadCount('en', 42), 'Downloaded 42 times');
assert.equal(homepage.formatDownloadCount('zh-TW', null), '已下載 — 次');
```

Use fake fetch functions to assert GET and POST options:

```js
const calls = [];
const fetcher = async (url, options = {}) => {
  calls.push({ url, options });
  return { ok: true, json: async () => ({ totalDownloads: 8 }) };
};
assert.equal(await homepage.fetchDownloadTotal(fetcher), 8);
assert.equal(calls[0].url, '/sweety-downloads.php');
assert.equal(calls[0].options.headers.Accept, 'application/json');
assert.equal(await homepage.recordDownload(fetcher), 8);
assert.deepEqual(calls[1].options, {
  method: 'POST',
  headers: { Accept: 'application/json' },
  keepalive: true,
});
```

Test `attachDownloadTracking()` with a fake link whose `addEventListener`
captures the handler. Calling the handler must return immediately without
`preventDefault`, perform one POST, and pass the returned count to the callback.

Require the DOM and CSS contracts:

```js
assert.match(html, /class="section-heading download-heading"/);
assert.match(html, /data-download-count[^>]*>—</);
assert.match(css, /\.download-heading[^}]*display:\s*flex[^}]*justify-content:\s*space-between/s);
assert.match(css, /\.download-count[^}]*font-size:/s);
assert.match(mobile, /\.download-heading\s*\{[^}]*align-items:\s*flex-start[^}]*flex-direction:\s*column/);
```

- [ ] **Step 2: Run the homepage suite and verify RED**

```bash
node --test web/tests/homepage.test.mjs
```

Expected: FAIL because parsing, tracking, copy, markup, and layout are absent.

- [ ] **Step 3: Implement frontend data functions**

Add exported functions in `web/homepage.js`:

```js
export function parseDownloadTotal(payload) {
  return Number.isSafeInteger(payload?.totalDownloads) && payload.totalDownloads >= 0
    ? payload.totalDownloads
    : null;
}

export async function fetchDownloadTotal(fetchImpl = globalThis.fetch) {
  try {
    const response = await fetchImpl('/sweety-downloads.php', {
      headers: { Accept: 'application/json' },
    });
    return response?.ok ? parseDownloadTotal(await response.json()) : null;
  } catch {
    return null;
  }
}

export async function recordDownload(fetchImpl = globalThis.fetch) {
  try {
    const response = await fetchImpl('/sweety-downloads.php', {
      method: 'POST',
      headers: { Accept: 'application/json' },
      keepalive: true,
    });
    return response?.ok ? parseDownloadTotal(await response.json()) : null;
  } catch {
    return null;
  }
}
```

Add localized formatting:

```js
export function formatDownloadCount(locale, total) {
  const value = Number.isSafeInteger(total) && total >= 0 ? String(total) : '—';
  return locale === 'zh-TW' ? `已下載 ${value} 次` : `Downloaded ${value} times`;
}
```

Add `attachDownloadTracking(link, onCount, fetchImpl)` so its click listener
starts `recordDownload()` without receiving the event or preventing navigation.
On a valid response it invokes `onCount(total)`.

- [ ] **Step 4: Wire only platform links**

Change `renderDownloads(strings)` to accept an `onPlatformLink` callback and call
it only for the links created from `[data-platform]`. In `initializePage()`:

1. Render the em-dash localized fallback.
2. Fetch and render the initial total.
3. Attach tracking to Windows and macOS links.
4. Render the returned total after a successful POST.

The existing GitHub link remains outside `[data-platform]` and receives no
listener.

- [ ] **Step 5: Add responsive markup and CSS**

Change the heading to:

```html
<div class="section-heading download-heading">
  <div><p class="eyebrow">Sweety</p><h2 data-copy="download.title">Download Sweety</h2></div>
  <p class="download-count" aria-live="polite" aria-atomic="true" data-download-count>Downloaded — times</p>
</div>
```

Add desktop CSS:

```css
.download-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; max-width: none; }
.download-count { margin: 0 0 .35em; color: var(--muted); font-size: .9rem; font-weight: 750; white-space: nowrap; }
```

Inside the existing `@media (max-width: 768px)` block:

```css
.download-heading { align-items: flex-start; flex-direction: column; gap: 12px; }
.download-count { margin: 0; }
```

Bump both CSS and JavaScript query versions in `index.html` to
`1.0.1-download-counter`.

- [ ] **Step 6: Verify frontend GREEN**

```bash
node --test web/tests/homepage.test.mjs
node --check web/homepage.js
```

Expected: all homepage tests pass and the module syntax check exits zero.

- [ ] **Step 7: Commit the frontend**

```bash
git add web/homepage.js web/index.html web/homepage.css web/tests/homepage.test.mjs
git commit -m "feat: show homepage download count"
```

### Task 3: Deployment contract and release

**Files:**
- Modify: `app/tools/deploy_homepage.php`
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Add the failing deployment allowlist test**

Require both files in the parsed `$files` array:

```js
for (const file of ['sweety-downloads.php', 'sweety-downloads-lib.php']) {
  assert.match(manifest, new RegExp(`['"]${file.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&')}['"]`));
}
```

- [ ] **Step 2: Verify RED**

```bash
node --test --test-name-pattern="deployment manifest" web/tests/homepage.test.mjs
```

Expected: FAIL because the download endpoint files are not deployed.

- [ ] **Step 3: Add the endpoint files to deployment**

Add:

```php
'sweety-downloads.php',
'sweety-downloads-lib.php',
```

next to the existing metrics endpoint entries in
`app/tools/deploy_homepage.php`. Extend the success output to print the verified
`downloadTotal` returned by the migration runner.

- [ ] **Step 4: Run complete pre-deployment verification**

```bash
php web/tests/sweety_downloads_test.php
php web/tests/sweety_metrics_test.php
node --test web/tests/homepage.test.mjs
node --check web/homepage.js
php -l web/sweety-downloads.php
php -l web/sweety-downloads-lib.php
php -l app/tools/deploy_homepage.php
git diff --check
```

Expected: all test suites and syntax checks pass.

- [ ] **Step 5: Commit the deployment contract**

```bash
git add app/tools/deploy_homepage.php web/tests/homepage.test.mjs
git commit -m "chore: deploy download counter endpoint"
```

- [ ] **Step 6: Deploy**

```bash
php app/tools/deploy_homepage.php
```

Expected: endpoint and assets upload with matching sizes, all four metrics
tables are verified, the current download total is printed, and the signed
macOS app rebuild completes.

### Task 4: Live count and rendered-layout verification

**Files:**
- Verify: `https://sweety.tw/`
- Verify: `https://sweety.tw/sweety-downloads.php`

- [ ] **Step 1: Verify the live API and perform one deliberate count**

Record GET value `before`, POST once, then GET with a cache-busting query.
Require POST result to equal `before + 1` and the fresh GET to be at least the
POST result.

- [ ] **Step 2: Verify the real homepage**

Load `https://sweety.tw/` in a browser and confirm:

- the page loads `1.0.1-download-counter` assets;
- Traditional Chinese renders `已下載 <number> 次`;
- the number matches a fresh API GET;
- Windows and macOS have enabled download links;
- GitHub remains a plain repository link;
- at large width the count is right-aligned;
- at mobile width the count stacks left below the title.

- [ ] **Step 3: Final verification**

```bash
php web/tests/sweety_downloads_test.php
php web/tests/sweety_metrics_test.php
node --test web/tests/homepage.test.mjs
git status --short
git log -5 --oneline
```

Expected: every suite passes, the worktree is clean, and all download-counter
commits are present.
