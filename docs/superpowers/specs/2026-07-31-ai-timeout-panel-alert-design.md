# AI Timeout Panel Alert Design

## Goal

When an AI reply request exhausts its existing timeout and retry behavior, keep the current LINE recovery behavior and show a clear warning in the Sweety panel. The warning helps the user switch AI models or try again later without treating unrelated AI failures as a provider timeout.

## Scope

- Applies to AI reply generation for both the built-in AGNES provider and a user-selected OpenAI provider.
- Does not change the existing request timeout, retry count, reply delay, screenshot retention, send, persistence, or chat-window recovery behavior.
- Does not show the warning for invalid structured output, unsafe links, missing credentials, screenshot errors, LINE automation failures, or send failures.

## Timeout classification

Add a dedicated `AiTimeoutError` derived from `AiError`.

The AI client converts only provider request timeout exceptions into `AiTimeoutError`. The existing retry loop continues to run unchanged. If a later attempt succeeds, no timeout escapes the AI client and no warning is shown. If all attempts are exhausted and the final failure is a timeout, `AiTimeoutError` reaches the monitor.

All other failures retain their current `AiError` or original exception behavior.

## Monitor state lifecycle

The monitor owns a transient boolean state exposed in its snapshot as `aiTimeoutAlert`.

- Initial value: hidden.
- Immediately before every real AI reply request: hidden. This represents the assumption that the new execution will succeed.
- When that request ends with `AiTimeoutError`: shown.
- When the user presses Stop: hidden immediately.
- Ordinary unread scans do not clear it. If there is no new AI execution, the previous timeout remains visible so the user can act on it.
- Starting the monitor without yet making an AI request does not clear the warning; Stop is the explicit way to dismiss it without another request.

The existing target failure recovery remains in place. A timeout still discards or retains the capture according to diagnostic mode, closes the opened LINE chat window, sends no reply, and persists no exchange.

## Panel presentation

The native macOS panel adds a hidden alert box directly above the Start/Stop button. It uses a compact warning treatment with an orange/yellow background or border that remains readable in macOS light and dark appearances.

Copy:

- Traditional Chinese: `AI 目前沒有回應，請切換 AI 模型或稍後再試。`
- English: `AI is not responding. Switch AI models or try again later.`

The panel already refreshes from the monitor snapshot once per second, so it shows and hides the alert without a new callback or UI thread coupling. The alert occupies the designated space only when visible and must not cover the status text or Start/Stop button.

## Diagnostics

The existing `target_processing_failed` event continues to record the failure and stage. Its `error_type` becomes `AiTimeoutError` for a classified timeout, which keeps the reason inspectable while respecting the global `SWEETY_LOG_ENABLED` switch.

No new logging switch or raw response behavior is introduced.

## Tests

Automated coverage will verify:

1. Provider timeout exceptions become `AiTimeoutError` only after the existing retry behavior is exhausted.
2. A successful retry returns normally and does not surface a timeout.
3. Monitor timeout failure shows `aiTimeoutAlert`, closes the LINE chat, sends nothing, and persists nothing.
4. A non-timeout `AiError` does not show the alert.
5. Stop hides the alert.
6. The next actual AI execution hides the previous alert before calling the AI, and shows it again only if that execution also times out.
7. The panel copy is localized and snapshot-driven.

