# Homepage Language Support FAQ Design

## Goal

Add a sixth homepage FAQ that explains which interface languages Sweety supports and clarifies that AI replies primarily follow the other person's language. The FAQ must remain complete and equivalent in Traditional Chinese, English, and Japanese.

## Localized Copy

Traditional Chinese:

- Question: `Sweety 支援哪些語系？`
- Answer: `Sweety 介面支援繁中、英文及日文，但是 AI 的回覆將以對方使用的語言為主。`

English:

- Question: `Which languages does Sweety support?`
- Answer: `The Sweety interface supports Traditional Chinese, English, and Japanese. AI replies will primarily use the language spoken by the other person.`

Japanese:

- Question: `Sweetyはどの言語に対応していますか？`
- Answer: `Sweetyのインターフェースは繁体字中国語、英語、日本語に対応しています。ただし、AIは主に相手が使用している言語で返信します。`

## Architecture and Components

Keep the existing homepage architecture unchanged:

- Append the localized question and answer as item 6 in each `copy.<locale>.faq.items` array in `web/homepage.js`.
- Append one sixth static `<details class="faq-item">` disclosure to the FAQ list in `web/index.html`. Its English fallback content uses `data-copy="faq.items.5.question"` and `data-copy="faq.items.5.answer"` so the existing text-only localization path updates it.
- Append the Traditional Chinese sixth question and answer to the static FAQPage JSON-LD fallback in `web/index.html`.
- Continue generating runtime FAQPage JSON-LD from the selected locale's `copy.<locale>.faq.items` through `buildFaqStructuredData(locale)`. No new renderer or metadata path is needed.

## Data Flow and Safety

The browser resolves one of `zh-TW`, `en`, or `ja`, applies the matching strings to the existing `data-copy` nodes with `textContent`, then replaces the FAQPage node with structured data built from that same locale object. This keeps the visible FAQ and search-engine data aligned without introducing localized HTML or `innerHTML`.

If locale resolution ever falls back, the existing English fallback behavior remains unchanged. The sixth entry contains only plain text and needs no special emphasis markup or error handling.

## Testing

Follow test-driven development:

1. Update `web/tests/homepage.test.mjs` first to require six FAQ entries for all three locales, the exact new translations, the sixth HTML disclosure and hooks, and six generated FAQPage entries.
2. Run the focused homepage test and confirm it fails because the sixth FAQ is absent.
3. Make the minimal changes to `web/homepage.js` and `web/index.html`.
4. Re-run the homepage test and the relevant homepage/deployment verification suite.

## Publishing and Verification

Publish only the website with `app/tools/deploy_homepage.php`; do not build, sign, or package the desktop App. After publishing, perform a cache-busted live fetch and verify:

- the homepage contains six `<details>` and six `<summary>` elements;
- the sixth FAQ hooks and English fallback text are present;
- the deployed JavaScript contains all three localized versions;
- runtime FAQPage structured data contains six entries for each supported locale;
- the homepage CSS and JavaScript cache versions remain synchronized.

## Scope Boundaries

- Do not change Sweety's application language-selection or AI reply-language behavior.
- Do not rewrite the existing five FAQ entries.
- Do not add styling or alter the FAQ layout.
- Do not rebuild or release the desktop App.
- Preserve the untracked `videos/` directory and unrelated worktree content.
