# No-Skip Color-Based Chat Reply Design

**Date:** 2026-07-31

## Goal

Once Sweety opens a monitored contact from the unread-contact scan, it must always ask the AI to produce a reply. The AI must understand that the screenshot is a communication-app conversation and identify message ownership by bubble color rather than horizontal position.

## Decisions

- Remove `action` from `ReplyDecision`; there is no `skip` outcome.
- Require non-empty `incoming_summary` and `msg_reply` fields.
- Treat green-background messages as messages sent by the Sweety user.
- Treat gray-background messages as messages sent by the other person.
- Do not instruct the AI to infer ownership from left/right placement.
- Opening a matched unread chat is sufficient evidence that a new message needs a reply.

## Screenshot Interpretation Contract

The prompt must explicitly tell the model that the supplied image is a LINE communication-app conversation screen.

To identify the current incoming batch:

1. Find the lowest visible green-background message.
2. Collect every visible gray-background message after that green message, in screen order.
3. If no green-background message is visible, collect every visible gray-background message in screen order.
4. Do not use left/right placement to identify the sender.

Gray stickers, photos, videos, voice messages, other audio, and emoji-only messages all count as incoming messages. Describe non-text content briefly and objectively, retaining a visible duration when present.

A reply-style box inside a gray message is quoted history. Exclude the quoted preview from `incoming_summary` and collect only the new content outside the box.

The model may use recent persisted history and persona information to compose a natural reply, but `incoming_summary` must contain only the newly collected gray content visible in the current screenshot. It must not add sender labels, paraphrase the batch as a narrative, include green messages, scroll, or infer off-screen content.

## AI Response Contract

`ReplyDecision` contains exactly:

- `incoming_summary`: a non-empty normalized summary of the visible incoming batch.
- `msg_reply`: a non-empty reply that follows the persona and immutable safety rules.

The schema forbids extra fields. A response containing `action`, missing either field, or containing blank content is invalid. Existing AI retry behavior handles the first invalid result; two invalid attempts raise `AiError`.

The existing unsafe-link check remains unchanged. A link-bearing reply is regenerated once and rejected if the retry is also unsafe.

## Monitor Flow

The runtime remains:

1. Scan unread contacts.
2. Match an enabled target.
3. Open the matched chat.
4. Capture the visible conversation.
5. Request a structured reply from the AI.
6. Apply the configured reply delay.
7. Send and verify the outgoing message.
8. Persist the incoming batch and reply.
9. Close the chat.

Remove the `should_reply` property and the monitor's `ai_decision_skipped` / `ai_decision_skip` branch. A valid `ReplyDecision` always proceeds to the reply delay and send stages.

If AI validation fails twice, the monitor logs `target_processing_failed`, does not send or persist an exchange, and closes the chat through the existing recovery path. Send verification and persistence failures retain their existing behavior.

## Diagnostics

When `SWEETY_LOG_ENABLED=1`, continue logging the raw AI response and retaining the last completed chat screenshot. This allows the screenshot, structured result, and monitor stages to be compared for an incident.

Release builds keep diagnostics disabled and continue deleting diagnostic screenshots according to the existing global logging contract.

## Testing

Tests must verify:

- The structured schema requires exactly `incoming_summary` and `msg_reply`.
- Extra `action` fields, missing fields, and blank values are rejected.
- The system and image instructions say this is a communication-app screen, green means self, and gray means the other person.
- The prompt contains no left/right ownership rule and no `skip` outcome.
- The prompt preserves the visible-batch, non-text-content, and quoted-preview rules.
- A successful AI result always enters delay and send handling.
- The monitor no longer has a skip branch or skip events.
- Invalid AI results do not send or persist anything and follow the existing failure logging path.
- The full desktop test suite passes.
- A logging-enabled local test App builds with `SWEETY_LOG_ENABLED=1` and passes code-sign verification.

Build verification must not start monitoring or send LINE messages. `main` remains the only canonical branch, and the unrelated untracked `videos/` directory must remain untouched.

## Out of Scope

- Changing unread-contact OCR or target matching.
- Deterministic pixel-color extraction in application code.
- Cropping or preprocessing screenshots.
- Changing reply delay, outgoing-bubble verification, persistence, personas, providers, or external-link safety rules.
- Publishing a release DMG or changing the public website.
