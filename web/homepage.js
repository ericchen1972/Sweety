export function resolveLocale(locales, fallbackLocale) {
  const locale = Array.isArray(locales) && locales.length ? locales[0] : (typeof locales === 'string' ? locales : fallbackLocale);
  if (typeof locale !== 'string') return 'en';
  const normalized = locale.toLowerCase();
  return normalized === 'zh-tw' || normalized === 'zh-hk' || normalized === 'zh-mo' || normalized === 'zh-hant' || normalized.startsWith('zh-hant-')
    ? 'zh-TW'
    : 'en';
}

export const downloadConfig = Object.freeze({
  windows: 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.1-e255e85d',
  macos: 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-28e69419',
});

export function parseDownloadTotal(payload) {
  return Number.isSafeInteger(payload?.totalDownloads) && payload.totalDownloads >= 0
    ? payload.totalDownloads
    : null;
}

export async function fetchDownloadTotal(fetchImpl = globalThis.fetch) {
  try {
    const response = await fetchImpl('/sweety-downloads.php', {
      headers: { Accept: 'application/json' },
    });
    return response?.ok ? parseDownloadTotal(await response.json()) : null;
  } catch {
    return null;
  }
}

export async function recordDownload(fetchImpl = globalThis.fetch) {
  try {
    const response = await fetchImpl('/sweety-downloads.php', {
      method: 'POST',
      headers: { Accept: 'application/json' },
      keepalive: true,
    });
    return response?.ok ? parseDownloadTotal(await response.json()) : null;
  } catch {
    return null;
  }
}

export function formatDownloadCount(locale, total) {
  const value = Number.isSafeInteger(total) && total >= 0 ? String(total) : '—';
  return locale === 'zh-TW' ? `已下載 ${value} 次` : `Downloaded ${value} times`;
}

export function attachDownloadTracking(link, onCount, fetchImpl = globalThis.fetch) {
  link.addEventListener('click', () => {
    void recordDownload(fetchImpl).then((total) => {
      if (total !== null) onCount(total);
    });
  });
}

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
      body: '你覺得詐騙噁心嗎？\n除了刪除封鎖，視而不見外，現在～你有另一種選擇\n使用 Sweety 作為',
      emphasis: '詐騙殺蟲劑',
      closing: '只要在閒置的電腦上運作 Sweety，就可以開始殺蟲',
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
    download: { title: '下載 Sweety', windows: 'Windows', macOS: 'macOS', soon: '稍後提供', actions: { windows: '下載 Windows 版', macos: '下載 macOS 版' } },
    instructions: {
      title: '使用說明',
      intro: 'Sweety 使用你閒置的電腦並操作 Line 桌面 App ，透過人物設定，讓 AI 不斷消耗詐騙的時間，請注意 - AI 不會主動與詐騙聯繫，只會被動回覆，你可以透過修改人設，讓 AI 發揮更大的拖延效果。',
      quote: '「你拖延對方越多的時間、代表他們要付出更多的時間與人力成本、而你挽救了更多人免於被騙。」',
      openSourceNote: '＊Sweety 是一款完全免費且開源的程式，如果您對以編譯完成的執行檔有安全疑慮，歡迎透過 Git 重新編譯',
      guide: {
        controlPanel: {
          title: '控制面板',
          body: '執行 Sweety 前請先開啟 LINE 主視窗，點擊開啟管理介面編輯要回覆的對象，點擊開始後 Sweety 將會針對 LINE 聯絡人視窗進行辨識，當監控對象發送訊息來時 Sweety 將自動點開對話匡並交由 AI 進行回覆。',
          imageAlt: 'Sweety 控制面板，包含開始、開啟管理介面與結束 App 按鈕',
        },
        dashboard: {
          title: '儀表板',
          body: '儀表板顯示對象人數、總花費時間、總來回次數與已結束數量，下方可查看最近對象與各自的來回次數，右上角則顯示目前執行狀態及已勾選對象數。',
          imageAlt: 'Sweety 儀表板，顯示統計數字、最近對象與執行狀態',
        },
        basicSettings: {
          title: '基本設定',
          body: '在 AI 設定選擇 Sweety 預設或 OpenAI；若選擇 OpenAI，請輸入 API Key 並指定模型。對話設定可調整檢查新訊息的間隔，以及開啟視窗後等待多久才送出回覆，完成後點擊儲存設定。',
          imageAlt: 'Sweety 基本設定，包含 AI 選擇、檢查間隔與回覆等待時間',
        },
        targetList: {
          title: '騙子列表',
          body: '在騙子列表新增或管理監控對象。只有勾選「回覆」的對象會由 Sweety 監控與回覆；你也可以編輯、結束或匯出個別對象的對話。LINE 名稱請輸入聯絡人畫面顯示的完整名稱。',
          imageAlt: 'Sweety 騙子列表，顯示監控勾選、對象、人設與操作按鈕',
        },
        basePersonas: {
          title: '基礎人設',
          body: '在人設編輯的「基礎人設」頁面，可依年齡與性別篩選預設人設。先閱讀卡片摘要，再點擊顯示全文查看完整設定；若希望修改內容，可將基礎人設增加到自訂人設。',
          imageAlt: 'Sweety 基礎人設頁面，顯示年齡、性別篩選與人設卡片',
        },
        personaDetails: {
          title: '人設詳細內容',
          body: '點擊「顯示全文」可查看人設的完整人物資料、說話方式、個性與常用語。確認內容適合後，可直接點擊「增加到自訂人設」，再依需求調整。',
          imageAlt: 'Sweety 人設詳情視窗，顯示完整人物資料與增加到自訂人設按鈕',
        },
        customPersonas: {
          title: '自訂人設',
          body: '在「自訂人設」頁面建立或管理自己的角色設定。你可以從空白建立人設，也可以從基礎人設複製後修改；完成的人設可套用到騙子列表中的監控對象。',
          imageAlt: 'Sweety 自訂人設頁面，包含建立人設按鈕',
        },
      },
      triggerNotice: 'Sweety 不會主動傳送訊息給對方，只有當對方傳訊息來時才會進行回覆，也就是視窗內必須有來自監控對象的未讀訊息才會觸發 Sweety',
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
        {
          question: '為什麼按下開始後顯示「需要 Mac 權限」？',
          answerPrefix: '因為程式更新後可能被系統判斷為新的程式，所以請到偏好設定的',
          answerEmphasis: '「輔助使用」及「螢幕與系統錄音」內，移除 Sweety 後再重新加入。',
        },
      ],
    },
    author: {
      eyebrow: '作者',
      title: 'Eric / 網站 / AI 工程師',
      experience: '20 年開發經驗',
      projectsTitle: '目前開發項目',
      projects: { slimweb: 'AI First 電商系統 SlimWeb', kingjoo: 'AI 主動行銷工具 KingJoo', sweety: '主動式反詐騙 App Sweety' },
      invitation: '任何程式開發、電商都歡迎與作者接洽。',
      threads: { prefix: '如想得到更多AI開發應用訊息，請追蹤我的', label: 'Threads' },
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
      openSourceNote: '* Sweety is completely free and open source. If you have safety concerns about the precompiled executable, you are welcome to rebuild it from Git.',
      guide: {
        controlPanel: {
          title: 'Control panel',
          body: 'Before running Sweety, open the main LINE window. Select Open management interface to edit the contacts to reply to. After you select Start, Sweety scans the LINE contact window. When a monitored contact sends a message, Sweety opens that conversation and asks AI to reply.',
          imageAlt: 'Sweety control panel with Start, Open management interface, and Quit App buttons',
        },
        dashboard: {
          title: 'Dashboard',
          body: 'The dashboard shows the number of contacts, total time consumed, total exchanges, and completed conversations. Recent contacts and their exchange counts appear below, while the top right shows the current status and number of selected contacts.',
          imageAlt: 'Sweety dashboard showing totals, recent contacts, and monitoring status',
        },
        basicSettings: {
          title: 'Basic settings',
          body: 'Choose Sweety default or OpenAI under AI settings. When using OpenAI, enter an API key and choose a model. Conversation settings control how often Sweety checks for new messages and how long it waits after opening a chat before sending a reply. Select Save settings when finished.',
          imageAlt: 'Sweety basic settings for AI provider, scan interval, and reply delay',
        },
        targetList: {
          title: 'Scammer list',
          body: 'Add and manage monitored contacts in the scammer list. Sweety monitors and replies only to contacts whose Reply checkbox is selected. You can also edit, end, or export an individual conversation. Enter the full LINE name exactly as it appears in the contact list.',
          imageAlt: 'Sweety scammer list with reply checkboxes, contacts, personas, and actions',
        },
        basePersonas: {
          title: 'Base personas',
          body: 'On the Base personas tab, filter built-in personas by age and gender. Read the card summary, then select Show full text to review the complete persona. To customize it, add the base persona to Custom personas.',
          imageAlt: 'Sweety base personas with age and gender filters and persona cards',
        },
        personaDetails: {
          title: 'Persona details',
          body: 'Select Show full text to review the persona’s full background, speaking style, personality, and common phrases. If it fits your needs, select Add to custom personas and adjust it further.',
          imageAlt: 'Sweety persona details dialog with full profile and Add to custom personas button',
        },
        customPersonas: {
          title: 'Custom personas',
          body: 'Create and manage your own character settings on the Custom personas tab. Start from a blank persona or copy and edit a base persona. You can then apply the completed persona to a monitored contact in the scammer list.',
          imageAlt: 'Sweety custom personas tab with a Create persona button',
        },
      },
      triggerNotice: 'Sweety never initiates messages. It replies only after the other person sends a message, which means the chat window must contain an unread message from a monitored contact before Sweety is triggered.',
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
        {
          question: 'Why does Sweety show “macOS permissions required” after I press Start?',
          answerPrefix: 'After an update, macOS may treat Sweety as a new app. In System Settings, ',
          answerEmphasis: 'remove Sweety from Accessibility and Screen & System Audio Recording, then add it again.',
        },
      ],
    },
    author: {
      eyebrow: 'Author',
      title: 'Eric / Web / AI Engineer',
      experience: '20 years of development experience',
      projectsTitle: 'Current projects',
      projects: { slimweb: 'AI First ecommerce system SlimWeb', kingjoo: 'AI proactive marketing tool KingJoo', sweety: 'Proactive anti-scam app Sweety' },
      invitation: 'For software development or ecommerce work, you are welcome to contact the author.',
      threads: { prefix: 'For more AI development and application updates, follow me on', label: 'Threads' },
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

function renderDownloads(strings, onPlatformLink = () => {}) {
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
    onPlatformLink(link);
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
  renderList(document.querySelector('[data-list="notice.permissions"]'), strings.notice.permissions);
  const downloadCount = document.querySelector('[data-download-count]');
  const renderDownloadTotal = (total) => {
    if (downloadCount) downloadCount.textContent = formatDownloadCount(locale, total);
  };
  renderDownloadTotal(null);
  renderDownloads(strings, (link) => {
    attachDownloadTracking(link, renderDownloadTotal);
  });
  void fetchDownloadTotal().then((total) => {
    if (total !== null) renderDownloadTotal(total);
  });

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
