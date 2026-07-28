# Mac-Only Main Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace local and GitHub `main` with a tested macOS-only lineage that retains the approved multimodal reply and homepage changes while preserving the Windows worktree as a backup.

**Architecture:** Work only in the isolated `codex/mac-only-main` worktree based on `a100395`, and reapply the two retained change sets test-first. After verification, preserve the old local main tip and its tracked patch, release the clean branch from its linked worktree, repoint local `main`, and push only after proving the update is a fast-forward.

**Tech Stack:** Python 3.11, pytest, FastAPI desktop runtime, Node.js built-in test runner, Vitest, Git worktrees.

---

### Task 1: Lock the multimodal reply boundary with regression tests

**Files:**
- Modify: `app/desktop/tests/test_ai.py`
- Test: `app/desktop/tests/test_ai.py`

- [ ] **Step 1: Add the bottom-left and full-width-colon assertions**

Add this assertion to
`test_prompt_isolates_persona_and_sends_role_preserving_history_with_image`:

```python
assert "最底下一則可見訊息位於左側時，action 必須使用 reply，不得使用 skip" in messages[0]["content"]
```

Add this test immediately before
`test_skip_decision_with_empty_fields_is_accepted`:

```python
def test_fullwidth_colon_after_known_json_key_is_accepted(tmp_path):
    response = ai_response(
        '{"action":"reply","incoming_summary":"對方傳來一張雪納瑞照片","msg_reply"："這圖哪來的？"}'
    )
    client = AiClient(session=FakeSession(response), agnes_key="agnes-test")

    decision = client.generate_reply(
        target=target_payload(),
        screenshot_path=screenshot_path(tmp_path),
        history=[],
        total_messages=0,
        settings=settings(),
    )

    assert decision.msg_reply == "這圖哪來的？"
```

- [ ] **Step 2: Run the focused tests and verify the clean base fails**

Run:

```bash
cd app/desktop
uv run pytest tests/test_ai.py::test_prompt_isolates_persona_and_sends_role_preserving_history_with_image tests/test_ai.py::test_fullwidth_colon_after_known_json_key_is_accepted -q
```

Expected: two failures—one because the prompt lacks the bottom-left rule and one
because `json.loads` rejects the full-width colon.

- [ ] **Step 3: Commit the failing regression tests**

```bash
git add app/desktop/tests/test_ai.py
git commit -m "test: cover mac chat reply boundary"
```

### Task 2: Implement the macOS multimodal reply boundary

**Files:**
- Modify: `app/desktop/src/sweety_app/ai.py`
- Test: `app/desktop/tests/test_ai.py`

- [ ] **Step 1: Replace the immutable visible-message rules**

Replace rules 2–7 in `IMMUTABLE_SAFETY_RULES` with:

```text
2. 先查看畫面最下方，也就是最底下一則可見訊息，判斷它位於左側或右側。最底下一則可見訊息位於左側時，action 必須使用 reply，不得使用 skip；即使它只有貼圖、照片或純表情符號也一樣。
3. 最底下一則可見訊息位於左側時，再找出它上方最接近的一則右側訊息，依畫面由上到下收集該右側訊息下方所有可見的左側訊息。若畫面中沒有任何右側訊息，就收集畫面中所有可見的左側訊息。
4. 文字、貼圖、照片與純表情符號都算訊息。把收集到的內容忠實濃縮成一筆繁體中文 incoming_summary，保留先後順序與非文字內容的客觀描述。
5. 只能根據目前可見畫面判斷，不可向上捲動、推測或補入截圖上方看不到的內容。
6. 有收集到新訊息時 action 使用 reply，並根據最近歷史、人設和完整 incoming_summary 產生一則自然、簡短、能延續對話的回覆。
7. 只有最底下一則可見訊息位於右側，亦即沒有待回覆的左側訊息時，action 才能使用 skip；incoming_summary 和 msg_reply 都必須是空字串。
8. 只輸出一個 JSON 物件，不要 Markdown 或其他文字：
```

- [ ] **Step 2: Align the screenshot request text with the immutable rules**

Replace the screenshot instruction block in `build_messages` with:

```python
(
    "請先判斷畫面最底下一則可見訊息位於左側或右側。"
    "若最底下一則位於左側，必須 action=reply，不得 skip；照片、貼圖與純表情符號也算左側訊息。"
    "接著找出它上方最接近的一則右側訊息，也就是畫面中最下方的右側訊息，"
    "依畫面由上到下收集它下方所有可見的左側訊息。"
    "若畫面沒有任何右側訊息，就收集畫面中所有可見的左側訊息。"
    "文字、貼圖、照片與純表情符號都要依順序濃縮進同一個 incoming_summary。"
    "只處理這張截圖目前看得到的內容，不可向上捲動、推測或補入畫面外的訊息。"
    "只有最底下一則可見訊息位於右側時，才輸出"
    '{"action":"skip","incoming_summary":"","msg_reply":""}；'
    "否則輸出 action 為 reply 的指定 JSON。"
)
```

- [ ] **Step 3: Normalize full-width colons on known response keys**

After stripping an optional leading `json` marker and before `json.loads`, add:

```python
for key in ("action", "incoming_summary", "msg_reply"):
    text = text.replace(f'"{key}"：', f'"{key}":')
```

- [ ] **Step 4: Run the focused and complete AI tests**

Run:

```bash
cd app/desktop
uv run pytest tests/test_ai.py -q
```

Expected: all `test_ai.py` tests pass.

- [ ] **Step 5: Commit the implementation**

```bash
git add app/desktop/src/sweety_app/ai.py
git commit -m "fix: reply to bottommost incoming mac message"
```

### Task 3: Lock the macOS-only homepage contract with tests

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Update the download and machine-readable contract**

Import the hash helper and define only the macOS artifact:

```javascript
import { createHash } from 'node:crypto';

const expectedMacDownload = 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-9ff118bd';
```

Remove the `windows` property from the expected update manifest, and add:

```javascript
test('machine-readable homepage copy marks Windows as coming later', () => {
  assert.match(llms, /目前下載：macOS/);
  assert.match(llms, /Windows：稍後提供/);
  assert.doesNotMatch(llms, /支援平台：Windows、macOS/);
});
```

Replace the active Windows download assertions with:

```javascript
test('download configuration enables macOS and keeps Windows unavailable', () => {
  assert.deepEqual(homepage.downloadConfig, {
    windows: null,
    macos: expectedMacDownload,
  });
  assert.deepEqual(homepage.getDownloadDecision('macos', 'zh-TW'), {
    enabled: true,
    href: expectedMacDownload,
    label: '下載 macOS 版',
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
  assert.equal((html.match(/data-platform="(?:windows|macos)"/g) ?? []).length, 2);
  assert.equal((html.match(/class="platform-icon[^"]*"[^>]*aria-hidden="true"/g) ?? []).length, 3);
});
```

- [ ] **Step 2: Add open-source and asset-hash assertions**

Add `instructions.openSourceNote` to the Chinese exact-copy expectation and the
required localization-hook list. In the asset-version test, add:

```javascript
const assetVersion = createHash('sha256')
  .update(css)
  .update('\0')
  .update(javascript)
  .digest('hex')
  .slice(0, 12);
assert.equal(scriptVersion, assetVersion, 'homepage asset version should match the CSS and JavaScript content hash');
```

Change the static script assertion to:

```javascript
assert.match(html, /<script type="module" src="homepage\.js\?v=[a-f0-9]{12}"><\/script>/);
```

- [ ] **Step 3: Run the homepage tests and verify the clean base fails**

Run:

```bash
cd web
node --test tests/homepage.test.mjs
```

Expected: failures for the still-active Windows installer, old macOS release
digest, absent open-source hook, and old non-hash cache version.

- [ ] **Step 4: Commit the failing homepage tests**

```bash
git add web/tests/homepage.test.mjs
git commit -m "test: require mac-only download contract"
```

### Task 4: Implement the macOS-only homepage contract

**Files:**
- Modify: `web/homepage.js`
- Modify: `web/index.html`
- Modify: `web/llms.txt`
- Modify: `web/sweety-update.json`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Disable Windows and select the verified macOS artifact**

Set the download configuration to:

```javascript
export const downloadConfig = Object.freeze({
  windows: null,
  macos: 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-9ff118bd',
});
```

Set Chinese `download.soon` to `稍後提供`. Add these localized instruction
fields:

```javascript
openSourceNote: '＊Sweety 是一款完全免費且開源的程式，如果您對以編譯完成的執行檔有安全疑慮，歡迎透過 Git 重新編譯',
```

```javascript
openSourceNote: '* Sweety is completely free and open source. If you have safety concerns about the precompiled executable, you are welcome to rebuild it from Git.',
```

- [ ] **Step 2: Synchronize static HTML, discovery copy, and update manifest**

Add the default-English open-source paragraph to the instruction heading:

```html
<p class="instruction-intro" data-copy="instructions.openSourceNote">* Sweety is completely free and open source. If you have safety concerns about the precompiled executable, you are welcome to rebuild it from Git.</p>
```

Replace the platform lines in `web/llms.txt` with:

```text
- 目前下載：macOS
- Windows：稍後提供
```

Set `web/sweety-update.json` downloads to:

```json
"downloads": {
  "macos": "https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-9ff118bd"
}
```

- [ ] **Step 3: Set the content-derived cache version**

Use the SHA-256 prefix already proven by the test for the final CSS and
JavaScript contents:

```html
<link rel="stylesheet" href="homepage.css?v=3a97200747bc">
<script type="module" src="homepage.js?v=3a97200747bc"></script>
```

- [ ] **Step 4: Run the homepage suite**

Run:

```bash
cd web
node --test tests/homepage.test.mjs
```

Expected: 37 tests pass.

- [ ] **Step 5: Commit the homepage implementation**

```bash
git add web/homepage.js web/index.html web/llms.txt web/sweety-update.json
git commit -m "fix: keep public downloads mac-only"
```

### Task 5: Verify the clean branch and Windows backup

**Files:**
- Verify: `app/desktop/`
- Verify: `app/frontend/`
- Verify: `web/`

- [ ] **Step 1: Run all project suites**

Run:

```bash
cd app/desktop && uv run pytest -q
cd ../../app/frontend && npm test -- --run
cd ../../web && node --test tests/homepage.test.mjs
```

Expected: desktop 206 tests, frontend 29 tests, and homepage 37 tests pass.

- [ ] **Step 2: Verify only approved commits follow the Mac base**

Run:

```bash
git log --oneline --reverse a100395..HEAD
git diff --check
git status --short
```

Expected: only the approved design, plan, AI tests/implementation, and homepage
tests/implementation appear; the worktree is clean.

- [ ] **Step 3: Prove Windows experiment files are absent**

Run:

```bash
test ! -e app/desktop/Sweety-Windows.spec
test ! -e app/desktop/build_windows.ps1
test ! -e app/desktop/src/sweety_app/line_windows.py
test ! -e app/desktop/src/sweety_app/main_windows.py
test ! -e app/windows-shell
test ! -e docs/superpowers/specs/2026-07-27-windows-control-panel-design.md
test ! -e docs/superpowers/specs/2026-07-27-windows-portable-line-mvp-design.md
```

Expected: every command exits successfully. Pre-existing historical release
documents and `app/tools/deploy_windows_release.php` are allowed by the spec.

- [ ] **Step 4: Capture the Windows backup state**

Run from the repository root:

```bash
git -C .worktrees/windows-control-panel rev-parse HEAD
git -C .worktrees/windows-control-panel status --porcelain=v1
```

Expected: HEAD remains `5682d29`; its existing modified and untracked backup
files remain present.

### Task 6: Move local main safely and push GitHub

**Files:**
- Preserve: root tracked patch in a named stash
- Preserve: root `videos/`
- Preserve: `.worktrees/windows-control-panel`

- [ ] **Step 1: Preserve the old local main and tracked working patch**

Run from the repository root:

```bash
git branch backup/windows-main-2026-07-28 8c94916
git stash push -m "backup: pre-clean mac-only tracked patch" -- \
  app/desktop/src/sweety_app/ai.py \
  app/desktop/tests/test_ai.py \
  web/homepage.js \
  web/index.html \
  web/llms.txt \
  web/sweety-update.json \
  web/tests/homepage.test.mjs
```

Expected: the seven tracked files become clean, `videos/` remains untracked,
and the old main tip is recoverable from the backup branch.

- [ ] **Step 2: Release the clean branch and repoint local main**

Record the clean commit hash in a task-specific shell variable, then run:

```bash
sweety_clean_commit=$(git -C .worktrees/mac-only-main rev-parse HEAD)
git switch --detach 8c94916
git -C .worktrees/mac-only-main switch --detach "$sweety_clean_commit"
git branch -f main "$sweety_clean_commit"
git switch main
```

Expected: root is on `main` at that hash; `.worktrees/mac-only-main` is detached
at the same hash; `videos/` is still present and untracked.

- [ ] **Step 3: Re-fetch and enforce fast-forward safety**

Run:

```bash
git fetch origin main
git merge-base --is-ancestor origin/main main
git rev-list --left-right --count origin/main...main
```

Expected: the ancestor check succeeds and the count shows zero remote-only
commits with local clean commits ahead.

- [ ] **Step 4: Push and verify the remote branch**

Run:

```bash
git push origin main
test "$(git rev-parse main)" = "$(git ls-remote origin refs/heads/main | cut -f1)"
```

Expected: normal fast-forward push succeeds and local/remote hashes match.

- [ ] **Step 5: Perform final preservation checks**

Run:

```bash
git status --short --branch
test -d videos
git -C .worktrees/windows-control-panel rev-parse HEAD
git -C .worktrees/windows-control-panel status --porcelain=v1
git branch --list backup/windows-main-2026-07-28
git stash list
```

Expected: root `main` matches `origin/main` and shows only the pre-existing
untracked `videos/`; Windows backup HEAD remains `5682d29` with its original
working changes; the old main branch and tracked patch both remain recoverable.
