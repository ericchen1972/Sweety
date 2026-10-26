export function resolveLocale(locales, fallbackLocale) {
  const locale = Array.isArray(locales) && locales.length ? locales[0] : (typeof locales === 'string' ? locales : fallbackLocale);
  if (typeof locale !== 'string') return 'en';
  const normalized = locale.toLowerCase();
  if (normalized === 'zh-tw' || normalized === 'zh-hk' || normalized === 'zh-mo' || normalized === 'zh-hant' || normalized.startsWith('zh-hant-')) return 'zh-TW';
  if (normalized === 'ja' || normalized.startsWith('ja-')) return 'ja';
  return 'en';
}

export const downloadConfig = Object.freeze({
  windows: 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.2-d1f2664b',
  macos: 'https://sweety.tw/downloads/Sweety-macos12.7-arm64-latest.dmg?release=2.0.2-20261026',
  macosIntel: 'https://sweety.tw/downloads/Sweety-macos12.7-x86_64-latest.dmg?release=2.0.2-20261026',
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
  if (locale === 'zh-TW') return `已下載 ${value} 次`;
  if (locale === 'ja') return `ダウンロード数：${value}回`;
  return `Downloaded ${value} times`;
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
    meta: {
      title: 'Sweety｜主動反詐',
      description: 'Sweety 是完全開源的主動式反詐騙 App，透過 AI 回覆可疑對象、消耗詐騙者的時間，讓每個人都能參與反詐。',
      socialTitle: 'Sweety 主動反詐',
      socialDescription: '讓 AI 成為我們的武器，主動消耗詐騙者的時間。',
      ogLocale: 'zh_TW',
    },
    skipLink: '跳至主要內容',
    brandLabel: 'Sweety 首頁',
    nav: { label: '主要導覽', antiScam: '主動反詐', download: '下載', instructions: "Sweety 2.0 使用說明" },
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
      body: "設定 LINE 對象並開啟 Sweety，讓 AI 代為回覆。請讓電腦保持開機、網路連線與非休眠狀態；不必保持螢幕亮著或開啟 LINE 桌面視窗。",
      close: '當您起床後，相信對方與 AI 之間的對話，會給您帶來一整天的好心情～',
      artAlt: '藍色水彩時鐘',
    },
    counter: { intro: '目前 Sweety 已經消耗了詐騙總計', days: '天', hours: '小時' },
    download: { title: '下載 Sweety', windows: 'Windows', macOS: 'macOS 12.7+', soon: '稍後提供', actions: { windows: '下載 Windows 版', macos: '下載 Apple Silicon 版', macosIntel: '下載 Intel 版' } },
    instructions: {
      title: "Sweety 2.0 使用說明",
      intro: "Sweety 2.0 使用 OKLine 登入 LINE，直接接收訊息並依您選擇的人設被動回覆。先設定 AI Key、登入 LINE，再選取監控對象；AI 不會主動聯絡任何人。",
      quote: '「你拖延對方越多的時間、代表他們要付出更多的時間與人力成本、而你挽救了更多人免於被騙。」',
      openSourceNote: '＊Sweety 是一款完全免費且開源的程式，如果您對以編譯完成的執行檔有安全疑慮，歡迎透過 Git 重新編譯',
      perspective: {
        title: 'ChatGPT 對 Sweety 的觀點',
        source: '以下內容是 ChatGPT 在與作者討論 Sweety 時，對此專案提出的觀點。',
        summary: 'Sweety 不只是消耗詐騙者的時間，而是在污染「聊得下去＝值得繼續騙」的篩選訊號。',
        core: '「我們不是讓詐騙訊息消失，而是讓詐騙者無法判斷誰值得繼續騙。」',
        conclusion: '「能聊下去，什麼也不代表。」',
        expandLabel: '閱讀完整觀點',
        collapseLabel: '收合完整觀點',
        full: {
          opening: '我覺得你這個核心論點其實比「AI 反詐」四個字有意思很多。',
          difference: '因為你不是在做另一個「辨識詐騙 → 跳警告 → 請封鎖」的工具，你是在改變詐騙端的篩選成本。',
          processLead: '現在典型流程其實很殘酷地有效率：',
          process: '廣撒 10,000 人 → 9,900 人封鎖 → 剩下 100 個願意回話 → 集中火力攻那 100 個。',
          classifier: '所以「全民提高警覺、遇到就封鎖」對個體當然是正確的，但從攻擊者角度看，它同時也是一個非常有效的免費 classifier。大家等於主動幫他們把低價值名單剔掉了。',
          alternativeLead: 'Sweety 想做的事情反而是：',
          alternative: '廣撒 10,000 人 → 裡面突然有一堆 AI 陪你聊三天 →「聊得下去」不再等於「有機會成交」。',
          economicModel: '這是從經濟模型上改變攻防關係。',
          coreImpact: '「我們不是讓詐騙訊息消失，而是讓詐騙者無法判斷誰值得繼續騙。」',
          signalPollution: '這句比「消耗詐騙時間」更接近真正的影響。因為時間成本只是第一層，第二層其實是訊號污染。',
          funnelLead: '假設原本詐騙集團的漏斗：',
          funnelBefore: '10,000 個接觸\n→ 500 個回覆\n→ 100 個長聊\n→ 10 個匯款',
          funnelSignal: '他們會把「長聊」視為超強訊號。',
          funnelAfterLead: '如果 Sweety 類型的工具真的普及，變成：',
          funnelAfter: '10,000 個接觸\n→ 1,500 個回覆\n→ 800 個長聊\n→ 其中 700 個其實是 AI',
          kpiLead: '那他們最痛的地方不只是多聊了 700 個人，而是：',
          kpiFailure: '「長聊」這個 KPI 本身失效了。',
          extraSteps: '接著他們勢必要增加判斷流程，例如真人驗證、語音、視訊、更多前置問題、帳號驗證……每加一層，詐騙成本就上升一層，而且真正受害者也因此多了一些反應時間。',
          honeypot: '這才是這套工具真正有趣的地方：它不是防毒軟體思維，而比較像 spam honeypot、tar pit、蜜罐，只是把它做成一般人也能參與的分散式版本。',
          networkLead: '「大家提供閒置電腦」這點也很有意思，因為它讓故事從：',
          networkBefore: '「我們做了一個反詐 App」',
          networkTransition: '變成：',
          networkAfter: '「我們想建立一個由普通人組成的反詐算力／時間網路。」',
          threeLayersLead: '整個專案最值得放大的，是這三層：',
          layer1: '傳統反詐只保護單一受害者。',
          layer2: 'Sweety 主動增加攻擊者的邊際成本。',
          layer3: '大量假陽性會污染詐騙者的目標篩選機制。',
          thirdValue: '第三點最有價值。',
          diagram: '現在\n\n詐騙訊息\n↓\n封鎖的人 ❌\n封鎖的人 ❌\n封鎖的人 ❌\n願意聊的人 ✅ ← 集中攻擊\n\nSweety\n\n詐騙訊息\n↓\n真人 ❓\nSweety ❓\nSweety ❓\n真人 ❓\nSweety ❓\n\n→ 攻擊者失去有效篩選訊號',
          positioning: '還有一個很重要的定位：不要把目標講成「消滅詐騙」。那個太大，而且很容易被挑戰。',
          roiLead: '可以講成：',
          roiStatement: '降低詐騙產業的 ROI。',
          roiBusiness: '詐騙本質也是生意，粗略簡化就是：',
          roi: 'Profit = 成功詐得金額 − 人力 − 帳號 − 廣告 − 洗錢 − 時間成本',
          antiScam: '大部分反詐都在降低「成功率」。',
          sweetyIncreaseLead: 'Sweety 是直接去增加：',
          sweetyIncrease: '人力成本 + 時間成本 + 錯誤目標成本',
          asymmetry: '而且成本轉嫁到 AI，所以防守方的邊際成本反而很低。',
          aiFit: '這種成本不對稱，才是 AI 最適合做的事。',
          ruleBefore: '「能聊下去，就代表有希望騙到。」',
          ruleAfterLead: 'Sweety 要做的就是把這條規則破壞掉，變成：',
          ruleAfter: '「能聊下去，什麼也不代表。」',
        },
      },
      guide: {
        controlPanel: {
          title: '控制面板',
          body: "按「開啟管理介面」完成 AI 與 LINE 設定，勾選對象，再按「開始」。監控啟動後按鈕變為紅色「停止」，可隨時停止並自行接手；未填所選 AI 的 API Key 時無法開始。",
          imageAlt: 'Sweety 控制面板，包含開始、開啟管理介面與結束 App 按鈕',
        },
        dashboard: {
          title: '儀表板',
          body: '儀表板顯示對象人數、總花費時間、總來回次數與已結束數量，下方可查看最近對象與各自的來回次數，右上角則顯示目前執行狀態及已勾選對象數。',
          imageAlt: 'Sweety 儀表板，顯示統計數字、最近對象與執行狀態',
        },
        basicSettings: {
          title: '基本設定',
          body: "選擇 Agnes 或 OpenAI，填寫該服務的 API Key 與 Model；Agnes 預設 agnes-3.0-flash，下方提供兩家的 Key 申請連結。兩家的 Key 與模型分開保存，切換時不會清除。交談歷史預設 6 筆，可設 4–30 筆；每次直接從 LINE 取得上下文，交談內容不存入本機資料庫，也不提供交談匯出；也可設定回覆送出前的等待時間。完成後按「儲存設定」。",
          imageAlt: "Sweety 2.0 — Agnes API Key, agnes-3.0-flash, conversation history",
        },
        targetList: {
          title: '騙子列表',
          body: "到「騙子列表」按「登入 LINE」，透過 OKLine 產生 QR Code，用手機 LINE 掃描並依提示確認登入或輸入驗證碼。「新增對象」可搜尋個人聯絡人或 LINE 群組，選擇人設後建立並勾選「回覆」。不需手動輸入完整 LINE 名稱，也不受桌面視窗範圍限制。",
          imageAlt: "Sweety 2.0 — LINE connection and monitored targets",
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
      triggerNotice: "Sweety 只回覆監控期間接收的對象訊息。群組訊息須包含基本設定中的用戶名稱，或真正 LINE 標註目前帳號才回覆；多個名稱以逗號分隔，留空時只回覆標註。圖片與貼圖由所選 AI 辨識，請使用支援圖片的模型；動態貼圖目前以靜態預覽辨識。",
    },
    notice: {
      title: '注意事項',
      intro: "2.0 版開始前，請完成以下設定：",
      checklist: ["設定 Agnes／OpenAI API Key", "用手機掃碼登入 LINE", "選取對象並勾選回覆"],
      connection: "請保持 Sweety 執行、電腦連網且不進入休眠。停止監控期間不接收新訊息，重新開始不會集中補回覆。",
    },
    faq: {
      title: '常見問題',
      items: [
        { question: '如果對方開始懷疑是 AI 在搞他時該怎麼辦？', answer: '可先按停止鍵，由自己接手，待情況穩定後再繼續。' },
        { question: '我可以一次設定多個對象嗎？', answer: "可以，從聯絡人或群組清單加入多個對象並勾選回覆，不受 LINE 桌面視窗範圍限制。" },
        { question: 'Sweety 可用來回覆非詐騙對象嗎？', answer: '可以，但不建議。' },
        { question: '為什麼叫 Sweety？', answer: '被詐騙的人太苦了，吃顆糖吧。' },
        {
          question: "為什麼按「開始」後提示輸入 API Key？",
          answerPrefix: "請到基本設定選擇 Agnes 或 OpenAI，輸入目前所選服務的 API Key。",
          answerEmphasis: "按「儲存設定」後，確認 LINE 已登入並勾選至少一個對象，再開始監控。",
        },
        { question: 'Sweety 支援哪些語系？', answer: 'Sweety 介面支援繁中、英文及日文，但是 AI 的回覆將以對方使用的語言為主。' },
        { question: "我是否需要保持電腦版的 LINE 登入？", answer: "不用，你只需在 Sweety 內用 QRCode 登入至 LINE 即可，不需安裝電腦版的 LINE。如有需要，電腦版的 LINE 可同時並存使用。" },
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
    meta: {
      title: 'Sweety | Proactive anti-scam',
      description: 'Sweety is a free and open-source anti-scam app that uses AI to reply to suspicious contacts and consume scammers’ time.',
      socialTitle: 'Sweety | Proactive anti-scam',
      socialDescription: 'Use AI to actively consume scammers’ time.',
      ogLocale: 'en_US',
    },
    skipLink: 'Skip to main content',
    brandLabel: 'Sweety home',
    nav: { label: 'Primary navigation', antiScam: 'Anti-scam', download: 'Download', instructions: "Sweety 2.0 instructions" },
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
      body: "Choose LINE targets and let Sweety handle replies. Keep the computer powered on, online, and awake. The display and LINE desktop window do not need to stay open.",
      close: 'When you wake up, the conversation between the other person and AI may put you in a good mood for the rest of the day.',
      artAlt: 'Blue watercolor clock',
    },
    counter: { intro: 'So far, Sweety has consumed a total of', days: 'days', hours: 'hours' },
    download: { title: 'Download Sweety', windows: 'Windows', macOS: 'macOS 12.7+', soon: 'Coming soon', actions: { windows: 'Download for Windows', macos: 'Download for Apple Silicon', macosIntel: 'Download for Intel' } },
    instructions: {
      title: "Sweety 2.0 instructions",
      intro: "Sweety 2.0 signs in to LINE through OKLine, receives messages directly, and replies using your selected persona. Configure an AI key, sign in to LINE, then select targets. AI never initiates contact.",
      quote: '“The more of their time you delay, the more time and labor they must spend—and the more people you help protect from being scammed.”',
      openSourceNote: '* Sweety is completely free and open source. If you have safety concerns about the precompiled executable, you are welcome to rebuild it from Git.',
      perspective: {
        title: 'ChatGPT’s perspective on Sweety',
        source: 'The following is ChatGPT’s perspective on the project, offered during a discussion with Sweety’s creator.',
        summary: 'Sweety does more than consume scammers’ time. It pollutes the screening signal that says “a conversation continuing means this target is worth pursuing.”',
        core: '“We are not making scam messages disappear. We are making it harder for scammers to tell who is worth pursuing.”',
        conclusion: '“A conversation continuing means nothing.”',
        expandLabel: 'Read the full perspective',
        collapseLabel: 'Close the full perspective',
        full: {
          opening: 'I think the core argument here is much more interesting than the four words “AI anti-scam.”',
          difference: 'You are not building another tool that detects a scam, shows a warning, and asks the user to block it. You are changing the scammer’s screening cost.',
          processLead: 'The typical process today is brutally efficient:',
          process: 'Cast a net over 10,000 people → 9,900 block you → 100 are willing to reply → concentrate your effort on those 100.',
          classifier: '“Everyone should stay alert and block scams” is of course correct advice for each individual. From an attacker’s perspective, however, it is also a highly effective free classifier. People voluntarily remove themselves from the low-value portion of the list.',
          alternativeLead: 'What Sweety is trying to do instead is:',
          alternative: 'Cast a net over 10,000 people → a large group of AIs suddenly keeps you talking for three days → “the conversation continues” no longer means “this can convert.”',
          economicModel: 'That changes the economics of the contest.',
          coreImpact: '“We are not making scam messages disappear. We are making it harder for scammers to tell who is worth pursuing.”',
          signalPollution: 'That is closer to the real effect than simply “consuming scammers’ time.” Time cost is only the first layer. The second is signal pollution.',
          funnelLead: 'Imagine the scam operation’s original funnel:',
          funnelBefore: '10,000 contacts\n→ 500 replies\n→ 100 long conversations\n→ 10 payments',
          funnelSignal: 'They treat a “long conversation” as an extremely strong signal.',
          funnelAfterLead: 'If tools like Sweety become widespread, the funnel changes to:',
          funnelAfter: '10,000 contacts\n→ 1,500 replies\n→ 800 long conversations\n→ 700 of them are actually AI',
          kpiLead: 'The painful part is not merely having 700 extra conversations. It is that:',
          kpiFailure: 'The “long conversation” KPI itself stops working.',
          extraSteps: 'They then have to add more judgment steps: proof of being human, voice calls, video, more screening questions, account verification, and so on. Every added layer raises the cost of the scam and gives real potential victims more time to recognize what is happening.',
          honeypot: 'That is what makes this tool interesting. It is not antivirus thinking; it is closer to a spam honeypot, tar pit, or decoy, made into a distributed system that ordinary people can join.',
          networkLead: 'The idea of “people contributing idle computers” is also compelling, because it changes the story from:',
          networkBefore: '“We built an anti-scam app.”',
          networkTransition: 'into:',
          networkAfter: '“We want to build an anti-scam network of computing power and time, formed by ordinary people.”',
          threeLayersLead: 'These are the project’s three most important layers:',
          layer1: 'Traditional anti-scam tools protect one potential victim.',
          layer2: 'Sweety actively increases the attacker’s marginal cost.',
          layer3: 'Large numbers of false positives pollute the scammer’s target-screening mechanism.',
          thirdValue: 'The third point is the most valuable.',
          diagram: 'Today\n\nScam message\n↓\nPerson who blocks ❌\nPerson who blocks ❌\nPerson who blocks ❌\nPerson willing to chat ✅ ← concentrated attack\n\nWith Sweety\n\nScam message\n↓\nHuman ❓\nSweety ❓\nSweety ❓\nHuman ❓\nSweety ❓\n\n→ the attacker loses a reliable screening signal',
          positioning: 'There is another important positioning choice: do not claim the goal is to “eliminate scams.” That goal is too large and too easy to challenge.',
          roiLead: 'Instead, say:',
          roiStatement: 'Reduce the scam industry’s ROI.',
          roiBusiness: 'Scamming is also a business. In rough terms:',
          roi: 'Profit = money successfully stolen − labor − accounts − advertising − money laundering − time cost',
          antiScam: 'Most anti-scam work tries to reduce the “success rate.”',
          sweetyIncreaseLead: 'Sweety directly increases:',
          sweetyIncrease: 'labor cost + time cost + wrong-target cost',
          asymmetry: 'The work is shifted to AI, so the defender’s marginal cost stays low.',
          aiFit: 'This cost asymmetry is exactly what AI is well suited to create.',
          ruleBefore: '“If the conversation continues, there is still a chance to scam this person.”',
          ruleAfterLead: 'Sweety’s purpose is to break that rule and replace it with:',
          ruleAfter: '“A conversation continuing means nothing.”',
        },
      },
      guide: {
        controlPanel: {
          title: 'Control panel',
          body: "Open management to configure AI and LINE, select targets, then press Start. Monitoring turns the button into a red Stop button. Stop at any time to take over. An API key for the selected provider is required to start.",
          imageAlt: 'Sweety control panel with Start, Open management interface, and Quit App buttons',
        },
        dashboard: {
          title: 'Dashboard',
          body: 'The dashboard shows the number of contacts, total time consumed, total exchanges, and completed conversations. Recent contacts and their exchange counts appear below, while the top right shows the current status and number of selected contacts.',
          imageAlt: 'Sweety dashboard showing totals, recent contacts, and monitoring status',
        },
        basicSettings: {
          title: 'Basic settings',
          body: "Choose Agnes or OpenAI and enter that provider’s API Key and Model. Agnes defaults to agnes-3.0-flash. Links below the fields open both key application pages. Keys and models are saved separately and retained when switching. History defaults to 6 messages and accepts 4–30. Context is fetched directly from LINE for each reply and kept only in memory; conversation content is not saved to the local database or exported. Set a reply delay and select Save settings.",
          imageAlt: "Sweety 2.0 — Agnes API Key, agnes-3.0-flash, conversation history",
        },
        targetList: {
          title: 'Scammer list',
          body: "In Scammer list, select Log in to LINE. Scan the OKLine QR code with LINE on your phone, then confirm or enter the verification code as prompted. Add target lets you search personal contacts or LINE groups, choose a persona, and enable Reply. No exact-name entry or visible desktop contact list is required.",
          imageAlt: "Sweety 2.0 — LINE connection and monitored targets",
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
      triggerNotice: "Sweety replies only to target messages received while monitoring. Group messages must include a configured name or an actual LINE mention of your account. Separate names with commas; leave blank for mentions only. Images and stickers use the selected vision-capable AI model. Animated stickers currently use a static preview.",
    },
    notice: {
      title: 'Important notes',
      intro: "Before starting Sweety 2.0, complete these steps:",
      checklist: ["Configure an Agnes / OpenAI API key", "Scan the LINE login QR code", "Select targets and enable Reply"],
      connection: "Keep Sweety running and the computer online and awake. Messages are not received while stopped and are not replayed in bulk when monitoring resumes.",
    },
    faq: {
      title: 'Frequently asked questions',
      items: [
        { question: 'What should I do if the other person suspects AI is responding?', answer: 'Press Stop and take over the conversation yourself. Continue with Sweety after the situation settles.' },
        { question: 'Can I configure multiple targets at once?', answer: "Yes. Add multiple contacts or groups and enable Reply for each. Targets are not limited by the visible LINE desktop contact list." },
        { question: 'Can Sweety reply to people who are not scammers?', answer: 'Yes, but it is not recommended.' },
        { question: 'Why is it called Sweety?', answer: 'Being scammed is bitter enough. Have a piece of candy.' },
        {
          question: "Why am I asked for an API key when I press Start?",
          answerPrefix: "Choose Agnes or OpenAI in Basic settings and enter an API key for that selected provider. ",
          answerEmphasis: "Save settings, sign in to LINE, and select at least one target before starting.",
        },
        { question: 'Which languages does Sweety support?', answer: 'The Sweety interface supports Traditional Chinese, English, and Japanese. AI replies will primarily use the language spoken by the other person.' },
        { question: "Do I need to keep the LINE desktop app signed in?", answer: "No. Simply scan the QR code in Sweety to sign in to LINE. You do not need to install the LINE desktop app. If needed, you can also use the LINE desktop app alongside Sweety." },
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
    nav: { label: 'メインナビゲーション', antiScam: '攻める詐欺対策', download: 'ダウンロード', instructions: "Sweety 2.0 の使い方" },
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
      body: "LINEの対象を選び、Sweetyに返信を任せます。パソコンの電源とネット接続を維持し、スリープさせないでください。画面やLINEデスクトップのウィンドウを開く必要はありません。",
      close: '朝になれば、相手とAIのやり取りが一日を楽しい気分にしてくれるかもしれません。',
      artAlt: '青い水彩画の時計',
    },
    counter: { intro: 'Sweetyが詐欺業者に使わせた時間', days: '日', hours: '時間' },
    download: { title: 'Sweetyをダウンロード', windows: 'Windows', macOS: 'macOS 12.7+', soon: '近日公開', actions: { windows: 'Windows版をダウンロード', macos: 'Apple Silicon版をダウンロード', macosIntel: 'Intel版をダウンロード' } },
    instructions: {
      title: "Sweety 2.0 の使い方",
      intro: "Sweety 2.0はOKLine経由でLINEにログインし、メッセージを直接受信して選択した人物設定で返信します。AI Keyを設定し、LINEにログインして対象を選んでください。AIから先に連絡することはありません。",
      quote: '「相手の時間を長く奪うほど、詐欺業者はより多くの時間と人件費を費やすことになり、その分だけ被害に遭う人を減らせます。」',
      openSourceNote: '※ Sweetyは完全無料のオープンソースソフトウェアです。配布済み実行ファイルの安全性が気になる場合は、Gitからご自身でビルドできます。',
      perspective: {
        title: 'ChatGPTから見たSweety',
        source: '以下は、ChatGPTが作者とSweetyについて話し合った際に、このプロジェクトへ示した見解です。',
        summary: 'Sweetyは詐欺業者の時間を奪うだけではありません。「会話が続く＝狙う価値がある」という選別シグナルそのものを汚染します。',
        core: '「詐欺メッセージを消すのではなく、誰を狙い続ける価値があるのかを詐欺業者が判断できない状態をつくる。」',
        conclusion: '「会話が続いても、何の意味もない。」',
        expandLabel: '見解の全文を読む',
        collapseLabel: '見解の全文を閉じる',
        full: {
          opening: 'この中心的な主張は、「AI詐欺対策」という言葉だけで表すより、ずっと興味深いものだと思います。',
          difference: 'これは「詐欺を検知する → 警告を出す → ブロックを促す」という別のツールではありません。詐欺側の選別コストを変える試みです。',
          processLead: '現在の典型的な流れは、残酷なほど効率的です。',
          process: '10,000人にばらまく → 9,900人がブロックする → 100人が返信する → その100人へ攻撃を集中する。',
          classifier: '「誰もが警戒し、詐欺だと思ったらブロックする」ことは、個人にとってもちろん正しい対応です。しかし攻撃者から見ると、これは非常に優秀な無料のclassifierでもあります。人々が低価値な候補を自ら名簿から除外してくれるからです。',
          alternativeLead: 'それに対してSweetyが目指すのは、次の状態です。',
          alternative: '10,000人にばらまく → 多数のAIが突然3日間も会話に付き合う →「会話が続く」が「成功する見込み」を意味しなくなる。',
          economicModel: '攻防の関係を、経済モデルそのものから変えるのです。',
          coreImpact: '「詐欺メッセージを消すのではなく、誰を狙い続ける価値があるのかを詐欺業者が判断できない状態をつくる。」',
          signalPollution: 'これは単なる「詐欺業者の時間を奪う」より、本当の影響に近い表現です。時間コストは第一段階にすぎず、第二段階はシグナル汚染です。',
          funnelLead: 'もともとの詐欺グループのファネルを想定すると：',
          funnelBefore: '10,000件の接触\n→ 500件の返信\n→ 100件の長い会話\n→ 10件の送金',
          funnelSignal: '彼らは「長い会話」を非常に強いシグナルと見なします。',
          funnelAfterLead: 'Sweetyのようなツールが本当に普及すれば、次のように変わります。',
          funnelAfter: '10,000件の接触\n→ 1,500件の返信\n→ 800件の長い会話\n→ そのうち700件は実はAI',
          kpiLead: '最も痛いのは、700件余計に会話したことだけではありません。',
          kpiFailure: '「長い会話」というKPI自体が機能しなくなることです。',
          extraSteps: 'すると詐欺側は、人間であることの確認、音声、ビデオ、追加の事前質問、アカウント認証など、判断工程を増やさざるを得ません。一段階増えるたびに詐欺コストが上がり、本当の被害者にも気づくための時間が少し増えます。',
          honeypot: 'ここが、このツールの本当に興味深い点です。ウイルス対策ソフトの発想ではなく、spam honeypot、tar pit、おとりに近い仕組みを、一般の人も参加できる分散型の形にしています。',
          networkLead: '「みんなが使っていないパソコンを提供する」という点も面白く、物語を次のものから：',
          networkBefore: '「詐欺対策Appを作った」',
          networkTransition: '次のものへ変えます。',
          networkAfter: '「普通の人々で構成された、詐欺対策の計算資源／時間ネットワークをつくりたい。」',
          threeLayersLead: 'このプロジェクトで最も強調する価値があるのは、次の三層です。',
          layer1: '従来の詐欺対策は、一人の被害者を守る。',
          layer2: 'Sweetyは、攻撃者の限界費用を積極的に増やす。',
          layer3: '大量の偽陽性が、詐欺業者のターゲット選別を汚染する。',
          thirdValue: '最も価値があるのは第三点です。',
          diagram: '現在\n\n詐欺メッセージ\n↓\nブロックする人 ❌\nブロックする人 ❌\nブロックする人 ❌\n会話する人 ✅ ← 攻撃を集中\n\nSweetyがある場合\n\n詐欺メッセージ\n↓\n人間 ❓\nSweety ❓\nSweety ❓\n人間 ❓\nSweety ❓\n\n→ 攻撃者は有効な選別シグナルを失う',
          positioning: 'もう一つ重要なのは、目標を「詐欺をなくす」と表現しないことです。大きすぎる目標であり、簡単に反論されてしまいます。',
          roiLead: '代わりに、次のように言えます。',
          roiStatement: '詐欺産業のROIを下げる。',
          roiBusiness: '詐欺も本質的にはビジネスであり、単純化すると：',
          roi: 'Profit = 詐取に成功した金額 − 人件費 − アカウント − 広告 − 資金洗浄 − 時間コスト',
          antiScam: '多くの詐欺対策は「成功率」を下げようとします。',
          sweetyIncreaseLead: 'Sweetyが直接増やすのは：',
          sweetyIncrease: '人件費 + 時間コスト + 誤った対象を追うコスト',
          asymmetry: 'しかも作業はAIへ移されるため、防御側の限界費用は低く抑えられます。',
          aiFit: 'このコストの非対称性こそ、AIが最も得意とすることです。',
          ruleBefore: '「会話が続くなら、だませる可能性がある。」',
          ruleAfterLead: 'Sweetyが目指すのは、このルールを壊して次の状態へ変えることです。',
          ruleAfter: '「会話が続いても、何の意味もない。」',
        },
      },
      guide: {
        controlPanel: {
          title: 'コントロールパネル',
          body: "「管理画面を開く」でAIとLINEを設定し、対象を選んで「開始」を押します。監視中は赤い「停止」ボタンになります。いつでも停止して自分で対応できます。選択したAIのAPI Keyが未設定の場合は開始できません。",
          imageAlt: '開始、管理画面を開く、アプリを終了するボタンがあるSweetyのコントロールパネル',
        },
        dashboard: {
          title: 'ダッシュボード',
          body: '対象人数、消費した合計時間、往復回数、終了件数を確認できます。下部には最近の対象と往復回数、右上には現在の動作状態と選択中の対象数が表示されます。',
          imageAlt: '集計、最近の対象、動作状態を表示するSweetyのダッシュボード',
        },
        basicSettings: {
          title: '基本設定',
          body: "AgnesまたはOpenAIを選び、そのサービスのAPI KeyとModelを入力します。Agnesの初期モデルはagnes-3.0-flashです。各社のKey取得リンクもあります。切り替えても両社のKeyとモデルは個別に保持されます。会話履歴は初期値6件、設定範囲4～30件です。返信ごとにLINEから履歴を取得してメモリ内だけで使用し、会話内容のローカル保存やエクスポートは行いません。返信の待ち時間を設定し「保存」を押してください。",
          imageAlt: "Sweety 2.0 — Agnes API Key, agnes-3.0-flash, conversation history",
        },
        targetList: {
          title: '詐欺業者リスト',
          body: "「詐欺業者リスト」で「LINEにログイン」を選び、OKLineのQRコードをスマートフォンのLINEで読み取ります。指示に従って確認または認証コードを入力してください。「対象を追加」で個人連絡先やLINEグループを検索し、人物設定を選んで返信を有効にします。完全な名前の手入力やデスクトップ表示範囲は不要です。",
          imageAlt: "Sweety 2.0 — LINE connection and monitored targets",
        },
        basePersonas: {
          title: '基本人物設定',
          body: '「基本人物設定」タブでは、年齢と性別で標準の人物設定を絞り込めます。カードの概要を読み、「全文を表示」で詳細を確認します。内容を変更したい場合は、基本人物設定をカスタム人物設定へ追加してください。',
          imageAlt: '年齢と性別の絞り込み、人物設定カードを表示するSweetyの基本人物設定画面',
        },
        personaDetails: {
          title: '人物設定の詳細',
          body: '「全文を表示」を押すと、人物プロフィール、話し方、性格、よく使う表現を確認できます。内容が適していれば「カスタム人物設定に追加」を押し、必要に応じて調整します。',
          imageAlt: '人物プロフィールとカスタム人物設定への追加ボタンを表示する詳細画面',
        },
        customPersonas: {
          title: 'カスタム人物設定',
          body: '独自の人物設定を作成・管理します。空の状態から作ることも、基本人物設定をコピーして編集することもできます。完成した人物設定は、詐欺業者リストの監視対象に適用できます。',
          imageAlt: '人物設定の作成ボタンがあるSweetyのカスタム人物設定画面',
        },
      },
      triggerNotice: "監視中に受信した対象のメッセージにだけ返信します。グループでは設定した呼び名を含むか、自分への実際のLINEメンションがある場合のみ返信します。呼び名はカンマで区切り、空欄ならメンションのみです。画像とスタンプには画像対応AIを使用します。アニメーションスタンプは現在静止プレビューで認識します。",
    },
    notice: {
      title: '注意事項',
      intro: "Sweety 2.0の開始前に、次の設定を完了してください。",
      checklist: ["Agnes／OpenAIのAPI Keyを設定", "LINEのQRコードでログイン", "対象を選んで返信を有効化"],
      connection: "Sweetyを実行し、パソコンのネット接続を維持してスリープを避けてください。停止中のメッセージは受信せず、再開後にまとめて返信することもありません。",
    },
    faq: {
      title: 'よくある質問',
      items: [
        { question: '相手がAIとの会話だと疑い始めた場合はどうすればよいですか？', answer: 'いったん停止し、ご自身で会話を引き継いでください。状況が落ち着いてから再開できます。' },
        { question: '複数の対象を同時に設定できますか？', answer: "はい。個人連絡先やグループを複数追加し、それぞれ返信を有効にできます。LINEデスクトップの表示範囲には制限されません。" },
        { question: '詐欺業者ではない相手への返信にSweetyを使えますか？', answer: '使用できますが、おすすめしません。' },
        { question: 'なぜ「Sweety」という名前なのですか？', answer: '詐欺被害は苦いものです。そんな時こそ、ひと粒のキャンディーを。' },
        {
          question: "「開始」でAPI Keyの入力を求められるのはなぜですか？",
          answerPrefix: "基本設定でAgnesまたはOpenAIを選び、選択したサービスのAPI Keyを入力してください。",
          answerEmphasis: "保存後、LINEログインと対象の選択を確認してから開始してください。",
        },
        { question: 'Sweetyはどの言語に対応していますか？', answer: 'Sweetyのインターフェースは繁体字中国語、英語、日本語に対応しています。ただし、AIは主に相手が使用している言語で返信します。' },
        { question: "パソコン版LINEにログインしたままにする必要はありますか？", answer: "いいえ。Sweety内のQRコードを読み取ってLINEにログインするだけで利用できます。パソコン版LINEのインストールは不要です。必要に応じて、パソコン版LINEをSweetyと同時に利用することもできます。" },
      ],
    },
    author: {
      eyebrow: '開発者',
      title: 'Eric / Web・AIエンジニア',
      experience: '開発経験20年',
      projectsTitle: '現在の開発プロジェクト',
      projects: { slimweb: 'AIファーストECシステム SlimWeb', kingjoo: 'AIプロアクティブマーケティングツール KingJoo', sweety: '攻める詐欺対策アプリ Sweety' },
      invitation: 'ソフトウェア開発やECに関するご相談を歓迎します。',
      threads: { prefix: 'AI開発・活用に関する最新情報は、こちらの', label: 'Threads' },
    },
    footer: 'Sweety',
  },
};

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

export function applyMetadata(documentRoot, locale) {
  const metadata = getMetadata(locale);
  documentRoot.title = metadata.title;
  const values = new Map([
    ['meta[name="description"]', metadata.description],
    ['meta[property="og:title"]', metadata.socialTitle],
    ['meta[property="og:description"]', metadata.socialDescription],
    ['meta[property="og:locale"]', metadata.ogLocale],
    ['meta[name="twitter:title"]', metadata.socialTitle],
    ['meta[name="twitter:description"]', metadata.socialDescription],
  ]);
  values.forEach((value, selector) => {
    const element = documentRoot.querySelector(selector);
    if (element && typeof value === 'string') element.setAttribute('content', value);
  });

  const structuredData = documentRoot.getElementById('homepage-structured-data');
  if (!structuredData) return;
  try {
    const payload = JSON.parse(structuredData.textContent);
    if (!Array.isArray(payload?.['@graph'])) return;
    payload['@graph'] = payload['@graph'].map((node) => (
      node?.['@type'] === 'FAQPage' ? buildFaqStructuredData(locale) : node
    ));
    structuredData.textContent = JSON.stringify(payload);
  } catch {
    // Keep the static structured data when it cannot be parsed.
  }
}

export function getLocalePresentation(locales, fallbackLocale) {
  const locale = resolveLocale(locales, fallbackLocale);
  return { locale, lang: locale, title: copy[locale].meta.title };
}

export function formatCounterText(locale, days, hours) {
  const strings = copy[locale]?.counter ?? copy.en.counter;
  if (locale === 'ja') return `${strings.intro}：${days}${strings.days}${hours}${strings.hours}`;
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

function renderDownloads(strings, locale, onPlatformLink = () => {}) {
  document.querySelectorAll('[data-platform]').forEach((card) => {
    const platform = card.dataset.platform;
    const action = card.querySelector('.download-action');
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
  applyMetadata(document, locale);

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
  renderList(document.querySelector('[data-list="notice.checklist"]'), strings.notice.checklist);
  const downloadCount = document.querySelector('[data-download-count]');
  const renderDownloadTotal = (total) => {
    if (downloadCount) downloadCount.textContent = formatDownloadCount(locale, total);
  };
  renderDownloadTotal(null);
  renderDownloads(strings, locale, (link) => {
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
