# macOS Release and Windows Coming-Soon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a fresh macOS 1.0.1 DMG and make the public Windows download display `稍後提供` / `Coming soon`.

**Architecture:** Keep the stable macOS filename and derive its cache-busting release query from the newly uploaded DMG. Represent Windows unavailability by removing its URL from the homepage and update manifest, allowing the existing download-decision renderer to preserve the disabled static button and avoid attaching download tracking.

**Tech Stack:** Bash, PyInstaller, hdiutil, PHP FTP release helpers, JavaScript ES modules, Node test runner, static HTML/JSON/text assets.

---

### Task 1: Build and upload the macOS release artifact

**Files:**
- Verify: `app/tools/deploy_macos_release.php`
- Generate: `app/desktop/dist/Sweety.app`
- Generate: `app/desktop/dist/Sweety-macos-latest.dmg`

- [ ] **Step 1: Confirm the release helper contract**

Run:

```bash
node --test --test-name-pattern="macOS DMG build|macOS release helper" web/tests/homepage.test.mjs
```

Expected: both release-helper contract tests pass.

- [ ] **Step 2: Build, sign, package, upload, and byte-verify the DMG**

Run:

```bash
php app/tools/deploy_macos_release.php
```

Expected: the app build and code-sign verification pass, `hdiutil verify` and
read-only mount checks pass, and the helper reports the uploaded byte count for
`/sweety.tw/downloads/Sweety-macos-latest.dmg`.

- [ ] **Step 3: Derive the concrete release identifier**

Run:

```bash
MAC_DIGEST="$(shasum -a 256 app/desktop/dist/Sweety-macos-latest.dmg | awk '{print substr($1,1,8)}')"
MAC_RELEASE="1.0.1-${MAC_DIGEST}"
printf '%s\n' "$MAC_RELEASE"
```

Expected: one value matching `^1\.0\.1-[a-f0-9]{8}$`. Preserve that exact value
for Tasks 2–4.

### Task 2: Change the homepage download contract with TDD

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `web/homepage.js`
- Modify: `web/index.html`

- [ ] **Step 1: Write the failing download-contract assertions**

Change the test constants so `expectedMacDownload` uses the release identifier
from Task 1 and remove `expectedWindowsDownload`. Replace the download contract
assertions with:

```js
assert.deepEqual(homepage.downloadConfig, {
  windows: null,
  macos: expectedMacDownload,
});
assert.deepEqual(homepage.getDownloadDecision('windows', 'zh-TW'), {
  enabled: false,
  href: null,
  label: '稍後提供',
});
assert.deepEqual(homepage.getDownloadDecision('windows', 'en'), {
  enabled: false,
  href: null,
  label: 'Coming soon',
});
```

Retain the existing enabled-macOS assertion and static semantic checks.

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```bash
node --test --test-name-pattern="download configuration" web/tests/homepage.test.mjs
```

Expected: FAIL because Windows still has a URL and the Chinese unavailable copy
is still `即將推出`.

- [ ] **Step 3: Implement the minimal homepage behavior**

In `web/homepage.js`, set:

```js
export const downloadConfig = Object.freeze({
  windows: null,
  macos: 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=' + MAC_RELEASE,
});
```

Use the concrete Task 1 value in the actual JavaScript string rather than a
runtime variable. Change the Chinese download copy to:

```js
download: {
  title: '下載 Sweety',
  windows: 'Windows',
  macOS: 'macOS',
  soon: '稍後提供',
  actions: { windows: '下載 Windows 版', macos: '下載 macOS 版' },
},
```

Keep English `soon: 'Coming soon'`. In `web/index.html`, preserve the disabled
Windows button and the default-English `Coming soon` fallback.

- [ ] **Step 4: Run the targeted test and verify GREEN**

Run:

```bash
node --test --test-name-pattern="download configuration" web/tests/homepage.test.mjs
```

Expected: PASS.

### Task 3: Synchronize manifest, machine-readable copy, and cache version

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `web/sweety-update.json`
- Modify: `web/llms.txt`
- Modify: `web/index.html`

- [ ] **Step 1: Write the failing manifest and public-copy assertions**

Change the manifest expectation to:

```js
assert.deepEqual(updateManifest, {
  latestVersion: '1.0.1',
  downloads: {
    macos: expectedMacDownload,
  },
});
```

Add these assertions:

```js
assert.match(llms, /目前下載：macOS/);
assert.match(llms, /Windows：稍後提供/);
assert.doesNotMatch(llms, /支援平台：Windows、macOS/);
```

- [ ] **Step 2: Run the targeted tests and verify RED**

Run:

```bash
node --test --test-name-pattern="production update manifest|machine-readable" web/tests/homepage.test.mjs
```

Expected: FAIL because the manifest and `llms.txt` still advertise the Windows
download.

- [ ] **Step 3: Implement the synchronized public contract**

Apply the following JSON shape, using the concrete `MAC_RELEASE` value printed
in Task 1 as the URL suffix:

```text
latestVersion = 1.0.1
downloads.macos = https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=$MAC_RELEASE
downloads.windows is absent
```

The saved file must remain valid JSON and contain the literal release value,
not a shell variable. In `web/llms.txt`, replace the platform line with:

```text
- 目前下載：macOS
- Windows：稍後提供
```

- [ ] **Step 4: Recalculate the shared asset cache version**

Run:

```bash
ASSET_VERSION="$(node -e "const fs=require('fs'),c=require('crypto');process.stdout.write(c.createHash('sha256').update(fs.readFileSync('web/homepage.css')).update('\\0').update(fs.readFileSync('web/homepage.js')).digest('hex').slice(0,12))")"
printf '%s\n' "$ASSET_VERSION"
```

Use the printed value for both `homepage.css?v=` and `homepage.js?v=` in
`web/index.html`.

- [ ] **Step 5: Run the complete homepage suite**

Run:

```bash
node --test web/tests/homepage.test.mjs
```

Expected: all tests pass, including the content-hash cache-version assertion.

### Task 4: Deploy and verify the public release

**Files:**
- Deploy: `web/homepage.js`
- Deploy: `web/index.html`
- Deploy: `web/sweety-update.json`
- Deploy: `web/llms.txt`
- Verify: `app/desktop/dist/Sweety-macos-latest.dmg`

- [ ] **Step 1: Run local regression checks**

Run:

```bash
node --test web/tests/homepage.test.mjs
cd app/desktop && uv run --extra dev --extra desktop pytest -q
```

Expected: homepage and desktop suites both pass.

- [ ] **Step 2: Deploy the homepage**

Run from the repository root:

```bash
php app/tools/deploy_homepage.php
```

Expected: every homepage file has a verified remote size, metrics verification
passes, and the desktop rebuild/signing step exits successfully.

- [ ] **Step 3: Verify the live cache-busted homepage contract**

Run with the concrete asset version from Task 3:

```bash
curl -fsSL "https://sweety.tw/homepage.js?v=${ASSET_VERSION}" |
  rg "windows: null|Sweety-macos-latest\.dmg\?release=${MAC_RELEASE}|soon: '稍後提供'"
curl -fsSL "https://sweety.tw/sweety-update.json?verify=${ASSET_VERSION}"
curl -fsSL "https://sweety.tw/llms.txt?verify=${ASSET_VERSION}" |
  rg "目前下載：macOS|Windows：稍後提供"
```

Expected: all three current release-contract values are present and the update
manifest contains only the macOS download.

- [ ] **Step 4: Verify the public DMG**

Run:

```bash
LOCAL_SIZE="$(stat -f %z app/desktop/dist/Sweety-macos-latest.dmg)"
REMOTE_SIZE="$(curl -fsSI "https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=${MAC_RELEASE}" | awk 'BEGIN{IGNORECASE=1}/^content-length:/{gsub("\\r","",$2); print $2}' | tail -1)"
test "$REMOTE_SIZE" = "$LOCAL_SIZE"
```

Expected: exit code 0 with equal local and public byte counts.

### Task 5: Preserve user-owned work and report the release

**Files:**
- Inspect: repository worktree

- [ ] **Step 1: Confirm only the intended release fields changed**

Run:

```bash
git diff --check
git diff -- web/homepage.js web/index.html web/tests/homepage.test.mjs web/sweety-update.json web/llms.txt
```

Expected: the pre-existing open-source note changes remain intact, and the new
diff is limited to the macOS digest, Windows unavailable copy/configuration,
manifest, machine-readable platform copy, tests, and cache version.

- [ ] **Step 2: Leave overlapping homepage files uncommitted**

Do not stage or commit the user-owned pre-existing modifications in
`web/homepage.js`, `web/index.html`, and `web/tests/homepage.test.mjs`. Report
the deployed release identifier, DMG byte count, test totals, and live
verification results.
