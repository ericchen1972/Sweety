# Japanese Homepage Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete Japanese browser-locale presentation to the existing Sweety homepage, including the Japanese tutorial video, runtime metadata, localized FAQ JSON-LD, deployment, and live verification.

**Architecture:** Keep the single-page `web/index.html` and extend the existing `resolveLocale` / `copy` / `tutorialVideos` contracts in `web/homepage.js` with a `ja` locale. Add pure metadata and FAQ structured-data builders so localization is testable without a browser, then use the existing runtime initialization to update the document. Preserve English static HTML fallback and the website-only deployment boundary.

**Tech Stack:** Browser ES modules, semantic HTML, Node.js built-in test runner, SHA-256 cache versioning, PHP FTP deployment, Playwright/browser verification.

---

## File map

- Modify `web/homepage.js`: Japanese locale resolution, Japanese copy, Japanese tutorial video, locale formatting, pure metadata/FAQ builders, and DOM application.
- Modify `web/index.html`: add `ja_JP` Open Graph alternate and a stable identifier for the homepage JSON-LD block; update CSS/JS cache version only after tests pass.
- Modify `web/tests/homepage.test.mjs`: encode Japanese locale, copy, video, metadata, JSON-LD, regression, and cache contracts.
- Do not modify `web/homepage.css`: the existing layout and typography remain unchanged; its bytes still participate in the shared cache hash.
- Do not modify or invoke desktop App build or release files.

### Task 1: Encode the Japanese locale and tutorial contracts

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Extend the locale test with Japanese inputs**

Add assertions that `ja`, `ja-JP`, and `ja-JP-u-ca-japanese` resolve to `ja`; remove `ja-JP` from the English-fallback input set:

```js
for (const locale of ['ja', 'ja-JP', 'ja-JP-u-ca-japanese']) {
  assert.equal(resolveLocale(locale), 'ja');
}
for (const locale of ['zh', 'zh-CN', 'en', 'en-US', 'fr-FR', undefined]) {
  assert.equal(resolveLocale(locale), 'en');
}
```

- [ ] **Step 2: Add the Japanese tutorial expectation**

```js
assert.deepEqual(homepage.getTutorialVideo('ja'), {
  id: 'CLLEgl9tRWA',
  src: 'https://www.youtube-nocookie.com/embed/CLLEgl9tRWA',
  title: 'Sweety 日本語使い方ガイド',
});
```

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```bash
node --test --test-name-pattern='locale|tutorial video' web/tests/homepage.test.mjs
```

Expected: failures showing Japanese resolves to `en` and the Japanese tutorial falls back to the English video.

- [ ] **Step 4: Add minimal locale and video implementation**

Update `resolveLocale` after the Traditional Chinese check:

```js
if (normalized === 'ja' || normalized.startsWith('ja-')) return 'ja';
return 'en';
```

Add this frozen `tutorialVideos.ja` value:

```js
ja: Object.freeze({
  id: 'CLLEgl9tRWA',
  src: 'https://www.youtube-nocookie.com/embed/CLLEgl9tRWA',
  title: 'Sweety 日本語使い方ガイド',
}),
```

- [ ] **Step 5: Run the focused tests and confirm GREEN**

Run the same focused command. Expected: the locale and tutorial tests pass.

### Task 2: Add complete Japanese homepage copy and formatting

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `web/homepage.js`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Add failing structural and presentation assertions**

Assert that `copy.ja` exists, has the same top-level keys as `copy.en`, has the same seven guide keys, and has five FAQ entries. Add exact checks for the most visible and operational strings:

```js
assert.deepEqual(Object.keys(homepage.copy.ja), Object.keys(homepage.copy.en));
assert.deepEqual(
  Object.keys(homepage.copy.ja.instructions.guide),
  Object.keys(homepage.copy.en.instructions.guide),
);
assert.equal(homepage.copy.ja.faq.items.length, 5);
assert.equal(homepage.copy.ja.hero.title, '詐欺に対して、私たちは受け身で防ぐことしかできないのでしょうか？');
assert.equal(homepage.copy.ja.instructions.title, '使い方');
assert.equal(homepage.copy.ja.notice.title, '注意事項');
assert.equal(homepage.copy.ja.tutorialVideo.title, '使い方動画');
assert.equal(homepage.formatDownloadCount('ja', 42), 'ダウンロード数：42回');
assert.equal(homepage.formatCounterText('ja', 12, 7), 'Sweetyが詐欺業者に使わせた時間：12日7時間');
assert.deepEqual(homepage.getLocalePresentation(['ja-JP'], 'en-US'), {
  locale: 'ja',
  lang: 'ja',
  title: 'Sweety｜攻める詐欺対策',
});
assert.deepEqual(homepage.getDownloadDecision('macos', 'ja'), {
  enabled: true,
  href: expectedMacDownload,
  label: 'macOS版をダウンロード',
});
```

- [ ] **Step 2: Run the focused copy tests and confirm RED**

Run:

```bash
node --test --test-name-pattern='Japanese|locale presentation|download' web/tests/homepage.test.mjs
```

Expected: `copy.ja` is undefined and Japanese formatting falls back to English.

- [ ] **Step 3: Add the complete `copy.ja` object**

Mirror the existing English object exactly and use these Japanese values:

```js
ja: {
  meta: {
    title: 'Sweety｜攻める詐欺対策',
    description: 'Sweetyは、AIが不審な相手に返信して詐欺業者の時間を消費させる、完全無料・オープンソースの詐欺対策アプリです。',
    socialTitle: 'Sweety｜攻める詐欺対策',
    socialDescription: 'AIを味方につけて、詐欺業者の時間を積極的に奪います。',
    ogLocale: 'ja_JP',
  },
  skipLink: 'メインコンテンツへ移動',
  brandLabel: 'Sweety ホーム',
  nav: { label: 'メインナビゲーション', antiScam: '攻める詐欺対策', download: 'ダウンロード', instructions: '使い方' },
  hero: {
    title: '詐欺に対して、私たちは受け身で防ぐことしかできないのでしょうか？',
    subtitle: 'AIを私たちの武器に',
    body: '詐欺を不快に感じていませんか？\n削除やブロック、無視するだけでなく、今は別の選択肢があります。\nSweetyを',
    emphasis: '詐欺撃退ツール',
    closing: '使っていないパソコンでSweetyを動かすだけで、詐欺業者の時間を奪えます。',
    artAlt: 'パソコンの前で途方に暮れる人物を描いた青い水彩画',
  },
  time: {
    title: '詐欺業者にとって最大のコストは「時間」',
    subtitle: '誰にとっても1日は24時間。詐欺業者も例外ではありません。',
    body: 'あなた自身が詐欺業者のために時間を使う必要はありません。LINEの対象を設定し、寝る前にSweetyを起動するだけです。必要なのは、パソコンとディスプレイを付けたままにし、スリープやスクリーンセーバーを無効にすることだけです。',
    close: '朝になれば、相手とAIのやり取りが一日を楽しい気分にしてくれるかもしれません。',
    artAlt: '青い水彩画の時計',
  },
  counter: { intro: 'Sweetyが詐欺業者に使わせた時間', days: '日', hours: '時間' },
  download: { title: 'Sweetyをダウンロード', windows: 'Windows', macOS: 'macOS', soon: '近日公開', actions: { windows: 'Windows版をダウンロード', macos: 'macOS版をダウンロード' } },
  instructions: {
    title: '使い方',
    intro: 'Sweetyは、使っていないパソコンからLINEデスクトップアプリを操作し、設定した人物像に基づいてAIが詐欺業者の時間を消費させます。AIから相手へ連絡することはなく、受信したメッセージにだけ返信します。人物設定を調整すると、より効果的に会話を長引かせることができます。',
    quote: '「相手の時間を長く奪うほど、詐欺業者はより多くの時間と人件費を費やすことになり、その分だけ被害に遭う人を減らせます。」',
    openSourceNote: '※ Sweetyは完全無料のオープンソースソフトウェアです。配布済み実行ファイルの安全性が気になる場合は、Gitからご自身でビルドできます。',
    guide: {
      controlPanel: { title: 'コントロールパネル', body: 'Sweetyを起動する前に、LINEのメインウィンドウを開いてください。「管理画面を開く」から返信対象を編集し、「開始」を押すと、SweetyがLINEの連絡先画面を確認します。監視対象からメッセージが届くと、そのトークを開いてAIが返信します。', imageAlt: '開始、管理画面を開く、アプリを終了するボタンがあるSweetyのコントロールパネル' },
      dashboard: { title: 'ダッシュボード', body: '対象人数、消費した合計時間、往復回数、終了件数を確認できます。下部には最近の対象と往復回数、右上には現在の動作状態と選択中の対象数が表示されます。', imageAlt: '集計、最近の対象、動作状態を表示するSweetyのダッシュボード' },
      basicSettings: { title: '基本設定', body: 'AI設定でSweety標準またはOpenAIを選択します。OpenAIを使う場合はAPI Keyとモデルを指定してください。会話設定では、新着メッセージの確認間隔と、トークを開いてから返信するまでの待ち時間を調整できます。設定後は「保存」を押します。', imageAlt: 'AI、確認間隔、返信待ち時間を設定するSweetyの基本設定画面' },
      targetList: { title: '詐欺業者リスト', body: '監視対象を追加・管理します。「返信」にチェックを入れた対象だけをSweetyが監視して返信します。対象ごとに編集、終了、会話のエクスポートもできます。LINE名は連絡先画面に表示される完全な名前を入力してください。', imageAlt: '返信チェック、対象、人物設定、操作ボタンを表示するSweetyの詐欺業者リスト' },
      basePersonas: { title: '基本人物設定', body: '「基本人物設定」タブでは、年齢と性別で標準の人物設定を絞り込めます。カードの概要を読み、「全文を表示」で詳細を確認します。内容を変更したい場合は、基本人物設定をカスタム人物設定へ追加してください。', imageAlt: '年齢と性別の絞り込み、人物設定カードを表示するSweetyの基本人物設定画面' },
      personaDetails: { title: '人物設定の詳細', body: '「全文を表示」を押すと、人物プロフィール、話し方、性格、よく使う表現を確認できます。内容が適していれば「カスタム人物設定に追加」を押し、必要に応じて調整します。', imageAlt: '人物プロフィールとカスタム人物設定への追加ボタンを表示する詳細画面' },
      customPersonas: { title: 'カスタム人物設定', body: '独自の人物設定を作成・管理します。空の状態から作ることも、基本人物設定をコピーして編集することもできます。完成した人物設定は、詐欺業者リストの監視対象に適用できます。', imageAlt: '人物設定の作成ボタンがあるSweetyのカスタム人物設定画面' },
    },
    triggerNotice: 'Sweetyから相手へ先にメッセージを送ることはありません。監視対象からメッセージが届いた場合だけ返信します。つまり、Sweetyを動作させるには、画面内に監視対象からの未読メッセージが必要です。',
  },
  notice: {
    title: '注意事項',
    intro: 'macOSでは、Sweetyに次の3つの権限を許可してください。',
    permissions: ['アクセシビリティ', '画面収録とシステムオーディオ録音', 'オートメーション'],
    windowPosition: 'LINEデスクトップアプリのウィンドウを画面の左右端からはみ出させないでください。はみ出すとSweetyが正しく認識できません。',
  },
  tutorialVideo: { eyebrow: 'VIDEO', title: '使い方動画' },
  faq: {
    title: 'よくある質問',
    items: [
      { question: '相手がAIとの会話だと疑い始めた場合はどうすればよいですか？', answer: 'いったん停止し、ご自身で会話を引き継いでください。状況が落ち着いてから再開できます。' },
      { question: '複数の対象を同時に設定できますか？', answer: 'はい。ただし、LINEのメインウィンドウに表示できる連絡先の範囲を超えないようにしてください。' },
      { question: '詐欺業者ではない相手への返信にSweetyを使えますか？', answer: '使用できますが、おすすめしません。' },
      { question: 'なぜ「Sweety」という名前なのですか？', answer: '詐欺被害は苦いものです。そんな時こそ、ひと粒のキャンディーを。' },
      { question: '開始後に「macOSの権限が必要です」と表示されるのはなぜですか？', answerPrefix: 'アップデート後、macOSがSweetyを新しいアプリとして認識する場合があります。システム設定の', answerEmphasis: '「アクセシビリティ」と「画面収録とシステムオーディオ録音」からSweetyを一度削除し、再度追加してください。' },
    ],
  },
  author: {
    eyebrow: '開発者', title: 'Eric / Web・AIエンジニア', experience: '開発経験20年', projectsTitle: '現在の開発プロジェクト',
    projects: { slimweb: 'AIファーストECシステム SlimWeb', kingjoo: 'AIプロアクティブマーケティングツール KingJoo', sweety: '攻める詐欺対策アプリ Sweety' },
    invitation: 'ソフトウェア開発やECに関するご相談を歓迎します。',
    threads: { prefix: 'AI開発・活用に関する最新情報は、こちらの', label: 'Threads' },
  },
  footer: 'Sweety',
},
```

- [ ] **Step 4: Generalize formatting without changing Chinese or English**

Implement explicit Japanese branches:

```js
export function formatDownloadCount(locale, total) {
  const value = Number.isSafeInteger(total) && total >= 0 ? String(total) : '—';
  if (locale === 'zh-TW') return `已下載 ${value} 次`;
  if (locale === 'ja') return `ダウンロード数：${value}回`;
  return `Downloaded ${value} times`;
}

export function formatCounterText(locale, days, hours) {
  const strings = copy[locale]?.counter ?? copy.en.counter;
  if (locale === 'zh-TW') return `${strings.intro} ${days} ${strings.days} ${hours} ${strings.hours}`;
  if (locale === 'ja') return `${strings.intro}：${days}${strings.days}${hours}${strings.hours}`;
  return `${strings.intro} ${days} ${strings.days} ${hours} ${strings.hours}`;
}
```

- [ ] **Step 5: Run the full homepage suite**

Run:

```bash
node --test web/tests/homepage.test.mjs
```

Expected: all tests through Task 2 pass.

### Task 3: Localize metadata and FAQ structured data

**Files:**
- Modify: `web/tests/homepage.test.mjs`
- Modify: `web/homepage.js`
- Modify: `web/index.html`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Add failing pure-function tests**

Add exact tests for these exports:

```js
assert.deepEqual(homepage.getMetadata('ja'), {
  title: 'Sweety｜攻める詐欺対策',
  description: homepage.copy.ja.meta.description,
  socialTitle: 'Sweety｜攻める詐欺対策',
  socialDescription: homepage.copy.ja.meta.socialDescription,
  ogLocale: 'ja_JP',
});

const faq = homepage.buildFaqStructuredData('ja');
assert.equal(faq['@type'], 'FAQPage');
assert.equal(faq.mainEntity.length, 5);
assert.equal(faq.mainEntity[0].name, homepage.copy.ja.faq.items[0].question);
assert.equal(
  faq.mainEntity[4].acceptedAnswer.text,
  homepage.copy.ja.faq.items[4].answerPrefix + homepage.copy.ja.faq.items[4].answerEmphasis,
);
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```bash
node --test --test-name-pattern='metadata|structured data' web/tests/homepage.test.mjs
```

Expected: `getMetadata` and `buildFaqStructuredData` are not functions.

- [ ] **Step 3: Give every locale one metadata contract**

Add `description`, `socialTitle`, `socialDescription`, and `ogLocale` to the existing `meta` objects for `zh-TW` and `en`. Preserve the current static values:

```js
'zh-TW': {
  meta: {
    title: 'Sweety｜主動反詐',
    description: 'Sweety 是完全開源的主動式反詐騙 App，透過 AI 回覆可疑對象、消耗詐騙者的時間，讓每個人都能參與反詐。',
    socialTitle: 'Sweety 主動反詐',
    socialDescription: '讓 AI 成為我們的武器，主動消耗詐騙者的時間。',
    ogLocale: 'zh_TW',
  },
},
en: {
  meta: {
    title: 'Sweety | Proactive anti-scam',
    description: 'Sweety is a free and open-source anti-scam app that uses AI to reply to suspicious contacts and consume scammers’ time.',
    socialTitle: 'Sweety | Proactive anti-scam',
    socialDescription: 'Use AI to actively consume scammers’ time.',
    ogLocale: 'en_US',
  },
},
```

- [ ] **Step 4: Implement pure builders**

```js
export function getMetadata(locale) {
  return copy[locale]?.meta ?? copy.en.meta;
}

export function buildFaqStructuredData(locale) {
  const items = (copy[locale] ?? copy.en).faq.items;
  return {
    '@type': 'FAQPage',
    '@id': 'https://sweety.tw/#faq',
    mainEntity: items.map((item) => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer ?? `${item.answerPrefix}${item.answerEmphasis}`,
      },
    })),
  };
}
```

- [ ] **Step 5: Add safe runtime DOM application**

Implement `applyMetadata(document, locale)` so it updates the title, description, OG title/description/locale, Twitter title/description, and the FAQPage node within the JSON-LD graph. Query each optional node and skip it when missing. Call it from `initializeHomepage()` after locale resolution and before asynchronous metric/download requests.

Use a stable HTML hook:

```html
<meta property="og:locale:alternate" content="ja_JP">
<script id="homepage-structured-data" type="application/ld+json">
```

Within `applyMetadata`, parse and replace only the FAQPage node while preserving WebSite, Organization, Person, and SoftwareApplication:

```js
const structuredData = document.getElementById('homepage-structured-data');
if (structuredData) {
  try {
    const payload = JSON.parse(structuredData.textContent);
    if (Array.isArray(payload?.['@graph'])) {
      payload['@graph'] = payload['@graph'].map((node) => (
        node?.['@type'] === 'FAQPage' ? buildFaqStructuredData(locale) : node
      ));
      structuredData.textContent = JSON.stringify(payload);
    }
  } catch {
    // Preserve the static JSON-LD when malformed instead of breaking the page.
  }
}
```

- [ ] **Step 6: Run focused and full tests**

Run:

```bash
node --test --test-name-pattern='metadata|structured data' web/tests/homepage.test.mjs
node --test web/tests/homepage.test.mjs
```

Expected: both commands pass.

### Task 4: Refresh the asset version and complete local verification

**Files:**
- Modify: `web/index.html`
- Test: `web/tests/homepage.test.mjs`

- [ ] **Step 1: Compute the exact shared cache version**

Run:

```bash
node -e "const fs=require('node:fs');const crypto=require('node:crypto');const css=fs.readFileSync('web/homepage.css');const js=fs.readFileSync('web/homepage.js');process.stdout.write(crypto.createHash('sha256').update(css).update(Buffer.from([0])).update(js).digest('hex').slice(0,12)+'\n')"
```

Expected: one 12-character lowercase hexadecimal value.

- [ ] **Step 2: Put that exact value in both asset URLs**

Update only these two attributes with the computed value:

```html
<link rel="stylesheet" href="homepage.css?v=<computed 12-character value>">
<script type="module" src="homepage.js?v=<computed 12-character value>"></script>
```

- [ ] **Step 3: Run all local homepage checks**

Run:

```bash
node --test web/tests/homepage.test.mjs
node --test web/tests/about.test.mjs
php web/tests/sweety_metrics_test.php
php web/tests/sweety_downloads_test.php
git diff --check
```

Expected: all tests pass, PHP scripts report success, and `git diff --check` prints nothing.

- [ ] **Step 4: Confirm the deployment boundary and working tree scope**

Run:

```bash
rg -n 'build_app\.sh|build_dmg\.sh|deploy_macos_release|dist/Sweety\.app' app/tools/deploy_homepage.php
git status --short
```

Expected: the deployment search has no matches; only `web/homepage.js`, `web/index.html`, `web/tests/homepage.test.mjs`, the implementation plan, and pre-existing untracked `videos/` are present.

- [ ] **Step 5: Commit the implementation on main**

```bash
git add web/homepage.js web/index.html web/tests/homepage.test.mjs docs/superpowers/plans/2026-08-04-japanese-homepage-localization.md
git commit -m "feat: add Japanese homepage localization"
```

### Task 5: Deploy the website and verify Japanese live behavior

**Files:**
- Deploy with: `app/tools/deploy_homepage.php`
- Verify live: `https://sweety.tw/`

- [ ] **Step 1: Publish website files only**

Run:

```bash
rtk php app/tools/deploy_homepage.php
```

Expected: homepage files/assets are uploaded and verified; metrics schema and download counter checks pass. No desktop App build or signing output appears.

- [ ] **Step 2: Verify deployed asset bytes and cache query**

Fetch `https://sweety.tw/?verify=<timestamp>`, read the version used for both `homepage.css` and `homepage.js`, download those exact resources, and compare their SHA-256 content hash with the local computed 12-character value.

- [ ] **Step 3: Verify Japanese browser presentation**

Open the live page with `navigator.language` / `navigator.languages` set to `ja-JP`. Confirm:

```text
html lang: ja
document title: Sweety｜攻める詐欺対策
tutorial iframe count: 1
tutorial iframe src contains: CLLEgl9tRWA
tutorial section immediately precedes: FAQ
instruction guide items: 7
FAQ details: 5
FAQ JSON-LD questions: 5 Japanese entries
```

Also confirm both Windows and macOS download actions remain enabled, the download counter and total-time live region use Japanese formatting, desktop and mobile widths have no horizontal overflow, and the browser console has no new errors.

- [ ] **Step 4: Verify the other locale regressions live**

Check `zh-Hant-TW` selects `w2w5HGmXxwo` with Traditional Chinese text, and `en-US` selects `-qS4MGvnsa4` with English text. Each mode must contain exactly one tutorial iframe.

- [ ] **Step 5: Report publication evidence**

Report the implementation commit, local test counts, deployed cache version, Japanese video ID, live locale results, and confirmation that the desktop App was neither built nor published.
