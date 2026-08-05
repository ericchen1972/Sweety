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
2. Move the pointer into the contact-list area.
3. issue two large upward scroll operations.
4. Wait briefly for the contact list to settle.

`unread_contacts()` will invoke this operation after resolving the main window and before capturing it. Unlike the legacy whomai implementation, Sweety will not send `Cmd+A`; avoiding keyboard selection reduces focus-dependent side effects.

## Failure Handling and Diagnostics

Failure to scroll is non-fatal. `unread_contacts()` will continue with the capture so a transient pointer or automation problem does not abort the monitoring cycle. The adapter will expose the scroll result so the monitor diagnostics can record whether the pre-scan normalization succeeded without introducing a separate logging switch.

## Tests

Focused macOS adapter tests will establish:

- the pointer moves into the LINE contact-list area and scrolls upward twice;
- `unread_contacts()` attempts the scroll before capturing the main window;
- a failed scroll attempt still proceeds to capture and OCR.

The test will be observed failing before production code is changed, then rerun after the implementation. The full desktop test suite will run before compilation.

## Build and Verification

Run `app/desktop/build_app.sh`, which produces `app/desktop/dist/Sweety.app` with `SWEETY_LOG_ENABLED=1` by default. Verify the bundle exists, its `Info.plist` embeds diagnostic logging as enabled, and the relevant tests pass. The build will not be packaged or deployed.
