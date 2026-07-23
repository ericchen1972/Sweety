# Sweety Windows Inno Setup Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the verified Sweety 1.0.1 Inno Setup installer and enable Windows downloads on the homepage and update manifest.

**Architecture:** A focused PHP release helper uploads the already-built Windows installer to a stable public path and refuses to proceed unless the local PE signature and remote size are valid. The static homepage and update manifest then reference that stable path with a version-and-digest cache token; existing homepage tests own the public contract.

**Tech Stack:** PHP 8 FTP extension, Node.js test runner, static HTML/ES modules/JSON, HTTPS verification with curl

---

## File structure

- Create `app/tools/deploy_windows_release.php`: validate and upload the existing
  Inno Setup executable, then verify its remote size.
- Modify `web/tests/homepage.test.mjs`: define the Windows release-helper,
  download URL, manifest, and public metadata contracts.
- Modify `web/homepage.js`: enable the Windows download using the verified URL.
- Modify `web/sweety-update.json`: expose Windows and macOS downloads for version
  1.0.1.
- Modify `web/index.html`: advertise Windows and macOS in SoftwareApplication
  structured data.
- Modify `web/llms.txt`: remove the stale “Windows coming soon” statement.

### Task 1: Windows release-helper contract

**Files:**
- Create: `app/tools/deploy_windows_release.php`
- Modify: `web/tests/homepage.test.mjs`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write the failing release-helper contract test**

Add the helper fixture beside the existing macOS helper fixture:

```js
const windowsReleaseHelper = await readFile(new URL('../app/tools/deploy_windows_release.php', webRoot), 'utf8').catch(() => '');
```

Add this test:

```js
test('Windows release helper validates and verifies the uploaded Inno Setup binary', () => {
  assert.match(windowsReleaseHelper, /web\/sftp-config\.json/);
  assert.match(windowsReleaseHelper, /Sweety-Windows-Setup-1\.0\.1\.exe/);
  assert.match(windowsReleaseHelper, /\/sweety\.tw\/downloads\/Sweety-Windows-Setup-latest\.exe/);
  assert.match(windowsReleaseHelper, /fread\([^,]+,\s*2\)[^;]*===\s*['"]MZ['"]/s);
  assert.match(windowsReleaseHelper, /FTP_BINARY/);
  assert.match(windowsReleaseHelper, /ftp_size\([^)]*\)[^;]*filesize\(/s);
  assert.doesNotMatch(windowsReleaseHelper, /echo[^;]*(?:password|user)/i);
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
node --test --test-name-pattern="Windows release helper" web/tests/homepage.test.mjs
```

Expected: FAIL because `app/tools/deploy_windows_release.php` does not exist.

- [ ] **Step 3: Implement the minimal uploader**

Create `app/tools/deploy_windows_release.php` with the same comment-tolerant
configuration parser, FTP login, passive-mode setting, and recursive directory
creation pattern used by `deploy_macos_release.php`. Use these exact paths:

```php
$remoteDirectory = '/sweety.tw/downloads';
$remotePath = '/sweety.tw/downloads/Sweety-Windows-Setup-latest.exe';
$localPath = $root . '/app/desktop/dist/Sweety-Windows-Setup-1.0.1.exe';
```

Before connecting, validate the artifact:

```php
if (!is_file($localPath) || filesize($localPath) <= 0) {
    fail('Windows installer is missing or empty.');
}
$stream = fopen($localPath, 'rb');
if ($stream === false || fread($stream, 2) !== 'MZ') {
    if (is_resource($stream)) {
        fclose($stream);
    }
    fail('Windows installer does not have a valid executable signature.');
}
fclose($stream);
```

Upload and verify:

```php
if (!ftp_put($ftp, $remotePath, $localPath, FTP_BINARY)) {
    ftp_close($ftp);
    fail('Unable to upload the Windows installer.');
}
if (ftp_size($ftp, $remotePath) !== filesize($localPath)) {
    ftp_close($ftp);
    fail('Remote Windows installer size verification failed.');
}
```

Print only the verified byte count and remote path.

- [ ] **Step 4: Run focused and syntax verification**

Run:

```bash
node --test --test-name-pattern="Windows release helper" web/tests/homepage.test.mjs
php -l app/tools/deploy_windows_release.php
```

Expected: the focused Node test passes and PHP reports no syntax errors.

- [ ] **Step 5: Commit the green helper**

```bash
git add app/tools/deploy_windows_release.php web/tests/homepage.test.mjs
git commit -m "feat: add Windows installer release helper"
```

### Task 2: Homepage and manifest Windows contract

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `web/homepage.js`
- Modify: `web/sweety-update.json`
- Modify: `web/index.html`
- Modify: `web/llms.txt`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write the failing Windows download assertions**

Define:

```js
const expectedWindowsDownload = 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.1-cec623ac';
```

Update the existing download test to require:

```js
assert.deepEqual(homepage.downloadConfig, {
  windows: expectedWindowsDownload,
  macos: expectedMacDownload,
});
assert.deepEqual(homepage.getDownloadDecision('windows', 'zh-TW'), {
  enabled: true,
  href: expectedWindowsDownload,
  label: '下載 Windows 版',
});
```

Update the manifest assertion to require:

```js
assert.deepEqual(updateManifest, {
  latestVersion: '1.0.1',
  downloads: {
    windows: expectedWindowsDownload,
    macos: expectedMacDownload,
  },
});
```

Update SoftwareApplication and discovery assertions:

```js
assert.equal(app.operatingSystem, 'Windows, macOS');
assert.match(llms, /支援平台：Windows、macOS/);
assert.doesNotMatch(llms, /Windows 版即將推出/);
```

- [ ] **Step 2: Run the complete homepage suite and verify RED**

Run:

```bash
node --test web/tests/homepage.test.mjs
```

Expected: FAIL because Windows is disabled, absent from the update manifest, and
absent from public platform metadata.

- [ ] **Step 3: Enable the verified Windows URL**

Change `web/homepage.js`:

```js
export const downloadConfig = Object.freeze({
  windows: 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.1-cec623ac',
  macos: 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-2c2c458',
});
```

Change `web/sweety-update.json`:

```json
{
  "latestVersion": "1.0.1",
  "downloads": {
    "windows": "https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.1-cec623ac",
    "macos": "https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-2c2c458"
  }
}
```

Change the SoftwareApplication field in `web/index.html`:

```json
"operatingSystem": "Windows, macOS"
```

Change the platform line in `web/llms.txt`:

```text
- 支援平台：Windows、macOS
```

- [ ] **Step 4: Run the complete local verification**

Run:

```bash
node --test web/tests/homepage.test.mjs
node --check web/homepage.js
php -l app/tools/deploy_windows_release.php
php -l app/tools/deploy_homepage.php
```

Expected: all homepage tests pass and every syntax check exits zero.

- [ ] **Step 5: Commit the public Windows contract**

```bash
git add web/tests/homepage.test.mjs web/homepage.js web/sweety-update.json web/index.html web/llms.txt
git commit -m "feat: publish Windows download"
```

### Task 3: Upload binary and publish homepage

**Files:**
- Use: `app/desktop/dist/Sweety-Windows-Setup-1.0.1.exe`
- Use: `app/tools/deploy_windows_release.php`
- Use: `app/tools/deploy_homepage.php`

- [ ] **Step 1: Verify the local artifact immediately before upload**

Run:

```bash
stat -f '%z' app/desktop/dist/Sweety-Windows-Setup-1.0.1.exe
xxd -l 2 app/desktop/dist/Sweety-Windows-Setup-1.0.1.exe
shasum -a 256 app/desktop/dist/Sweety-Windows-Setup-1.0.1.exe
```

Expected: size `79174928`, signature `4d5a`, and SHA-256 beginning
`cec623ac`.

- [ ] **Step 2: Upload and remotely size-check the Windows installer**

Run:

```bash
php app/tools/deploy_windows_release.php
```

Expected: output confirms 79,174,928 bytes uploaded to
`/sweety.tw/downloads/Sweety-Windows-Setup-latest.exe`.

- [ ] **Step 3: Deploy the homepage only after binary verification**

Run:

```bash
php app/tools/deploy_homepage.php
```

Expected: all homepage files report verified upload sizes, the metrics migration
passes, and the existing signed macOS app rebuild completes.

### Task 4: Live release verification

**Files:**
- Verify: `https://sweety.tw/`
- Verify: `https://sweety.tw/homepage.js`
- Verify: `https://sweety.tw/sweety-update.json`
- Verify: `https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe`

- [ ] **Step 1: Verify the live public contract**

Run:

```bash
curl -fsS https://sweety.tw/homepage.js | grep -F 'Sweety-Windows-Setup-latest.exe?release=1.0.1-cec623ac'
curl -fsS https://sweety.tw/sweety-update.json
curl -fsS https://sweety.tw/ | grep -F '"operatingSystem": "Windows, macOS"'
```

Expected: the live JavaScript contains the Windows URL, the manifest contains
both Windows and macOS URLs, and structured data advertises both platforms.

- [ ] **Step 2: Verify the public binary over HTTPS**

Run:

```bash
curl -fsSI 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.1-cec623ac'
curl -fsS --range 0-1 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.1-cec623ac' | xxd -p
```

Expected: HTTP 200 or 206, a content length of 79,174,928 bytes for the full
artifact, and leading bytes `4d5a`.

- [ ] **Step 3: Re-run local tests and inspect repository state**

Run:

```bash
node --test web/tests/homepage.test.mjs
git status --short
git log -3 --oneline
```

Expected: all homepage tests pass, only expected ignored build artifacts remain,
and the Windows release commits are present.
