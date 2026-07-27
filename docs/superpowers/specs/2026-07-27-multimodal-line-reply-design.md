# Multimodal LINE Reply Design

## Goal

Replace OCR-based chat-content extraction with one multimodal AI request that receives recent structured history and the current LINE chat screenshot. The model identifies the latest incoming item on the left side and generates the reply in the same request.

Contact-list OCR and unread-badge detection remain unchanged.

## AI contract

The request contains:

- the immutable Sweety safety rules and selected persona;
- at most the latest 20 persisted messages with their existing roles;
- the current LINE chat screenshot as a Base64 image data URL;
- an explicit rule that the left side is the other party, the right side is Sweety, and the latest left-side item must be selected even when it is a sticker, photo, or emoji.

The model must return JSON with:

```json
{
  "message_type": "text",
  "last_msg": "the latest incoming item",
  "msg_reply": "the reply to send"
}
```

Supported message types are `text`, `sticker`, `image`, and `emoji`. Text is preserved as extracted. Non-text content is normalized for history as a readable marker and description, for example `[貼圖] 頭上冒著黑線的無奈卡通角色` or `[照片] 一張超商繳費單`.

AGNES accepts Base64 image data URLs in live testing but does not currently accept grammar-backed `response_format`. The implementation therefore validates prompt-requested JSON locally, including JSON wrapped in Markdown fences, and retries once when the response is unsafe or invalid.

## Runtime flow

1. Detect an enabled unread target using the existing contact-list OCR and badge logic.
2. Open the matching chat, scroll to the bottom, and capture the chat window.
3. Load the latest 20 persisted messages and total message count.
4. Send the history, persona, screenshot, and extraction contract to the selected AI provider.
5. Validate `message_type`, `last_msg`, and `msg_reply`; reject empty, malformed, unknown-type, or unsafe-link replies.
6. Apply the configured reply delay and send `msg_reply` to the same verified LINE window.
7. Only after a successful send, atomically persist the normalized incoming item and assistant reply, increment the round-trip count, and report metrics.
8. On capture, AI, validation, delay cancellation, or send failure, close the chat and persist neither side of the exchange.

The screenshot is transient and is not stored in conversation history.

## Components

- `LineMacAdapter.capture_visible_chat()` owns scrolling, capture, and returning the local screenshot path. Its contact-list OCR behavior is unchanged.
- `AiClient.generate_reply()` accepts the screenshot path and returns a typed reply decision rather than a bare string.
- `MonitorController` validates the decision boundary, sends the reply, and commits the normalized incoming item plus reply after successful delivery.
- `Repository.record_exchange()` remains the atomic persistence boundary; no schema migration is required because media type and description are represented in message content.

## Testing

Tests cover:

- screenshot requests contain recent role-preserving history and a Base64 image block;
- left/right and latest-incoming extraction rules are present in the immutable contract;
- text, sticker, photo, and emoji decisions normalize into readable history entries;
- fenced JSON is accepted while malformed or unknown-type output is rejected;
- unsafe links trigger one regeneration and remain rejected after a second unsafe response;
- successful sends persist the extracted incoming item and reply;
- capture, AI, or send failures persist nothing and do not increment metrics;
- stop requests between capture, AI, delay, and send prevent delivery and persistence.

## macOS 12 compatibility boundary

This feature does not change the published minimum macOS version. The current bundle explicitly declares macOS 13 and contains OpenCV binaries targeting macOS 13 plus NumPy and ONNX Runtime binaries targeting macOS 14. A separate compatibility release must rebuild or replace those OCR dependencies and verify the complete bundle on both Apple Silicon and Intel macOS 12 before lowering `LSMinimumSystemVersion`.
