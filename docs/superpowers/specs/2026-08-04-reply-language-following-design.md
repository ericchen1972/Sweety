# Sweety AI 回覆語言跟隨設計

日期：2026-08-04

## 目標

讓 AI 回覆語言由對方的實際對話內容決定，不受 Sweety App 介面語系或基礎人設以繁體中文撰寫所影響。對方使用日文時以自然日文回覆，使用英文時以英文回覆，使用中文時以中文回覆。

## 已確認方案

在共用 system prompt 增加明確的「回覆語言」契約，讓 App 內建 prompt 與 server seed prompt 使用完全相同的規則。不要把 App UI locale 傳入 AI，也不要為中、英、日建立三份 prompt；回覆語言只根據 LINE 截圖與最近對話歷史判斷。

這比依 App 語系決定回覆更正確，因為使用者可能使用日文介面，對方卻用英文或中文。也比只依賴模型自行推測更穩定，因為目前 system prompt 與人設說明主要是繁體中文。

## 語言判斷契約

- `msg_reply` 使用對方最新一則可辨識實質文字訊息的主要語言。
- 同一批訊息混用多種語言時，以畫面中最下方、時間最新的實質文字為準。
- 最新內容只有貼圖、圖片、影片、語音或其他沒有可辨識文字的媒體時，沿用最近對話的主要語言。
- 歷史中也沒有足夠文字可判斷時，才使用人設／prompt 的既有預設語言，不自行宣稱已偵測到特定語言。
- 專有名詞、人名、品牌、帳號顯示名稱與對方原本用詞可以保留，不為了統一語言而強制翻譯。
- `incoming_summary` 保留對方原始語言、字句與順序，不翻譯成 system prompt 或 App UI 的語言。
- 這項規則只影響輸出語言，不改變安全限制、人設、長度、拖延策略、連結禁止、截圖判讀或 structured output schema。

## App 與 Server 同步

App 內建來源為 `app/desktop/src/sweety_app/catalog.py` 的 `DEFAULT_SYSTEM_PROMPT_TEMPLATE`。Server seed 來源為 `app/tools/base_catalog.sql` 中 `system_prompts` 的同一份提示內容。

兩處必須加入相同語意與相同關鍵句，避免 App 離線時和遠端同步後出現不同回覆行為。既有 `deploy_base_catalog.php` 仍負責把 server seed 套用到 production；本次會修改並驗證 server 程式，但除非使用者另行要求，不直接部署 production server。

## 測試

- prompt contract 測試確認 App 內建 prompt 包含最新文字決定語言、混合語言、純媒體 fallback、保留專有名詞及 `incoming_summary` 不翻譯等規則。
- server contract 測試直接讀取 `base_catalog.sql`，確認 server seed 含有相同語言契約。
- `build_messages()` 測試確認實際送入模型的 system message 包含語言規則，不只存在於未使用的常數。
- 既有 AI、prompt、catalog 與桌面完整測試必須持續通過。

## 建置與交付

測試通過後使用 `app/desktop/build_app.sh` 產生 logging-enabled 測試版 `app/desktop/dist/Sweety.app`，再執行 `codesign --verify --deep --strict`。這不是 DMG 或 production release，不變更版本號，也不發布下載頁。

本次只提交 prompt、server seed、測試與規格，不修改或移除未追蹤的 `videos/`。是否推送 Git 或部署 server 由使用者另行指示。
