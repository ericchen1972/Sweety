import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const webRoot = new URL('../', import.meta.url);
const html = await readFile(new URL('index.html', webRoot), 'utf8').catch(() => '');
const css = await readFile(new URL('homepage.css', webRoot), 'utf8').catch(() => '');
const javascript = await readFile(new URL('homepage.js', webRoot), 'utf8').catch(() => '');
const deployHelper = await readFile(new URL('../app/tools/deploy_homepage.php', webRoot), 'utf8').catch(() => '');
const dmgBuildHelper = await readFile(new URL('../app/desktop/build_dmg.sh', webRoot), 'utf8').catch(() => '');
const macReleaseHelper = await readFile(new URL('../app/tools/deploy_macos_release.php', webRoot), 'utf8').catch(() => '');
const windowsReleaseHelper = await readFile(new URL('../app/tools/deploy_windows_release.php', webRoot), 'utf8').catch(() => '');
const updateManifest = JSON.parse(await readFile(new URL('sweety-update.json', webRoot), 'utf8').catch(() => '{}'));
const robots = await readFile(new URL('robots.txt', webRoot), 'utf8').catch(() => '');
const sitemap = await readFile(new URL('sitemap.xml', webRoot), 'utf8').catch(() => '');
const llms = await readFile(new URL('llms.txt', webRoot), 'utf8').catch(() => '');
const moduleUrl = new URL('homepage.js', webRoot);
const homepage = await import(moduleUrl).catch(() => ({}));
const expectedWindowsDownload = 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.2-d1f2664b';
const expectedMacDownload = 'https://sweety.tw/downloads/Sweety-macos12.7-arm64-latest.dmg?release=2.0.2-20261026';

test('macOS DMG build uses a drag-to-Applications staging folder and verifies the mounted image', () => {
  assert.match(dmgBuildHelper, /codesign --verify --deep --strict .*Sweety\.app/);
  assert.match(dmgBuildHelper, /dist\/dmg-staging/);
  assert.match(dmgBuildHelper, /cp -R .*Sweety\.app["\s].*dmg-staging/);
  assert.match(dmgBuildHelper, /ln -s \/Applications .*dmg-staging["\/]*Applications/);
  assert.match(dmgBuildHelper, /hdiutil create[\s\S]*?\$DMG_PATH/);
  assert.match(dmgBuildHelper, /hdiutil verify .*\$DMG_PATH/);
  assert.match(dmgBuildHelper, /hdiutil attach[\s\S]*?readonly/);
  assert.match(dmgBuildHelper, /\[\[ -d [^\n]*Sweety\.app[^\n]*\]\]/);
  assert.match(dmgBuildHelper, /\[\[ -L [^\n]*Applications[^\n]*\]\]/);
});

test('macOS release helper preserves the metrics environment and verifies the uploaded binary', () => {
  assert.match(macReleaseHelper, /web\/sftp-config\.json/);
  assert.match(macReleaseHelper, /\/sweety\.tw\/\.sweety-runtime-env\.php/);
  assert.match(macReleaseHelper, /SWEETY_METRICS_APP_TOKEN=\(\[a-f0-9\]\{64\}\)/);
  assert.match(macReleaseHelper, /putenv\('SWEETY_METRICS_APP_TOKEN=' \./);
  assert.match(dmgBuildHelper, /SWEETY_LOG_ENABLED=0.*build_app\.sh/);
  assert.match(macReleaseHelper, /ftp_rename/);
  assert.match(macReleaseHelper, /build_dmg\.sh/);
  assert.match(macReleaseHelper, /Sweety-macos12\.7-/);
  assert.match(macReleaseHelper, /SWEETY_TARGET_ARCH/);
  assert.match(macReleaseHelper, /FTP_BINARY/);
  assert.match(macReleaseHelper, /ftp_size\([^)]*\)[^;]*filesize\(/s);
  assert.doesNotMatch(macReleaseHelper, /echo[^;]*(?:password|metricsToken)/i);
});

test('Windows release helper validates and verifies the uploaded Inno Setup binary', () => {
  assert.match(windowsReleaseHelper, /web\/sftp-config\.json/);
  assert.match(windowsReleaseHelper, /Sweety-Setup-1\.0\.2-Windows-x64\.exe/);
  assert.match(windowsReleaseHelper, /\/sweety\.tw\/downloads\/Sweety-Windows-Setup-latest\.exe/);
  assert.match(windowsReleaseHelper, /fread\([^,]+,\s*2\)[^;]*===\s*['"]MZ['"]/s);
  assert.match(windowsReleaseHelper, /FTP_BINARY/);
  assert.match(windowsReleaseHelper, /ftp_size\([^)]*\)[^;]*filesize\(/s);
  assert.doesNotMatch(windowsReleaseHelper, /echo[^;]*(?:password|user)/i);
});

test('homepage deployment remains website-only and never rebuilds the desktop app', () => {
  assert.doesNotMatch(deployHelper, /build_app\.sh/);
  assert.doesNotMatch(deployHelper, /build_dmg\.sh/);
  assert.doesNotMatch(deployHelper, /dist\/Sweety\.app/);
});

test('production update manifest advertises 2.0.2 and deploys publicly', () => {
  assert.deepEqual(updateManifest, {
    latestVersion: '2.0.2',
    downloads: {
      windows: expectedWindowsDownload,
      macos: "https://sweety.tw/#download",
    },
  });
  const manifest = deployHelper.match(/\$files\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
  assert.match(manifest, /['"]sweety-update\.json['"]/);
});

test('machine-readable homepage copy lists both desktop downloads', () => {
  assert.match(llms, /最新版本：2\.0\.2/);
  assert.match(llms, /目前下載：Windows、macOS/);
  assert.doesNotMatch(llms, /Windows：稍後提供/);
});

test('resolveLocale follows browser language preference order and fallback', () => {
  const { resolveLocale } = homepage;
  assert.equal(typeof resolveLocale, 'function');
  for (const locale of ['zh-TW', 'zh-Hant', 'zh-Hant-TW', 'zh-HK', 'zh-MO']) {
    assert.equal(resolveLocale(locale), 'zh-TW');
  }
  for (const locale of ['ja', 'ja-JP', 'ja-JP-u-ca-japanese']) {
    assert.equal(resolveLocale(locale), 'ja');
  }
  for (const locale of ['zh', 'zh-CN', 'en', 'en-US', 'fr-FR', undefined]) {
    assert.equal(resolveLocale(locale), 'en');
  }
  assert.equal(resolveLocale(['zh-Hant-TW', 'en-US'], 'en-US'), 'zh-TW');
  assert.equal(resolveLocale(['en-US', 'zh-TW'], 'zh-TW'), 'en');
  assert.equal(resolveLocale(['zh-CN', 'zh-TW'], 'zh-TW'), 'en');
  assert.equal(resolveLocale([], 'zh-HK'), 'zh-TW');
});

test('2.0 removes obsolete video instructions', () => {
  assert.doesNotMatch(html, /data-tutorial-video|youtube-nocookie/);
});

test('splitWholeHours converts non-negative whole hours to days and hours', () => {
  const { splitWholeHours } = homepage;
  assert.deepEqual(splitWholeHours(0), { days: 0, hours: 0 });
  assert.deepEqual(splitWholeHours(23), { days: 0, hours: 23 });
  assert.deepEqual(splitWholeHours(24), { days: 1, hours: 0 });
  assert.deepEqual(splitWholeHours(49), { days: 2, hours: 1 });
});

test('fetchAggregate accepts only valid day and hour totals', async () => {
  const { fetchAggregate } = homepage;
  const ok = async () => ({ ok: true, json: async () => ({ totalDays: 12, totalHours: 7 }) });
  assert.deepEqual(await fetchAggregate(ok), { days: 12, hours: 7 });

  const invalidBodies = [
    { totalDays: -1, totalHours: 0 },
    { totalDays: 1.5, totalHours: 0 },
    { totalDays: 0, totalHours: -1 },
    { totalDays: 0, totalHours: 24 },
    { totalDays: '1', totalHours: 2 },
    { totalDays: 1, totalHours: Number.NaN },
  ];
  for (const body of invalidBodies) {
    const fetcher = async () => ({ ok: true, json: async () => body });
    assert.equal(await fetchAggregate(fetcher), null);
  }
  assert.equal(await fetchAggregate(async () => ({ ok: false })), null);
  assert.equal(await fetchAggregate(async () => { throw new Error('offline'); }), null);
});

test('locale presentation and live counter text are pure and localized', () => {
  assert.deepEqual(homepage.getLocalePresentation(['zh-Hant-TW', 'en-US'], 'en-US'), {
    locale: 'zh-TW',
    lang: 'zh-TW',
    title: 'Sweety｜主動反詐',
  });
  assert.deepEqual(homepage.getLocalePresentation(['en-US'], 'zh-TW'), {
    locale: 'en',
    lang: 'en',
    title: 'Sweety | Proactive anti-scam',
  });
  assert.equal(homepage.formatCounterText('zh-TW', 12, 7), '目前 Sweety 已經消耗了詐騙總計 12 天 7 小時');
  assert.equal(homepage.formatCounterText('en', 12, 7), 'So far, Sweety has consumed a total of 12 days 7 hours');
});

test('Japanese copy covers the complete homepage and uses Japanese formatting', () => {
  assert.deepEqual(Object.keys(homepage.copy.ja), Object.keys(homepage.copy.en));
  assert.deepEqual(
    Object.keys(homepage.copy.ja.instructions.guide),
    Object.keys(homepage.copy.en.instructions.guide),
  );
  assert.equal(homepage.copy.ja.faq.items.length, 7);
  assert.equal(homepage.copy.ja.hero.title, '詐欺に対して、私たちは受け身で防ぐことしかできないのでしょうか？');
  assert.equal(homepage.copy.ja.instructions.title, "Sweety 2.0 の使い方");
  assert.equal(homepage.copy.ja.notice.title, '注意事項');
  assert.equal(homepage.formatDownloadCount('ja', 42), 'ダウンロード数：42回');
  assert.equal(homepage.formatDownloadCount('ja', null), 'ダウンロード数：—回');
  assert.equal(homepage.formatCounterText('ja', 12, 7), 'Sweetyが詐欺業者に使わせた時間：12日7時間');
  assert.deepEqual(homepage.getLocalePresentation(['ja-JP'], 'en-US'), {
    locale: 'ja',
    lang: 'ja',
    title: 'Sweety｜攻める詐欺対策',
  });
  assert.deepEqual(homepage.getDownloadDecision('macos', 'ja'), {
    enabled: true,
    href: expectedMacDownload,
    label: 'Apple Silicon版をダウンロード',
  });
  assert.deepEqual(homepage.getDownloadDecision('windows', 'ja'), {
    enabled: true,
    href: expectedWindowsDownload,
    label: 'Windows版をダウンロード',
  });
});

test('Japanese metadata and FAQ structured data come from the localized copy', () => {
  assert.deepEqual(homepage.getMetadata('ja'), {
    title: 'Sweety｜攻める詐欺対策',
    description: 'Sweetyは、AIが不審な相手に返信して詐欺業者の時間を消費させる、完全無料・オープンソースの詐欺対策アプリです。',
    socialTitle: 'Sweety｜攻める詐欺対策',
    socialDescription: 'AIを味方につけて、詐欺業者の時間を積極的に奪います。',
    ogLocale: 'ja_JP',
  });

  const faq = homepage.buildFaqStructuredData('ja');
  assert.equal(faq['@type'], 'FAQPage');
  assert.equal(faq['@id'], 'https://sweety.tw/#faq');
  assert.equal(faq.mainEntity.length, 7);
  assert.equal(faq.mainEntity[0].name, homepage.copy.ja.faq.items[0].question);
  assert.equal(
    faq.mainEntity[4].acceptedAnswer.text,
    homepage.copy.ja.faq.items[4].answerPrefix + homepage.copy.ja.faq.items[4].answerEmphasis,
  );
  assert.equal(faq.mainEntity[5].name, homepage.copy.ja.faq.items[5].question);
  assert.equal(faq.mainEntity[5].acceptedAnswer.text, homepage.copy.ja.faq.items[5].answer);
  assert.match(html, /<meta property="og:locale:alternate" content="ja_JP">/);
  assert.match(html, /<script[^>]+type="application\/ld\+json"[^>]+id="homepage-structured-data"[^>]*>/);
  assert.match(html, /"inLanguage":\s*\[\s*"zh-TW",\s*"en",\s*"ja"\s*\]/);
  assert.match(javascript, /applyMetadata\(document,\s*locale\)/);
});

test('aggregate loader releases after timeout and ignores a late stale completion', async () => {
  let calls = 0;
  const releases = [];
  const fetcher = () => {
    calls += 1;
    return new Promise((resolve) => { releases.push(resolve); });
  };
  const loader = homepage.createAggregateLoader(fetcher, 5);
  assert.equal(await loader.load(), null);
  const fresh = loader.load();
  assert.equal(calls, 2);
  releases[0]({ ok: true, json: async () => ({ totalDays: 99, totalHours: 4 }) });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(await loader.load(), null, 'late old completion must not unlock the fresh request');
  assert.equal(calls, 2);
  releases[1]({ ok: true, json: async () => ({ totalDays: 5, totalHours: 6 }) });
  assert.deepEqual(await fresh, { days: 5, hours: 6 });
  const next = loader.load();
  assert.equal(calls, 3);
  releases[2]({ ok: true, json: async () => ({ totalDays: 7, totalHours: 8 }) });
  assert.deepEqual(await next, { days: 7, hours: 8 });
});

test('unchanged aggregates do not trigger visual or live-region updates', () => {
  assert.equal(homepage.hasAggregateChanged({ days: 3, hours: 4 }, { days: 3, hours: 4 }), false);
  assert.equal(homepage.hasAggregateChanged({ days: 3, hours: 4 }, { days: 3, hours: 5 }), true);
  assert.equal(homepage.hasAggregateChanged({ days: 3, hours: 4 }, { days: 4, hours: 4 }), true);
});

test('split-flap digit helpers use four-digit days, two-digit hours, and changed indexes only', () => {
  assert.deepEqual(homepage.toFlipDigits({ days: 12, hours: 7 }), { days: ['0', '0', '1', '2'], hours: ['0', '7'] });
  assert.deepEqual(homepage.toFlipDigits({ days: 0, hours: 23 }), { days: ['0', '0', '0', '0'], hours: ['2', '3'] });
  assert.deepEqual(homepage.changedDigitIndexes(['0', '7'], ['0', '8']), [1]);
  assert.deepEqual(homepage.changedDigitIndexes(['9'], ['1', '0']), [0, 1]);
});

test('Chinese copy preserves every supplied block and step verbatim', () => {
  const { copy } = homepage;
  assert.deepEqual({
    title: copy['zh-TW'].hero.title,
    subtitle: copy['zh-TW'].hero.subtitle,
    body: copy['zh-TW'].hero.body,
    emphasis: copy['zh-TW'].hero.emphasis,
    closing: copy['zh-TW'].hero.closing,
  }, {
    title: '面對詐騙，我們永遠只能被動的防禦嗎？',
    subtitle: '讓 AI 成為我們的武器',
    body: '你覺得詐騙噁心嗎？\n除了刪除封鎖，視而不見外，現在～你有另一種選擇\n使用 Sweety 作為',
    emphasis: '詐騙殺蟲劑',
    closing: '只要在閒置的電腦上運作 Sweety，就可以開始殺蟲',
  });
  assert.deepEqual({
    title: copy['zh-TW'].time.title,
    subtitle: copy['zh-TW'].time.subtitle,
    body: copy['zh-TW'].time.body,
    close: copy['zh-TW'].time.close,
  }, {
    title: '詐騙最大的成本～時間',
    subtitle: '上帝是公平的、詐騙同樣只有24小時',
    body: "設定 LINE 對象並開啟 Sweety，讓 AI 代為回覆。請讓電腦保持開機、網路連線與非休眠狀態；不必保持螢幕亮著或開啟 LINE 桌面視窗。",
    close: '當您起床後，相信對方與 AI 之間的對話，會給您帶來一整天的好心情～',
  });
  assert.equal(copy['zh-TW'].counter.intro, '目前 Sweety 已經消耗了詐騙總計');
  assert.equal(copy['zh-TW'].download.title, '下載 Sweety');
  assert.equal(copy['zh-TW'].instructions.title, "Sweety 2.0 使用說明");
  assert.equal(copy['zh-TW'].instructions.intro, "Sweety 2.0 使用 OKLine 登入 LINE，直接接收訊息並依您選擇的人設被動回覆。先設定 AI Key、登入 LINE，再選取監控對象；AI 不會主動聯絡任何人。");
  assert.equal(copy['zh-TW'].instructions.quote, '「你拖延對方越多的時間、代表他們要付出更多的時間與人力成本、而你挽救了更多人免於被騙。」');
  assert.equal(copy['zh-TW'].instructions.openSourceNote, '＊Sweety 是一款完全免費且開源的程式，如果您對以編譯完成的執行檔有安全疑慮，歡迎透過 Git 重新編譯');
  assert.deepEqual(Object.keys(copy['zh-TW'].instructions.guide), [
    'controlPanel', 'dashboard', 'basicSettings', 'targetList',
    'basePersonas', 'personaDetails', 'customPersonas',
  ]);
  assert.equal(copy['zh-TW'].instructions.guide.controlPanel.title, '控制面板');
  assert.equal(copy['zh-TW'].instructions.guide.dashboard.title, '儀表板');
  assert.equal(copy['zh-TW'].instructions.guide.basicSettings.title, '基本設定');
  assert.equal(copy['zh-TW'].instructions.guide.targetList.title, '騙子列表');
  assert.equal(copy['zh-TW'].instructions.guide.basePersonas.title, '基礎人設');
  assert.equal(copy['zh-TW'].instructions.guide.personaDetails.title, '人設詳細內容');
  assert.equal(copy['zh-TW'].instructions.guide.customPersonas.title, '自訂人設');
  assert.equal(copy['zh-TW'].notice.title, '注意事項');
  assert.equal(copy['zh-TW'].notice.intro, "2.0 版開始前，請完成以下設定：");
  assert.deepEqual(copy['zh-TW'].notice.checklist, ["設定 Agnes／OpenAI API Key", "用手機掃碼登入 LINE", "選取對象並勾選回覆"]);
});

test('copy contains no extra hero lead-in or unsupplied Chinese slogans', () => {
  const { copy } = homepage;
  assert.equal(copy.en.hero.emphasis, 'powerless');
  assert.equal('eyebrow' in copy['zh-TW'].hero, false);
  assert.equal('eyebrow' in copy.en.hero, false);
  assert.equal(typeof copy['zh-TW'].instructions.intro, 'string');
  assert.equal(typeof copy['zh-TW'].instructions.openSourceNote, 'string');
  assert.equal(copy['zh-TW'].footer, 'Sweety');
  assert.doesNotMatch(JSON.stringify(copy['zh-TW']), /Sweety · 主動反詐|從建立對象到啟動，只需要幾個步驟。|Anti-scam companion/);
  assert.doesNotMatch(html, /data-copy="hero\.eyebrow"|Anti-scam companion/);
});

test('homepage instructions use seven single-column illustrated guide items', () => {
  const guideItems = [
    ['controlPanel', 'instructions-control-panel-v2.webp', 500, 500],
    ['dashboard', 'instructions-dashboard-v2.webp', 1280, 720],
    ['basicSettings', 'instructions-basic-settings-v2.webp', 1265, 967],
    ['targetList', 'instructions-target-list-v2.webp', 1280, 720],
    ['basePersonas', 'instructions-base-personas-v2.webp', 1265, 712],
    ['personaDetails', 'instructions-persona-details-v2.webp', 1265, 712],
    ['customPersonas', 'instructions-custom-personas-v2.webp', 1280, 720],
  ];

  assert.equal((html.match(/class="instruction-guide-item/g) ?? []).length, 7);
  for (const [key, filename, width, height] of guideItems) {
    assert.match(html, new RegExp(`src="images/home/${filename}(?:\\?v=[^"]+)?"`));
    assert.match(html, new RegExp(`data-copy="instructions\\.guide\\.${key}\\.title"`));
    assert.match(html, new RegExp(`data-copy="instructions\\.guide\\.${key}\\.body"`));
    assert.match(html, new RegExp(`data-alt="instructions\\.guide\\.${key}\\.imageAlt"`));
    assert.match(html, new RegExp(`src="images/home/${filename}(?:\\?v=[^"]+)?"[^>]+width="${width}"[^>]+height="${height}"`));
  }
  assert.equal(
    homepage.copy['zh-TW'].instructions.triggerNotice,
    "Sweety 只回覆監控期間接收的對象訊息。群組訊息須包含基本設定中的用戶名稱，或真正 LINE 標註目前帳號才回覆；多個名稱以逗號分隔，留空時只回覆標註。圖片與貼圖由所選 AI 辨識，請使用支援圖片的模型；動態貼圖目前以靜態預覽辨識。",
  );
  assert.match(html, /data-copy="instructions\.triggerNotice"/);
  assert.match(css, /\.instruction-guide\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)/s);
  assert.doesNotMatch(html, /quick-start|custom-persona(?:-edit|-apply)?\.(?:png|webp)/);
  assert.doesNotMatch(html, /data-list="(?:quick|advanced)\.steps"/);
});

test('homepage presents the complete ChatGPT perspective in all three locales below the instructions copy', () => {
  const perspectiveKeys = [
    'title', 'source', 'summary', 'core', 'conclusion', 'expandLabel', 'collapseLabel',
    'full.opening', 'full.difference', 'full.processLead', 'full.process', 'full.classifier',
    'full.alternativeLead', 'full.alternative', 'full.economicModel', 'full.coreImpact',
    'full.signalPollution', 'full.funnelLead', 'full.funnelBefore', 'full.funnelSignal',
    'full.funnelAfterLead', 'full.funnelAfter', 'full.kpiLead', 'full.kpiFailure',
    'full.extraSteps', 'full.honeypot', 'full.networkLead', 'full.networkBefore',
    'full.networkTransition', 'full.networkAfter', 'full.threeLayersLead', 'full.layer1',
    'full.layer2', 'full.layer3', 'full.thirdValue', 'full.diagram', 'full.positioning',
    'full.roiLead', 'full.roiStatement', 'full.roiBusiness', 'full.roi', 'full.antiScam',
    'full.sweetyIncreaseLead', 'full.sweetyIncrease', 'full.asymmetry', 'full.aiFit',
    'full.ruleBefore', 'full.ruleAfterLead', 'full.ruleAfter',
  ];
  const valueAt = (source, path) => path.split('.').reduce((value, key) => value?.[key], source);
  const zh = homepage.copy['zh-TW'].instructions.perspective;
  const en = homepage.copy.en.instructions.perspective;
  const ja = homepage.copy.ja.instructions.perspective;

  for (const key of perspectiveKeys) {
    assert.equal(typeof valueAt(zh, key), 'string', `missing zh-TW perspective.${key}`);
    assert.equal(typeof valueAt(en, key), 'string', `missing en perspective.${key}`);
    assert.equal(typeof valueAt(ja, key), 'string', `missing ja perspective.${key}`);
    assert.match(html, new RegExp(`data-copy="instructions\\.perspective\\.${key.replaceAll('.', '\\.')}`));
  }

  assert.equal(zh.title, 'ChatGPT 對 Sweety 的觀點');
  assert.equal(zh.source, '以下內容是 ChatGPT 在與作者討論 Sweety 時，對此專案提出的觀點。');
  assert.equal(zh.full.funnelBefore, '10,000 個接觸\n→ 500 個回覆\n→ 100 個長聊\n→ 10 個匯款');
  assert.equal(zh.full.funnelAfter, '10,000 個接觸\n→ 1,500 個回覆\n→ 800 個長聊\n→ 其中 700 個其實是 AI');
  assert.equal(zh.full.roiStatement, '降低詐騙產業的 ROI。');
  assert.equal(zh.full.roi, 'Profit = 成功詐得金額 − 人力 − 帳號 − 廣告 − 洗錢 − 時間成本');
  assert.equal(zh.full.aiFit, '這種成本不對稱，才是 AI 最適合做的事。');
  assert.equal(zh.full.ruleAfter, '「能聊下去，什麼也不代表。」');
  assert.equal(en.full.ruleAfter, '“A conversation continuing means nothing.”');
  assert.equal(ja.full.ruleAfter, '「会話が続いても、何の意味もない。」');

  const openSourceOffset = html.indexOf('data-copy="instructions.openSourceNote"');
  const perspectiveOffset = html.indexOf('class="chatgpt-perspective"');
  const guideOffset = html.indexOf('class="instruction-guide"');
  assert.ok(openSourceOffset < perspectiveOffset && perspectiveOffset < guideOffset);
  assert.match(html, /<aside class="chatgpt-perspective"[^>]*>/);
  assert.match(html, /<details class="chatgpt-perspective-details">/);
  assert.match(html, /<summary class="chatgpt-perspective-toggle">/);
});

test('ChatGPT perspective styles keep the expandable article readable on mobile', () => {
  for (const selector of [
    '.chatgpt-perspective',
    '.chatgpt-perspective-summary',
    '.chatgpt-perspective-details',
    '.perspective-funnel',
    '.perspective-diagram',
    '.perspective-expand-label',
    '.perspective-collapse-label',
  ]) {
    assert.match(css, new RegExp(`\\${selector}[^,{]*[,{]`));
  }
  const preRule = css.match(/\.perspective-funnel[^}]*\.perspective-diagram[^}]*\{([^}]*)\}/s)?.[1] ?? '';
  assert.match(preRule, /overflow-x:\s*auto/);
  assert.match(css, /\.chatgpt-perspective-details\[open\][^{]*\.perspective-expand-label\s*\{[^}]*display:\s*none/s);
  assert.match(css, /@media \(max-width:\s*768px\)[\s\S]*?\.chatgpt-perspective\s*\{[^}]*padding:/);
});

test('homepage includes 2.0 setup notes and seven independent localized FAQs', () => {
  const permissionFaqZh = homepage.copy['zh-TW'].faq.items[4];
  const permissionFaqEn = homepage.copy.en.faq.items[4];
  const languageFaqZh = homepage.copy['zh-TW'].faq.items[5];
  const languageFaqEn = homepage.copy.en.faq.items[5];
  const languageFaqJa = homepage.copy.ja.faq.items[5];

  assert.equal(homepage.copy['zh-TW'].notice.connection, "請保持 Sweety 執行、電腦連網且不進入休眠。停止監控期間不接收新訊息，重新開始不會集中補回覆。");
  assert.equal(homepage.copy['zh-TW'].faq.items.length, 7);
  assert.equal(homepage.copy.en.faq.items.length, 7);
  assert.equal(homepage.copy.ja.faq.items.length, 7);
  assert.deepEqual(permissionFaqZh, {
    question: "為什麼按「開始」後提示輸入 API Key？",
    answerPrefix: "請到基本設定選擇 Agnes 或 OpenAI，輸入目前所選服務的 API Key。",
    answerEmphasis: "按「儲存設定」後，確認 LINE 已登入並勾選至少一個對象，再開始監控。",
  });
  assert.deepEqual(permissionFaqEn, {
    question: "Why am I asked for an API key when I press Start?",
    answerPrefix: "Choose Agnes or OpenAI in Basic settings and enter an API key for that selected provider. ",
    answerEmphasis: "Save settings, sign in to LINE, and select at least one target before starting.",
  });
  assert.deepEqual(languageFaqZh, {
    question: 'Sweety 支援哪些語系？',
    answer: 'Sweety 介面支援繁中、英文及日文，但是 AI 的回覆將以對方使用的語言為主。',
  });
  assert.deepEqual(languageFaqEn, {
    question: 'Which languages does Sweety support?',
    answer: 'The Sweety interface supports Traditional Chinese, English, and Japanese. AI replies will primarily use the language spoken by the other person.',
  });
  assert.deepEqual(languageFaqJa, {
    question: 'Sweetyはどの言語に対応していますか？',
    answer: 'Sweetyのインターフェースは繁体字中国語、英語、日本語に対応しています。ただし、AIは主に相手が使用している言語で返信します。',
  });
  assert.equal((html.match(/<details class="faq-item"/g) ?? []).length, 7);
  assert.equal((html.match(/<details\b/g) ?? []).length, 8);
  assert.equal((html.match(/<summary\b/g) ?? []).length, 8);
  assert.doesNotMatch(html, /<details[^>]+\bname=/);
  for (const hook of [
    'faq.title',
    'faq.items.0.question',
    'faq.items.0.answer',
    'faq.items.4.question',
    'faq.items.4.answerPrefix',
    'faq.items.4.answerEmphasis',
    'faq.items.5.question',
    'faq.items.5.answer',
    'instructions.openSourceNote',
    'notice.connection',
  ]) {
    assert.match(html, new RegExp(`data-copy="${hook.replaceAll('.', '\\.')}`));
  }
  assert.match(html, /<span data-copy="faq\.items\.4\.answerPrefix">/);
  assert.match(html, /<strong data-copy="faq\.items\.4\.answerEmphasis">/);
  assert.match(html, /"name": "Sweety 支援哪些語系？"/);
  assert.match(html, /"text": "Sweety 介面支援繁中、英文及日文，但是 AI 的回覆將以對方使用的語言為主。"/);
  assert.doesNotMatch(html, /\*\*「輔助使用」/);
  assert.match(css, /\.faq-item/);
  assert.match(css, /\.faq-item summary/);
});

test('homepage author card uses the public portrait and safe new-tab project links', async () => {
  const portrait = await readFile(new URL('images/eric.png', webRoot));
  assert.equal(portrait.toString('hex', 0, 8), '89504e470d0a1a0a');
  assert.equal(portrait.readUInt32BE(16), 256);
  assert.equal(portrait.readUInt32BE(20), 256);
  assert.match(html, /class="author-card"/);
  assert.match(html, /class="author-avatar"[^>]+src="images\/eric\.png"[^>]+width="256"[^>]+height="256"/);
  for (const href of ['https://slimweb.tw', 'https://slimweb.tw/kingjoo/', 'https://sweety.tw']) {
    const escaped = href.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    assert.match(html, new RegExp(`href="${escaped}"[^>]+target="_blank"[^>]+rel="noopener noreferrer"`));
  }
  for (const href of ['https://line.me/ti/p/ekr53MoZc6', 'https://www.threads.com/@eric_slimweb']) {
    const escaped = href.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    assert.match(html, new RegExp(`href="${escaped}"[^>]+target="_blank"[^>]+rel="noopener noreferrer"`));
  }
  assert.deepEqual(homepage.copy['zh-TW'].author.threads, { prefix: '如想得到更多AI開發應用訊息，請追蹤我的', label: 'Threads' });
  assert.deepEqual(homepage.copy.en.author.threads, { prefix: 'For more AI development and application updates, follow me on', label: 'Threads' });
  assert.match(css, /\.author-card/);
  assert.match(css, /\.author-avatar[^}]*border-radius:\s*50%/s);
});

test('download configuration enables Windows and macOS', () => {
  assert.deepEqual(homepage.downloadConfig, {
    windows: expectedWindowsDownload,
    macos: expectedMacDownload,
    macosIntel: 'https://sweety.tw/downloads/Sweety-macos12.7-x86_64-latest.dmg?release=2.0.2-20261026',
  });
  assert.deepEqual(homepage.getDownloadDecision('macos', 'zh-TW'), {
    enabled: true,
    href: expectedMacDownload,
    label: '下載 Apple Silicon 版',
  });
  assert.deepEqual(homepage.getDownloadDecision('windows', 'zh-TW'), {
    enabled: true,
    href: expectedWindowsDownload,
    label: '下載 Windows 版',
  });
  assert.deepEqual(homepage.getDownloadDecision('windows', 'en'), {
    enabled: true,
    href: expectedWindowsDownload,
    label: 'Download for Windows',
  });
  assert.equal((html.match(/data-platform="(?:windows|macos|macosIntel)"/g) ?? []).length, 3);
  assert.equal((html.match(/class="platform-icon[^"]*"[^>]*aria-hidden="true"/g) ?? []).length, 4);
  assert.equal((html.match(/class="download-action"[^>]*disabled/g) ?? []).length, 0);
  assert.match(html, new RegExp(`href="${expectedWindowsDownload.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"`));
  assert.match(html, new RegExp(`href="${expectedMacDownload.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"`));
  assert.doesNotMatch(html, /<div class="platform-icon"[^>]*>[●⊞]<\/div>/);
});

test('download totals are parsed, localized, fetched, and recorded safely', async () => {
  assert.equal(homepage.parseDownloadTotal({ totalDownloads: 0 }), 0);
  assert.equal(homepage.parseDownloadTotal({ totalDownloads: 42 }), 42);
  for (const invalid of [
    { totalDownloads: -1 },
    { totalDownloads: '42' },
    { totalDownloads: 1.5 },
    {},
    null,
  ]) assert.equal(homepage.parseDownloadTotal(invalid), null);

  assert.equal(homepage.formatDownloadCount('zh-TW', 42), '已下載 42 次');
  assert.equal(homepage.formatDownloadCount('en', 42), 'Downloaded 42 times');
  assert.equal(homepage.formatDownloadCount('zh-TW', null), '已下載 — 次');

  const calls = [];
  const fetcher = async (url, options = {}) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ totalDownloads: 8 }) };
  };
  assert.equal(await homepage.fetchDownloadTotal(fetcher), 8);
  assert.equal(calls[0].url, '/sweety-downloads.php');
  assert.equal(calls[0].options.headers.Accept, 'application/json');
  assert.equal(await homepage.recordDownload(fetcher), 8);
  assert.deepEqual(calls[1], {
    url: '/sweety-downloads.php',
    options: {
      method: 'POST',
      headers: { Accept: 'application/json' },
      keepalive: true,
    },
  });
  assert.equal(await homepage.fetchDownloadTotal(async () => ({ ok: false })), null);
  assert.equal(await homepage.recordDownload(async () => { throw new Error('offline'); }), null);
});

test('platform tracking never blocks navigation and reports a successful total', async () => {
  let clickHandler = null;
  const link = {
    addEventListener(type, handler) {
      if (type === 'click') clickHandler = handler;
    },
  };
  const totals = [];
  homepage.attachDownloadTracking(
    link,
    (total) => totals.push(total),
    async () => ({ ok: true, json: async () => ({ totalDownloads: 9 }) }),
  );
  assert.equal(typeof clickHandler, 'function');
  assert.equal(clickHandler(), undefined);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.deepEqual(totals, [9]);
});

test('download count sits right on large screens and stacks left on mobile', () => {
  assert.match(html, /class="section-heading download-heading"/);
  assert.match(html, /class="download-count"[^>]+aria-live="polite"[^>]+data-download-count[^>]*>Downloaded — times</);
  assert.match(css, /\.download-heading\s*\{[^}]*display:\s*flex[^}]*justify-content:\s*space-between/s);
  assert.match(css, /\.download-count\s*\{[^}]*font-size:\s*\.9rem/s);
  const mobile = css.match(/@media \(max-width:\s*768px\)\s*\{([\s\S]*?)\n\}/)?.[1] ?? '';
  assert.match(mobile, /\.download-heading\s*\{[^}]*align-items:\s*flex-start[^}]*flex-direction:\s*column/s);
});

test('download section includes a Git card beside architecture-specific downloads with a safe new-tab repository link', () => {
  assert.equal((html.match(/class="download-card/g) ?? []).length, 4);
  assert.match(html, /class="download-card git-card"/);
  assert.match(html, /class="platform-icon github"[^>]*aria-hidden="true"/);
  assert.match(html, /href="https:\/\/github\.com\/ericchen1972\/Sweety"[^>]+target="_blank"[^>]+rel="noopener noreferrer"[^>]*>Git<\/a>/);
  assert.match(css, /\.download-grid[^}]*grid-template-columns:\s*repeat\(2,/s);
  const mobile = css.match(/@media \(max-width:\s*768px\)\s*\{([\s\S]*?)\n\}/)?.[1] ?? '';
  assert.match(mobile, /\.download-grid\s*\{[^}]*grid-template-columns:\s*1fr/);
});

test('homepage exposes complete social metadata and machine-readable application facts', async () => {
  for (const expected of [
    '<link rel="canonical" href="https://sweety.tw/">',
    '<meta property="og:type" content="website">',
    '<meta property="og:url" content="https://sweety.tw/">',
    '<meta property="og:image" content="https://sweety.tw/images/sweety-social-1200x630.png">',
    '<meta property="og:image:width" content="1200">',
    '<meta property="og:image:height" content="630">',
    '<meta name="twitter:card" content="summary_large_image">',
  ]) assert.match(html, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));

  const social = await readFile(new URL('images/sweety-social-1200x630.png', webRoot));
  assert.equal(social.toString('hex', 0, 8), '89504e470d0a1a0a');
  assert.equal(social.readUInt32BE(16), 1200);
  assert.equal(social.readUInt32BE(20), 630);

  const blocks = [...html.matchAll(/<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g)].map((match) => JSON.parse(match[1]));
  const graph = blocks.flatMap((block) => block['@graph'] ?? [block]);
  for (const type of ['WebSite', 'Organization', 'Person', 'SoftwareApplication', 'FAQPage']) {
    assert.ok(graph.some((node) => node['@type'] === type), `JSON-LD should include ${type}`);
  }
  const app = graph.find((node) => node['@type'] === 'SoftwareApplication');
  assert.equal(app.softwareVersion, '2.0.0');
  assert.equal(app.operatingSystem, 'Windows, macOS');
  assert.equal(app.offers.price, '0');
});

test('robots, sitemap, and llms discovery files identify the canonical public site', () => {
  assert.match(robots, /User-agent:\s*\*/);
  assert.match(robots, /Allow:\s*\//);
  assert.match(robots, /Sitemap:\s*https:\/\/sweety\.tw\/sitemap\.xml/);
  for (const url of ['https://sweety.tw/', 'https://sweety.tw/about_sweety.html']) assert.match(sitemap, new RegExp(url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  assert.match(llms, /^# Sweety/m);
  assert.match(llms, /主動式反詐騙 App/);
  assert.match(llms, /https:\/\/github\.com\/ericchen1972\/Sweety/);
  assert.match(llms, /目前下載：Windows、macOS/);
  assert.doesNotMatch(llms, /Windows：稍後提供/);
});

test('future download decisions allow HTTPS or safe relative paths and use action copy', () => {
  assert.equal(homepage.sanitizeDownloadUrl('https://cdn.example.com/sweety.exe'), 'https://cdn.example.com/sweety.exe');
  assert.equal(homepage.sanitizeDownloadUrl('/downloads/sweety.dmg'), '/downloads/sweety.dmg');
  assert.equal(homepage.sanitizeDownloadUrl('./downloads/sweety.dmg'), './downloads/sweety.dmg');
  assert.equal(homepage.sanitizeDownloadUrl('downloads/sweety.dmg'), 'downloads/sweety.dmg');
  for (const unsafe of ['http://cdn.example.com/sweety.exe', '//cdn.example.com/sweety.exe', 'javascript:alert(1)', 'data:text/plain,x']) {
    assert.equal(homepage.sanitizeDownloadUrl(unsafe), null);
  }
  assert.deepEqual(homepage.getDownloadDecision('windows', 'zh-TW', { windows: '/downloads/sweety.exe', macos: null }), {
    enabled: true,
    href: '/downloads/sweety.exe',
    label: '下載 Windows 版',
  });
  assert.deepEqual(homepage.getDownloadDecision('macos', 'en', { windows: null, macos: null }), {
    enabled: false,
    href: null,
    label: 'Coming soon',
  });
});

test('landing page has semantic sections, required assets, and no dead download hrefs', () => {
  assert.match(html, /<header\b/);
  assert.match(html, /<main\b/);
  assert.match(html, /<section[^>]+id="anti-scam"/);
  assert.match(html, /<section[^>]+id="time-cost"/);
  assert.match(html, /<section[^>]+id="total-time"/);
  assert.match(html, /<section[^>]+id="download"/);
  assert.match(html, /<section[^>]+id="instructions"/);
  for (const anchor of ['anti-scam', 'download', 'instructions']) {
    assert.match(html, new RegExp(`href="#${anchor}"`));
  }
  assert.match(html, /images\/home\/hero-helpless\.png/);
  assert.match(html, /images\/home\/time-clock-blue\.png/);
  for (const asset of [
    'instructions-control-panel-v2.webp',
    'instructions-dashboard-v2.webp',
    'instructions-basic-settings-v2.webp',
    'instructions-target-list-v2.webp',
    'instructions-base-personas-v2.webp',
    'instructions-persona-details-v2.webp',
    'instructions-custom-personas-v2.webp',
  ]) assert.match(html, new RegExp(`images/home/${asset}`));
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /homepage\.js/);
  assert.match(html, /homepage\.css/);
  assert.doesNotMatch(html, /href=["'](?:#|javascript:|)["']/i);
  assert.equal((html.match(/class="download-action"[^>]*disabled/g) ?? []).length, 0);
});

test('homepage stylesheet and module script share an explicit cache-busting version', () => {
  const stylesheetVersion = html.match(/<link[^>]+href="homepage\.css\?v=([^"&]+)"/)?.[1] ?? '';
  const scriptVersion = html.match(/<script[^>]+src="homepage\.js\?v=([^"&]+)"/)?.[1] ?? '';
  const assetVersion = createHash('sha256').update(css).update('\0').update(javascript).digest('hex').slice(0, 12);
  assert.ok(stylesheetVersion, 'homepage.css URL should include a non-empty version query');
  assert.equal(scriptVersion, stylesheetVersion, 'homepage.js should use the same version query');
  assert.equal(scriptVersion, assetVersion, 'homepage asset version should match the CSS and JavaScript content hash');
});

test('static HTML is a complete default-English document without JavaScript', () => {
  for (const text of [
    'When facing scams, can we only defend ourselves passively?',
    'Many people share this question. Beyond public awareness campaigns, repeated again and again,',
    'Now, users can run Sweety on an idle computer',
    'A scammer’s greatest cost: time',
    'Choose LINE targets and let Sweety handle replies.',
    'When you wake up, the conversation between the other person and AI may put you in a good mood for the rest of the day.',
    'Control panel',
    'Dashboard',
    'Basic settings',
    'Scammer list',
    'Base personas',
    'Persona details',
    'Custom personas',
    'Sweety replies only to target messages received while monitoring.',
    'Configure an Agnes / OpenAI API key',
    'Scan the LINE login QR code',
    'Select targets and enable Reply',
  ]) assert.match(html, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  const permissions = html.match(/data-list="notice\.checklist"[^>]*>([\s\S]*?)<\/ul>/)?.[1] ?? '';
  assert.equal((html.match(/class="instruction-guide-item/g) ?? []).length, 7);
  assert.equal((permissions.match(/<li>/g) ?? []).length, 3);
  assert.doesNotMatch(html, /data-copy="(?:hero\.body|hero\.closing|time\.subtitle|time\.body|time\.close)"\s*><\/p>/);
});

test('counter exposes one stable polite live string outside animated visuals', () => {
  assert.match(html, /class="counter"[^>]*aria-hidden="true"/);
  assert.match(html, /class="sr-only"[^>]*aria-live="polite"[^>]*aria-atomic="true"[^>]*data-counter-live/);
  assert.match(html, /So far, Sweety has consumed a total of 0 days 0 hours/);
  assert.doesNotMatch(html, /class="counter"[^>]*aria-live/);
});

test('counter uses local split-flap markup and reduced-motion styling', () => {
  assert.equal((html.match(/class="flip-group"/g) ?? []).length, 2);
  assert.match(html, /data-flip-digits="days"/);
  assert.match(html, /data-flip-digits="hours"/);
  assert.match(css, /\.flip-digit/);
  assert.match(css, /\.flip-face\.top/);
  assert.match(css, /\.flip-face\.bottom/);
  assert.match(css, /@keyframes\s+flip-top/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)[\s\S]*\.is-flipping/);
  assert.doesNotMatch(javascript, /FlipClock|jquery|codepen/i);
});

test('images declare intrinsic dimensions and compressed WebP sources', async () => {
  const pngAssets = [
    ['images/logo.png', 373, 373, false],
    ['images/home/hero-helpless.png', 1672, 941, false],
    ['images/home/time-clock-blue.png', 1672, 941, false],
  ];
  for (const [path, width, height, lazy] of pngAssets) {
    const png = await readFile(new URL(path, webRoot));
    assert.equal(png.toString('hex', 0, 8), '89504e470d0a1a0a');
    assert.equal(png.readUInt32BE(16), width);
    assert.equal(png.readUInt32BE(20), height);
    const escaped = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const tag = html.match(new RegExp(`<img[^>]+src="${escaped}(?:\\?v=[^"]+)?"[^>]*>`))?.[0] ?? '';
    assert.match(tag, new RegExp(`width="${width}"`));
    assert.match(tag, new RegExp(`height="${height}"`));
    assert.match(tag, /decoding="async"/);
    if (lazy) assert.match(tag, /loading="lazy"/);
  }
  const webpAssets = [
    ['images/home/instructions-control-panel-v2.webp', 500, 500],
    ['images/home/instructions-dashboard-v2.webp', 1280, 720],
    ['images/home/instructions-basic-settings-v2.webp', 1265, 967],
    ['images/home/instructions-target-list-v2.webp', 1280, 720],
    ['images/home/instructions-base-personas-v2.webp', 1265, 712],
    ['images/home/instructions-persona-details-v2.webp', 1265, 712],
    ['images/home/instructions-custom-personas-v2.webp', 1280, 720],
  ];
  for (const [path, width, height] of webpAssets) {
    const webp = await readFile(new URL(path, webRoot));
    assert.equal(webp.toString('ascii', 0, 4), 'RIFF');
    assert.equal(webp.toString('ascii', 8, 12), 'WEBP');
    const escaped = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const tag = html.match(new RegExp(`<img[^>]+src="${escaped}(?:\\?v=[^"]+)?"[^>]*>`))?.[0] ?? '';
    assert.match(tag, new RegExp(`width="${width}"`));
    assert.match(tag, new RegExp(`height="${height}"`));
    assert.match(tag, /decoding="async"/);
    assert.match(tag, /loading="lazy"/);
  }
});

test('header logo prefers a valid compressed WebP with a PNG fallback', async () => {
  const picture = html.match(/<a class="brand"[\s\S]*?<picture>([\s\S]*?)<\/picture>/)?.[1] ?? '';
  const sourceOffset = picture.indexOf('<source srcset="images/logo.webp" type="image/webp">');
  const fallbackOffset = picture.indexOf('<img src="images/logo.png"');
  assert.ok(sourceOffset >= 0, 'brand picture should offer images/logo.webp');
  assert.ok(fallbackOffset > sourceOffset, 'WebP source should precede the PNG fallback');

  const png = await readFile(new URL('images/logo.png', webRoot));
  const webp = await readFile(new URL('images/logo.webp', webRoot));
  assert.equal(webp.toString('ascii', 0, 4), 'RIFF');
  assert.equal(webp.toString('ascii', 8, 12), 'WEBP');
  assert.ok(webp.byteLength < png.byteLength, 'logo.webp should be smaller than logo.png');
});

test('time content order and localization hooks match the DOM contract', () => {
  assert.ok(html.indexOf('data-copy="time.title"') < html.indexOf('data-copy="time.subtitle"'));
  assert.match(html, /<script type="module" src="homepage\.js\?v=[a-f0-9]{12}"><\/script>/);
  for (const hook of ['skipLink', 'brandLabel', 'nav.label', 'nav.antiScam', 'nav.download', 'nav.instructions']) {
    assert.match(html, new RegExp(`data-(?:copy|aria-label)="${hook.replace('.', '\\.')}`));
  }
});

test('hero is a full-width isolated viewport with full-bleed background art', () => {
  const heroRule = css.match(/\.hero\s*\{([^}]*)\}/)?.[1] ?? '';
  assert.match(heroRule, /width:\s*100%/);
  assert.match(heroRule, /position:\s*relative/);
  assert.match(heroRule, /isolation:\s*isolate/);
  assert.match(heroRule, /overflow:\s*hidden/);
  assert.match(heroRule, /min-height:\s*calc\(100vh\s*-\s*76px\)/);

  const artRule = css.match(/\.hero-art\s*\{([^}]*)\}/)?.[1] ?? '';
  assert.match(artRule, /position:\s*absolute/);
  assert.match(artRule, /inset:\s*0/);
  assert.match(artRule, /z-index:\s*0/);

  const pictureRule = css.match(/\.hero-art picture\s*\{([^}]*)\}/)?.[1] ?? '';
  assert.match(pictureRule, /width:\s*100%/);
  assert.match(pictureRule, /height:\s*100%/);

  const imageRule = css.match(/\.hero-art img\s*\{([^}]*)\}/)?.[1] ?? '';
  assert.match(imageRule, /width:\s*100%/);
  assert.match(imageRule, /height:\s*100%/);
  assert.match(imageRule, /object-fit:\s*cover/);
  assert.match(imageRule, /object-position:\s*right center/);
});

test('hero copy sits above a white-to-transparent reading gradient', () => {
  const copyRule = css.match(/\.hero-copy\s*\{([^}]*)\}/)?.[1] ?? '';
  assert.match(copyRule, /z-index:\s*2/);
  assert.match(copyRule, /padding-inline:\s*clamp\(/);

  const overlayRule = css.match(/\.hero::after\s*\{([^}]*)\}/)?.[1] ?? '';
  assert.match(overlayRule, /content:\s*["']{2}/);
  assert.match(overlayRule, /position:\s*absolute/);
  assert.match(overlayRule, /inset:\s*0/);
  assert.match(overlayRule, /z-index:\s*1/);
  assert.match(overlayRule, /linear-gradient\(to right,\s*#fff/);
  assert.match(overlayRule, /transparent/);
});

test('mobile keeps hero art as a background layer without legacy layout overrides', () => {
  const mobile = css.match(/@media \(max-width:\s*768px\)\s*\{([\s\S]*?)\n\}/)?.[1] ?? '';
  assert.doesNotMatch(mobile, /\.hero-art\s*\{[^}]*(?:grid-row|margin|max-height)/);
  assert.doesNotMatch(mobile, /\.hero-art img\s*\{[^}]*max-height/);
  assert.match(mobile, /\.hero-art img\s*\{[^}]*object-position:\s*68% center/);
  assert.match(mobile, /\.hero::after\s*\{[^}]*linear-gradient\(to bottom/);
  assert.doesNotMatch(mobile, /\.hero\s*\{[^}]*grid-template-columns/);
});

test('homepage deployment manifest includes public pages, endpoints, discovery files, and social assets', () => {
  const manifest = deployHelper.match(/\$files\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
  for (const file of ['images/logo.webp', 'images/logo.png', 'images/eric.png', 'images/sweety-social-1200x630.png', 'about_sweety.html', 'robots.txt', 'sitemap.xml', 'llms.txt', 'sweety-downloads.php', 'sweety-downloads-lib.php']) {
    assert.match(manifest, new RegExp(`['"]${file.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}['"]`));
  }
});

test('navigation observer targets only sections represented by header links', () => {
  assert.match(javascript, /const sections = links\s*\.map\(\(link\) => document\.querySelector\(link\.hash\)\)\s*\.filter\(Boolean\)/);
  assert.doesNotMatch(javascript, /querySelectorAll\(['"]main section\[id\]['"]\)/);
});


test('2.0 guides document OKLine, user keys, history and groups without legacy setup', () => {
  for (const locale of ['zh-TW','en','ja']) {
    const section=homepage.copy[locale].instructions;
    assert.match(section.intro,/OKLine/);
    assert.match(section.guide.basicSettings.body,/Agnes/);
    assert.match(section.guide.basicSettings.body,/OpenAI/);
    assert.match(section.guide.basicSettings.body,/agnes-3.0-flash/);
    assert.match(section.guide.basicSettings.body,/6/);
    assert.match(section.guide.basicSettings.body,/4[–～]30/);
    assert.match(section.guide.targetList.body,/QR/);
    assert.match(section.triggerNotice,/LINE/);
  }
  assert.doesNotMatch(javascript+html,/需要 Mac 權限|Screen &amp; System Audio Recording|Sweety 預設|檢查新訊息的間隔|youtube-nocookie/);
  assert.match(deployHelper,/--docs-only/);
});
