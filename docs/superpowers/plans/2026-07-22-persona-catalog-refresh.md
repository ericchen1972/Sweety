# Persona Catalog Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the 35-50 catalog and add a testable 50-65 remote catalog with correct 16:9 artwork and readable persona styles.

**Architecture:** Repair source data rather than masking it: generate each image independently, store prose in remote style fields, and include all three age groups in the authenticated PHP response. Add a frontend compatibility formatter for stale JSON and verify remote-to-local synchronization end to end.

**Tech Stack:** React, TypeScript, Vitest, Python, SQLite, PHP 8.2, MySQL, FTP, imagegen, Pillow.

---

### Task 1: Legacy style display compatibility

**Files:**
- Modify: `app/frontend/src/domain.ts`
- Modify: `app/frontend/src/domain.test.ts`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/i18n.ts`
- Create: `app/frontend/src/i18n.test.ts`

- [ ] Add a failing test that passes serialized style JSON and expects readable text with no opening JSON brace.
- [ ] Run `npm test -- --run src/domain.test.ts` and confirm the test fails because the formatter does not exist.
- [ ] Implement `formatPersonaStyle(value, locale)` and use it in the persona detail modal.
- [ ] Add exact Traditional Chinese copy tests for the persona-name label and both requested placeholders.
- [ ] Merge profile and style into one visible persona-content section and update the custom-persona form copy.
- [ ] Re-run the focused frontend test and confirm it passes.

### Task 2: Independent persona artwork

**Files:**
- Replace: `web/images/personas/careful-bank-operations-specialist.jpg`
- Replace: `web/images/personas/busy-bakery-owner.jpg`
- Replace: `web/images/personas/guarded-insurance-clerk.jpg`
- Replace: `web/images/personas/practical-taxi-driver.jpg`
- Replace: `web/images/personas/factory-shift-supervisor.jpg`
- Replace: `web/images/personas/independent-repair-technician.jpg`
- Create: six `50-65` persona JPG files under `web/images/personas/`

- [ ] Generate one source image per persona using twelve separate imagegen requests.
- [ ] Inspect every generated source for identity, occupation, natural proportions, and absence of text.
- [ ] Center-crop each source to 16:9 and export at exactly 1280-by-720 without non-uniform scaling.
- [ ] Verify all twelve files report a 1.7778 aspect ratio.

### Task 3: Remote catalog data

**Files:**
- Modify: `app/tools/base_catalog.sql`
- Modify: `web/sweety-catalog.php`
- Modify: `app/tools/deploy_base_catalog.php`
- Modify: `app/tools/catalog_remote_runner.template.php`

- [ ] Add the `50-65` age group and six localized personas to SQL.
- [ ] Replace serialized style JSON with natural-language descriptions.
- [ ] Include `50-65` in the PHP query and add the six new assets to deployment.
- [ ] Update remote checks to require 18 personas, six per group, three women and three men per group, and non-JSON style text.
- [ ] Run PHP syntax checks before deployment.

### Task 4: Deploy and refresh local cache

**Files:**
- Update remote MySQL and catalog assets through `app/tools/deploy_base_catalog.php`.
- Update local `~/Library/Application Support/Sweety/sweety.sqlite3` data.

- [ ] Deploy SQL, PHP, and all catalog images to the configured remote server.
- [ ] Call the authenticated catalog endpoint and verify 18 personas, six in 35-50 and six in 50-65.
- [ ] Verify each new remote embedded image decodes to 1280-by-720 and each style value is prose.
- [ ] Stop Sweety, delete local `35-50` base persona rows, and confirm zero remain before relaunch.
- [ ] Relaunch the rebuilt app and verify local state receives six 35-50 and six 50-65 personas.

### Task 5: Build verification

**Files:**
- Verify: `app/frontend`
- Verify: `app/desktop`

- [ ] Run frontend tests, typecheck, and production build.
- [ ] Run the complete desktop pytest suite.
- [ ] Build `app/desktop/dist/Sweety.app`.
- [ ] Verify the app signature and inspect the live UI at desktop and mobile widths for undistorted 16:9 artwork and readable style prose.

### Task 6: Remote About page

**Files:**
- Create: `web/about_sweety.html`
- Create: `app/desktop/src/sweety_app/about.py`
- Create: `app/desktop/tests/test_about.py`
- Modify: `app/desktop/src/sweety_app/api.py`
- Modify: `app/desktop/src/sweety_app/__main__.py`
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/api.test.ts`
- Modify: `app/frontend/src/i18n.ts`
- Modify: `app/frontend/src/i18n.test.ts`
- Modify: `app/tools/deploy_base_catalog.php`

- [ ] Add a failing copy test for the `關於 Sweety` navigation label and load-error text.
- [ ] Add backend tests proving dangerous remote markup is removed and safe semantic content remains.
- [ ] Add the sidebar item directly below Persona Editor and render sanitized backend content in normal page flow without an iframe.
- [ ] Create a responsive, standalone About document with no external scripts.
- [ ] Deploy the document and verify the public URL returns HTML successfully.
