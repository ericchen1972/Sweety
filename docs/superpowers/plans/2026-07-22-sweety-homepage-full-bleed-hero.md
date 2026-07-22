# Sweety Homepage Full-Bleed Hero Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the production header logo and make the approved watercolor hero image cover the entire first viewport while keeping the supplied copy readable.

**Architecture:** Keep the existing semantic hero image and `<picture>` fallback, but turn `.hero-art` into an absolutely positioned full-bleed visual layer. Keep `.hero-copy` above it and use a hero pseudo-element for the white readability gradient. Extend the deployment manifest so both logo formats are always published.

**Tech Stack:** Static HTML, CSS, Node test runner, WebP/cwebp, PHP FTP deployment helper.

---

### Task 1: Lock the visual and asset contract with failing tests

**Files:**
- Modify: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Add regression assertions**

Add tests requiring the logo `<picture>` to reference `images/logo.webp`, requiring `.hero` to be positioned and full viewport width, requiring `.hero-art` to use absolute full-bleed positioning, requiring the hero image to use `object-fit: cover` and right-side positioning, and requiring a white readability overlay.

- [ ] **Step 2: Run the tests and verify RED**

Run: `node --test web/tests/homepage.test.mjs`

Expected: failures for the missing logo WebP file, non-full-bleed hero rules, and deployment manifest.

### Task 2: Convert and publish the logo asset

**Files:**
- Create: `web/images/logo.webp`
- Modify: `app/tools/deploy_homepage.php`

- [ ] **Step 1: Convert the existing logo**

Run: `cwebp -quiet -q 88 web/images/logo.png -o web/images/logo.webp`

Verify the file starts with a RIFF/WebP signature and is smaller than the PNG.

- [ ] **Step 2: Add logo files to deployment**

Add both `images/logo.webp` and `images/logo.png` to the explicit `$files` array in `deploy_homepage.php` so the existing preferred WebP source and PNG fallback are always uploaded.

### Task 3: Implement the full-bleed hero

**Files:**
- Modify: `web/homepage.css`

- [ ] **Step 1: Make the hero a full-width positioning context**

Override the shared section width for `.hero`, set `position: relative`, `isolation: isolate`, `overflow: hidden`, and retain `min-height: calc(100vh - 76px)`. Move horizontal spacing to `.hero-copy` using the same responsive page gutter.

- [ ] **Step 2: Place the artwork behind the full hero**

Set `.hero-art` to `position: absolute; inset: 0; z-index: -2; margin: 0`. Make its picture and image fill the layer, with `object-fit: cover` and `object-position: right center`.

- [ ] **Step 3: Add the readability gradient**

Use `.hero::after` as an absolute non-interactive layer between artwork and text with a left-to-right white gradient. Preserve a strong white field behind the text and fade to transparent before the person on the right.

- [ ] **Step 4: Adapt tablet and mobile rules**

Remove the old grid/margin/image-height hero-art overrides. Keep the background layer absolute on mobile, change its object-position to approximately `68% center`, strengthen the vertical/left white overlay, and retain no horizontal overflow.

- [ ] **Step 5: Run homepage tests and verify GREEN**

Run: `node --test web/tests/homepage.test.mjs && node --check web/homepage.js && php -l app/tools/deploy_homepage.php`

Expected: every homepage test passes and both syntax checks exit 0.

### Task 4: Deploy and verify production

**Files:**
- Use: `app/tools/deploy_homepage.php`

- [ ] **Step 1: Deploy the homepage**

Run: `php app/tools/deploy_homepage.php`

Expected: homepage assets upload, the existing metrics migration remains healthy, and the signed macOS app rebuild completes.

- [ ] **Step 2: Verify the live assets and source**

Check that `https://sweety.tw/images/logo.webp` and `https://sweety.tw/images/home/hero-helpless.webp` return HTTP 200 with `image/webp`. Compare live `index.html` and `homepage.css` SHA-256 values against local files.

- [ ] **Step 3: Verify responsive layout**

Render the live site at desktop and mobile widths. Confirm the logo appears, the artwork covers the full hero, the person remains on the right, the text remains readable, and the document has no horizontal overflow.
