# Retain Last Chat Screenshot Design

## Goal

Preserve the most recent complete LINE chat screenshot while diagnostic logging
is enabled, so a no-reply incident can be compared with the recorded AI raw
response. Release builds must continue deleting chat screenshots.

## Runtime Contract

`LineMacAdapter` receives a `retain_chat_capture` flag from the existing global
`LOG_ENABLED` value. This does not introduce another environment variable or
module-specific switch.

Each capture is first written to `line-chat.next.png`. After the capture finishes
successfully, the temporary file atomically replaces `line-chat.png`. If capture
fails, only the temporary file is removed and the previous complete
`line-chat.png` remains available.

After AI processing:

- with diagnostic logging enabled, `line-chat.png` remains in the Sweety cache
  and the monitor records `screenshot_retained`;
- with diagnostic logging disabled, `line-chat.png` is deleted and the monitor
  records `screenshot_discarded`.

Only one completed screenshot is retained. No timestamped archive or screenshot
history is created.

## Privacy and Startup Cleanup

When `retain_chat_capture` is false, adapter initialization removes any existing
`line-chat.png` and `line-chat.next.png`. This clears evidence left by a previous
diagnostic build when a release build starts. When retention is enabled, adapter
initialization removes only a stale temporary file and preserves the last
completed screenshot until the first successful replacement.

The existing macOS cache path remains unchanged:
`~/Library/Caches/Sweety/line-chat.png`.

## Interface Changes

- Add `retain_chat_capture: bool = False` to `LineMacAdapter`.
- Pass `LOG_ENABLED` from the desktop entrypoint.
- Make `discard_chat_capture()` report whether it deleted or retained the
  adapter-owned screenshot, so `MonitorController` can emit the correct event.
- Preserve the rule that `discard_chat_capture()` never deletes an unrelated
  path.

## Failure Handling

- A failed new capture never replaces or deletes the previous completed image.
- A partial temporary capture is always removed.
- A successful capture replaces the previous image before it is sent to AI.
- Release-mode cleanup remains best-effort and idempotent through
  `missing_ok=True`.

## Tests

Add test-first coverage for:

1. diagnostic mode retains the adapter screenshot after AI processing;
2. release mode deletes the adapter screenshot after AI processing;
3. a successful new capture replaces the previous completed screenshot;
4. a failed new capture removes the partial temporary file and preserves the
   previous completed screenshot;
5. release-mode adapter startup removes diagnostic leftovers;
6. diagnostic-mode adapter startup preserves the completed screenshot but
   removes a stale temporary file;
7. unrelated paths are never deleted;
8. monitor diagnostics use `screenshot_retained` or `screenshot_discarded` to
   match the actual result.

Run the focused LINE adapter and monitor tests, then the complete desktop test
suite. Build the local App through `app/desktop/build_app.sh`, which keeps
`SWEETY_LOG_ENABLED=1`, and confirm the retained screenshot survives an AI
decision. Do not create a DMG or publish a release unless separately requested.
