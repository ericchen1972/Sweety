# Sweety 官網日文語系設計

日期：2026-08-04

## 目標

在現有單一首頁 `https://sweety.tw/` 中加入完整日文語系。瀏覽器的主要語系為日文時，首頁的可見文案、下載資訊、使用說明、注意事項、FAQ、作者資訊、頁面 metadata、FAQ 結構化資料與教學影片都顯示日文；繁體中文與英文行為保持不變。

日文教學影片使用 YouTube ID `CLLEgl9tRWA`，嵌入網址使用既有的隱私加強網域 `https://www.youtube-nocookie.com/embed/CLLEgl9tRWA`。

## 已確認方案

沿用 `web/homepage.js` 的瀏覽器語系偵測與單頁文案物件，新增 `ja` 語系，不建立 `/ja/` 副本，也不新增查詢參數或手動語系選單。

這個方案維持一份首頁結構與一套部署流程，避免日後改版時同步多個 HTML 頁面。因所有語系共用同一個 canonical URL，搜尋引擎與不執行 JavaScript 的社群爬蟲仍可能讀到靜態英文預設內容；本次會補齊可由瀏覽器執行的日文 metadata，以及 `og:locale:alternate=ja_JP`，但不宣稱具有獨立日文網址等級的 SEO 效果。

## 語系解析契約

- `ja`、`ja-JP`，以及其他以 `ja-` 開頭的有效日文語系標籤解析為 `ja`。
- 既有繁體中文集合繼續解析為 `zh-TW`。
- 英文與所有未支援語系繼續解析為 `en`。
- 沿用目前只看瀏覽器第一優先語系的行為，不改變 fallback 次序。
- 套用日文後，`document.documentElement.lang` 設為 `ja`。

## 日文內容範圍

在 `web/homepage.js` 的 `copy` 中加入與繁中、英文完全相同結構的 `ja` 物件，涵蓋：

- 頁面標題、描述與導覽的無障礙標籤
- 主視覺與「詐騙最大成本是時間」區塊
- 累計時間與下載次數格式
- Windows、macOS 與 Git 下載區塊
- 七個使用說明項目、圖片替代文字、開源提示與觸發條件
- macOS 權限與 LINE 視窗位置注意事項
- 教學影片區標題與 iframe title
- 五個 FAQ，包括 macOS 權限修復的粗體重點
- 作者、專案、聯絡與 Threads 文案
- 頁尾文字

翻譯以自然、清楚的日文產品文案為準，不逐字保留中文標點或語序。產品名稱 `Sweety`、平台名稱 `LINE`、`Windows`、`macOS`、`OpenAI`、`Git`、`Threads` 保持官方寫法。畫面截圖仍沿用既有圖片，因此替代文字會以日文說明圖片內容，但不修改圖片本身。

## 教學影片

`tutorialVideos` 新增 `ja` 項目：

- ID：`CLLEgl9tRWA`
- embed：`https://www.youtube-nocookie.com/embed/CLLEgl9tRWA`
- iframe title：`Sweety 日本語使い方ガイド`

`getTutorialVideo('ja')` 必須回傳日文影片。頁面仍只保留一個 iframe，並在執行時更新其 `src` 與 `title`；影片區維持在 FAQ 正上方，現有 16:9 響應式版面不變。

## Metadata 與結構化資料

日文頁面啟動後會更新：

- `<title>`
- `meta[name="description"]`
- `meta[property="og:title"]`
- `meta[property="og:description"]`
- `meta[property="og:locale"]` 為 `ja_JP`
- `meta[name="twitter:title"]`
- `meta[name="twitter:description"]`
- FAQPage JSON-LD 的五組日文問答

靜態 HTML 增加 `og:locale:alternate` 的 `ja_JP` 宣告。canonical 仍為 `https://sweety.tw/`，不建立不存在的 `hreflang` 日文 URL。

Metadata 更新需採用既有文案資料，不另外維護一份容易失同步的日文常數。FAQ JSON-LD 也必須由同一套 `copy[locale].faq.items` 產生，並正確合併一般答案以及 macOS 權限 FAQ 的 `answerPrefix`、`answerEmphasis`。

## 靜態預設與錯誤處理

- `web/index.html` 繼續作為完整可閱讀的英文無 JavaScript fallback，不將靜態預設改成日文。
- 找不到指定語系文案或影片時，沿用英文 fallback，頁面不得因單一欄位缺少而中斷初始化。
- metadata DOM 節點或 JSON-LD 節點不存在時，更新函式應安全略過，不影響主要頁面渲染。
- 下載計數或累計時間 API 失敗時，維持既有降級行為，只將可顯示的 fallback 文字日文化。

## 測試契約

先擴充 `web/tests/homepage.test.mjs`，再修改實作。測試至少涵蓋：

1. `ja`、`ja-JP`、`ja-JP-u-ca-japanese` 解析為 `ja`，未支援語系仍為 `en`。
2. `copy.ja` 與其他語系具有相同的必要結構、七個說明項目與五個 FAQ。
3. 日文下載按鈕、下載次數與累計時間格式正確。
4. 日文影片 ID、embed 網域及 iframe title 正確，頁面只有一個 iframe 且位於 FAQ 前。
5. 日文 presentation 會回傳 `lang: 'ja'` 與日文標題。
6. 日文 metadata 與 FAQ JSON-LD 由同一份文案產生，權限 FAQ 的兩段答案會完整合併。
7. 繁中與英文既有契約全部繼續通過。
8. `homepage.css` 與 `homepage.js` 的共同 cache-busting hash 更新且相符。
9. `deploy_homepage.php` 仍不呼叫 App build、簽章或桌面發布流程。

## 部署與驗證

通過首頁完整測試與 `git diff --check` 後，依既有公式重新計算 `homepage.css + NUL + homepage.js` 的 SHA-256 前 12 碼，將相同版本寫入 HTML 的 CSS 與 JS URL。

使用 `app/tools/deploy_homepage.php` 只發布網站。部署後以日文瀏覽器語系驗證：

- `<html lang="ja">`、頁面標題與主要文案為日文。
- iframe 指向 `CLLEgl9tRWA`，全頁只有一個教學 iframe，且位於 FAQ 正上方。
- 七個使用說明與五個 FAQ 都是日文，FAQ 結構化資料同步。
- Windows 與 macOS 下載仍可用，下載次數與累計時間使用日文格式。
- 桌面與手機寬度沒有橫向溢出，瀏覽器 console 沒有新增錯誤。
- 線上 CSS、JS 的版本 query 與實際內容 hash 一致。

本次部署不得建置、簽章、替換或發布 Sweety 桌面 App，也不得修改或移除專案中既有未追蹤的 `videos/`。

## 不在本次範圍

- 日文版 App 介面
- 手動語系切換器或語系偏好儲存
- 獨立 `/ja/` URL 與伺服器端語系導向
- 翻譯圖片內的既有繁中文字
- 修改、重新上傳或管理 YouTube 影片
- 桌面 App 的建置與發布
