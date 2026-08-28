# ChatGPT Perspective Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user explicitly requested inline execution without subagents.

**Goal:** Add the complete README ChatGPT perspective to the homepage in Traditional Chinese, English, and Japanese, with a visible summary and an expandable full article below the instructions copy.

**Architecture:** Keep localized content in the existing `copy` objects and use safe `textContent`-based `data-copy` hooks in static semantic HTML. Use native `<details>` and `<summary>` for progressive disclosure, with CSS extending the homepage's existing pale-blue editorial treatment. Preserve the existing page initialization and deployment contracts.

**Tech Stack:** Static HTML, CSS, ECMAScript modules, Node.js built-in test runner.

---

### Task 1: Lock the localized content and placement contract

**Files:**
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Write the failing tests**

Add a test that requires `copy['zh-TW'].instructions.perspective`, `copy.en.instructions.perspective`, and `copy.ja.instructions.perspective` to have the same keys. Assert the exact Traditional Chinese title, source note, core statement, expansion labels, two funnels, ROI formula, and closing statement. Assert that `web/index.html` places `.chatgpt-perspective` after `instructions.openSourceNote` and before `.instruction-guide`, contains a native `<details>`/`<summary>`, and exposes every perspective field through `data-copy`.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `rtk node --test --test-name-pattern="ChatGPT perspective" web/tests/homepage.test.mjs`

Expected: FAIL because the perspective copy and markup do not exist.

- [ ] **Step 3: Commit the red test**

```bash
git add web/tests/homepage.test.mjs
git commit -m "test: define homepage ChatGPT perspective contract"
```

### Task 2: Add the trilingual perspective content and semantic markup

**Files:**
- Modify: `web/homepage.js`
- Modify: `web/index.html`

- [ ] **Step 1: Add localized copy objects**

Under each locale's `instructions` object, add a `perspective` object with parallel keys for the visible title/source/summary/conclusion, the expand and collapse labels, and every full-article paragraph, emphasized line, funnel, numbered point, diagram, and formula. Use the README Traditional Chinese verbatim; add faithful English and Japanese translations with identical numbers and conceptual ordering.

- [ ] **Step 2: Add the static accessible section**

Insert `<aside class="chatgpt-perspective" aria-labelledby="chatgpt-perspective-title">` immediately after the open-source paragraph. Use a visible `<h3>`, source paragraph, summary, highlighted conclusion, and `<details class="chatgpt-perspective-details">` with an English fallback article. Every localized text node uses a `data-copy="instructions.perspective.…"` hook; content is never assigned with `innerHTML`.

- [ ] **Step 3: Support localized open and closed labels**

Place two spans inside `<summary>`:

```html
<span class="perspective-expand-label" data-copy="instructions.perspective.expandLabel">Read the full perspective</span>
<span class="perspective-collapse-label" data-copy="instructions.perspective.collapseLabel">Close the full perspective</span>
```

CSS will choose the appropriate label from the native `details[open]` state, so no new JavaScript event handler is required.

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `rtk node --test --test-name-pattern="ChatGPT perspective" web/tests/homepage.test.mjs`

Expected: PASS.

### Task 3: Style the summary and expanded article responsively

**Files:**
- Modify: `web/homepage.css`
- Modify: `web/index.html`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Add a failing style contract**

Require CSS selectors for `.chatgpt-perspective`, `.chatgpt-perspective-summary`, `.chatgpt-perspective-details`, `.perspective-funnel`, `.perspective-diagram`, and the open/closed labels. Require `overflow-x: auto` on preformatted content and a mobile rule that reduces card padding.

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `rtk node --test --test-name-pattern="ChatGPT perspective" web/tests/homepage.test.mjs`

Expected: FAIL because the new CSS selectors do not exist.

- [ ] **Step 3: Implement the style**

Extend the current instructions palette with a pale-blue rounded card, blue left accent, restrained typography, a high-contrast summary button, readable article measure, shaded preformatted data blocks, and responsive padding. Hide `.perspective-collapse-label` while closed and `.perspective-expand-label` while open.

- [ ] **Step 4: Refresh the asset digest**

Compute `sha256(homepage.css + NUL + homepage.js).slice(0, 12)` and replace both `homepage.css?v=…` and `homepage.js?v=…` in `web/index.html` with the same value.

- [ ] **Step 5: Run the complete homepage suite**

Run: `rtk node --test web/tests/homepage.test.mjs`

Expected: all homepage tests PASS.

### Task 4: Verify the rendered result

**Files:**
- Verify: `web/index.html`
- Verify: `web/homepage.css`
- Verify: `web/homepage.js`

- [ ] **Step 1: Run static validation**

Run: `rtk git diff --check`

Expected: no output and exit status 0.

- [ ] **Step 2: Render desktop and mobile views**

Serve `web/` locally and inspect the instructions section at desktop and mobile widths. Confirm the title, summary, conclusion, expand control, full article, and close control render correctly; confirm the first guide image follows the card.

- [ ] **Step 3: Check overflow and interaction**

At 390px width, confirm `document.documentElement.scrollWidth === document.documentElement.clientWidth`, expand and collapse the full article, and confirm preformatted funnels scroll only inside their own containers.

- [ ] **Step 4: Commit the implementation**

```bash
git add web/homepage.js web/index.html web/homepage.css web/tests/homepage.test.mjs docs/superpowers/plans/2026-08-28-chatgpt-perspective-homepage.md
git commit -m "feat: add ChatGPT perspective to homepage"
```
