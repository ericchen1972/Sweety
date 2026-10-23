# OkLine 版本與第三方資源

- 原始庫：https://github.com/NiceDayZc/OkLine
- 固定 commit：2e3437977368802edcc2219798b9d5333665ebca，版本 2.9.2。
- Python 原始碼專案標示 MIT，授權文字隨安裝套件提供。
- SDK 帶有從 LINE Chrome 元件取得的 ltsm.wasm、ltsmSandbox.js；不能將專案 MIT 標示直接解讀為 LINE 自有元件的重新散布授權。此測試版沒有做對外發佈，公開散布前須確認這些元件及非官方協定的授權與維護條件。
- Node 由本機建置環境選取並包入 App；須保留其授權與第三方 notices。建置時將 Node 安裝目錄的 `LICENSE` 保存為 Resources/third-party/Node-LICENSE.txt。
- SDK 的 send_image/send_file 在研究中成功送達，但其高階 helper 實際回條為未 sealed；不能宣稱此版所有傳送媒體均使用 Letter Sealing。文字 E2EE 與加密圖片／檔案接收曾獨立驗證。
- 不包含正式版或測試版 LINE App、不修改用戶的 LINE 主程式。私人測試 session 與聊天檔案不進入套件。

Sweety 的 OKLine session、請求序號與收發設計參考本機 LINEDot 實作；只移植本專案所需的文字及群組名稱／標註觸發回覆。
