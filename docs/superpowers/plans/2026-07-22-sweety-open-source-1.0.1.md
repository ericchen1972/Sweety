# Sweety 1.0.1 Open-Source Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a secret-free Sweety 1.0.1 source repository with the requested homepage FAQ, LINE warning, open-source About content, author cards, README, and MIT License.

**Architecture:** Keep the public site as bilingual static HTML/CSS/JavaScript and keep the desktop dashboard as the existing React/FastAPI application. Add narrowly scoped About-image sanitization, inject the AGNES credential only from ignored local configuration at build time, and preserve the remote About-content flow used by the App.

**Tech Stack:** HTML, CSS, ES modules, Node test runner, React 19, TypeScript, Python 3.11, FastAPI, pytest, PHP 8, PyInstaller, GitHub CLI.

---

## File map

- Create `.gitignore`: public-repository exclusion boundary.
- Create `config.example.json`: placeholder-only local build configuration.
- Create `README.md`: public project documentation.
- Create `LICENSE`: MIT License.
- Modify `web/index.html`, `web/homepage.js`, `web/homepage.css`: homepage warning, FAQ, and author card.
- Modify `web/about_sweety.html`: open-source section and About author card.
- Modify `web/tests/homepage.test.mjs`: homepage, deployment allowlist, author asset, and release contract tests.
- Modify `app/desktop/src/sweety_app/about.py`: safe author-image sanitization.
- Modify `app/desktop/tests/test_about.py`: sanitizer regression tests.
- Modify `app/frontend/src/index.css`: in-App About author-card presentation.
- Modify `app/desktop/src/sweety_app/config.py`, `app/desktop/Sweety.spec`, `app/desktop/build_app.sh`: secret-free build-time credential injection and 1.0.1 metadata.
- Modify `app/desktop/tests/test_config.py`, `app/desktop/tests/test_metrics_integration_contract.py`: credential and bundle-environment contracts.
- Create `app/desktop/tests/test_release_version.py`: cross-file version contract.
- Modify `app/desktop/pyproject.toml`, `app/desktop/uv.lock`, `app/frontend/package.json`, `app/frontend/package-lock.json`: version 1.0.1.
- Modify `app/tools/deploy_homepage.php`: deploy About page and author image.

### Task 1: Establish the public-repository security boundary

**Files:**
- Create: `.gitignore`
- Create: `config.example.json`
- Modify: `app/desktop/tests/test_config.py`
- Modify: `app/desktop/tests/test_metrics_integration_contract.py`
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/desktop/Sweety.spec`
- Modify: `app/desktop/build_app.sh`

- [ ] **Step 1: Replace the embedded-key test with environment-only tests**

Add tests that reload `sweety_app.config` under controlled environment values:

```python
def test_agnes_key_is_empty_without_environment(monkeypatch):
    monkeypatch.delenv("SWEETY_AGNES_KEY", raising=False)
    config = importlib.reload(importlib.import_module("sweety_app.config"))
    assert config.BUNDLED_AGNES_KEY == ""


def test_agnes_key_comes_only_from_environment(monkeypatch):
    monkeypatch.setenv("SWEETY_AGNES_KEY", "test-agnes-key")
    config = importlib.reload(importlib.import_module("sweety_app.config"))
    assert config.BUNDLED_AGNES_KEY == "test-agnes-key"
```

Extend the bundle contract test to require `SWEETY_AGNES_KEY` in the generated `LSEnvironment` and to reject `_EMBEDDED_AGNES_KEY_B64`, `base64.b64decode`, and literal `sk-` credentials in `config.py`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
cd app/desktop
.venv/bin/pytest -q tests/test_config.py tests/test_metrics_integration_contract.py
```

Expected: FAIL because the current configuration still reads `config.json` and embeds an encoded AGNES key.

- [ ] **Step 3: Implement environment-only runtime and local build injection**

In `config.py`, remove `base64` and the embedded literal, then use:

```python
BUNDLED_AGNES_KEY = os.getenv("SWEETY_AGNES_KEY", "").strip()
```

In `build_app.sh`, if `SWEETY_AGNES_KEY` is unset and ignored `config.json` exists, load only `AGNES_KEY` without printing it, export it, and fail with a clear message if no build credential is available.

In `Sweety.spec`, read both build credentials and construct one conditional environment map:

```python
app_environment = {
    key: value
    for key, value in {
        "SWEETY_AGNES_KEY": os.getenv("SWEETY_AGNES_KEY", "").strip(),
        "SWEETY_METRICS_APP_TOKEN": os.getenv("SWEETY_METRICS_APP_TOKEN", "").strip(),
    }.items()
    if value
}
```

Set `LSEnvironment` only when `app_environment` is non-empty.

- [ ] **Step 4: Add ignored-file rules and a safe example**

Create `.gitignore` covering:

```gitignore
.DS_Store
.lean-ctx/
.superpowers/
config.json
web/sftp-config.json
*.sqlite3
*.sqlite3-*
*.db
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
node_modules/
dist/
build/
*.tsbuildinfo
*.log
```

Create `config.example.json` containing only:

```json
{
  "AGNES_KEY": "replace-with-your-own-build-key"
}
```

- [ ] **Step 5: Verify GREEN and inspect ignored secrets**

Run the focused tests again, then run:

```bash
git status --ignored --short
git check-ignore -v config.json web/sftp-config.json app/desktop/.venv app/desktop/dist app/frontend/node_modules
```

Expected: tests pass and every sensitive/generated path is ignored.

- [ ] **Step 6: Create the safe source baseline commit**

Stage the source tree only after the ignore rules are active:

```bash
git add -A
git diff --cached --check
git diff --cached --name-only
git grep --cached -n -E 'sk-[A-Za-z0-9_-]{20,}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|"password"[[:space:]]*:' -- . ':!config.example.json'
git commit -m "chore: prepare public Sweety source"
```

Expected: the secret scan returns no matches; `config.json`, `web/sftp-config.json`, build output, and dependencies are absent from the staged list.

### Task 2: Lock every product version to 1.0.1

**Files:**
- Create: `app/desktop/tests/test_release_version.py`
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/desktop/pyproject.toml`
- Modify: `app/desktop/uv.lock`
- Modify: `app/frontend/package.json`
- Modify: `app/frontend/package-lock.json`
- Modify: `app/desktop/Sweety.spec`

- [ ] **Step 1: Add a failing cross-file version test**

Read the source files as text/JSON/TOML and assert:

```python
assert config.APP_VERSION == "1.0.1"
assert pyproject["project"]["version"] == "1.0.1"
assert frontend_package["version"] == "1.0.1"
assert frontend_lock["version"] == "1.0.1"
assert frontend_lock["packages"][""]["version"] == "1.0.1"
assert '"CFBundleShortVersionString": "1.0.1"' in spec
assert '"CFBundleVersion": "101"' in spec
```

- [ ] **Step 2: Run the release test and verify RED**

Run `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_release_version.py`.

Expected: FAIL with current `0.1.0` values.

- [ ] **Step 3: Update package and bundle metadata**

Change all asserted values to `1.0.1`, set macOS build number to `101`, run `uv lock` in `app/desktop`, and run `npm install --package-lock-only` in `app/frontend` so lock metadata is generated rather than hand-edited.

- [ ] **Step 4: Verify GREEN and commit**

Run the release test and package-manager consistency checks, then commit:

```bash
git add app/desktop app/frontend/package.json app/frontend/package-lock.json
git commit -m "chore: release Sweety 1.0.1"
```

### Task 3: Add the homepage warning, FAQ, and author card

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `web/index.html`
- Modify: `web/homepage.js`
- Modify: `web/homepage.css`

- [ ] **Step 1: Add failing homepage contract tests**

Require all of the following:

```javascript
assert.equal(copy['zh-TW'].notice.windowPosition, 'Line 桌面 App 視窗位置請勿超過螢幕左側或右側邊緣，否則將造成 Sweety 辨識失敗');
assert.equal(copy['zh-TW'].faq.items.length, 4);
assert.equal((html.match(/<details\b/g) ?? []).length, 4);
assert.equal((html.match(/<summary\b/g) ?? []).length, 4);
assert.match(html, /images\/eric\.png/);
assert.match(html, /class="author-avatar"/);
assert.match(html, /https:\/\/slimweb\.tw/);
assert.match(html, /https:\/\/slimweb\.tw\/kingjoo\//);
assert.match(html, /https:\/\/sweety\.tw/);
assert.match(css, /\.faq-item/);
assert.match(css, /\.author-card/);
assert.match(css, /border-radius:\s*50%/);
```

Also assert that project links use `target="_blank"` and `rel="noopener noreferrer"`, and that the four `<details>` elements do not share a `name` attribute, preserving non-exclusive behavior.

- [ ] **Step 2: Run the homepage tests and verify RED**

Run `node --test web/tests/homepage.test.mjs`.

Expected: FAIL because the requested content and hooks do not exist.

- [ ] **Step 3: Add semantic static markup**

In `web/index.html`:

- append the window-position warning inside the existing notice;
- add `<section class="faq-section">` immediately after the notice with four independent `<details class="faq-item">` blocks;
- add `<section class="author-section">` after FAQ with a two-column `<article class="author-card">`, `images/eric.png`, project links, email, LINE ID, and contact invitation;
- increment the shared homepage CSS/JS cache-busting query to a `1.0.1` release token.

The static fallback document contains complete English content so the page remains useful without JavaScript.

- [ ] **Step 4: Add localized copy and initialization hooks**

Add `notice.windowPosition`, `faq.title`, four `faq.items`, and the author-card labels/body to both locale objects. Use stable `data-copy` paths for the fixed FAQ and author fields so `initializePage()` can localize them through the existing generic `[data-copy]` loop without a new renderer.

- [ ] **Step 5: Style desktop, mobile, focus, and disclosure states**

Add restrained `.faq-section`, `.faq-list`, `.faq-item`, `.faq-item summary`, `.author-section`, `.author-card`, `.author-avatar`, `.author-projects`, and `.author-contact` rules. Use CSS-only disclosure indicators, a visible focus state, a circular 160px author image, and a one-column author card below 768px.

- [ ] **Step 6: Verify GREEN and commit**

Run the homepage tests, then commit the four homepage files with `feat: add homepage FAQ and author profile`.

### Task 4: Add open-source and author content to About Sweety

**Files:**
- Modify: `app/desktop/tests/test_about.py`
- Modify: `app/desktop/src/sweety_app/about.py`
- Modify: `web/about_sweety.html`
- Modify: `app/frontend/src/index.css`

- [ ] **Step 1: Add failing sanitizer tests**

Add a source fragment containing one safe image and unsafe variants, then assert:

```python
assert '<img src="https://sweety.tw/images/eric.png" alt="Eric" width="256" height="256" loading="lazy">' in result
assert "javascript:" not in result
assert "data:image" not in result
assert "onerror" not in result
```

Also assert the GitHub anchor survives with enforced new-tab and `noopener noreferrer` attributes.

- [ ] **Step 2: Run focused tests and verify RED**

Run `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_about.py`.

Expected: FAIL because `<img>` is currently removed.

- [ ] **Step 3: Allow only safe remote images**

Add `img` to allowed tags and allow only:

- HTTPS `src`;
- escaped `alt` up to 200 characters;
- decimal `width`/`height` values;
- `loading="lazy"` or `loading="eager"`.

Treat `img` as a void tag and continue dropping all other attributes and unsafe URL schemes.

- [ ] **Step 4: Build the About content and dashboard styling**

Add the approved Open-Source Project section, GitHub link, and author card to `web/about_sweety.html`. Use `https://sweety.tw/images/eric.png` for the portrait. Add matching `.about-content .author-card`, `.author-avatar`, `.author-projects`, and responsive rules in `app/frontend/src/index.css` because remote `<style>` is intentionally stripped.

- [ ] **Step 5: Verify GREEN and commit**

Run the About tests and frontend type/build checks, then commit with `feat: add open source About profile`.

### Task 5: Deploy the complete public-page asset set

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `app/tools/deploy_homepage.php`

- [ ] **Step 1: Add a failing deployment-allowlist test**

Assert that `deploy_homepage.php` explicitly includes both:

```javascript
assert.match(deployHelper, /'about_sweety\.html'/);
assert.match(deployHelper, /'images\/eric\.png'/);
```

- [ ] **Step 2: Run the test and verify RED**

Run `node --test web/tests/homepage.test.mjs`.

Expected: FAIL because neither file is uploaded today.

- [ ] **Step 3: Extend the upload allowlist**

Add `about_sweety.html` and `images/eric.png` to `$files`. Preserve binary transfer, size verification, and the existing remote metrics migration/build workflow.

- [ ] **Step 4: Verify GREEN and commit**

Run homepage and PHP contract tests, then commit with `chore: deploy About and author assets`.

### Task 6: Write public documentation and licensing

**Files:**
- Create: `README.md`
- Create: `LICENSE`

- [ ] **Step 1: Write the README as an executable setup contract**

Include exact commands:

```bash
cp config.example.json config.json
cd app/frontend && npm install && npm test && npm run build
cd ../desktop && uv sync --extra desktop --extra dev
./build_app.sh
```

Document required macOS permissions, LINE window-position limitation, environment/config behavior, OpenAI alternative, remote catalog/About dependencies, test commands, responsible use, project structure, version 1.0.1, three project links, author contact, and the GitHub repository URL.

- [ ] **Step 2: Add MIT License**

Use the standard MIT text with `Copyright (c) 2026 Eric Chen`.

- [ ] **Step 3: Verify documentation references**

Run commands that confirm every referenced local path and script exists and scan for placeholder markers or accidental credentials.

- [ ] **Step 4: Commit documentation**

Commit `README.md` and `LICENSE` with `docs: add public project guide and license`.

### Task 7: Run the full release verification matrix

**Files:**
- No source changes expected.

- [ ] **Step 1: Run all automated suites**

```bash
cd app/frontend && npm test && npm run typecheck && npm run build
cd ../..
node --test web/tests/homepage.test.mjs
php web/tests/sweety_catalog_contract_test.php
php web/tests/sweety_metrics_test.php
app/desktop/.venv/bin/pytest -q app/desktop/tests
```

Expected: every command exits 0 with no failed test.

- [ ] **Step 2: Build the macOS App**

Run `app/desktop/build_app.sh` with the ignored local build credential available. Confirm code signing verification exits 0 and `CFBundleShortVersionString` is `1.0.1`.

- [ ] **Step 3: Perform browser visual verification**

Serve `web/` locally, inspect at 1440px and 390px widths, and capture evidence that:

- the warning is visible;
- all four FAQ items can remain open simultaneously;
- author portrait is circular and card links open new tabs;
- no horizontal overflow occurs.

- [ ] **Step 4: Perform in-App About verification**

Restart the built App, load the local management page, open About Sweety, and confirm the GitHub link, portrait, author information, dark mode, and mobile-width layout render without console errors.

### Task 8: Publish the tested pages to sweety.tw

**Files:**
- No source changes expected unless verification reveals a defect.

- [ ] **Step 1: Run the existing deployment workflow**

Run `php app/tools/deploy_homepage.php`. Do not print values from `web/sftp-config.json`, `config.json`, or generated runtime environment files.

- [ ] **Step 2: Verify live assets and content**

Use HTTPS checks for:

- `https://sweety.tw/`
- `https://sweety.tw/about_sweety.html`
- `https://sweety.tw/images/eric.png`

Confirm status 200, versioned homepage assets, the four FAQ questions, the LINE warning, the GitHub URL, and the author-card text.

- [ ] **Step 3: Recheck in-App remote About**

Reload About Sweety in the rebuilt App and confirm it is consuming the newly deployed sanitized remote document.

### Task 9: Audit and push the public repository

**Files:**
- No source changes expected.

- [ ] **Step 1: Review the complete history and working tree**

Run:

```bash
git status -sb
git log --oneline --decorate
git diff main --check
git ls-files
```

Confirm only source, public assets, tests, plans/specs, README, License, and safe examples are tracked.

- [ ] **Step 2: Run a final tracked-content secret scan**

Scan tracked text for high-risk token/private-key/password patterns. Manually inspect every match that is a variable name or test fixture. Do not push if a real credential, FTP password, local path secret, database, or generated build artifact is present.

- [ ] **Step 3: Run fresh final tests**

Repeat the complete automated verification matrix from Task 7 after the last commit. Record actual passing counts.

- [ ] **Step 4: Push the bootstrap main branch**

```bash
git push -u origin main
gh repo view ericchen1972/Sweety --json defaultBranchRef,url,isPrivate
```

Expected: push succeeds, `main` becomes the public default branch, and the repository remains public.

- [ ] **Step 5: Verify GitHub-rendered project files**

Confirm the public GitHub repository shows README, MIT License, version 1.0.1 source metadata, `web/images/eric.png`, and no ignored secret/build paths.
