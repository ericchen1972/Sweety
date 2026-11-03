# 給 Windows Codex 的交接提示

請在 SweetyGame 的既有 main 工作，不開分支或 worktree。先檢查本機未提交修改並保留，再拉取 origin/main；不要 reset --hard 或覆蓋本機資料。

這次版本是 2.0.3。Mac 端已新增四位惡搞基礎人設及無文字插圖：仙界韓天尊（韓立，男，65+）、後宮甄嬛（甄婉，女，35–50）、霸道總裁（顧霆深，男，35–50）、紅樓黛玉（林若黛，女，20–35）。原24位保留，共28位。canonical 檔案是 `app/catalog/base_personas.json`，圖在 `web/images/personas/`，前後端與SQL生成檔已同步。伺服器人設也已更新；不需要重跑整份 base_catalog.sql，以免覆寫伺服器提示詞。

## Windows／Mac 分開更新：請完成 Windows 實機驗證與必要修正

共用 Python 後端 `app/desktop/src/sweety_app/updates.py` 已修改：用 `sys.platform` 將 win32 對應 windows、darwin 對應 macos，只讀自己平台的 `latestVersion` 與 `downloadUrl`。伺服器 JSON 格式如下：

```json
{
  "latestVersion": "2.0.2",
  "downloads": {
    "windows": "https://sweety.tw/downloads/Sweety-Windows-Setup-2.0.2.exe",
    "macos": "https://sweety.tw/#download"
  },
  "platforms": {
    "windows": {
      "latestVersion": "2.0.2",
      "downloadUrl": "https://sweety.tw/downloads/Sweety-Windows-Setup-2.0.2.exe"
    },
    "macos": {
      "latestVersion": "2.0.2",
      "downloadUrl": "https://sweety.tw/downloads/Sweety.dmg?release=2.0.2-20261027"
    }
  }
}
```

根層舊欄位凍結於2.0.2，供舊App過渡；2.0.3起不再用根層欄位判斷。缺少自己平台、版本不合法、URL不是HTTPS、版本相同或更舊時都不提示。不能回退到另一平台或共用版本。回傳給UI的既有 `downloads` 結構只放自己的平台。正式manifest仍為2.0.2，因為2.0.3安裝檔尚未建立及驗證，請勿提前發布不存在的2.0.3下載。

請驗證 Windows 浮動面板及前端只顯示 Windows 更新連結，新增人設能顯示正確分齡、三語內容與圖片。測試情境：Windows 2.0.4/Mac 2.0.3時，已裝Windows 2.0.3應提示、已裝Mac 2.0.3不提示；反向也要驗證。App啟動同步API後應接受完整三語人設，不應因缺少日文整批拒絕。

```powershell
python -m pytest app/desktop/tests/test_updates.py app/desktop/tests/test_platform_updates.py app/desktop/tests/test_release_manifest.py app/desktop/tests/test_parody_personas.py app/desktop/tests/test_release_version.py -q
cd app/frontend
npm ci
npm test -- --run
npm run build
```

再跑Windows適用的完整後端測試；Mac原生測試在Windows應按平台跳過。確認Windows檢出 `app/frontend/public/images` 的連結是否可用，必要時在建置流程從 `web/images` 複製實際檔案，避免Git在Windows將symlink檢出為文字後導致圖片漏包。

測試包必須將唯一日誌開關 `SWEETY_LOG_ENABLED=1` 打包進runtime設定；正式安裝包用0。不能只依賴建置Shell的環境變數，從Explorer開啟後仍須正確套用。日誌位於 `%USERPROFILE%\.sweety\logs\sweety.log`。最終交付放專案既有dist，使用穩定檔名，先驗證替代品再清除舊交付，保留使用者資料及仍在用的runtime。

## 發布 Windows 2.0.3 時

1. 建置並在Windows安裝、啟動、驗證2.0.3後，才上傳安裝檔。`deploy_windows_release.php` 目前仍指向已發布2.0.2，請依實際2.0.3交付修正路徑、上傳檔名及對應測試，確認遠端檔案大小、雜湊與可下載狀態。
2. 先讀取並備份伺服器**當下最新** `sweety-update.json`，保留Mac最新值及凍結的根層欄位。不要直接以過時本機manifest覆蓋線上Mac更新。
3. 對最新manifest副本執行下列工具，只改Windows欄位（URL換成實際驗證過的安裝檔網址）：

   ```powershell
   python app/tools/set_update_release.py --manifest <最新manifest副本> --platform windows --version 2.0.3 --url <已驗證的HTTPS安裝檔網址>
   ```

4. 檢查diff只有 `platforms.windows` 改變，再原子發布manifest，公開讀回核對。根層 `latestVersion` 不提高、`platforms.macos` 不改。
5. 若需要更新官網Windows下載按鈕，只改Windows連結，保留Mac既有下載。提交本次Windows修正並推送main，回報commit、實機驗證、交付路徑、日誌開關與正式manifest版本。

平台分開的Python判斷已完成，不需要另外做一套Windows版本比較器；只需處理Windows端實際驗證發現的問題及發布流程。
