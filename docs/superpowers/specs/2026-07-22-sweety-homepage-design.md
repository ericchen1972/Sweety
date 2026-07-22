# Sweety Homepage Design

## Goal

Create the public `sweety.tw` homepage as a light, editorial anti-scam landing page. The page explains active anti-scam behavior, presents a truthful aggregate of scammer time consumed by Sweety, offers Windows and macOS download cards, and teaches the current dashboard flow with real product screenshots.

The Traditional Chinese copy supplied by the user is immutable. It must be reproduced verbatim, including punctuation, capitalization such as `Line`, full-width quotation marks, and the original wording. The English page is a translation shown only when the browser is not using Traditional Chinese.

## Visual Direction

The page uses a clean white canvas, strong black typography, generous spacing, and restrained accent colors. It does not use a dark hero or text baked into images.

The hero is a two-column composition:

- Left: the supplied Traditional Chinese or English copy.
- Right: the user-supplied 16:9 blue watercolor illustration of a hunched young person.
- The main headline is heavy and oversized.
- `束手無策` is the only oversized red emphasis in the Chinese hero. The English equivalent, `powerless`, receives the same treatment.
- The watercolor edges blend into the white page without a visible image frame.

The time-cost section uses the approved 16:9 blue watercolor clock. The clock occupies the left side; pale blue watercolor extends behind the right-side copy at low enough contrast for black text. On mobile, the illustration and copy stack rather than overlap.

The remaining page stays mostly white with pale blue and pale rose section washes, thin neutral borders, rounded download cards, and no decorative gradients unrelated to the supplied artwork.

## Page Structure

### 1. Header

- Sweety logo and wordmark.
- Anchor links for active anti-scam, downloads, and instructions.
- One primary download anchor.
- Sticky on desktop with a translucent white background after scroll; compact non-sticky layout is acceptable on mobile.

### 2. Active Anti-Scam Hero

Traditional Chinese copy, verbatim:

> 面對詐騙，我們永遠只能被動的防禦嗎？
>
> 讓 AI 成為我們的武器
>
> 相信很多人都有這種疑問，我們的政府除了宣導、宣導、再宣導外，
> 對於跨境詐騙，可以說是
>
> 束手無策
>
> 現在，用戶只要在閒置的電腦上運作 Sweety，
> 就可以進行「主動反詐」

The hero does not add an eyebrow, slogan, or rewritten lead-in.

### 3. Time Is the Cost

Traditional Chinese copy, verbatim:

> 詐騙最大的成本～時間
>
> 上帝是公平的、詐騙同樣只有24小時
>
> 您不用「花費任何時間」在詐騙身上，您只需設定好 Line 對象，睡覺前開啟 Sweety 即可，唯一要付出的微末成本，電腦及螢幕不要關，不要進入休眠，不要進入螢幕保護。
>
> 當您起床後，相信對方與 AI 之間的對話，會給您帶來一整天的好心情～

### 4. Aggregate Time Counter

Traditional Chinese copy, verbatim:

> 目前 Sweety 已經消耗了詐騙總計

The counter shows only whole days and remaining whole hours. A true total of zero renders `0 days 0 hours`; the page never invents or animates fake elapsed time.

The visual treatment may use a flip/odometer transition inspired by the linked CodePen, implemented locally without a runtime dependency on CodePen. Animation occurs only when the API value changes and respects `prefers-reduced-motion`.

### 5. Downloads

Traditional Chinese heading, verbatim:

> 下載 Sweety

Two equal cards:

- Windows system icon, platform name, and download action.
- macOS system icon, platform name, and download action.

Download URLs are configured in one small page configuration object. A card must not link to a missing file. Until a real artifact URL exists, its action is visibly unavailable and localized as coming soon. The current workspace contains a macOS `.app` build but no distributable `.dmg`/`.zip` and no Windows installer, so the initial implementation must not publish dead download links.

### 6. Instructions

Traditional Chinese heading, verbatim:

> 使用說明

Real screenshots from the current Sweety dashboard accompany the relevant instruction groups. Screenshots use the existing product UI; they are not invented mockups. The implementation will capture and crop only the areas needed to explain each flow.

#### 快速上手

1. 在騙子列表內建立對象，輸入對方的 Line 名稱
2. 選擇要使用的人設（建議選擇與您自身類似的人設）
3. 勾選要回覆的對象
4. 在面板上案開始
5. 如果你想親自接手交談，可隨時按停止
6. 睡覺去

#### 進階設定

> 如果您覺得預設人物不夠精準，您可以自訂人設，或者用基礎人設做延伸

1. 選擇基礎人設
2. 點擊「增加到自訂人設」
3. 進入自訂人設修改
4. 在監控對象上套用自訂人設

#### 注意事項

> Mac OS 系統下，需賦予 Sweety 三種權限，分別是
>
> 輔助使用
>
> 螢幕與系統錄音
>
> 自動化

The visible text preserves `在面板上案開始` exactly as supplied even though it may be a typo. It must not be silently corrected.

## Locale Behavior

The page includes complete `zh-TW` and `en` dictionaries. It chooses Traditional Chinese when the first matching browser language is one of:

- `zh-TW`
- `zh-Hant` or a `zh-Hant-*` variant
- `zh-HK`
- `zh-MO`

Every other language uses English. There is no machine translation at runtime. The selected language sets the document `lang`, title, navigation, image alt text, download state, counter units, and all page copy.

The Chinese dictionary is copied from the approved source text and protected by an automated exact-string test. English is a faithful translation, not a rewrite of the Chinese marketing position.

## Aggregate Metrics Architecture

### Desktop App

The existing dashboard metric `total_duration_ms` is calculated from each target's first and last successful reply timestamps. The app reports only the cumulative whole-hour total; message text, target names, persona choices, IP addresses, and conversation records are never uploaded.

On first run after the feature is installed, the local SQLite database creates a random installation identifier. The identifier is persisted locally and sent only to deduplicate cumulative reports. The server stores a one-way hash rather than the raw identifier.

Reporting runs in a daemon thread after startup and after a successful conversation update. Network failures are silent and never prevent monitoring, AI replies, or app startup.

### Server

`sweety-metrics.php` supports two operations:

- Public `GET`: returns `{ "totalDays": 0, "totalHours": 0 }`, where `totalHours` is the remainder after whole days.
- Authenticated desktop `POST`: accepts the installation identifier and cumulative whole hours, validates the desktop headers already used by the catalog endpoint, and updates that installation's maximum reported value.

The server table stores the hashed installation identifier, cumulative whole hours, and update timestamp. Repeated reports replace the previous value rather than adding it, preventing double counting. The public total is the sum of the latest cumulative values for all installations.

The endpoint rejects negative, non-integer, malformed, or implausibly large values. It returns no per-installation data. Responses are JSON with `no-store` on POST and a short public cache window on GET.

### Homepage

The page requests the public aggregate on load and periodically refreshes it. Before a successful response, it renders the truthful fallback `0 days 0 hours`. Invalid responses and network failures keep the last known valid value; they do not start a client-side clock.

## Files and Assets

- `web/index.html`: semantic homepage markup, styles, locale dictionaries, counter rendering, and responsive behavior.
- `web/sweety-metrics.php`: public aggregate and authenticated report endpoint.
- `web/images/home/hero-helpless.png`: the user-supplied first illustration.
- `web/images/home/time-clock-blue.png`: the approved blue 16:9 clock illustration.
- `web/images/home/`: captured dashboard instruction screenshots.
- `app/desktop/src/sweety_app/metrics_reporter.py`: anonymous cumulative reporter.
- `app/desktop/src/sweety_app/database.py`: local installation identifier persistence.
- `app/desktop/src/sweety_app/config.py`: remote metrics URL.
- `app/desktop/src/sweety_app/__main__.py`: non-blocking reporter startup.
- Server schema migration under `app/tools/` for the aggregate table.

## Responsive and Accessible Behavior

- Desktop hero and time-cost sections use two columns.
- Tablet narrows both columns without overlapping text and art.
- Mobile stacks copy and artwork, keeps headings readable, and uses full-width download cards.
- Navigation anchors have visible keyboard focus.
- Decorative watercolor has meaningful alt text only when it communicates the section idea; purely decorative layers use empty alt text.
- Counter updates use an `aria-live="polite"` text equivalent.
- Platform actions meet a 44-pixel touch target.
- Motion is disabled for users requesting reduced motion.

## Verification

- Exact-string tests protect every Traditional Chinese block from rewriting.
- Locale tests cover `zh-TW`, `zh-Hant`, `zh-HK`, `zh-MO`, `zh-CN`, and English.
- Counter tests cover zero, 23 hours, 24 hours, multi-day totals, invalid JSON, and request failure.
- PHP endpoint tests cover empty totals, cumulative replacement, multiple installations, invalid payloads, and unauthorized POST requests.
- Desktop tests cover stable installation identity, whole-hour truncation, payload privacy, non-blocking startup, successful reporting, and network failure.
- Visual verification covers desktop and mobile widths, both languages, black-text readability over the clock wash, download disabled states, and instruction screenshot cropping.
- The complete desktop and frontend test suites run before rebuilding the macOS app.

## Out of Scope

- User accounts, leaderboards, public per-user metrics, or conversation uploads.
- Client-side fake counting between server refreshes.
- Publishing a Windows installer or macOS disk image that does not exist.
- Rewriting or proofreading the supplied Traditional Chinese copy.
