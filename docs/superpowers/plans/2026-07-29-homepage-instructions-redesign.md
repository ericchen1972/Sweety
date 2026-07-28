# Homepage Instructions Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the homepage’s old two-column instruction gallery with seven supplied WebP screenshots, each followed by localized explanatory text, plus the supplied final reminder.

**Architecture:** Keep homepage localization in `web/homepage.js`, static English fallback and semantic markup in `web/index.html`, and presentation in `web/homepage.css`. Contract tests in `web/tests/homepage.test.mjs` verify the exact image and copy surface; `deploy_homepage.php` already uploads every WebP under `web/images/home`.

**Tech Stack:** Static HTML, CSS, ES modules, Node test runner, macOS `sips`, PHP FTP deployment.

---

### Task 1: Lock the new instruction contract

**Files:**
- Modify: `web/tests/homepage.test.mjs`

- [ ] Replace the Quick start and Advanced settings assertions with a test requiring seven `.webp` images named `instructions-control-panel.webp` through `instructions-custom-personas.webp`.
- [ ] Require `instructions.guide.<key>.title`, `.body`, and `.imageAlt` for all seven items, plus the exact `instructions.triggerNotice` Chinese sentence.
- [ ] Require seven `.instruction-guide-item` elements and CSS that declares a one-column guide layout.
- [ ] Run `node --test web/tests/homepage.test.mjs`; expect failure because the new assets and markup do not exist.

### Task 2: Convert the supplied screenshots

**Files:**
- Create: `web/images/home/instructions-control-panel.webp`
- Create: `web/images/home/instructions-dashboard.webp`
- Create: `web/images/home/instructions-basic-settings.webp`
- Create: `web/images/home/instructions-target-list.webp`
- Create: `web/images/home/instructions-base-personas.webp`
- Create: `web/images/home/instructions-persona-details.webp`
- Create: `web/images/home/instructions-custom-personas.webp`

- [ ] Convert each approved PNG with `sips -s format webp -s formatOptions 82 <source> --out <destination>`.
- [ ] Verify the control panel is 419×499 and each management screenshot is 1325×757.
- [ ] Verify every output begins with a RIFF/WebP header and is smaller than its PNG source.

### Task 3: Replace markup, localization, and layout

**Files:**
- Modify: `web/index.html`
- Modify: `web/homepage.js`
- Modify: `web/homepage.css`

- [ ] Replace `.instruction-block` and `.advanced-block` with `.instruction-guide`, containing seven semantic `<article>` elements in the approved order.
- [ ] Give every `<img>` a WebP source, explicit natural dimensions, `loading="lazy"`, `decoding="async"`, and a `data-alt` hook.
- [ ] Add Traditional Chinese and English title/body/alt strings under `instructions.guide`, and add `instructions.triggerNotice`.
- [ ] Remove the obsolete Quick start and Advanced settings list rendering calls.
- [ ] Add one-column guide/card styling and centered narrow-panel styling at all breakpoints.
- [ ] Recompute `sha256(homepage.css + NUL + homepage.js).slice(0, 12)` and update both asset query versions in `web/index.html`.

### Task 4: Verify and deploy

**Files:**
- Verify: `web/tests/homepage.test.mjs`
- Deploy: `app/tools/deploy_homepage.php`

- [ ] Run `node --test web/tests/homepage.test.mjs`; expect all tests to pass.
- [ ] Run `git diff --check`.
- [ ] Render the local homepage at desktop and mobile widths and inspect the instruction section.
- [ ] Run `rtk php app/tools/deploy_homepage.php`.
- [ ] Fetch cache-busted production HTML, the exact versioned JavaScript, and all seven WebP images; require HTTP 200 and the new copy.
- [ ] Inspect the live desktop and mobile instruction section, then commit and push only the intended homepage files and assets.
