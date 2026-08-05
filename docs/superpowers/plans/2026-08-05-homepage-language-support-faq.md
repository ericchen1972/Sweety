# Homepage Language Support FAQ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and publish a sixth homepage FAQ describing Sweety's interface and AI reply-language support in Traditional Chinese, English, and Japanese.

**Architecture:** Extend the existing localized FAQ arrays and static English disclosure without changing the renderer. Keep runtime FAQPage JSON-LD generated from the same locale data, update the static Traditional Chinese JSON-LD fallback, and use the established website-only deployment helper.

**Tech Stack:** Semantic HTML, browser ES modules, Node.js built-in test runner, SHA-256 cache versioning, PHP FTP deployment.

---

## File Map

- Modify `web/tests/homepage.test.mjs`: lock the six-item, three-locale FAQ contract and structured-data count.
- Modify `web/homepage.js`: append the sixth localized FAQ item to `zh-TW`, `en`, and `ja`.
- Modify `web/index.html`: append the static English disclosure, append the static Traditional Chinese JSON-LD question, and refresh the shared asset version.
- Use `app/tools/deploy_homepage.php` unchanged: upload only homepage files and verify remote metrics/download state.

### Task 1: Add the failing six-item FAQ contract

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Test: `web/tests/homepage.test.mjs`

- [x] **Step 1: Update the localized FAQ assertions**

Change the Japanese count in `Japanese copy covers the complete homepage and uses Japanese formatting` to six. In the homepage FAQ test, rename it to `homepage includes the LINE window warning and six independent localized FAQs` and add:

```js
const languageFaqZh = homepage.copy['zh-TW'].faq.items[5];
const languageFaqEn = homepage.copy.en.faq.items[5];
const languageFaqJa = homepage.copy.ja.faq.items[5];

assert.equal(homepage.copy['zh-TW'].faq.items.length, 6);
assert.equal(homepage.copy.en.faq.items.length, 6);
assert.equal(homepage.copy.ja.faq.items.length, 6);
assert.deepEqual(languageFaqZh, {
  question: 'Sweety 支援哪些語系？',
  answer: 'Sweety 介面支援繁中、英文及日文，但是 AI 的回覆將以對方使用的語言為主。',
});
assert.deepEqual(languageFaqEn, {
  question: 'Which languages does Sweety support?',
  answer: 'The Sweety interface supports Traditional Chinese, English, and Japanese. AI replies will primarily use the language spoken by the other person.',
});
assert.deepEqual(languageFaqJa, {
  question: 'Sweetyはどの言語に対応していますか？',
  answer: 'Sweetyのインターフェースは繁体字中国語、英語、日本語に対応しています。ただし、AIは主に相手が使用している言語で返信します。',
});
assert.equal((html.match(/<details\b/g) ?? []).length, 6);
assert.equal((html.match(/<summary\b/g) ?? []).length, 6);
assert.match(html, /data-copy="faq\.items\.5\.question"/);
assert.match(html, /data-copy="faq\.items\.5\.answer"/);
assert.match(html, /"name": "Sweety 支援哪些語系？"/);
```

Update the Japanese structured-data test to expect six entries and assert:

```js
assert.equal(faq.mainEntity.length, 6);
assert.equal(faq.mainEntity[5].name, homepage.copy.ja.faq.items[5].question);
assert.equal(faq.mainEntity[5].acceptedAnswer.text, homepage.copy.ja.faq.items[5].answer);
```

- [x] **Step 2: Run the focused test and verify RED**

Run:

```bash
node --test --test-name-pattern='Japanese copy|Japanese metadata|six independent localized FAQs' web/tests/homepage.test.mjs
```

Expected: FAIL because each locale and the static HTML still have five FAQ items.

### Task 2: Add the sixth localized FAQ and static fallback

**Files:**
- Modify: `web/homepage.js`
- Modify: `web/index.html`
- Test: `web/tests/homepage.test.mjs`

- [x] **Step 1: Append the localized copy in `web/homepage.js`**

Append these plain-text objects after the existing permission FAQ in their matching locale arrays:

```js
{ question: 'Sweety 支援哪些語系？', answer: 'Sweety 介面支援繁中、英文及日文，但是 AI 的回覆將以對方使用的語言為主。' }
{ question: 'Which languages does Sweety support?', answer: 'The Sweety interface supports Traditional Chinese, English, and Japanese. AI replies will primarily use the language spoken by the other person.' }
{ question: 'Sweetyはどの言語に対応していますか？', answer: 'Sweetyのインターフェースは繁体字中国語、英語、日本語に対応しています。ただし、AIは主に相手が使用している言語で返信します。' }
```

- [x] **Step 2: Append the English fallback disclosure in `web/index.html`**

```html
<details class="faq-item"><summary data-copy="faq.items.5.question">Which languages does Sweety support?</summary><p data-copy="faq.items.5.answer">The Sweety interface supports Traditional Chinese, English, and Japanese. AI replies will primarily use the language spoken by the other person.</p></details>
```

- [x] **Step 3: Append the Traditional Chinese static FAQPage entry**

Add this as the sixth `mainEntity` item, preserving valid JSON commas:

```json
{ "@type": "Question", "name": "Sweety 支援哪些語系？", "acceptedAnswer": { "@type": "Answer", "text": "Sweety 介面支援繁中、英文及日文，但是 AI 的回覆將以對方使用的語言為主。" } }
```

- [x] **Step 4: Run the focused test and verify GREEN except for cache version**

Run:

```bash
node --test --test-name-pattern='Japanese copy|Japanese metadata|six independent localized FAQs' web/tests/homepage.test.mjs
```

Expected: selected FAQ tests pass.

### Task 3: Refresh cache version and verify locally

**Files:**
- Modify: `web/index.html`
- Test: `web/tests/homepage.test.mjs`

- [x] **Step 1: Compute the shared CSS/JavaScript cache version**

Run:

```bash
node -e "const fs=require('node:fs');const crypto=require('node:crypto');const css=fs.readFileSync('web/homepage.css');const js=fs.readFileSync('web/homepage.js');process.stdout.write(crypto.createHash('sha256').update(css).update(Buffer.from([0])).update(js).digest('hex').slice(0,12)+'\n')"
```

Expected: one 12-character lowercase hexadecimal value.

- [x] **Step 2: Put the exact version in both asset URLs**

```html
<link rel="stylesheet" href="homepage.css?v=<computed value>">
<script type="module" src="homepage.js?v=<computed value>"></script>
```

- [x] **Step 3: Run complete local verification**

Run:

```bash
node --test web/tests/homepage.test.mjs
node --test web/tests/about.test.mjs
php web/tests/sweety_metrics_test.php
php web/tests/sweety_downloads_test.php
git diff --check
```

Expected: all Node tests and PHP checks pass; `git diff --check` prints nothing.

- [x] **Step 4: Verify the deployment boundary and commit**

Run:

```bash
rg -n 'build_app\.sh|build_dmg\.sh|deploy_macos_release|dist/Sweety\.app' app/tools/deploy_homepage.php
git status --short
```

Expected: deployment search has no matches; changes are limited to this plan, the three homepage files, and pre-existing untracked `videos/`.

Commit:

```bash
git add docs/superpowers/plans/2026-08-05-homepage-language-support-faq.md web/tests/homepage.test.mjs web/homepage.js web/index.html
git commit -m "feat: add homepage language support FAQ"
```

### Task 4: Publish the website and verify live output

**Files:**
- Deploy with: `app/tools/deploy_homepage.php`
- Verify: `https://sweety.tw/`

- [ ] **Step 1: Publish website files only**

Run:

```bash
php app/tools/deploy_homepage.php
```

Expected: homepage files/assets upload successfully, metrics schema and download counter checks pass, and there is no desktop build/signing output.

- [ ] **Step 2: Fetch cache-busted live assets**

Fetch `https://sweety.tw/?verify=<timestamp>`, extract the shared asset version, and download that exact `homepage.js` resource. Expected: the live asset version equals the local 12-character hash and the response contains all three new translations.

- [ ] **Step 3: Verify live FAQ and structured data**

Expected live evidence:

- six `<details>` and six `<summary>` elements;
- sixth `faq.items.5.question` and `faq.items.5.answer` hooks;
- static FAQPage JSON-LD contains six entries including `Sweety 支援哪些語系？`;
- `buildFaqStructuredData('zh-TW')`, `buildFaqStructuredData('en')`, and `buildFaqStructuredData('ja')` each produce six entries from the deployed JavaScript;
- no desktop App files were built or published.
