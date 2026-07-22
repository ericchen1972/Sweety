# Sweety 1.0.1 Open-Source Release Design

## Goal

Publish Sweety 1.0.1 as a safe public source repository, expand the public homepage and in-app About page with open-source, FAQ, and author information, and keep the live application experience consistent with the checked-in source.

## Release scope

- Publish source code and documentation to `https://github.com/ericchen1972/Sweety` on `main`.
- Do not upload the built macOS application, virtual environments, dependency folders, build output, database files, credentials, or deployment configuration.
- Use the MIT License.
- Set product and package versions to `1.0.1`. Keep API/state schema version `1` because it describes the persisted data contract rather than the product release.

## Public homepage

The existing static homepage remains framework-free and bilingual.

The Important Notes block gains this additional warning in Chinese and an equivalent English translation:

> Line 桌面 App 視窗位置請勿超過螢幕左側或右側邊緣，否則將造成 Sweety 辨識失敗。

Immediately below Important Notes, add a Frequently Asked Questions section using native `<details>` and `<summary>` elements. Each question is independent, so opening one answer does not close another. The four supplied questions and answers remain faithful to the approved Chinese copy and receive equivalent English copy for the homepage's English mode.

The author card appears after the FAQ. It uses the existing `web/images/eric.png` asset as a circular portrait and contains:

- Eric / 網站 / AI 工程師
- 20 年開發經驗
- SlimWeb, KingJoo, and Sweety project links, each opening in a new tab with `noopener noreferrer`
- Email `eric.chen1972@gmail.com`
- LINE ID `bobo2010`
- The invitation to contact Eric for software development or ecommerce work

The card follows the homepage's existing light watercolor visual system, uses semantic headings and links, and collapses to a single-column layout on mobile.

## About Sweety

Add an Open-Source Project section containing the approved explanation and a new-tab link to the GitHub repository. Add the same author information at the end of the About page.

The desktop app fetches `https://sweety.tw/about_sweety.html` and sanitizes it before rendering. The sanitizer therefore adds narrowly scoped support for `<img>` with HTTPS `src`, plain `alt`, numeric `width` and `height`, and safe `loading` values. Existing blocking of scripts, styles, forms, inline handlers, unsafe URLs, and active embeds remains unchanged. The About document uses the absolute HTTPS author-image URL so it renders correctly from both `sweety.tw` and the local dashboard origin.

Homepage FAQ markup is not added to the in-app About view because the sanitizer intentionally does not allow interactive disclosure elements. The FAQ belongs only to the homepage as requested.

## Open-source security boundary

Create a root `.gitignore` that excludes:

- `config.json` and `web/sftp-config.json`
- local runtime-environment and database files
- `app/desktop/.venv`, `app/desktop/build`, and `app/desktop/dist`
- `app/frontend/node_modules` and `app/frontend/dist`
- Python, Node, editor, OS, test-cache, and temporary artifacts

Remove the embedded AGNES credential from source. Runtime code reads `SWEETY_AGNES_KEY` from the environment. The macOS build specification may copy that value into the locally built app's environment only when the builder explicitly supplies it; the value must never be written to a tracked file or build log. Add safe example configuration that contains placeholders only.

Before the initial public commit, scan every staged file for tokens, passwords, private keys, FTP credentials, runtime secrets, generated binaries, and local databases. Only the intended source, tests, public assets, documentation, and safe examples are staged.

## README and repository metadata

Create a root README in Traditional Chinese with concise English-facing labels where helpful. It covers:

- Sweety's proactive anti-scam purpose and safety boundary
- Supported status and macOS requirements
- Required Accessibility, Screen Recording, and Automation permissions
- Setup, environment variables, frontend development, desktop build, and test commands
- How personas and remote catalog/About content work
- Project structure
- Privacy and responsible-use limitations
- Version 1.0.1, MIT License, project links, and author contact information

Include `LICENSE` with the MIT text and Eric Chen as the copyright holder.

## Versioning

Update all user-facing and package release version surfaces together:

- desktop `APP_VERSION`
- Python package version and lock metadata
- frontend package and lock root version
- macOS `CFBundleShortVersionString` and build number
- visible panel version

The panel already derives its visible version from `APP_VERSION`, so it requires no duplicate literal.

## Testing

Use test-driven changes:

1. Extend homepage contract tests to require the new warning, four independent FAQ disclosures, localized copy, safe external links, circular author image hook, and responsive style hooks.
2. Extend About sanitizer tests to prove safe HTTPS author images survive and unsafe image sources/attributes are removed.
3. Add version-contract tests so the release surfaces cannot drift.
4. Run the complete frontend, homepage, PHP, and desktop Python suites.
5. Build the production frontend and macOS app.
6. Inspect the homepage at desktop and mobile widths, then inspect the in-app About page using the running local App.

## Deployment and publication

Extend the existing homepage deployment allowlist to include `about_sweety.html` and `images/eric.png`. Deploy the tested homepage and About assets to `sweety.tw`, then verify the live homepage text, GitHub links, author image, and fetched in-app About content.

Initialize the empty public repository on `main`, commit only the reviewed source tree, and push to `origin`. Because the remote repository has no default branch yet, the first source commit establishes `main` directly; no pull request is created for this bootstrap release.
