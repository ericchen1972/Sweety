# Homepage Tutorial Restoration Design

## Goal

Restore the previously deployed locale-dependent tutorial video to the current
homepage without reverting or replacing the newer homepage instructions.

## Source of Truth

The original implementation is preserved in Git stash commit `025b147`. It was
created while work was occurring on `agent/agnes-structured-replies`. Restore
only the tutorial-related portions from that snapshot, adapted to the current
`main` files.

## Behavior

- Traditional Chinese browser locales use YouTube video `w2w5HGmXxwo`.
- All other supported locales use YouTube video `-qS4MGvnsa4`.
- The page contains exactly one tutorial iframe, using
  `youtube-nocookie.com`.
- The iframe is selected at runtime through the homepage's existing locale
  resolution and has a localized accessible title.
- The responsive 16:9 tutorial section appears immediately before the FAQ.

## Files and Boundaries

- `web/homepage.js`: restore the locale-to-video mapping, lookup helper,
  localized section labels, and runtime iframe update.
- `web/index.html`: restore the static English fallback markup immediately
  before the FAQ and refresh the shared CSS/JS cache version.
- `web/homepage.css`: restore only the tutorial section's responsive styling.
- `web/tests/homepage.test.mjs`: restore the regression contract before the
  production changes.

Do not apply the complete stash, alter download configuration, replace the
current seven-item instruction guide, modify desktop build artifacts, or touch
the untracked `videos/` directory.

## Verification and Publication

First run the new regression test and confirm that it fails because the tutorial
contract is absent. After restoring the production code, run the complete
homepage test suite and `git diff --check`. Publish with the website-only
homepage deployment helper, then verify the live localized iframe, its position
before FAQ, the versioned CSS/JS assets, and the absence of horizontal overflow
or browser console errors.
