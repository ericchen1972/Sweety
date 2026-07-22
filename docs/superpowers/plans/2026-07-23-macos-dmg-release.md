# Sweety macOS DMG Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, upload, and publish a verified drag-to-Applications DMG for Sweety 1.0.1.

**Architecture:** A shell script owns deterministic local app/DMG construction and mounted-content verification. A PHP helper owns binary FTP upload and byte-size verification. The existing homepage configuration and static update manifest expose the same cache-busted HTTPS URL only after the binary upload succeeds.

**Tech Stack:** Bash, `hdiutil`, PyInstaller, codesign, PHP FTP extension, static JavaScript/JSON, Node test runner

---

### Task 1: Add the DMG package contract

**Files:**
- Create: `app/desktop/build_dmg.sh`
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write the failing build-script contract test**

Read `app/desktop/build_dmg.sh` in `web/tests/homepage.test.mjs` and assert that it invokes `build_app.sh`, creates `dist/dmg-staging`, copies `Sweety.app`, creates `Applications -> /Applications`, calls `hdiutil create` and `hdiutil verify`, mounts the image, and checks both mounted entries.

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test web/tests/homepage.test.mjs`

Expected: failure because `build_dmg.sh` does not exist.

- [ ] **Step 3: Implement `build_dmg.sh`**

The script must:

```bash
./build_app.sh
rm -rf dist/dmg-staging dist/Sweety-macos-latest.dmg
mkdir -p dist/dmg-staging
cp -R dist/Sweety.app dist/dmg-staging/
ln -s /Applications dist/dmg-staging/Applications
hdiutil create -volname Sweety -srcfolder dist/dmg-staging -ov -format UDZO dist/Sweety-macos-latest.dmg
hdiutil verify dist/Sweety-macos-latest.dmg
```

It must then mount read-only into a temporary directory, assert `Sweety.app` is a directory and `Applications` resolves to `/Applications`, detach through a trap, and print SHA-256 and byte size.

- [ ] **Step 4: Run the contract test and syntax check**

Run: `node --test web/tests/homepage.test.mjs && bash -n app/desktop/build_dmg.sh`

Expected: all homepage tests pass and Bash syntax exits zero.

- [ ] **Step 5: Commit the package script**

```bash
git add app/desktop/build_dmg.sh web/tests/homepage.test.mjs
git commit -m "build: add verified macOS DMG packaging"
```

### Task 2: Add the binary upload helper

**Files:**
- Create: `app/tools/deploy_macos_release.php`
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write the failing upload-helper contract test**

Assert the helper reads `web/sftp-config.json`, uploads `app/desktop/dist/Sweety-macos-latest.dmg` to `/sweety.tw/downloads/Sweety-macos-latest.dmg` with `FTP_BINARY`, creates the remote downloads directory, verifies `ftp_size()` against `filesize()`, and never prints credentials.

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test web/tests/homepage.test.mjs`

Expected: failure because `deploy_macos_release.php` does not exist.

- [ ] **Step 3: Implement the PHP uploader**

Reuse the existing JSON-with-comments config parsing, FTP login, passive-mode setting, and recursive directory creation pattern from `app/tools/deploy_homepage.php`. Upload exactly one DMG and print only its local size and remote path.

- [ ] **Step 4: Run contract and PHP syntax checks**

Run: `node --test web/tests/homepage.test.mjs && php -l app/tools/deploy_macos_release.php`

Expected: all tests pass and PHP reports no syntax errors.

- [ ] **Step 5: Commit the upload helper**

```bash
git add app/tools/deploy_macos_release.php web/tests/homepage.test.mjs
git commit -m "build: add macOS release uploader"
```

### Task 3: Enable the public macOS download

**Files:**
- Modify: `web/homepage.js`
- Modify: `web/sweety-update.json`
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write failing public-link tests**

Define the expected cache-busted URL using version 1.0.1 and the approved release-design commit `2c2c458`. Assert:

```javascript
assert.deepEqual(homepage.downloadConfig, { windows: null, macos: expectedMacUrl });
assert.deepEqual(updateManifest, {
  latestVersion: '1.0.1',
  downloads: { macos: expectedMacUrl },
});
assert.equal(homepage.getDownloadDecision('macos', 'zh-TW').enabled, true);
assert.equal(homepage.getDownloadDecision('windows', 'zh-TW').enabled, false);
```

- [ ] **Step 2: Run the test and verify RED**

Run: `node --test web/tests/homepage.test.mjs`

Expected: failure because both macOS URLs are still absent.

- [ ] **Step 3: Add the exact URL to both sources**

Set `downloadConfig.macos` and `downloads.macos` to:

`https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-2c2c458`

Keep `downloadConfig.windows` null and omit Windows from the manifest.

- [ ] **Step 4: Run homepage tests and commit**

Run: `node --test web/tests/homepage.test.mjs`

Expected: all tests pass.

```bash
git add web/homepage.js web/sweety-update.json web/tests/homepage.test.mjs
git commit -m "feat: publish macOS download links"
```

### Task 4: Build and validate the release artifact

**Files:**
- Generate, do not commit: `app/desktop/dist/Sweety-macos-latest.dmg`

- [ ] **Step 1: Run all local tests**

Run:

```bash
cd app/frontend && npm test
cd ../desktop && .venv/bin/pytest -q
cd ../.. && node --test web/tests/*.test.mjs
```

Expected: zero failures.

- [ ] **Step 2: Build the DMG**

Run from `app/desktop`: `./build_dmg.sh`

Expected: the app signature, DMG verification, mounted entries, SHA-256, and size all validate.

- [ ] **Step 3: Record release identity**

Run:

```bash
shasum -a 256 app/desktop/dist/Sweety-macos-latest.dmg
stat -f %z app/desktop/dist/Sweety-macos-latest.dmg
```

Expected: one SHA-256 digest and a positive byte size.

### Task 5: Upload binary, deploy links, and verify live

**Files:**
- Deploy: `app/desktop/dist/Sweety-macos-latest.dmg`
- Deploy: files listed by `app/tools/deploy_homepage.php`

- [ ] **Step 1: Upload and verify the DMG over FTP**

Run: `php app/tools/deploy_macos_release.php`

Expected: output confirms remote `/sweety.tw/downloads/Sweety-macos-latest.dmg` byte size equals the local artifact.

- [ ] **Step 2: Deploy homepage and manifest**

Run: `php app/tools/deploy_homepage.php`

Expected: all homepage files upload with verified sizes and the rebuilt app succeeds.

- [ ] **Step 3: Verify live links and sizes**

Fetch `https://sweety.tw/`, `https://sweety.tw/homepage.js`, and `https://sweety.tw/sweety-update.json` with the release query. Confirm homepage JavaScript and manifest expose the same macOS URL and no Windows URL. Compare HTTP `Content-Length` with the local DMG size.

- [ ] **Step 4: Download and validate the published DMG**

Download the cache-busted public URL into `/tmp/Sweety-macos-latest.dmg`, verify its SHA-256 equals the local artifact, run `hdiutil verify`, mount read-only, and confirm `Sweety.app` plus the `/Applications` symlink.

- [ ] **Step 5: Final repository check**

Run: `git status --short && git log -5 --oneline`

Expected: tracked sources are committed, the ignored DMG is absent from git status, and the release commits are visible on `main`.
