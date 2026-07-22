# WhomAI-style LINE Chat Window Cleanup Design

## Goal

After Sweety sends or skips a reply, close the detached LINE chat window reliably so the next unread scan sees the LINE main window instead of a foreground chat window.

## Design

- Replace the unverified `AXClose` action with WhomAI's proven Accessibility behavior: click button 1 of the target LINE chat window.
- Make chat-window cleanup return a boolean result so callers can distinguish success from failure.
- Before each unread scan, close every non-main LINE window. This mirrors WhomAI's defensive cleanup and recovers from an earlier close failure.
- Keep the existing targeted close calls on stop, empty reply, send failure, success, and exception paths.
- Do not change OCR, AI generation, reply persistence, delays, or target matching.

## Error Handling

- A missing target chat window counts as already clean and returns success.
- An Accessibility or AppleScript failure returns failure without crashing the monitor loop.
- Pre-scan cleanup is best-effort; unread scanning continues so a transient cleanup failure does not stop monitoring.

## Tests

- Assert the generated close script clicks button 1 and does not invoke `AXClose`.
- Assert pre-scan cleanup runs before unread-contact discovery.
- Assert all non-main windows are included in cleanup and failures return false.
- Run the focused monitor and LINE adapter tests, then the complete desktop test suite and application build.
