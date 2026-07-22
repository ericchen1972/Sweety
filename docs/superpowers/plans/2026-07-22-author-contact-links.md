# Author Contact Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add consistent, safely opened LINE and Threads links to the public homepage and App-loaded About author cards.

**Architecture:** Keep author-card markup static in both HTML surfaces and keep homepage language-specific sentences in the existing `copy` object. Reuse the current responsive flex layout, adding only baseline alignment and a focused Threads follow-up class.

**Tech Stack:** HTML, CSS, JavaScript localization, Node.js test runner, Python pytest

---

### Task 1: Lock The Author-Link Contract With Failing Tests

**Files:**
- Modify: `web/tests/about.test.mjs`
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Add About-page link assertions**

Assert that `web/about_sweety.html` contains both approved URLs with `target="_blank"` and `rel="noopener noreferrer"`, plus the sentence `如想得到更多AI開發應用訊息，請追蹤我的 Threads`.

- [ ] **Step 2: Add homepage link and localization assertions**

Extend the homepage author test to assert both approved safe new-tab links. Assert `homepage.copy['zh-TW'].author.threads` equals `如想得到更多AI開發應用訊息，請追蹤我的 Threads` and the English value equals `For more AI development and application updates, follow me on Threads.`

- [ ] **Step 3: Run both tests and verify they fail for the missing links**

Run: `node --test web/tests/about.test.mjs web/tests/homepage.test.mjs`

Expected: FAIL because LINE is plain text and the Threads links/copy do not exist.

### Task 2: Implement Both Author Cards

**Files:**
- Modify: `web/about_sweety.html`
- Modify: `web/index.html`
- Modify: `web/homepage.js`
- Modify: `web/homepage.css`

- [ ] **Step 1: Update About markup and focused styles**

Link `bobo2010` to `https://line.me/ti/p/ekr53MoZc6`, add the approved Threads sentence with `Threads` linked to `https://www.threads.com/@eric_slimweb`, and add `align-items: baseline` to `.author-contact`. Add `.author-threads` spacing and link color rules without changing the card layout.

- [ ] **Step 2: Update homepage markup, copy, and focused styles**

Apply the same LINE and Threads links to `web/index.html`; add `data-copy="author.threads"` to the follow-up paragraph. Add these localization entries in `web/homepage.js`:

```js
threads: '如想得到更多AI開發應用訊息，請追蹤我的 Threads',
```

```js
threads: 'For more AI development and application updates, follow me on Threads.',
```

Add baseline alignment and `.author-threads` spacing/link color rules to `web/homepage.css`.

- [ ] **Step 3: Run both web tests and verify they pass**

Run: `node --test web/tests/about.test.mjs web/tests/homepage.test.mjs`

Expected: PASS.

- [ ] **Step 4: Commit author-card changes**

```bash
git add web/about_sweety.html web/index.html web/homepage.js web/homepage.css web/tests/about.test.mjs web/tests/homepage.test.mjs
git commit -m "feat: add author LINE and Threads links"
```

### Task 3: Verify Embedded About Compatibility

**Files:**
- Verify: `app/desktop/tests/test_about.py`
- Verify: `app/frontend/src/index.css`

- [ ] **Step 1: Run the desktop About tests**

Run: `app/desktop/.venv/bin/pytest -q app/desktop/tests/test_about.py`

Expected: PASS; the sanitizer keeps safe HTTPS anchors and the App styles continue to support the author card.

- [ ] **Step 2: Run whitespace and scope checks**

Run: `git diff --check && git status --short`

Expected: no whitespace errors and only planned work remains.
