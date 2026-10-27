Sweety 2.0.2 — Windows x64 免安裝版

1. 保留完整 Sweety 資料夾，雙擊其中的 Sweety.exe。
   若取得的是 ZIP，請先完整解壓縮，不要只移出 exe。
2. 程式會顯示控制視窗並開啟瀏覽器管理頁面。
   若瀏覽器沒有開啟，按「開啟管理介面」，或前往 http://127.0.0.1:8891/。
3. 在管理頁面設定 AI API Key，登入 LINE，選取對象後開始監控。
4. 關閉瀏覽器不會停止服務；按「結束」或關閉 Sweety 控制視窗才會結束。

不需另裝 Python、Node.js 或 LINE 桌面版；首次使用需網路及 LINE 登入。
登入與設定保存在 %USERPROFILE%\.sweety，移除 ZIP 資料夾不會刪除設定。
登入加密金鑰保存在目前 Windows 使用者的憑證管理員，不可複製至其他電腦使用。
正式版預設關閉診斷日誌。
啟用診斷時的日誌路徑：%USERPROFILE%\.sweety\logs\sweety.log。
分享診斷資訊前請先檢查，避免分享私密對話或 API Key。

此程式未經數位簽署，Windows 可能顯示發行者無法辨識；請確認下載來源。

Portable Windows x64 build: keep the complete folder, then run Sweety.exe.
Python and Node are bundled. Closing the browser keeps the service running;
close the Sweety control window to quit. User data stays in %USERPROFILE%\.sweety.
This application is unsigned. Diagnostic logging is disabled by default.
