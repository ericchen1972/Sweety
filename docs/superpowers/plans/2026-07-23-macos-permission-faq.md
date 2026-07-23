# macOS Permission FAQ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and publish a fifth localized homepage FAQ that explains how to restore both required macOS permission entries after an app update.

**Architecture:** Keep localized strings in `web/homepage.js`, render the emphasized recovery instruction through dedicated text-only `<span>` and `<strong>` hooks in `web/index.html`, and mirror the complete Traditional Chinese answer in FAQPage JSON-LD. Extend the existing Node contract test before changing production files, then deploy with the established homepage helper and verify the live response.

**Tech Stack:** Static HTML, JavaScript ES modules, CSS, JSON-LD, Node.js test runner, PHP FTP deployment helper

---

### Task 1: Lock The Fifth FAQ Contract

**Files:**
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Replace the four-item FAQ test with a five-item contract**

Rename the test to `homepage includes the LINE window warning and five independent localized FAQs`. Assert:

```javascript
const permissionFaqZh = homepage.copy['zh-TW'].faq.items[4];
const permissionFaqEn = homepage.copy.en.faq.items[4];

assert.equal(homepage.copy['zh-TW'].faq.items.length, 5);
assert.equal(homepage.copy.en.faq.items.length, 5);
assert.equal((html.match(/<details\b/g) ?? []).length, 5);
assert.equal((html.match(/<summary\b/g) ?? []).length, 5);
assert.deepEqual(permissionFaqZh, {
  question: '為什麼按下開始後顯示「需要 Mac 權限」？',
  answerPrefix: '因為程式更新後可能被系統判斷為新的程式，所以請到偏好設定的',
  answerEmphasis: '「輔助使用」及「螢幕與系統錄音」內，移除 Sweety 後再重新加入。',
});
assert.deepEqual(permissionFaqEn, {
  question: 'Why does Sweety show “macOS permissions required” after I press Start?',
  answerPrefix: 'After an update, macOS may treat Sweety as a new app. In System Settings, ',
  answerEmphasis: 'remove Sweety from Accessibility and Screen & System Audio Recording, then add it again.',
});
```

Also assert that the fifth `<details>` contains:

```html
<span data-copy="faq.items.4.answerPrefix">
<strong data-copy="faq.items.4.answerEmphasis">
```

and that JSON-LD includes the full Traditional Chinese question and answer.

- [ ] **Step 2: Run the homepage test and verify RED**

Run: `node --test web/tests/homepage.test.mjs`

Expected: FAIL because both locale arrays and the HTML currently contain four FAQ entries.

### Task 2: Add The Localized FAQ And Structured Markup

**Files:**
- Modify: `web/homepage.js`
- Modify: `web/index.html`

- [ ] **Step 1: Add the fifth localized copy object**

Append to the Traditional Chinese FAQ array:

```javascript
{
  question: '為什麼按下開始後顯示「需要 Mac 權限」？',
  answerPrefix: '因為程式更新後可能被系統判斷為新的程式，所以請到偏好設定的',
  answerEmphasis: '「輔助使用」及「螢幕與系統錄音」內，移除 Sweety 後再重新加入。',
},
```

Append to the English FAQ array:

```javascript
{
  question: 'Why does Sweety show “macOS permissions required” after I press Start?',
  answerPrefix: 'After an update, macOS may treat Sweety as a new app. In System Settings, ',
  answerEmphasis: 'remove Sweety from Accessibility and Screen & System Audio Recording, then add it again.',
},
```

- [ ] **Step 2: Add safe structured answer markup**

Append this fifth disclosure to `.faq-list`:

```html
<details class="faq-item">
  <summary data-copy="faq.items.4.question">Why does Sweety show “macOS permissions required” after I press Start?</summary>
  <p><span data-copy="faq.items.4.answerPrefix">After an update, macOS may treat Sweety as a new app. In System Settings, </span><strong data-copy="faq.items.4.answerEmphasis">remove Sweety from Accessibility and Screen &amp; System Audio Recording, then add it again.</strong></p>
</details>
```

The generic renderer continues assigning localized strings with `textContent`; do not add `innerHTML`.

- [ ] **Step 3: Add the fifth JSON-LD question**

Append to `FAQPage.mainEntity`:

```json
{
  "@type": "Question",
  "name": "為什麼按下開始後顯示「需要 Mac 權限」？",
  "acceptedAnswer": {
    "@type": "Answer",
    "text": "因為程式更新後可能被系統判斷為新的程式，所以請到偏好設定的「輔助使用」及「螢幕與系統錄音」內，移除 Sweety 後再重新加入。"
  }
}
```

- [ ] **Step 4: Run the homepage tests and verify GREEN**

Run: `node --test web/tests/homepage.test.mjs`

Expected: all homepage tests PASS.

- [ ] **Step 5: Commit the FAQ implementation**

```bash
git add web/homepage.js web/index.html web/tests/homepage.test.mjs
git commit -m "feat: add macOS permission recovery FAQ"
```

### Task 3: Verify And Publish

**Files:**
- Deploy: `web/homepage.js`
- Deploy: `web/index.html`

- [ ] **Step 1: Run static verification**

Run:

```bash
node --test web/tests/*.test.mjs
git diff --check
```

Expected: all web tests PASS and the diff check exits zero.

- [ ] **Step 2: Deploy the homepage**

Run: `php app/tools/deploy_homepage.php`

Expected: all homepage files upload with verified sizes, the metrics schema check succeeds, and the signed local app rebuild succeeds.

- [ ] **Step 3: Verify the live homepage and JavaScript**

Fetch `https://sweety.tw/` and `https://sweety.tw/homepage.js` with a cache-busting query. Assert:

- The live HTML contains five `<details>` and five `<summary>` elements.
- The fifth answer contains the dedicated `<span>` and `<strong>` data-copy hooks.
- Live JSON-LD contains the full Traditional Chinese question and answer.
- Live JavaScript contains both localized fifth FAQ objects.

- [ ] **Step 4: Record completion**

Mark all plan checkboxes complete and commit the updated plan:

```bash
git add docs/superpowers/plans/2026-07-23-macos-permission-faq.md
git commit -m "docs: record macOS permission FAQ rollout"
```

- [ ] **Step 5: Review final repository state**

Run: `git status --short --branch && git log -5 --oneline`

Expected: the tracked worktree is clean on `main`, with the FAQ design, implementation, and rollout commits visible.
