# Sweety App 與人設 Server 日文語系設計

日期：2026-08-04

## 目標

讓 macOS Sweety App 在系統主要語系為日文時，完整顯示日文管理介面、原生狀態面板、權限與錯誤提示、關於頁面，以及 24 組內建人設的日文名稱與內容。同時將日文人設納入遠端 catalog server、桌面 App 的 SQLite 快取與 API 資料流，使日文內容和既有繁體中文、英文一樣可以由 server 更新。

本次只擴充語系與資料欄位，不改變監控、LINE 操作、訊息判斷、AI provider、回覆延遲、儲存或安全驗證行為。AI 實際組合 prompt 時繼續使用繁體中文人設內容 `content_zh_tw`，因此切換日文介面不會改變 AI 回覆邏輯。

## 已確認方案

採用端到端 `ja` 語系：canonical catalog、產生器、MySQL、遠端 PHP API、SQLite、本機 API、React 前端及 AppKit 原生介面都正式保存或識別日文。App 仍保留內建 catalog 作為離線預設；遠端同步成功後，以 server 回傳的繁中、英文、日文內容更新 SQLite。

不採用只在 React 前端依人格 ID 補上日文的方案。該做法雖然改動較小，但日文內容無法由 server 更新，也會讓不同語系走不同資料來源，不符合目前 server catalog 為正常連線時權威資料的架構。

## 語系解析契約

- `ja`、`ja-JP` 與其他以 `ja-` 開頭的日文語系標籤解析為 `ja`。
- 既有 `zh-TW`、繁體中文解析規則保持不變。
- 英文與未支援語系繼續解析為 `en`。
- React 頁面的 `<html lang>` 在日文時設為 `ja`。
- macOS `AppleLanguages` 偵測到日文時，AppKit 面板與權限提示使用日文。
- 所有語系查找仍有英文 fallback，單一缺漏不得造成 App 啟動失敗。

## 人設資料與同步流程

`app/catalog/base_personas.json` 繼續作為 24 組人設的 canonical source，每組人設的 `name` 與 `content` 新增 `ja`。日文內容是完整人物資料、背景、互動原則與語氣風格，不只翻譯顯示名稱。

`app/tools/generate_persona_catalogs.py` 由同一份 canonical source 產生：

- React 內建 catalog JSON
- Python 內建 catalog module
- MySQL seed/update SQL

產生器需驗證每組人設都有非空的 `zh-TW`、`en`、`ja`，並保持既有 24 組 ID、年齡層、性別、圖片與排序不變。重新產生檔案不得遺失日文欄位。

App 啟動後的資料流維持：

1. SQLite 首次建立時，以 App 內建 catalog 寫入三種語系。
2. 背景向遠端 catalog API 取得最新 system prompt 與人設。
3. payload 通過三語系驗證後，以單次交易更新 SQLite。
4. React 透過本機 `/api/state` 取得 SQLite 中的人設。
5. 遠端失敗或 payload 不完整時，保留 SQLite 既有資料，不清空也不降級覆寫。

`get_base_persona_text()` 與 AI prompt 組合繼續只讀 `content_zh_tw`。日文欄位只供日文 UI 顯示、預覽與複製為自訂人設使用。

## Server 與資料庫

遠端 MySQL `base_personas` 新增：

- `name_ja VARCHAR(100) NOT NULL`
- `content_ja LONGTEXT NOT NULL`

資料庫更新必須可安全套用到既有 production schema，不能只修改 `CREATE TABLE IF NOT EXISTS` 而漏掉現存資料表。部署 SQL 或部署工具需先以可重複執行的方式補欄位，再寫入 24 組日文內容；若日文 seed 尚未準備完整，部署應失敗，不得留下空白日文人設。

`web/sweety-catalog-lib.php` 的 catalog response 為每組人設回傳：

```json
{
  "name": { "zh-TW": "...", "en": "...", "ja": "..." },
  "content": { "zh-TW": "...", "en": "...", "ja": "..." }
}
```

既有 client token、版本 header、HTTP 狀態與 system prompt 格式不變。Server 不依請求語系裁切 payload，仍一次回傳全部支援語系，方便 App 離線切換與快取。

本次修改會把 server schema、PHP、SQL、部署與驗證程式一併準備好並提交 Git；除非另行要求，不在這次直接執行 production catalog 部署。

## App SQLite 與本機 API

SQLite schema version 遞增，`base_personas` 新增 `name_ja` 與 `content_ja`。migration 必須保留現有 targets、訊息、自訂項目、設定及其他資料；升級時先從新版內建 catalog 按 persona ID 補入日文，再允許下一次遠端同步更新。

Repository 的 seed、遠端 replace、row mapping 與 `/api/state` response 都納入 `ja`。遠端 payload 缺少任何必要日文欄位時，整次同步失敗並保留舊資料，避免部分人設變成空白或中英日版本不同步。

## React 管理介面

`Locale` 擴充為 `"zh-TW" | "en" | "ja"`，所有既有 copy key 加入日文，涵蓋：

- 側邊導覽、開始／停止、狀態與目標管理
- 新增與編輯目標、人設與武器
- 年齡、性別、AI 設定、延遲與檢查間隔
- 匯入、匯出、儲存、刪除與確認訊息
- 載入、連線、驗證與一般錯誤訊息
- 更新通知與關於 Sweety 導覽
- 無障礙標籤、按鈕 title 與頁面語系

移除散落在元件內的中英二選一判斷，統一透過 copy 物件或明確的三語系 formatter，避免日文落入英文分支。時間長度、人設風格摘要及其他格式化文字加入自然的日文格式。

日文 UI 從 `/api/state` 直接顯示 `name.ja`、`content.ja`。內建 frontend catalog 只作 API 不可用或狀態尚未建立時的離線 fallback，不覆蓋 server 已同步的資料。

## AppKit 原生介面

原生狀態面板、menu bar 選單、Start／Stop、目前目標、管理介面、結束 App、更新卡片、AI timeout 警告與 macOS 權限提示全部新增日文。狀態文案維持既有狀態機，只增加 copy mapping，不改變狀態判斷。

權限名稱在日文顯示為自然的 macOS 用語，並保留原有按鈕與系統設定開啟行為。

## 關於 Sweety

日文 App 不應在「Sweety について」頁面顯示中文。新增可由 server 提供的日文 about HTML，保留現有 sanitizer 與外部連結限制。App 依啟動時語系選擇繁中／既有頁面或日文頁面；取得失敗時顯示日文化的既有錯誤狀態，不把未消毒 HTML 直接送進前端。

日文 about 內容涵蓋產品用途、安全原則、免責聲明、開源專案與作者資訊。這是 App 內容語系的一部分，不改首頁結構。

## 相容性與錯誤處理

- 舊版 App 繼續只讀 server response 中的繁中與英文，不會因多出 `ja` key 失敗。
- 新版 App 若連到尚未升級的 server，因缺少 `ja` 而拒絕該次遠端更新，繼續使用 migration 後的內建日文 catalog。
- 遠端同步採全有或全無；解析、網路或資料庫寫入失敗都保留上一次可用資料。
- 既有使用者自訂人設不做自動翻譯，也不改寫內容；日文 UI 中仍照原文顯示使用者資料。
- 未支援語系維持英文，不新增手動語系切換器或偏好設定。

## 測試契約

採測試先行。至少涵蓋：

1. frontend 與 desktop 的 `ja`、`ja-JP` 語系偵測。
2. 三種 UI copy 具有相同 key，日文沒有空白值或英文 fallback。
3. 24 組人設全部具有非空日文名稱與完整日文內容。
4. catalog 產生器輸出的 React、Python、SQL 都包含同一組日文資料。
5. SQLite 新安裝與舊 schema migration 都保留資料並補齊日文欄位。
6. 遠端 catalog parser 接受完整三語 payload、拒絕缺少日文的 payload。
7. Repository replace 與 `/api/state` 正確回傳日文。
8. 日文 AppKit 狀態、更新、timeout 與權限提示文案正確。
9. 日文 React 主要畫面、表單、錯誤、格式化文字與人設預覽正確。
10. 日文 about HTML 經 sanitizer 後可載入，失敗狀態仍安全。
11. 既有繁中、英文與 AI 使用 `content_zh_tw` 的契約持續通過。
12. server PHP、SQL 與 remote verification 確認 API payload 有 24 組完整三語人設。

## 驗證與交付

完成後執行 frontend、desktop 與 server 相關測試，重新產生 catalog artifacts，執行 `git diff --check`。接著使用 `app/desktop/build_app.sh` 建置測試 App，並用 `codesign --verify --deep --strict app/desktop/dist/Sweety.app` 驗證簽章。

只提交與本次日文化相關的程式、測試、內容與產生檔；保留未追蹤的 `videos/`。所有變更直接提交 canonical `main`，最後推送至 `origin/main`。本次不建立分支、不製作或發布 DMG，也不直接部署 production server，除非使用者另行要求。

## 不在本次範圍

- 修改 AI 回覆提示所使用的繁體中文人設
- 自動翻譯使用者建立的自訂人設或歷史資料
- 手動語系切換器
- Windows installer／DMG 發布
- production catalog server 部署
- 修改 LINE 自動化、監控、AI provider 或安全判斷
