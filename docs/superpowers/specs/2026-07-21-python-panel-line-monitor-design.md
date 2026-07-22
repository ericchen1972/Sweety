# Sweety Python Panel And LINE Monitor Design

## Goal

Build the first macOS Sweety desktop runtime: a small PySide6 launcher, a localhost FastAPI service backed by SQLite, and a background LINE monitor derived from `whomai`. The browser dashboard, launcher, and monitor use the same API and database.

## Scope

This iteration runs in test mode only. It detects new LINE messages for enabled targets, opens matching chat windows, captures and reads the conversation, asks the configured AI for a reply, and pastes that reply into LINE without sending it. Test-mode activity does not create conversation records, increment round trips, or change duration metrics.

Windows packaging, automatic updates, production message sending, and the remote Sweety aggregate-hours service are outside this iteration.

## Runtime Architecture

The desktop app starts three cooperating units in one Python application:

1. A PySide6 launcher owns the visible desktop window and system tray lifecycle.
2. FastAPI serves localhost JSON endpoints and the built React dashboard. SQLite is the only persistent application store.
3. A monitor worker runs LINE OCR and desktop automation on a background thread. It communicates with the rest of the app through a controller with explicit start, stop, status, and snapshot methods.

OCR and AI work never run on the Qt UI thread. The launcher remains responsive while monitoring is active.

## Launcher Panel

The launcher follows the compact KingJoo panel pattern and the operating system light/dark color scheme. It contains:

- Sweety identity and version.
- Number of active targets whose reply checkbox is enabled.
- A primary Start button that becomes a red Stop button while monitoring.
- A visible Test Mode label.
- The latest short worker status, including the contact currently being processed or the last failure.
- An Open Management Interface button that opens the localhost dashboard in the default browser.
- A Quit App command. Closing the window hides it; quitting stops the worker and local server.

Traditional Chinese is used only when the system locale is `zh-TW`; every other locale uses English.

## Persistence

SQLite stores settings, targets, custom personas, custom weapons, conversations, messages, and runtime state. Base personas and weapons remain server-provided catalog data and are mirrored locally for assignment and offline display.

The React application stops using `localStorage` as its source of truth. On first API startup, the database is initialized with default settings and an empty target list. Existing development-only browser data is not automatically imported.

Conversation messages use normalized SQLite rows. JSON is produced only at the AI boundary and when the user exports a target record.

## Local API

The service exposes endpoints for:

- Health and application status.
- Settings read and update.
- Dashboard metrics.
- Active and ended target CRUD, reply enablement, end, revive, permanent delete, and JSON export.
- Base and custom persona/weapon reads and custom item CRUD.
- Monitor start, stop, and current snapshot.

The API rejects duplicate target names, invalid delay ranges, missing assignments, and deletion of referenced custom items. Responses use stable JSON error codes plus localized display messages.

## LINE Monitoring Flow

Each monitoring cycle:

1. Loads active targets with reply enabled from SQLite.
2. Waits for the configured check interval using an interruptible stop event.
3. Locates the LINE main window and captures the contact list.
4. Uses the proven `whomai` unread-message detection and OCR pipeline.
5. Matches OCR names only against enabled target names. Exact normalized matching is preferred; the limited `whomai` containment fallback is retained for OCR noise and logged when used.
6. Processes matching contacts in the order returned by the unread detector.
7. Opens one chat window, scrolls it to the bottom, captures the visible conversation, and obtains its text.
8. Loads the latest 20 stored messages and total stored-message count, then composes the AI request with the target persona and weapon.
9. Waits a random duration within the configured reply-delay range.
10. Pastes the generated reply into the LINE input box without pressing Enter.
11. Stops the cycle immediately after the first pasted draft so the user can inspect it. The chat window remains open.

Starting the monitor again performs a fresh unread scan. Stop is cooperative and prevents new clicks, AI calls, and paste actions as soon as the current safe boundary is reached.

## AI Boundary

The provider adapter supports Sweety and OpenAI settings. Sweety uses the bundled AGNES credential for this prototype; OpenAI uses the user-supplied key and model. The prompt receives persona, weapon, latest OCR text, the most recent 20 stored messages, and total message count.

The complete-history tool contract is defined in the adapter, but it returns stored SQLite history only. Because test mode creates no messages, generated drafts never become AI memory.

## Permissions And Safety

At startup, the app checks macOS Screen Recording and Accessibility permissions using the existing `whomai` permission helpers. Missing permissions keep monitoring stopped and present an actionable launcher error.

The worker verifies that LINE and the intended chat window are available before every destructive UI action. Test mode has no send action. Clipboard contents are restored after a successful or failed paste attempt where the platform permits it.

## Error Handling

LINE-not-running, window-not-found, OCR failure, unmatched unread names, AI failure, and paste failure are separate status outcomes. Recoverable failures end the current cycle and leave monitoring available for another Start. Unexpected worker exceptions are captured into status and logs without crashing Qt or FastAPI.

Logs exclude API keys and full screenshot contents. Temporary screenshots live under the application cache directory and are replaced on each cycle.

## Testing

Unit tests cover database migrations and repositories, API validation and lifecycle behavior, monitor state transitions, target filtering and OCR-name matching, prompt payload limits, and test-mode no-write guarantees. Desktop automation is behind injectable adapters so tests use fakes instead of clicking the real LINE app.

Integration verification starts the local service against a temporary SQLite database, runs the React application against it, and verifies launcher start/stop state. A final manual macOS smoke test uses LINE with a controlled target to confirm unread detection, chat opening, bottom scrolling, OCR, draft generation, and paste-without-send behavior.
