# Multimodal LINE Reply Design

## Goal

Replace OCR-based chat-content extraction with one multimodal AI request that receives recent structured history and the current LINE chat screenshot. The model identifies the complete visible batch of new incoming items on the left side, condenses that batch into one history entry, and generates one reply in the same request.

Contact-list OCR and unread-badge detection remain unchanged.

## AI contract

The request contains:

- the immutable Sweety safety rules and selected persona;
- at most the latest 20 persisted messages with their existing roles;
- the current LINE chat screenshot as a Base64 image data URL;
- an explicit rule that the left side is the other party and the right side is Sweety;
- a visible-message boundary rule that finds the lowest right-side item and selects every left-side item below it in top-to-bottom order;
- a fallback rule that selects every visible left-side item when no right-side item is visible;
- an explicit limit that the model only uses the current bottom screenshot and never infers or requests messages above the visible viewport.

The model must return JSON with:

```json
{
  "action": "reply",
  "incoming_summary": "one faithful summary of the visible incoming batch",
  "msg_reply": "the reply to send"
}
```

`action` is either `reply` or `skip`. A `reply` decision requires a non-empty `incoming_summary` and `msg_reply`. The summary preserves the meaning and order of every selected visible item while storing the batch as one incoming history record. Non-text items use readable markers and objective descriptions, for example `[貼圖] 頭上冒著黑線的無奈卡通角色` or `[照片] 一張超商繳費單`.

A `skip` decision is required when the lowest visible item is on the right or when no left-side item appears below the lowest right-side item. For `skip`, both `incoming_summary` and `msg_reply` must be empty. Sweety sends nothing and persists nothing.

The boundary is deliberately viewport-scoped. If enough incoming messages push the previous right-side item above the screenshot, all left-side items currently visible in the bottom screenshot are treated as the new batch. Sweety does not scroll upward or capture additional pages.

AGNES accepts Base64 image data URLs in live testing but does not currently accept grammar-backed `response_format`. The implementation therefore validates prompt-requested JSON locally, including JSON wrapped in Markdown fences, and retries once when the response is unsafe or invalid.

## Runtime flow

1. Detect an enabled unread target using the existing contact-list OCR and badge logic.
2. Open the matching chat, scroll to the bottom, and capture the chat window.
3. Load the latest 20 persisted messages and total message count.
4. Send the history, persona, screenshot, and extraction contract to the selected AI provider.
5. The model finds the lowest visible right-side item, selects all visible left-side items below it, and returns one `reply` or `skip` decision.
6. Validate `action`, `incoming_summary`, and `msg_reply`; reject malformed output, inconsistent empty fields, or unsafe-link replies.
7. For `skip`, close the chat without delay, delivery, persistence, round-trip increment, or metrics.
8. For `reply`, apply the configured reply delay and send `msg_reply` to the same verified LINE window.
9. Only after a successful send, atomically persist `incoming_summary` as one incoming message plus the assistant reply, increment the round-trip count, and report metrics.
10. On capture, AI, validation, delay cancellation, or send failure, close the chat and persist neither side of the exchange.

The screenshot is transient and is not stored in conversation history.

## Components

- `LineMacAdapter.capture_visible_chat()` owns scrolling, capture, and returning the local screenshot path. Its contact-list OCR behavior is unchanged.
- `AiClient.generate_reply()` accepts the screenshot path and returns a typed action, incoming summary, and reply rather than one extracted last item.
- `MonitorController` exits cleanly on `skip`; on `reply`, it sends the reply and commits the single incoming summary plus reply after successful delivery.
- `Repository.record_exchange()` remains the atomic persistence boundary. No schema migration is required because the selected batch is condensed into existing message content.

## Testing

Tests cover:

- screenshot requests contain recent role-preserving history and a Base64 image block;
- the prompt selects every visible left-side item below the lowest right-side item in top-to-bottom order;
- a screenshot with no visible right-side item selects all visible left-side items;
- mixed text, sticker, photo, and emoji batches condense into one faithful history entry;
- a lowest right-side item with no left-side item below it returns `skip`;
- `skip` causes no delay, send, persistence, round-trip increment, or metrics;
- fenced JSON is accepted while malformed actions and inconsistent empty fields are rejected;
- unsafe links trigger one regeneration and remain rejected after a second unsafe response;
- successful sends persist one incoming summary and one reply;
- capture, AI, or send failures persist nothing and do not increment metrics;
- stop requests between capture, AI, delay, and send prevent delivery and persistence.

## macOS 12 compatibility boundary

This feature does not change the published minimum macOS version. The current bundle explicitly declares macOS 13 and contains OpenCV binaries targeting macOS 13 plus NumPy and ONNX Runtime binaries targeting macOS 14. A separate compatibility release must rebuild or replace those OCR dependencies and verify the complete bundle on both Apple Silicon and Intel macOS 12 before lowering `LSMinimumSystemVersion`.
