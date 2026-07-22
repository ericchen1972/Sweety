import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const webRoot = new URL('../', import.meta.url);
const html = await readFile(new URL('index.html', webRoot), 'utf8').catch(() => '');
const css = await readFile(new URL('homepage.css', webRoot), 'utf8').catch(() => '');
const javascript = await readFile(new URL('homepage.js', webRoot), 'utf8').catch(() => '');
const deployHelper = await readFile(new URL('../app/tools/deploy_homepage.php', webRoot), 'utf8').catch(() => '');
const updateManifest = JSON.parse(await readFile(new URL('sweety-update.json', webRoot), 'utf8').catch(() => '{}'));
const robots = await readFile(new URL('robots.txt', webRoot), 'utf8').catch(() => '');
const sitemap = await readFile(new URL('sitemap.xml', webRoot), 'utf8').catch(() => '');
const llms = await readFile(new URL('llms.txt', webRoot), 'utf8').catch(() => '');
const moduleUrl = new URL('homepage.js', webRoot);
const homepage = await import(moduleUrl).catch(() => ({}));

test('production update manifest is safe for current 1.0.1 installations and deploys publicly', () => {
  assert.deepEqual(updateManifest, { latestVersion: '1.0.1', downloads: {} });
  const manifest = deployHelper.match(/\$files\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
  assert.match(manifest, /['"]sweety-update\.json['"]/);
});

test('resolveLocale follows browser language preference order and fallback', () => {
  const { resolveLocale } = homepage;
  assert.equal(typeof resolveLocale, 'function');
  for (const locale of ['zh-TW', 'zh-Hant', 'zh-Hant-TW', 'zh-HK', 'zh-MO']) {
    assert.equal(resolveLocale(locale), 'zh-TW');
  }
  for (const locale of ['zh', 'zh-CN', 'en', 'en-US', 'ja-JP', undefined]) {
    assert.equal(resolveLocale(locale), 'en');
  }
  assert.equal(resolveLocale(['zh-Hant-TW', 'en-US'], 'en-US'), 'zh-TW');
  assert.equal(resolveLocale(['en-US', 'zh-TW'], 'zh-TW'), 'en');
  assert.equal(resolveLocale(['zh-CN', 'zh-TW'], 'zh-TW'), 'en');
  assert.equal(resolveLocale([], 'zh-HK'), 'zh-TW');
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
    body: '相信很多人都有這種疑問，我們的政府除了宣導、宣導、再宣導外，\n對於跨境詐騙，可以說是',
    emphasis: '束手無策',
    closing: '現在，用戶只要在閒置的電腦上運作 Sweety，\n就可以進行「主動反詐」',
  });
  assert.deepEqual({
    title: copy['zh-TW'].time.title,
    subtitle: copy['zh-TW'].time.subtitle,
    body: copy['zh-TW'].time.body,
    close: copy['zh-TW'].time.close,
  }, {
    title: '詐騙最大的成本～時間',
    subtitle: '上帝是公平的、詐騙同樣只有24小時',
    body: '您不用「花費任何時間」在詐騙身上，您只需設定好 Line 對象，睡覺前開啟 Sweety 即可，唯一要付出的微末成本，電腦及螢幕不要關，不要進入休眠，不要進入螢幕保護。',
    close: '當您起床後，相信對方與 AI 之間的對話，會給您帶來一整天的好心情～',
  });
  assert.equal(copy['zh-TW'].counter.intro, '目前 Sweety 已經消耗了詐騙總計');
  assert.equal(copy['zh-TW'].download.title, '下載 Sweety');
  assert.deepEqual(copy['zh-TW'].instructions, {
    title: '使用說明',
    intro: 'Sweety 使用你閒置的電腦並操作 Line 桌面 App ，透過人物設定，讓 AI 不斷消耗詐騙的時間，請注意 - AI 不會主動與詐騙聯繫，只會被動回覆，你可以透過修改人設，讓 AI 發揮更大的拖延效果。',
    quote: '「你拖延對方越多的時間、代表他們要付出更多的時間與人力成本、而你挽救了更多人免於被騙。」',
  });
  assert.equal(copy['zh-TW'].quick.title, '快速上手');
  assert.deepEqual(copy['zh-TW'].quick.steps, [
    '在騙子列表內建立對象，輸入對方的 Line 名稱',
    '選擇要使用的人設（建議選擇與您自身類似的人設）',
    '勾選要回覆的對象',
    '在面板上案開始',
    '如果你想親自接手交談，可隨時按停止',
    '睡覺去',
  ]);
  assert.deepEqual(copy['zh-TW'].advanced.steps, [
    '選擇基礎人設',
    '點擊「增加到自訂人設」',
    '進入自訂人設修改',
    '在監控對象上套用自訂人設',
  ]);
  assert.equal(copy['zh-TW'].advanced.title, '進階設定');
  assert.equal(copy['zh-TW'].advanced.intro, '如果您覺得預設人物不夠精準，您可以自訂人設，或者用基礎人設做延伸');
  assert.equal(copy['zh-TW'].notice.title, '注意事項');
  assert.equal(copy['zh-TW'].notice.intro, 'Mac OS 系統下，需賦予 Sweety 三種權限，分別是');
  assert.deepEqual(copy['zh-TW'].notice.permissions, ['輔助使用', '螢幕與系統錄音', '自動化']);
});

test('copy contains no extra hero lead-in or unsupplied Chinese slogans', () => {
  const { copy } = homepage;
  assert.equal(copy.en.hero.emphasis, 'powerless');
  assert.equal('eyebrow' in copy['zh-TW'].hero, false);
  assert.equal('eyebrow' in copy.en.hero, false);
  assert.equal(typeof copy['zh-TW'].instructions.intro, 'string');
  assert.equal(copy['zh-TW'].footer, 'Sweety');
  assert.doesNotMatch(JSON.stringify(copy['zh-TW']), /Sweety · 主動反詐|從建立對象到啟動，只需要幾個步驟。|Anti-scam companion/);
  assert.doesNotMatch(html, /data-copy="hero\.eyebrow"|Anti-scam companion/);
});

test('homepage includes the LINE window warning and four independent localized FAQs', () => {
  assert.equal(homepage.copy['zh-TW'].notice.windowPosition, 'Line 桌面 App 視窗位置請勿超過螢幕左側或右側邊緣，否則將造成 Sweety 辨識失敗');
  assert.equal(homepage.copy['zh-TW'].faq.items.length, 4);
  assert.equal(homepage.copy.en.faq.items.length, 4);
  assert.equal((html.match(/<details\b/g) ?? []).length, 4);
  assert.equal((html.match(/<summary\b/g) ?? []).length, 4);
  assert.doesNotMatch(html, /<details[^>]+\bname=/);
  for (const hook of ['faq.title', 'faq.items.0.question', 'faq.items.0.answer', 'notice.windowPosition']) {
    assert.match(html, new RegExp(`data-copy="${hook.replaceAll('.', '\\.')}`));
  }
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
  assert.match(css, /\.author-card/);
  assert.match(css, /\.author-avatar[^}]*border-radius:\s*50%/s);
});

test('download configuration is centralized and null URLs render disabled controls with platform SVGs', () => {
  assert.deepEqual(homepage.downloadConfig, { windows: null, macos: null });
  assert.equal((html.match(/data-platform="(?:windows|macos)"/g) ?? []).length, 2);
  assert.equal((html.match(/class="platform-icon[^"]*"[^>]*aria-hidden="true"/g) ?? []).length, 3);
  assert.equal((html.match(/class="download-action"[^>]*disabled/g) ?? []).length, 2);
  assert.doesNotMatch(html, /<div class="platform-icon"[^>]*>[●⊞]<\/div>/);
});

test('download section adds a third Git card with a safe new-tab repository link', () => {
  assert.equal((html.match(/class="download-card/g) ?? []).length, 3);
  assert.match(html, /class="download-card git-card"/);
  assert.match(html, /class="platform-icon github"[^>]*aria-hidden="true"/);
  assert.match(html, /href="https:\/\/github\.com\/ericchen1972\/Sweety"[^>]+target="_blank"[^>]+rel="noopener noreferrer"[^>]*>Git<\/a>/);
  assert.match(css, /\.download-grid[^}]*grid-template-columns:\s*repeat\(3,/s);
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

  const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((match) => JSON.parse(match[1]));
  const graph = blocks.flatMap((block) => block['@graph'] ?? [block]);
  for (const type of ['WebSite', 'Organization', 'Person', 'SoftwareApplication', 'FAQPage']) {
    assert.ok(graph.some((node) => node['@type'] === type), `JSON-LD should include ${type}`);
  }
  const app = graph.find((node) => node['@type'] === 'SoftwareApplication');
  assert.equal(app.softwareVersion, '1.0.1');
  assert.equal(app.operatingSystem, 'macOS');
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
  assert.match(html, /images\/home\/quick-start\.png/);
  assert.match(html, /images\/home\/quick-start-create\.png/);
  assert.match(html, /images\/home\/quick-start-panel\.png/);
  assert.match(html, /images\/home\/custom-persona\.png/);
  assert.match(html, /images\/home\/custom-persona-edit\.png/);
  assert.match(html, /images\/home\/custom-persona-apply\.png/);
  assert.match(html, /aria-live="polite"/);
  assert.match(html, /homepage\.js/);
  assert.match(html, /homepage\.css/);
  assert.doesNotMatch(html, /href=["'](?:#|javascript:|)["']/i);
  assert.equal((html.match(/class="download-action"[^>]*disabled/g) ?? []).length, 2);
});

test('homepage stylesheet and module script share an explicit cache-busting version', () => {
  const stylesheetVersion = html.match(/<link[^>]+href="homepage\.css\?v=([^"&]+)"/)?.[1] ?? '';
  const scriptVersion = html.match(/<script[^>]+src="homepage\.js\?v=([^"&]+)"/)?.[1] ?? '';
  assert.ok(stylesheetVersion, 'homepage.css URL should include a non-empty version query');
  assert.equal(scriptVersion, stylesheetVersion, 'homepage.js should use the same version query');
});

test('static HTML is a complete default-English document without JavaScript', () => {
  for (const text of [
    'When facing scams, can we only defend ourselves passively?',
    'Many people share this question. Beyond public awareness campaigns, repeated again and again,',
    'Now, users can run Sweety on an idle computer',
    'A scammer’s greatest cost: time',
    'You do not need to spend any of your own time on scammers.',
    'When you wake up, the conversation between the other person and AI may put you in a good mood for the rest of the day.',
    'Create a contact in the scammer list and enter their LINE name',
    'Apply the custom persona to a monitored contact',
    'Accessibility',
    'Screen &amp; System Audio Recording',
    'Automation',
  ]) assert.match(html, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  const quickList = html.match(/data-list="quick\.steps"[^>]*>([\s\S]*?)<\/ol>/)?.[1] ?? '';
  const advancedList = html.match(/data-list="advanced\.steps"[^>]*>([\s\S]*?)<\/ol>/)?.[1] ?? '';
  const permissions = html.match(/data-list="notice\.permissions"[^>]*>([\s\S]*?)<\/ul>/)?.[1] ?? '';
  assert.equal((quickList.match(/<li>/g) ?? []).length, 6);
  assert.equal((advancedList.match(/<li>/g) ?? []).length, 4);
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
  const assets = [
    ['images/logo.png', 373, 373, false],
    ['images/home/hero-helpless.png', 1672, 941, false],
    ['images/home/time-clock-blue.png', 1672, 941, false],
    ['images/home/quick-start.png', 1498, 777, true],
    ['images/home/quick-start-create.png', 1498, 777, true],
    ['images/home/quick-start-panel.png', 420, 528, true],
    ['images/home/custom-persona.png', 1425, 891, true],
    ['images/home/custom-persona-edit.png', 1498, 777, true],
    ['images/home/custom-persona-apply.png', 1498, 777, true],
  ];
  for (const [path, width, height, lazy] of assets) {
    const png = await readFile(new URL(path, webRoot));
    assert.equal(png.toString('hex', 0, 8), '89504e470d0a1a0a');
    assert.equal(png.readUInt32BE(16), width);
    assert.equal(png.readUInt32BE(20), height);
    const escaped = path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const tag = html.match(new RegExp(`<img[^>]+src="${escaped}"[^>]*>`))?.[0] ?? '';
    assert.match(tag, new RegExp(`width="${width}"`));
    assert.match(tag, new RegExp(`height="${height}"`));
    assert.match(tag, /decoding="async"/);
    if (lazy) assert.match(tag, /loading="lazy"/);
    const webpPath = path.replace(/\.png$/, '.webp');
    const webp = await readFile(new URL(webpPath, webRoot)).catch(() => null);
    assert.ok(webp, `${webpPath} should exist`);
    assert.ok(webp.byteLength < png.byteLength, `${webpPath} should be smaller than PNG`);
    assert.match(html, new RegExp(`<source[^>]+srcset="${webpPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"[^>]+type="image/webp"`));
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

test('homepage deployment manifest includes public pages, discovery files, and social assets', () => {
  const manifest = deployHelper.match(/\$files\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
  for (const file of ['images/logo.webp', 'images/logo.png', 'images/eric.png', 'images/sweety-social-1200x630.png', 'about_sweety.html', 'robots.txt', 'sitemap.xml', 'llms.txt']) {
    assert.match(manifest, new RegExp(`['"]${file.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}['"]`));
  }
});

test('navigation observer targets only sections represented by header links', () => {
  assert.match(javascript, /const sections = links\s*\.map\(\(link\) => document\.querySelector\(link\.hash\)\)\s*\.filter\(Boolean\)/);
  assert.doesNotMatch(javascript, /querySelectorAll\(['"]main section\[id\]['"]\)/);
});
