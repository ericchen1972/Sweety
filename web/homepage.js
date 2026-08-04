export function resolveLocale(locales, fallbackLocale) {
  const locale = Array.isArray(locales) && locales.length ? locales[0] : (typeof locales === 'string' ? locales : fallbackLocale);
  if (typeof locale !== 'string') return 'en';
  const normalized = locale.toLowerCase();
  if (normalized === 'zh-tw' || normalized === 'zh-hk' || normalized === 'zh-mo' || normalized === 'zh-hant' || normalized.startsWith('zh-hant-')) return 'zh-TW';
  if (normalized === 'ja' || normalized.startsWith('ja-')) return 'ja';
  return 'en';
}

export const downloadConfig = Object.freeze({
  windows: 'https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe?release=1.0.1-1a2600f9',
  macos: 'https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-bb0d7e46',
});

export const tutorialVideos = Object.freeze({
  'zh-TW': Object.freeze({
    id: 'w2w5HGmXxwo',
    src: 'https://www.youtube-nocookie.com/embed/w2w5HGmXxwo',
    title: 'Sweety 中文使用教學',
  }),
  en: Object.freeze({
    id: '-qS4MGvnsa4',
    src: 'https://www.youtube-nocookie.com/embed/-qS4MGvnsa4',
    title: 'Sweety English tutorial',
  }),
  ja: Object.freeze({
    id: 'CLLEgl9tRWA',
    src: 'https://www.youtube-nocookie.com/embed/CLLEgl9tRWA',
    title: 'Sweety 日本語使い方ガイド',
  }),
});

export function getTutorialVideo(locale) {
  return tutorialVideos[locale] ?? tutorialVideos.en;
}

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
    tutorialVideo: { eyebrow: 'VIDEO', title: '使用教學影片' },
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
    meta: {
      title: 'Sweety | Proactive anti-scam',
      description: 'Sweety is a free and open-source anti-scam app that uses AI to reply to suspicious contacts and consume scammers’ time.',
      socialTitle: 'Sweety | Proactive anti-scam',
      socialDescription: 'Use AI to actively consume scammers’ time.',
      ogLocale: 'en_US',
    },
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
    tutorialVideo: { eyebrow: 'VIDEO', title: 'Video tutorial' },
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
        controlPanel: {
          title: 'コントロールパネル',
          body: 'Sweetyを起動する前に、LINEのメインウィンドウを開いてください。「管理画面を開く」から返信対象を編集し、「開始」を押すと、SweetyがLINEの連絡先画面を確認します。監視対象からメッセージが届くと、そのトークを開いてAIが返信します。',
          imageAlt: '開始、管理画面を開く、アプリを終了するボタンがあるSweetyのコントロールパネル',
        },
        dashboard: {
          title: 'ダッシュボード',
          body: '対象人数、消費した合計時間、往復回数、終了件数を確認できます。下部には最近の対象と往復回数、右上には現在の動作状態と選択中の対象数が表示されます。',
          imageAlt: '集計、最近の対象、動作状態を表示するSweetyのダッシュボード',
        },
        basicSettings: {
          title: '基本設定',
          body: 'AI設定でSweety標準またはOpenAIを選択します。OpenAIを使う場合はAPI Keyとモデルを指定してください。会話設定では、新着メッセージの確認間隔と、トークを開いてから返信するまでの待ち時間を調整できます。設定後は「保存」を押します。',
          imageAlt: 'AI、確認間隔、返信待ち時間を設定するSweetyの基本設定画面',
        },
        targetList: {
          title: '詐欺業者リスト',
          body: '監視対象を追加・管理します。「返信」にチェックを入れた対象だけをSweetyが監視して返信します。対象ごとに編集、終了、会話のエクスポートもできます。LINE名は連絡先画面に表示される完全な名前を入力してください。',
          imageAlt: '返信チェック、対象、人物設定、操作ボタンを表示するSweetyの詐欺業者リスト',
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
        {
          question: '開始後に「macOSの権限が必要です」と表示されるのはなぜですか？',
          answerPrefix: 'アップデート後、macOSがSweetyを新しいアプリとして認識する場合があります。システム設定の',
          answerEmphasis: '「アクセシビリティ」と「画面収録とシステムオーディオ録音」からSweetyを一度削除し、再度追加してください。',
        },
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
  const tutorialVideo = document.querySelector('[data-tutorial-video]');
  if (tutorialVideo) {
    const video = getTutorialVideo(locale);
    tutorialVideo.setAttribute('src', video.src);
    tutorialVideo.setAttribute('title', video.title);
  }
  renderList(document.querySelector('[data-list="notice.permissions"]'), strings.notice.permissions);
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
