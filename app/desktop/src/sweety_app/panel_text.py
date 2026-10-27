"""Shared localized panel text for macOS and Windows."""
from __future__ import annotations

from typing import Any

STATUS_COPY = {
    "zh-TW": {
        "api_key_required": "請到基本設定輸入所選 AI 的 API Key",
        "codex_not_ready": "請到基本設定檢查 Codex 連線並登入 ChatGPT",
        "stopped": "已停止",
        "monitoring": "正在監控新訊息",
        "waiting": "等待新訊息",
        "processing": "正在處理",
        "permission_required": "需要 macOS 權限",
        "line_login_required": "請先到管理介面登入 LINE",
        "line_window_required": "請先到管理介面登入 LINE",
        "target_required": "請先勾選至少一個對象",
        "error": "發生錯誤",
        "ai_rate_limited": "AI 額度或速率已達上限，請檢查 AI 設定",
    },
    "en": {
        "api_key_required": "Enter the selected AI API key in Settings",
        "codex_not_ready": "Check Codex and sign in to ChatGPT in Settings",
        "stopped": "Stopped",
        "monitoring": "Monitoring for new messages",
        "waiting": "Waiting for new messages",
        "processing": "Processing",
        "permission_required": "macOS permissions required",
        "line_login_required": "Log in to LINE in management first",
        "line_window_required": "Log in to LINE in management first",
        "target_required": "Select at least one target first",
        "error": "Error",
        "ai_rate_limited": "AI quota or rate limit reached; check AI settings",
    },
    "ja": {
        "api_key_required": "設定で選択したAIのAPI Keyを入力してください",
        "codex_not_ready": "設定でCodex接続を確認し、ChatGPTにログインしてください",
        "stopped": "停止中",
        "monitoring": "新着メッセージを監視中",
        "waiting": "新着メッセージを待っています",
        "processing": "処理中",
        "permission_required": "macOSの権限が必要です",
        "line_login_required": "管理画面でLINEにログインしてください",
        "line_window_required": "管理画面でLINEにログインしてください",
        "target_required": "対象を1人以上選択してください",
        "error": "エラー",
        "ai_rate_limited": "AIの利用上限です。AI設定を確認してください",
    },
}

AI_TIMEOUT_ALERT_COPY = {
    "zh-TW": "AI 目前沒有回應，請切換 AI 模型或稍後再試。",
    "en": "AI is not responding. Switch AI models or try again later.",
    "ja": "AIが応答していません。AIモデルを切り替えるか、しばらくしてから再試行してください。",
}

PANEL_SUBTITLE = "Scam Insecticide"

PANEL_UI_COPY = {
    "zh-TW": {"selected_targets": "已勾選對象", "start": "開始", "stop": "停止", "open_management": "開啟管理介面", "quit_app": "結束 App", "show": "顯示 Sweety", "quit": "結束"},
    "en": {"selected_targets": "Selected targets", "start": "Start", "stop": "Stop", "open_management": "Open management", "quit_app": "Quit App", "show": "Show Sweety", "quit": "Quit"},
    "ja": {"selected_targets": "選択中の対象", "start": "開始", "stop": "停止", "open_management": "管理画面を開く", "quit_app": "Appを終了", "show": "Sweetyを表示", "quit": "終了"},
}


def _supported_locale(locale: str) -> str:
    return locale if locale in {"zh-TW", "ja"} else "en"


def panel_ui_copy(locale: str) -> dict[str, str]:
    return {**PANEL_UI_COPY[_supported_locale(locale)], "subtitle": PANEL_SUBTITLE}


def permission_alert_copy(locale: str, missing_permissions: list[str] | tuple[str, ...]) -> dict[str, str]:
    language = _supported_locale(locale)
    names = {
        "zh-TW": {"Accessibility": "輔助使用", "Screen Recording": "螢幕錄製", "System Events": "System Events 自動化", "LINE": "LINE 自動化"},
        "en": {},
        "ja": {"Accessibility": "アクセシビリティ", "Screen Recording": "画面収録", "System Events": "システムイベントのオートメーション", "LINE": "LINEオートメーション"},
    }
    missing = ", ".join(names[language].get(name, name) for name in missing_permissions)
    if language == "zh-TW":
        return {"title": "Sweety 需要 macOS 權限", "message": f"尚未允許：{missing}。請完成授權，然後重新啟動 Sweety。"}
    if language == "ja":
        return {"title": "SweetyにはmacOSの権限が必要です", "message": f"未許可：{missing}。権限を許可してからSweetyを再起動してください。"}
    return {"title": "Sweety needs macOS permissions", "message": f"Not yet allowed: {missing}. Grant access, then restart Sweety."}


def ai_timeout_alert_copy(locale: str) -> str:
    return AI_TIMEOUT_ALERT_COPY[_supported_locale(locale)]


def status_text(locale: str, snapshot: dict[str, Any]) -> str:
    language = _supported_locale(locale)
    status = str(snapshot.get("status", "stopped"))
    text = STATUS_COPY[language].get(status, status)
    if snapshot.get("currentTarget"):
        text += f"：{snapshot['currentTarget']}" if language == "zh-TW" else f": {snapshot['currentTarget']}"
    if snapshot.get("message") and status not in {"permission_required", "line_window_required", "target_required"}:
        text += f" ({snapshot['message']})"
    return text
