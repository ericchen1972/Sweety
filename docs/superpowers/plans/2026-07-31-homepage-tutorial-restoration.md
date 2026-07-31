# Homepage Tutorial Restoration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the existing bilingual, locale-selected homepage tutorial video immediately before FAQ and publish it without rebuilding the desktop app.

**Architecture:** Reapply only the tutorial-specific contract preserved in Git stash commit `025b147`, adapting it to the current `main` homepage. Keep locale selection in `web/homepage.js`, semantic fallback markup in `web/index.html`, responsive presentation in `web/homepage.css`, and enforce the whole behavior with the existing Node homepage contract test.

**Tech Stack:** Static HTML, CSS, JavaScript ES modules, Node.js test runner, PHP website-only deployment helper.

---

### Task 1: Lock the missing tutorial contract

**Files:**
- Modify: `web/tests/homepage.test.mjs`

- [x] **Step 1: Add the failing regression test**

Insert after the locale-resolution test:

```js
test('tutorial video follows the resolved locale and appears immediately before FAQ', () => {
  assert.deepEqual(homepage.getTutorialVideo('zh-TW'), {
    id: 'w2w5HGmXxwo',
    src: 'https://www.youtube-nocookie.com/embed/w2w5HGmXxwo',
    title: 'Sweety 中文使用教學',
  });
  assert.deepEqual(homepage.getTutorialVideo('en'), {
    id: '-qS4MGvnsa4',
    src: 'https://www.youtube-nocookie.com/embed/-qS4MGvnsa4',
    title: 'Sweety English tutorial',
  });

  const videoIndex = html.indexOf('class="tutorial-video-section"');
  const faqIndex = html.indexOf('class="faq-section"');
  assert.ok(videoIndex >= 0, 'tutorial video section should exist');
  assert.ok(videoIndex < faqIndex, 'tutorial video should appear before FAQ');
  assert.equal((html.match(/data-tutorial-video/g) ?? []).length, 1);
  assert.match(html, /<iframe[^>]+data-tutorial-video[^>]+loading="lazy"[^>]+allowfullscreen/);
  assert.match(css, /\.tutorial-video-frame\s*\{[^}]*aspect-ratio:\s*16\s*\/\s*9/s);
});
```

- [x] **Step 2: Run the focused test and confirm RED**

Run:

```bash
rtk node --test --test-name-pattern='tutorial video' web/tests/homepage.test.mjs
```

Expected: FAIL because `homepage.getTutorialVideo` is absent.

### Task 2: Restore the minimal tutorial implementation

**Files:**
- Modify: `web/homepage.js`
- Modify: `web/index.html`
- Modify: `web/homepage.css`
- Test: `web/tests/homepage.test.mjs`

- [x] **Step 1: Restore the locale-to-video contract**

Add after `downloadConfig` in `web/homepage.js`:

```js
export const tutorialVideos = Object.freeze({
  'zh-TW': Object.freeze({
    id: 'w2w5HGmXxwo',
    src: 'https://www.youtube-nocookie.com/embed/w2w5HGmXxwo',
    title: 'Sweety 中文使用教學',
  }),
  en: Object.freeze({
    id: '-qS4MGvnsa4',
    src: 'https://www.youtube-nocookie.com/embed/-qS4MGvnsa4',
    title: 'Sweety English tutorial',
  }),
});

export function getTutorialVideo(locale) {
  return tutorialVideos[locale] ?? tutorialVideos.en;
}
```

Add `tutorialVideo: { eyebrow: 'VIDEO', title: '使用教學影片' }` to the Traditional Chinese copy and `tutorialVideo: { eyebrow: 'VIDEO', title: 'Video tutorial' }` to English copy. In `initializePage()`, after generic localized attributes are applied, select `[data-tutorial-video]` and assign the resolved video's `src` and `title`.

- [x] **Step 2: Restore the semantic section before FAQ**

Insert this immediately before `.faq-section` in `web/index.html`:

```html
<section class="tutorial-video-section" aria-labelledby="tutorial-video-title">
  <div class="section-heading"><p class="eyebrow" data-copy="tutorialVideo.eyebrow">VIDEO</p><h2 id="tutorial-video-title" data-copy="tutorialVideo.title">Video tutorial</h2></div>
  <div class="tutorial-video-shell">
    <iframe class="tutorial-video-frame" data-tutorial-video src="https://www.youtube-nocookie.com/embed/-qS4MGvnsa4" title="Sweety English tutorial" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
  </div>
</section>
```

- [x] **Step 3: Restore responsive styling**

Add before the FAQ styles in `web/homepage.css`:

```css
.tutorial-video-section { padding-top: clamp(72px, 9vw, 126px); }
.tutorial-video-section .section-heading { margin-bottom: 28px; }
.tutorial-video-shell { overflow: hidden; border: 1px solid var(--line); border-radius: 24px; background: #0f172a; box-shadow: 0 24px 70px rgba(35,104,169,.16); }
.tutorial-video-frame { display: block; width: 100%; aspect-ratio: 16 / 9; border: 0; }
```

- [x] **Step 4: Recalculate the homepage asset version**

Run:

```bash
rtk python3 - <<'PY'
from hashlib import sha256
from pathlib import Path
payload = Path('web/homepage.css').read_bytes() + b'\0' + Path('web/homepage.js').read_bytes()
print(sha256(payload).hexdigest()[:12])
PY
```

Replace both `homepage.css?v=...` and `homepage.js?v=...` query values in `web/index.html` with the printed 12-character version.

- [x] **Step 5: Run the focused test and confirm GREEN**

Run:

```bash
rtk node --test --test-name-pattern='tutorial video' web/tests/homepage.test.mjs
```

Expected: PASS.

### Task 3: Verify, commit, publish, and verify live

**Files:**
- Modify: `docs/superpowers/plans/2026-07-31-homepage-tutorial-restoration.md` only for checkbox tracking

- [x] **Step 1: Run complete local verification**

Run:

```bash
rtk node --test web/tests/homepage.test.mjs
rtk git diff --check
rtk git status --short
```

Expected: every homepage test passes, `git diff --check` emits no errors, and `videos/` remains untracked and untouched.

- [x] **Step 2: Commit only the planned restoration files**

```bash
rtk git add web/homepage.js web/index.html web/homepage.css web/tests/homepage.test.mjs docs/superpowers/plans/2026-07-31-homepage-tutorial-restoration.md
rtk git commit -m "fix: restore homepage tutorial video"
```

- [x] **Step 3: Publish through the website-only helper**

Run:

```bash
rtk php app/tools/deploy_homepage.php
```

Expected: homepage assets upload successfully; the helper does not invoke desktop App build or release scripts.

- [x] **Step 4: Verify the live homepage**

Open `https://sweety.tw/?verify=<asset-version>` and verify:

- the default static fallback is the English tutorial;
- a Traditional Chinese browser locale selects `w2w5HGmXxwo`;
- exactly one iframe is active;
- the video section is immediately before FAQ;
- the iframe remains 16:9 on desktop and mobile;
- there is no horizontal overflow or browser console error;
- live CSS and JavaScript use the new cache version.

- [ ] **Step 5: Push canonical `main` and confirm repository state**

```bash
rtk git push origin main
rtk git status --short --branch
```

Expected: `main` matches `origin/main`; only the unrelated `videos/` directory remains untracked.
