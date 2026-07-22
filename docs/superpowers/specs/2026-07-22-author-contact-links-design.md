# Author Contact Links Design

## Goal

Keep the author contact information consistent between the public homepage and the App-loaded About page, with safe new-tab links for LINE and Threads.

## Surfaces

The same contact changes apply to both author cards:

- `web/index.html`, with localized homepage copy supplied by `web/homepage.js`
- `web/about_sweety.html`, which is also fetched and displayed inside the desktop App

## LINE Contact

The existing `LINE: bobo2010` contact stays on the same row as Email when space permits. The two contact items align on their text baseline; on narrow screens they may wrap naturally.

`bobo2010` becomes a link to `https://line.me/ti/p/ekr53MoZc6`. It opens a new tab and uses `rel="noopener noreferrer"`.

## Threads Follow-up

Immediately below `任何程式開發、電商都歡迎與作者接洽。`, add:

`如想得到更多AI開發應用訊息，請追蹤我的 Threads`

`Threads` links to `https://www.threads.com/@eric_slimweb`, opens a new tab, and uses `rel="noopener noreferrer"`.

The homepage English locale receives an equivalent sentence through the existing localization object so switching locale does not leave Traditional Chinese text in the English view.

## Presentation

Reuse the current card, contact, and invitation styles. Add only focused rules for contact baseline alignment and the Threads follow-up spacing/link color. Do not redesign the card.

## Tests

- Both HTML author cards contain the safe new-tab LINE and Threads links.
- The About page contains the approved Traditional Chinese Threads sentence.
- Homepage localization contains both Traditional Chinese and English follow-up copy.
- Existing author-card, homepage, About sanitizer, frontend, and desktop tests continue to pass.

## Out Of Scope

- Changing the author portrait, email address, project list, or card structure.
- Publishing the modified pages unless separately requested.
