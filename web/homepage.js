export function resolveLocale(locales, fallbackLocale) {
  const locale = Array.isArray(locales) && locales.length ? locales[0] : (typeof locales === 'string' ? locales : fallbackLocale);
  if (typeof locale !== 'string') return 'en';
  const normalized = locale.toLowerCase();
  return normalized === 'zh-tw' || normalized === 'zh-hk' || normalized === 'zh-mo' || normalized === 'zh-hant' || normalized.startsWith('zh-hant-')
    ? 'zh-TW'
    : 'en';
}

export const downloadConfig = Object.freeze({ windows: null, macos: null });

export function splitWholeHours(totalHours) {
  const value = Number.isInteger(totalHours) && totalHours >= 0 ? totalHours : 0;
  return { days: Math.floor(value / 24), hours: value % 24 };
}

export async function fetchAggregate(fetchImpl = globalThis.fetch) {
  try {
    const response = await fetchImpl('/sweety-metrics.php', { headers: { Accept: 'application/json' } });
    if (!response?.ok) return null;
    const data = await response.json();
    const validDays = Number.isSafeInteger(data?.totalDays) && data.totalDays >= 0;
    const validHours = Number.isInteger(data?.totalHours) && data.totalHours >= 0 && data.totalHours <= 23;
    return validDays && validHours ? { days: data.totalDays, hours: data.totalHours } : null;
  } catch {
    return null;
  }
}

export function createAggregateLoader(fetchImpl = globalThis.fetch, timeoutMs = 10_000) {
  let inFlight = null;
  let generation = 0;
  return {
    async load() {
      if (inFlight) return null;
      const requestGeneration = ++generation;
      const request = fetchAggregate(fetchImpl);
      inFlight = { generation: requestGeneration, request };
      request.finally(() => {
        if (inFlight?.generation === requestGeneration) inFlight = null;
      });
      let timeoutId;
      const timeout = new Promise((resolve) => {
        timeoutId = setTimeout(() => {
          if (inFlight?.generation === requestGeneration) inFlight = null;
          resolve(null);
        }, timeoutMs);
      });
      const result = await Promise.race([request, timeout]);
      clearTimeout(timeoutId);
      return result;
    },
  };
}

export const copy = {
  'zh-TW': {
    meta: { title: 'Sweety｜主動反詐' },
    skipLink: '跳至主要內容',
    brandLabel: 'Sweety 首頁',
    nav: { label: '主要導覽', antiScam: '主動反詐', download: '下載', instructions: '使用說明' },
    hero: {
      title: '面對詐騙，我們永遠只能被動的防禦嗎？',
      subtitle: '讓 AI 成為我們的武器',
      body: '相信很多人都有這種疑問，我們的政府除了宣導、宣導、再宣導外，\n對於跨境詐騙，可以說是',
      emphasis: '束手無策',
      closing: '現在，用戶只要在閒置的電腦上運作 Sweety，\n就可以進行「主動反詐」',
      artAlt: '一個人坐在電腦前感到束手無策的藍色水彩插畫',
    },
    time: {
      title: '詐騙最大的成本～時間',
      subtitle: '上帝是公平的、詐騙同樣只有24小時',
      body: '您不用「花費任何時間」在詐騙身上，您只需設定好 Line 對象，睡覺前開啟 Sweety 即可，唯一要付出的微末成本，電腦及螢幕不要關，不要進入休眠，不要進入螢幕保護。',
      close: '當您起床後，相信對方與 AI 之間的對話，會給您帶來一整天的好心情～',
      artAlt: '藍色水彩時鐘',
    },
    counter: { intro: '目前 Sweety 已經消耗了詐騙總計', days: '天', hours: '小時' },
    download: { title: '下載 Sweety', windows: 'Windows', macOS: 'macOS', soon: '即將推出', actions: { windows: '下載 Windows 版', macos: '下載 macOS 版' } },
    instructions: {
      title: '使用說明',
      intro: 'Sweety 使用你閒置的電腦並操作 Line 桌面 App ，透過人物設定，讓 AI 不斷消耗詐騙的時間，請注意 - AI 不會主動與詐騙聯繫，只會被動回覆，你可以透過修改人設，讓 AI 發揮更大的拖延效果。',
      quote: '「你拖延對方越多的時間、代表他們要付出更多的時間與人力成本、而你挽救了更多人免於被騙。」',
    },
    quick: {
      title: '快速上手',
      imageAlt: 'Sweety 操作面板快速上手畫面',
      imageCaption: 'Sweety 操作面板',
      createImageAlt: 'Sweety 新增對象與選擇人設畫面',
      createImageCaption: '新增對象與選擇人設',
      panelImageAlt: 'Sweety 已停止狀態與開始按鈕',
      panelImageCaption: '已停止時的開始控制',
      steps: ['在騙子列表內建立對象，輸入對方的 Line 名稱', '選擇要使用的人設（建議選擇與您自身類似的人設）', '勾選要回覆的對象', '在面板上案開始', '如果你想親自接手交談，可隨時按停止', '睡覺去'],
    },
    advanced: {
      title: '進階設定',
      intro: '如果您覺得預設人物不夠精準，您可以自訂人設，或者用基礎人設做延伸',
      imageAlt: 'Sweety 自訂人設設定畫面',
      imageCaption: '增加到自訂人設',
      editImageAlt: 'Sweety 建立自訂人設的編輯畫面',
      editImageCaption: '建立或編輯自訂人設',
      applyImageAlt: 'Sweety 將人設套用到監控對象的畫面',
      applyImageCaption: '在監控對象上選擇人設',
      steps: ['選擇基礎人設', '點擊「增加到自訂人設」', '進入自訂人設修改', '在監控對象上套用自訂人設'],
    },
    notice: {
      title: '注意事項',
      intro: 'Mac OS 系統下，需賦予 Sweety 三種權限，分別是',
      permissions: ['輔助使用', '螢幕與系統錄音', '自動化'],
      windowPosition: 'Line 桌面 App 視窗位置請勿超過螢幕左側或右側邊緣，否則將造成 Sweety 辨識失敗',
    },
    faq: {
      title: '常見問題',
      items: [
        { question: '如果對方開始懷疑是 AI 在搞他時該怎麼辦？', answer: '可先按停止鍵，由自己接手，待情況穩定後再繼續。' },
        { question: '我可以一次設定多個對象嗎？', answer: '可以，但不要超過 Line 主視窗，聯絡人列表的可視範圍。' },
        { question: 'Sweety 可用來回覆非詐騙對象嗎？', answer: '可以，但不建議。' },
        { question: '為什麼叫 Sweety？', answer: '被詐騙的人太苦了，吃顆糖吧。' },
      ],
    },
    author: {
      eyebrow: '作者',
      title: 'Eric / 網站 / AI 工程師',
      experience: '20 年開發經驗',
      projectsTitle: '目前開發項目',
      projects: { slimweb: 'AI First 電商系統 SlimWeb', kingjoo: 'AI 主動行銷工具 KingJoo', sweety: '主動式反詐騙 App Sweety' },
      invitation: '任何程式開發、電商都歡迎與作者接洽。',
    },
    footer: 'Sweety',
  },
  en: {
    meta: { title: 'Sweety | Proactive anti-scam' },
    skipLink: 'Skip to main content',
    brandLabel: 'Sweety home',
    nav: { label: 'Primary navigation', antiScam: 'Anti-scam', download: 'Download', instructions: 'Instructions' },
    hero: {
      title: 'When facing scams, can we only defend ourselves passively?',
      subtitle: 'Let AI become our tool',
      body: 'Many people share this question. Beyond public awareness campaigns, repeated again and again,\nour government can be',
      emphasis: 'powerless',
      closing: 'Now, users can run Sweety on an idle computer\nto take part in “proactive anti-scam” work.',
      artAlt: 'Blue watercolor illustration of a person feeling helpless at a computer',
    },
    time: {
      title: 'A scammer’s greatest cost: time',
      subtitle: 'Time treats everyone equally—scammers also have only 24 hours a day',
      body: 'You do not need to spend any of your own time on scammers. Set the LINE contact, start Sweety before bed, and the only small cost is leaving the computer and display on, without sleep mode or a screen saver.',
      close: 'When you wake up, the conversation between the other person and AI may put you in a good mood for the rest of the day.',
      artAlt: 'Blue watercolor clock',
    },
    counter: { intro: 'So far, Sweety has consumed a total of', days: 'days', hours: 'hours' },
    download: { title: 'Download Sweety', windows: 'Windows', macOS: 'macOS', soon: 'Coming soon', actions: { windows: 'Download for Windows', macos: 'Download for macOS' } },
    instructions: {
      title: 'Instructions',
      intro: 'Sweety uses an idle computer to operate the LINE desktop app. Through a selected persona, AI keeps consuming a scammer’s time. Please note: AI never contacts scammers first and only replies passively. Editing the persona can make the delay more effective.',
      quote: '“The more of their time you delay, the more time and labor they must spend—and the more people you help protect from being scammed.”',
    },
    quick: {
      title: 'Quick start',
      imageAlt: 'Sweety dashboard quick-start screen',
      imageCaption: 'Sweety dashboard',
      createImageAlt: 'Sweety add-target and persona-selection screen',
      createImageCaption: 'Add a target and choose a persona',
      panelImageAlt: 'Sweety stopped state and Start button',
      panelImageCaption: 'Start control while stopped',
      steps: ['Create a contact in the scammer list and enter their LINE name', 'Choose a persona to use (we recommend one similar to yourself)', 'Select the contacts Sweety should reply to', 'Press Start on the dashboard', 'If you want to take over the conversation yourself, press Stop at any time', 'Go to sleep'],
    },
    advanced: {
      title: 'Advanced settings',
      intro: 'If the default personas are not precise enough, you can create your own or extend a base persona.',
      imageAlt: 'Sweety custom persona settings screen',
      imageCaption: 'Add to custom personas',
      editImageAlt: 'Sweety custom persona editor screen',
      editImageCaption: 'Create or edit a custom persona',
      applyImageAlt: 'Sweety monitored-target persona assignment screen',
      applyImageCaption: 'Choose a persona for a monitored target',
      steps: ['Choose a base persona', 'Click “Add to custom personas”', 'Open the custom persona and edit it', 'Apply the custom persona to a monitored contact'],
    },
    notice: {
      title: 'Important notes',
      intro: 'On macOS, Sweety requires three permissions:',
      permissions: ['Accessibility', 'Screen & System Audio Recording', 'Automation'],
      windowPosition: 'Keep the LINE desktop app window fully within the left and right edges of the display, or Sweety may fail to recognize it.',
    },
    faq: {
      title: 'Frequently asked questions',
      items: [
        { question: 'What should I do if the other person suspects AI is responding?', answer: 'Press Stop and take over the conversation yourself. Continue with Sweety after the situation settles.' },
        { question: 'Can I configure multiple targets at once?', answer: 'Yes, but keep them within the visible range of the contact list in the main LINE window.' },
        { question: 'Can Sweety reply to people who are not scammers?', answer: 'Yes, but it is not recommended.' },
        { question: 'Why is it called Sweety?', answer: 'Being scammed is bitter enough. Have a piece of candy.' },
      ],
    },
    author: {
      eyebrow: 'Author',
      title: 'Eric / Web / AI Engineer',
      experience: '20 years of development experience',
      projectsTitle: 'Current projects',
      projects: { slimweb: 'AI First ecommerce system SlimWeb', kingjoo: 'AI proactive marketing tool KingJoo', sweety: 'Proactive anti-scam app Sweety' },
      invitation: 'For software development or ecommerce work, you are welcome to contact the author.',
    },
    footer: 'Sweety',
  },
};

export function getLocalePresentation(locales, fallbackLocale) {
  const locale = resolveLocale(locales, fallbackLocale);
  return { locale, lang: locale, title: copy[locale].meta.title };
}

export function formatCounterText(locale, days, hours) {
  const strings = copy[locale]?.counter ?? copy.en.counter;
  return `${strings.intro} ${days} ${strings.days} ${hours} ${strings.hours}`;
}

export function hasAggregateChanged(current, next) {
  return current.days !== next.days || current.hours !== next.hours;
}

export function toFlipDigits(total) {
  return {
    days: Array.from(String(total.days).padStart(4, '0')),
    hours: Array.from(String(total.hours).padStart(2, '0')),
  };
}

export function changedDigitIndexes(previous, next) {
  const length = Math.max(previous.length, next.length);
  return Array.from({ length }, (_, index) => index).filter((index) => previous[index] !== next[index]);
}

export function sanitizeDownloadUrl(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const candidate = value.trim();
  if (candidate.startsWith('//') || candidate.includes('\\')) return null;
  if (!/^[a-z][a-z\d+.-]*:/i.test(candidate)) {
    try {
      const parsed = new URL(candidate, 'https://sweety.invalid/');
      return parsed.origin === 'https://sweety.invalid' ? candidate : null;
    } catch {
      return null;
    }
  }
  try {
    const parsed = new URL(candidate);
    return parsed.protocol === 'https:' ? parsed.href : null;
  } catch {
    return null;
  }
}

export function getDownloadDecision(platform, locale, config = downloadConfig) {
  const href = sanitizeDownloadUrl(config?.[platform]);
  const strings = copy[locale] ?? copy.en;
  return href
    ? { enabled: true, href, label: strings.download.actions[platform] }
    : { enabled: false, href: null, label: strings.download.soon };
}

function valueAt(source, path) {
  return path.split('.').reduce((value, key) => value?.[key], source);
}

function renderList(element, items) {
  if (!element) return;
  element.replaceChildren(...items.map((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    return li;
  }));
}

function renderDownloads(strings) {
  document.querySelectorAll('[data-platform]').forEach((card) => {
    const platform = card.dataset.platform;
    const action = card.querySelector('.download-action');
    const locale = strings === copy['zh-TW'] ? 'zh-TW' : 'en';
    const decision = getDownloadDecision(platform, locale);
    if (!action || !decision.enabled) return;
    const link = document.createElement('a');
    link.className = 'download-action is-enabled';
    link.href = decision.href;
    link.rel = 'noopener';
    link.textContent = decision.label;
    action.replaceWith(link);
  });
}

function digitFace(className, value) {
  const face = document.createElement('span');
  face.className = className;
  face.textContent = value;
  return face;
}

function createFlipDigit(value) {
  const digit = document.createElement('span');
  digit.className = 'flip-digit';
  digit.dataset.value = value;
  digit.append(digitFace('flip-face top', value), digitFace('flip-face bottom', value));
  return digit;
}

function renderFlipDigits(container, digits) {
  if (!container) return;
  container.replaceChildren(...digits.map(createFlipDigit));
}

function flipDigit(element, nextValue, reduceMotion) {
  if (!element || element.dataset.value === nextValue) return Promise.resolve();
  const previousValue = element.dataset.value ?? '0';
  element.dataset.value = nextValue;
  element.querySelectorAll('.flip-face').forEach((face) => { face.textContent = nextValue; });
  if (reduceMotion) return Promise.resolve();
  const oldLeaf = digitFace('flip-leaf flip-leaf-old', previousValue);
  const newLeaf = digitFace('flip-leaf flip-leaf-new', nextValue);
  element.append(oldLeaf, newLeaf);
  element.classList.add('is-flipping');
  return new Promise((resolve) => {
    window.setTimeout(() => {
      oldLeaf.remove();
      newLeaf.remove();
      element.classList.remove('is-flipping');
      resolve();
    }, 620);
  });
}

function updateFlipGroup(container, previous, next, reduceMotion) {
  if (!container) return Promise.resolve();
  if (previous.length !== next.length || container.children.length !== next.length) {
    renderFlipDigits(container, next);
    return Promise.resolve();
  }
  return Promise.all(changedDigitIndexes(previous, next).map((index) => flipDigit(container.children[index], next[index], reduceMotion)));
}

function initializePage() {
  const presentation = getLocalePresentation(navigator.languages, navigator.language);
  const locale = presentation.locale;
  const strings = copy[locale];
  document.documentElement.lang = presentation.lang;
  document.title = presentation.title;

  document.querySelectorAll('[data-copy]').forEach((element) => {
    const value = valueAt(strings, element.dataset.copy);
    if (typeof value === 'string') element.textContent = value;
  });
  document.querySelectorAll('[data-alt]').forEach((element) => {
    const value = valueAt(strings, element.dataset.alt);
    if (typeof value === 'string') element.setAttribute('alt', value);
  });
  document.querySelectorAll('[data-aria-label]').forEach((element) => {
    const value = valueAt(strings, element.dataset.ariaLabel);
    if (typeof value === 'string') element.setAttribute('aria-label', value);
  });
  renderList(document.querySelector('[data-list="quick.steps"]'), strings.quick.steps);
  renderList(document.querySelector('[data-list="advanced.steps"]'), strings.advanced.steps);
  renderList(document.querySelector('[data-list="notice.permissions"]'), strings.notice.permissions);
  renderDownloads(strings);

  const dayValue = document.querySelector('[data-flip-digits="days"]');
  const hourValue = document.querySelector('[data-flip-digits="hours"]');
  const liveValue = document.querySelector('[data-counter-live]');
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let current = { days: 0, hours: 0 };
  const initialDigits = toFlipDigits(current);
  renderFlipDigits(dayValue, initialDigits.days);
  renderFlipDigits(hourValue, initialDigits.hours);
  if (liveValue) liveValue.textContent = formatCounterText(locale, current.days, current.hours);
  const aggregateLoader = createAggregateLoader();
  const refresh = async () => {
    const next = await aggregateLoader.load();
    if (!next || !hasAggregateChanged(current, next)) return;
    const previousDigits = toFlipDigits(current);
    const nextDigits = toFlipDigits(next);
    await Promise.all([
      updateFlipGroup(dayValue, previousDigits.days, nextDigits.days, reduceMotion),
      updateFlipGroup(hourValue, previousDigits.hours, nextDigits.hours, reduceMotion),
    ]);
    current = next;
    if (liveValue) liveValue.textContent = formatCounterText(locale, next.days, next.hours);
  };
  refresh();
  window.setInterval(refresh, 300_000);

  const links = [...document.querySelectorAll('.site-nav a')];
  const sections = links
    .map((link) => document.querySelector(link.hash))
    .filter(Boolean);
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      links.forEach((link) => {
        const active = link.hash === `#${visible.target.id}`;
        link.classList.toggle('is-active', active);
        if (active) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    }, { rootMargin: '-20% 0px -65%', threshold: [0, 0.2, 0.6] });
    sections.forEach((section) => observer.observe(section));
  }
}

if (typeof document !== 'undefined' && typeof window !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializePage, { once: true });
  else initializePage();
}
