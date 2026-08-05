# macOS LINE Contact List Scroll-to-Top Design

## Goal

Before Sweety captures the LINE main window for unread-contact detection, return the contact list to its top position. This keeps the fixed 72-pixel contact-row grid aligned with the captured image and prevents unread badges near a shifted row boundary from being excluded.

## Scope

- Change only the macOS LINE adapter and its focused tests.
- Build the local macOS test App with diagnostic logging enabled.
- Do not create a DMG, publish a release, change Windows behavior, or modify unrelated files.

## Approach

Add a small `scroll_main_window_to_top` operation to `LineMacAdapter`. It will:

1. Activate LINE and obtain the current main-window geometry.
2. Move the pointer to the center of the LINE main window.
3. Use the legacy whomai AppleScript sequence: `Cmd+A`, then the Home key (`key code 115`).
4. Treat any AppleScript failure as a failed normalization attempt; do not issue a separate mouse-scroll fallback.

`unread_contacts()` will invoke this operation after resolving the main window and before capturing it. The keyboard sequence is retained because large PyAutoGUI scroll values alone do not reliably reach the top on macOS LINE, and no independent mouse-scroll fallback is used.

## Failure Handling and Diagnostics

Failure to scroll is non-fatal. `unread_contacts()` will continue with the capture so a transient pointer or automation problem does not abort the monitoring cycle. The adapter will expose the scroll result so the monitor diagnostics can record whether the pre-scan normalization succeeded without introducing a separate logging switch.

## Tests

Focused macOS adapter tests will establish:

- the pointer moves into the LINE main window and sends whomai's `Cmd+A` and Home sequence;
- AppleScript failure returns `False` without a mouse-scroll fallback;
- `unread_contacts()` attempts the scroll before capturing the main window;
- a failed scroll attempt still proceeds to capture and OCR.

The test will be observed failing before production code is changed, then rerun after the implementation. The full desktop test suite will run before compilation.

## Build and Verification

Run `app/desktop/build_app.sh`, which produces `app/desktop/dist/Sweety.app` with `SWEETY_LOG_ENABLED=1` by default. Verify the bundle exists, its `Info.plist` embeds diagnostic logging as enabled, and the relevant tests pass. The build will not be packaged or deployed.
