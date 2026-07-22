# Sweety

Sweety 是一套完全開源的主動式反詐騙桌面 App。使用者選定 LINE 桌面版中的對象與人設後，Sweety 會讓 AI 被動回覆訊息，持續消耗詐騙者的時間；AI 不會主動聯絡任何人，使用者也可隨時停止並自行接手。

- 官方網站：[sweety.tw](https://sweety.tw)
- 目前版本：`1.0.1`
- 支援平台：macOS（Windows 版規劃中）
- 授權：MIT

![Sweety 主動反詐](web/images/sweety-social-1200x630.png)

## 主要功能

- 為不同對象指定基礎或自訂人設
- 明確勾選要由 AI 回覆的對象
- 隨時開始、停止或由使用者接手
- 本機保存對象、人設與執行資料
- 無法連線更新時，仍可使用本機已保存的基礎人設

## 專案結構

```text
app/frontend/   React + TypeScript 使用者後台
app/desktop/    Python 桌面執行層、LINE 操作與本機 API
app/tools/      建置與網站部署工具
web/            sweety.tw 靜態網站與公開端點
docs/           設計與實作規格
```

## 本機開發

需求：Node.js 20 以上、Python 3.11–3.13、[uv](https://docs.astral.sh/uv/)；桌面自動化功能需在 macOS 執行。

### 前端

```bash
cd app/frontend
npm ci
npm run dev
```

### 桌面執行層

```bash
cd app/desktop
uv sync --extra desktop --extra dev
uv run python launcher.py
```

需要遠端 AI 服務時，請由環境變數提供 `SWEETY_AGNES_KEY`。不要把正式金鑰寫入程式碼或提交到 Git。

## 測試

```bash
cd app/frontend && npm test
cd ../desktop && uv run pytest
cd ../.. && node --test web/tests/*.test.mjs
```

## 建置 macOS App

先將根目錄的 `config.example.json` 複製為不會提交的 `config.json`，填入自己的設定，再執行：

```bash
cd app/desktop
./build_app.sh
```

輸出位於 `app/desktop/dist/Sweety.app`。正式金鑰、部署設定、資料庫、執行紀錄、依賴目錄與建置輸出皆不應提交。

## 使用注意事項

- LINE 桌面 App 視窗位置請勿超過螢幕左側或右側邊緣，否則將造成 Sweety 辨識失敗。
- 一次可設定多個對象，但請保持在 LINE 主視窗聯絡人列表的可視範圍。
- 如果對方懷疑是 AI，可先按停止鍵並自行接手，情況穩定後再繼續。
- Sweety 不能取代警方、金融機構或專業反詐單位；遇到疑似詐騙，請停止付款與提供資料，並透過可信任的官方管道查證。

## 參與開發

歡迎提出 Issue、改善建議或 Pull Request。請勿提交任何真實聯絡人對話、個資、API 金鑰或部署憑證。

## 作者

Eric，網站／AI 工程師，20 年開發經驗。

- [AI First 電商系統 SlimWeb](https://slimweb.tw)
- [AI 主動行銷工具 KingJoo](https://slimweb.tw/kingjoo/)
- [主動式反詐騙 App Sweety](https://sweety.tw)
- Email：eric.chen1972@gmail.com
- LINE：bobo2010

任何程式開發、電商需求都歡迎與作者接洽。

## License

[MIT License](LICENSE)
