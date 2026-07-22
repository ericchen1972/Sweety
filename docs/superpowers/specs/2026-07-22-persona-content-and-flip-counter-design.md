# Sweety Persona Content And Flip Counter Design

## Goal

Simplify every base persona to one name and one canonical content body, rewrite all twenty-four personas with substantially more detail, derive card previews from that content, and update both the desktop application and the server catalog together.

The public homepage also gains an explanatory introduction below `使用說明`, and its aggregate time display adopts the split-flap visual treatment of the supplied CodePen reference while continuing to show only truthful server totals.

## Persona Data Model

Each base persona has only two localized editorial fields:

- Name
- Content

The database keeps only the operational metadata required by the application in addition to those fields:

- Stable ID
- Age group
- Gender
- Localized name
- Localized content
- Image path or image value
- Sort order

The base-persona schema does not contain summary, profile, speech-style, or active-state fields. A persona exists in the catalog when its row exists; removing a persona requires removing the row rather than disabling it.

The server MySQL schema, catalog endpoint, remote payload parser, local SQLite schema, repository mapping, and bundled fallback catalog all use this same contract. The remote API exposes `id`, `ageGroup`, `gender`, `name`, `content`, `image`, and ordering where needed. It does not expose `summary`, `profile`, `style`, or a separately assembled `text` value.

Existing installations receive a forward migration that creates or adopts the canonical content columns, copies the current complete persona text into them, and stops reading the removed editorial fields. Deployment updates the server schema and data before an application build depends on the new payload contract.

## Persona Content

All twenty-four existing base personas across `20-35`, `35-50`, `50-65`, and `65+` are rewritten in Traditional Chinese and English. The Traditional Chinese version is the primary editorial source; the English version faithfully carries the same identity, history, motivation, uncertainty, and speaking behavior.

Each persona normally follows two conceptual sections, without enforcing a rigid template:

1. Character information: name, age or life stage, occupation, living situation, family and relationship background, interests, daily routine, and ordinary messaging length.
2. Personality and style: financial motivation, reaction to investment or money proposals, emotional tension, delaying behavior, suspicion patterns, characteristic questions, and natural Taiwanese conversational wording appropriate to the persona.

The beginning contains the details users are most likely to edit after cloning. Headings such as `人物資料` and `風格個性` may be used for readability but are a convention, not a validation requirement.

The cautious accounting assistant uses the user-approved Wang Xiaolan example, including:

- Three years of work as an accounting assistant.
- Living with her mother and younger sister in Banqiao, New Taipei City.
- Two previous boyfriends and a single-parent family background.
- Shopping, movies, concise messages, and a normal limit of about thirty Chinese characters.
- Approximately NT$700,000 saved for overseas study.
- Interest and anxiety when an investment is proposed.
- The characteristic suspicion line `你不是詐騙吧？我朋友被騙過，好可怕..`.
- The supplied set of Taiwanese-girl expressions and the instruction that unannotated entries are ordinary particles to use naturally.

The other twenty-three personas receive comparable detail, adjusted to their age, gender, occupation, family situation, financial motive, knowledge boundary, and individual speaking habits. Persona content changes behavior and tone only; immutable anti-scam safety policy remains outside the editable persona content.

## Persona Editor UI

Below the age and gender controls, the Traditional Chinese interface displays exactly:

> ＊如果你希望能修改基礎人設，增加其他細節，請點擊「增加到自訂人設」後，在自訂人設頁面進行修改

The English interface displays a faithful equivalent.

Base-persona cards do not read a separately authored summary. A shared preview helper:

- Reads the selected locale's canonical content.
- Normalizes section headings and line breaks only for compact card display.
- Takes the leading content segment at a consistent, tested character limit.
- Appends `...` only when the content is longer than the visible segment.

The full-text modal renders the canonical content unchanged, preserving headings, paragraphs, quoted phrases, and lists. `增加到自訂人設` copies that same content into the custom-persona editor. Custom personas continue to have a name and content body.

## Public Homepage Instructions Copy

Immediately below the `使用說明` heading and before the quick-start instructions, the Traditional Chinese homepage displays:

> Sweety 使用你閒置的電腦並操作 Line 桌面 App ，透過人物設定，讓 AI 不斷消耗詐騙的時間，請注意 - AI 不會主動與詐騙聯繫，只會被動回覆，你可以透過修改人設，讓 AI 發揮更大的拖延效果。
>
> 「你拖延對方越多的時間、代表他們要付出更多的時間與人力成本、而你挽救了更多人免於被騙。」

The first paragraph is normal explanatory copy. The quoted sentence receives stronger visual emphasis while remaining readable and responsive. The English locale contains a faithful translation rather than displaying Chinese or leaving the block absent.

## Aggregate Time Split-Flap Display

The existing aggregate metrics API remains the only time source. The homepage continues to display whole days and remaining whole hours, starts from the truthful zero fallback, retains the last valid value on request failure, and never advances a client-side clock.

The visible counter adopts the supplied CodePen's classic split-flap direction:

- Dark individual digit cards.
- Large light numerals.
- A horizontal center seam with distinct upper and lower halves.
- Subtle highlights and shadows that make each digit read as a physical flap.
- Separate labels for days and hours.

Days support a variable number of digits. Hours use two digits from `00` through `23`. When a refreshed server value changes, only changed digits animate through a short top-to-bottom flap transition. The implementation is local HTML, CSS, and JavaScript and does not load CodePen, FlipClock, jQuery, or another runtime dependency.

The screen-reader live region continues to announce the complete localized total as plain text. When `prefers-reduced-motion: reduce` is active, digits update without the flap animation. The layout remains legible at mobile widths.

## Compatibility And Deployment Order

The change is coordinated across server and desktop surfaces:

1. Add tests for the new payload and storage contract.
2. Add the server migration and transform all twenty-four persona rows.
3. Update the server endpoint to return canonical content only.
4. Update the desktop parser, SQLite migration, repository, bundled fallback data, and frontend domain contract.
5. Update the Persona Editor and card preview behavior.
6. Update the homepage copy and split-flap counter.
7. Deploy the server catalog and homepage files.
8. Rebuild the desktop application after the remote contract is live.
9. Verify both remote and local data and visually verify the homepage and Persona Editor.

The deploy sequence must avoid leaving a published endpoint that neither the current nor rebuilt desktop application can parse. During the transition, the endpoint may temporarily include both `content` and legacy fields if required for compatibility, but the final schema and final application contract contain only canonical content.

## Testing And Verification

Automated verification covers:

- The server table no longer depends on summary, profile, speech-style, or active-state fields.
- The catalog endpoint returns all twenty-four personas with non-empty localized names and content, six in each age group.
- The local payload parser accepts the new contract and rejects missing content.
- SQLite migration preserves usable content for an existing installation.
- Bundled fallback personas and remote personas expose the same contract.
- Every persona contains substantially detailed character and style behavior.
- Wang Xiaolan contains the approved family, savings, suspicion line, and conversational expressions.
- Card previews are derived from content, add `...` only when truncated, and never read a summary.
- Full-text and clone actions use the unchanged canonical content.
- The age/gender guidance copy is exact in Traditional Chinese.
- Homepage tests protect both new Traditional Chinese paragraphs.
- Split-flap rendering supports variable day digits, two-digit hours, changed-digit updates, request failure, and reduced motion.
- Existing desktop, frontend, PHP, and homepage test suites continue to pass.

Visual verification covers desktop and mobile Persona Editor layouts, readable card excerpts, full-text formatting, the homepage instruction introduction, split-flap proportions, digit transitions, and reduced-motion behavior.

Remote verification confirms the live catalog count and payload shape, live homepage copy and assets, live metrics behavior, and successful catalog synchronization into a clean local database.

## Out Of Scope

- A separate summary-writing workflow.
- Required profile/style form fields or validation.
- Persona enable/disable controls.
- A public persona administration interface.
- User-defined age groups, genders, or images beyond the existing custom-persona image flow.
- Client-side fake time accumulation.
- Importing the reference CodePen's Pomodoro controls, timer behavior, dependencies, or branding.
