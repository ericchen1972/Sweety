# macOS 1.0.1 Refresh Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish the current macOS main branch as a refreshed, signed Sweety 1.0.1 DMG and deploy a cache-safe website link to the new artifact.

**Architecture:** Use the existing macOS release helper as the single build, signing, packaging, mounting, and FTP-upload boundary. Derive the public query digest from the uploaded local DMG, update the website contract test-first, deploy with the existing homepage helper, then verify the live files and push the matching source commit.

**Tech Stack:** Python 3.11, pytest, React, TypeScript, Vitest, PyInstaller, codesign, hdiutil, PHP FTP helpers, Node.js test runner, curl, Git.

---

### Task 1: Verify the release baseline

**Files:**
- Verify: `app/desktop/`
- Verify: `app/frontend/`
- Verify: `web/`

- [ ] **Step 1: Confirm version and branch state**

Run:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
rg -n 'version = "1.0.1"|CFBundleShortVersionString.*1.0.1|CFBundleVersion.*101' \
  app/desktop/pyproject.toml app/desktop/Sweety.spec
```

Expected: `main` is ahead only by the approved release spec, `videos/` is the
only untracked path, and all three version declarations remain unchanged.

- [ ] **Step 2: Run all local suites and the frontend production build**

Run:

```bash
cd app/desktop && uv run pytest -q
cd ../frontend && npm test -- --run && npm run build
cd ../../web && node --test tests/homepage.test.mjs
```

Expected: desktop 212 tests, frontend 29 tests, and homepage 37 tests pass; the
frontend production build exits successfully.

### Task 2: Build, verify, and upload the refreshed DMG

**Files:**
- Replace generated artifact: `app/desktop/dist/Sweety.app`
- Replace generated artifact: `app/desktop/dist/Sweety-macos-latest.dmg`
- Execute: `app/tools/deploy_macos_release.php`

- [ ] **Step 1: Run the formal macOS release helper**

Run from the repository root:

```bash
php app/tools/deploy_macos_release.php
```

Expected output proves that:

- the frontend built;
- PyInstaller produced `Sweety.app`;
- `codesign --verify --deep --strict` passed;
- the DMG verified and mounted;
- `Sweety.app` and the Applications symlink were present;
- a SHA-256 and local byte size were printed;
- the stable remote DMG received the same byte size.

Stop immediately if the helper exits nonzero.

- [ ] **Step 2: Independently capture the artifact facts**

Run and retain the shell variables for the remaining tasks:

```bash
sweety_dmg_sha=$(shasum -a 256 app/desktop/dist/Sweety-macos-latest.dmg | awk '{print $1}')
sweety_release_digest=$(printf '%s' "$sweety_dmg_sha" | cut -c1-8)
sweety_dmg_size=$(stat -f %z app/desktop/dist/Sweety-macos-latest.dmg)
printf '%s\n%s\n%s\n' "$sweety_dmg_sha" "$sweety_release_digest" "$sweety_dmg_size"
codesign --verify --deep --strict --verbose=2 app/desktop/dist/Sweety.app
```

The new public URL is exactly:

```text
https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-${sweety_release_digest}
```

### Task 3: Update the public download contract test-first

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `web/homepage.js`
- Modify: `web/sweety-update.json`
- Modify: `web/index.html`

- [ ] **Step 1: Set the test expectation to the newly derived URL**

In `web/tests/homepage.test.mjs`, replace `expectedMacDownload` with:

```javascript
const expectedMacDownload = 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-${sweety_release_digest}';
```

At execution time, substitute the actual eight-character digest value rather
than committing the literal shell variable syntax.

- [ ] **Step 2: Run the homepage test and verify RED**

Run:

```bash
cd web
node --test tests/homepage.test.mjs
```

Expected: the manifest and download-configuration assertions fail because
production files still contain the previous `1.0.1-9ff118bd` URL.

- [ ] **Step 3: Update the JavaScript and manifest URL**

Set the macOS value in `web/homepage.js` to:

```javascript
macos: 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-${sweety_release_digest}',
```

Set the manifest download in `web/sweety-update.json` to:

```json
"macos": "https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-${sweety_release_digest}"
```

At execution time, use the actual digest. Preserve `windows: null` in
JavaScript and keep Windows absent from the JSON manifest.

- [ ] **Step 4: Calculate and apply the new homepage asset version**

Calculate and retain the result:

```bash
sweety_asset_version=$(node -e 'const fs=require("fs"),c=require("crypto");const css=fs.readFileSync("web/homepage.css"),js=fs.readFileSync("web/homepage.js");process.stdout.write(c.createHash("sha256").update(css).update("\0").update(js).digest("hex").slice(0,12))')
printf '%s\n' "$sweety_asset_version"
```

Record the output as `sweety_asset_version`. In `web/index.html`, set:

```html
<link rel="stylesheet" href="homepage.css?v=${sweety_asset_version}">
<script type="module" src="homepage.js?v=${sweety_asset_version}"></script>
```

At execution time, use the actual 12-character hash.

- [ ] **Step 5: Run focused verification**

Run:

```bash
cd web
node --test tests/homepage.test.mjs
```

Expected: all 37 tests pass, including the content-derived asset-version guard.

- [ ] **Step 6: Commit the release contract**

Run:

```bash
git diff --check
git add web/tests/homepage.test.mjs web/homepage.js web/sweety-update.json web/index.html
git commit -m "release: refresh macOS 1.0.1 download"
```

Do not stage `videos/` or generated desktop artifacts.

### Task 4: Deploy and live-verify the website

**Files:**
- Execute: `app/tools/deploy_homepage.php`
- Verify live: `https://sweety.tw/`
- Verify live: `https://sweety.tw/homepage.js`
- Verify live: `https://sweety.tw/sweety-update.json`
- Verify live: `https://sweety.tw/downloads/Sweety-macos-latest.dmg`

- [ ] **Step 1: Deploy the homepage**

Run:

```bash
php app/tools/deploy_homepage.php
```

Expected: every public file reports a successful remote size check, metrics and
download schema checks pass, and the signed desktop app rebuild completes.

- [ ] **Step 2: Verify live HTML and JavaScript with cache-busting**

Use a fresh timestamp value and run:

```bash
sweety_verify_nonce=$(date +%s)
curl -fsS "https://sweety.tw/?verify=${sweety_verify_nonce}"
curl -fsS "https://sweety.tw/homepage.js?v=${sweety_asset_version}&verify=${sweety_verify_nonce}"
curl -fsS "https://sweety.tw/sweety-update.json?verify=${sweety_verify_nonce}"
```

Verify:

- HTML references the exact new asset version;
- JavaScript contains `windows: null` and the exact new macOS URL;
- the manifest contains only the exact new macOS URL.

- [ ] **Step 3: Verify the public DMG response**

Run:

```bash
curl -fsSI "https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-${sweety_release_digest}&verify=${sweety_verify_nonce}"
```

Expected: a successful response for the stable DMG. FTP size verification from
Task 2 remains the authoritative byte-for-byte remote-size check.

### Task 5: Final verification and push

**Files:**
- Verify: Git working tree and remote main

- [ ] **Step 1: Re-run release contract tests**

Run:

```bash
cd web && node --test tests/homepage.test.mjs
cd ../app/desktop && uv run pytest -q
cd ../frontend && npm test -- --run
```

Expected: homepage 37, desktop 212, and frontend 29 tests pass.

- [ ] **Step 2: Verify the source and artifact facts agree**

Run:

```bash
rg -n "1.0.1-${sweety_release_digest}|${sweety_asset_version}" \
  web/homepage.js web/sweety-update.json web/index.html web/tests/homepage.test.mjs
shasum -a 256 app/desktop/dist/Sweety-macos-latest.dmg
git status --short --branch
```

Expected: all public source files use the derived values, the DMG checksum still
equals `sweety_dmg_sha`, and only `videos/` remains untracked.

- [ ] **Step 3: Push and verify GitHub main**

Run:

```bash
git fetch origin main
git merge-base --is-ancestor origin/main main
git push origin main
git rev-parse main
git ls-remote origin refs/heads/main
```

Expected: a normal fast-forward push succeeds and both hashes match.
