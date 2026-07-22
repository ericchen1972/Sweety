# Sweety Python Panel And LINE Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS PySide6 launcher, localhost FastAPI/SQLite backend, API-backed React dashboard, and test-mode LINE monitor derived from `whomai`.

**Architecture:** The Qt launcher owns application lifecycle and starts a localhost FastAPI server. FastAPI and the monitor controller share repository factories rather than live SQLite connections. The monitor runs on a background thread and delegates macOS UI work and AI calls to injectable adapters so core behavior is testable without touching LINE.

**Tech Stack:** Python 3.11+, PySide6, FastAPI, Uvicorn, SQLite, requests, mss, Pillow, NumPy, RapidOCR/macOS Vision, pytest, React 19, TypeScript, Vitest.

**Repository note:** `/Users/eric/Documents/SweetyGame` is not currently a Git repository, so the usual per-task commit steps are replaced with test checkpoints.

---

## File Structure

- `app/desktop/pyproject.toml`: Python package metadata and runtime/test dependencies.
- `app/desktop/src/sweety_app/config.py`: paths, localhost URLs, locale, and cache settings.
- `app/desktop/src/sweety_app/database.py`: SQLite migrations and connection factory.
- `app/desktop/src/sweety_app/repositories.py`: settings, targets, catalog, messages, and metrics queries.
- `app/desktop/src/sweety_app/schemas.py`: API request/response models.
- `app/desktop/src/sweety_app/api.py`: FastAPI application and static frontend hosting.
- `app/desktop/src/sweety_app/monitor.py`: worker state machine and test-mode orchestration.
- `app/desktop/src/sweety_app/line_mac.py`: macOS LINE window, OCR, click, capture, scroll, close, and paste adapter.
- `app/desktop/src/sweety_app/ai.py`: Sweety/AGNES and OpenAI request adapters plus prompt/history payload creation.
- `app/desktop/src/sweety_app/panel.py`: PySide6/QWebEngine launcher and bridge.
- `app/desktop/src/sweety_app/runtime.py`: Uvicorn thread and orderly shutdown.
- `app/desktop/src/sweety_app/__main__.py`: application entry point.
- `app/desktop/tests/`: repository, API, monitor, AI, panel bridge, and runtime tests.
- `app/frontend/src/api.ts`: typed localhost API client.
- `app/frontend/src/storage.ts`: API-backed state adapter replacing localStorage persistence.
- `app/frontend/src/App.tsx`: loading/error states and async mutations.

## Task 1: Python Package And SQLite Store

**Files:**
- Create: `app/desktop/pyproject.toml`
- Create: `app/desktop/src/sweety_app/__init__.py`
- Create: `app/desktop/src/sweety_app/config.py`
- Create: `app/desktop/src/sweety_app/database.py`
- Create: `app/desktop/src/sweety_app/repositories.py`
- Test: `app/desktop/tests/test_repositories.py`

- [ ] **Step 1: Write failing repository tests**

Cover default settings, target create/list/update/end/revive/delete, reply-enabled filtering, duplicate exact LINE names, custom-item reference deletion, message ordering, and aggregate metrics. Use a temporary SQLite path for every test.

```python
def test_monitor_targets_require_active_and_reply_enabled(repo):
    enabled = repo.create_target(target_payload(name="A", reply_enabled=True))
    repo.create_target(target_payload(name="B", reply_enabled=False))
    ended = repo.create_target(target_payload(name="C", reply_enabled=True))
    repo.end_target(ended["id"])
    assert [item["id"] for item in repo.list_monitor_targets()] == [enabled["id"]]
```

- [ ] **Step 2: Verify repository tests fail**

Run: `cd app/desktop && uv run pytest tests/test_repositories.py -q`

Expected: collection failure because `sweety_app.database` and repositories do not exist.

- [ ] **Step 3: Implement migrations and repositories**

Use `sqlite3.Row`, foreign keys, WAL mode, ISO-8601 timestamps, explicit transactions, and a schema-version table. Keep one connection per repository operation.

- [ ] **Step 4: Verify repository tests pass**

Run: `cd app/desktop && uv run pytest tests/test_repositories.py -q`

Expected: all repository tests pass.

## Task 2: FastAPI Contract

**Files:**
- Create: `app/desktop/src/sweety_app/schemas.py`
- Create: `app/desktop/src/sweety_app/api.py`
- Test: `app/desktop/tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Use `fastapi.testclient.TestClient` against a temporary database. Cover `/api/health`, `/api/state`, settings updates, target lifecycle, reply checkbox, catalog/custom CRUD, dashboard metrics, JSON export, and monitor status placeholders.

```python
def test_target_lifecycle(client):
    created = client.post("/api/targets", json=target_payload()).json()
    assert client.post(f"/api/targets/{created['id']}/end").json()["status"] == "ended"
    revived = client.post(f"/api/targets/{created['id']}/revive").json()
    assert revived["status"] == "active"
    assert revived["reply_enabled"] is False
```

- [ ] **Step 2: Verify API tests fail**

Run: `cd app/desktop && uv run pytest tests/test_api.py -q`

Expected: import failure for `sweety_app.api`.

- [ ] **Step 3: Implement API and stable errors**

Return `{ "code": "duplicate_target_name", "message": "..." }` for domain failures. Add CORS only for the configured localhost frontend origin. Mount `app/frontend/dist` at `/` when present.

- [ ] **Step 4: Verify repository and API tests pass**

Run: `cd app/desktop && uv run pytest tests/test_repositories.py tests/test_api.py -q`

Expected: all tests pass.

## Task 3: React Dashboard Uses The API

**Files:**
- Create: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/storage.ts`
- Modify: `app/frontend/src/App.tsx`
- Modify: `app/frontend/vite.config.ts`
- Test: `app/frontend/src/api.test.ts`

- [ ] **Step 1: Write failing API-client tests**

Test state loading, JSON error propagation, settings save, target actions, and custom catalog mutations with a fake `fetch`.

```typescript
it("surfaces stable API error messages", async () => {
  fetchMock.mockResolvedValue(new Response(JSON.stringify({ code: "duplicate_target_name", message: "Name exists" }), { status: 409 }));
  await expect(api.createTarget(payload)).rejects.toThrow("Name exists");
});
```

- [ ] **Step 2: Verify frontend test fails**

Run: `cd app/frontend && npm test`

Expected: failure because `src/api.ts` does not exist.

- [ ] **Step 3: Implement typed API adapter and async UI mutations**

Load `/api/state` on application start, show an inline retry state on failure, and refresh state after mutations. Remove state writes to `localStorage`; retain only non-authoritative UI preferences if needed.

- [ ] **Step 4: Verify frontend**

Run: `cd app/frontend && npm test && npm run typecheck && npm run build`

Expected: tests, typecheck, and build succeed.

## Task 4: Monitor Controller And Test-Mode Guarantees

**Files:**
- Create: `app/desktop/src/sweety_app/monitor.py`
- Test: `app/desktop/tests/test_monitor.py`

- [ ] **Step 1: Write failing state-machine tests**

Use fake LINE and AI adapters. Verify start/stop idempotency, enabled-target filtering, unread matching, one-contact processing, stop boundaries, and status snapshots.

```python
def test_test_mode_pastes_once_without_writing_history(controller, repo, fake_line):
    controller.run_cycle()
    assert fake_line.pasted == ["draft reply"]
    assert repo.list_messages("target-1") == []
    assert repo.get_target("target-1")["round_trips"] == 0
    assert controller.snapshot()["enabled"] is False
```

- [ ] **Step 2: Verify monitor tests fail**

Run: `cd app/desktop && uv run pytest tests/test_monitor.py -q`

Expected: import failure for `sweety_app.monitor`.

- [ ] **Step 3: Implement controller**

Use `threading.Event` for cooperative stop and interruptible waits. Test mode disables itself after the first pasted draft, keeps the chat open, and performs no repository write except ephemeral runtime status.

- [ ] **Step 4: Connect monitor endpoints**

Inject the controller into `create_app()`. Implement `POST /api/monitor/start`, `POST /api/monitor/stop`, and `GET /api/monitor/status`.

- [ ] **Step 5: Verify Python core tests**

Run: `cd app/desktop && uv run pytest tests/test_repositories.py tests/test_api.py tests/test_monitor.py -q`

Expected: all tests pass.

## Task 5: AI Payload And Provider Adapters

**Files:**
- Create: `app/desktop/src/sweety_app/ai.py`
- Test: `app/desktop/tests/test_ai.py`

- [ ] **Step 1: Write failing AI tests**

Verify at most 20 historical messages, total-message count, persona/weapon inclusion, OCR text inclusion, OpenAI key/model routing, Sweety routing, and secret-free errors.

- [ ] **Step 2: Verify AI tests fail**

Run: `cd app/desktop && uv run pytest tests/test_ai.py -q`

Expected: import failure for `sweety_app.ai`.

- [ ] **Step 3: Implement provider boundary**

Use `requests` with explicit timeouts. Keep provider URLs and bundled prototype credential in one config module; never include credentials in logs or API responses.

- [ ] **Step 4: Verify AI tests pass**

Run: `cd app/desktop && uv run pytest tests/test_ai.py -q`

Expected: all tests pass without network access.

## Task 6: macOS LINE Adapter From whomai

**Files:**
- Create: `app/desktop/src/sweety_app/line_mac.py`
- Create: `app/desktop/src/sweety_app/permissions.py`
- Test: `app/desktop/tests/test_line_mac.py`

- [ ] **Step 1: Write failing pure-logic tests**

Cover AppleScript window-info parsing, exact/containment OCR-name matching, unread contact ordering, geometry calculations, and clipboard restoration using injected command/capture functions.

- [ ] **Step 2: Verify LINE adapter tests fail**

Run: `cd app/desktop && uv run pytest tests/test_line_mac.py -q`

Expected: import failure for `sweety_app.line_mac`.

- [ ] **Step 3: Port only the required whomai operations**

Port permission checks, LINE main/chat window discovery, contact-list capture, unread badge/OCR detection, contact clicking, chat scrolling, chat capture, OCR, and paste-without-send. Remove idle-time gates, legacy fallback UI, chat-history JSON files, automatic sending, and debug scripts.

- [ ] **Step 4: Verify adapter and core tests**

Run: `cd app/desktop && uv run pytest tests/test_line_mac.py tests/test_monitor.py -q`

Expected: tests pass without launching LINE.

## Task 7: PySide6 Launcher And Runtime

**Files:**
- Create: `app/desktop/src/sweety_app/panel.py`
- Create: `app/desktop/src/sweety_app/runtime.py`
- Create: `app/desktop/src/sweety_app/__main__.py`
- Test: `app/desktop/tests/test_panel_bridge.py`
- Test: `app/desktop/tests/test_runtime.py`

- [ ] **Step 1: Write failing bridge/runtime tests**

Verify localized target count, start-to-stop state, monitor error propagation, management URL opening contract, Uvicorn startup readiness, and orderly shutdown.

- [ ] **Step 2: Verify tests fail**

Run: `cd app/desktop && uv run pytest tests/test_panel_bridge.py tests/test_runtime.py -q`

Expected: imports fail for panel/runtime modules.

- [ ] **Step 3: Implement compact KingJoo-style panel**

Use `QWebEngineView` plus `QWebChannel`, `color-scheme: light dark`, a target count, Test Mode badge, Start/Stop button, latest status, management button, tray restore, and quit action.

- [ ] **Step 4: Implement runtime lifecycle**

Start Uvicorn on `127.0.0.1:8891`, serve the production React build from FastAPI, wait for `/api/health`, then show the launcher. Shutdown stops monitor, server, tray, and Qt cleanly.

- [ ] **Step 5: Verify launcher tests**

Run: `cd app/desktop && QT_QPA_PLATFORM=offscreen uv run pytest tests/test_panel_bridge.py tests/test_runtime.py -q`

Expected: all tests pass.

## Task 8: End-To-End Verification

**Files:**
- Modify as failures require, limited to files above.

- [ ] **Step 1: Run the complete automated suite**

Run: `cd app/desktop && uv run pytest -q`

Run: `cd app/frontend && npm test && npm run typecheck && npm run build`

Expected: all commands succeed.

- [ ] **Step 2: Start the desktop app**

Run: `cd app/desktop && uv run python -m sweety_app`

Expected: the panel opens, `/api/health` returns 200, and Open Management Interface loads the API-backed dashboard.

- [ ] **Step 3: Browser verification**

Verify dashboard/settings/targets/catalog in light and dark mode, confirm persistence across reload, and confirm no console errors at desktop and mobile widths.

- [ ] **Step 4: Controlled LINE smoke test**

With one active, checked target and a known unread LINE message, press Start. Confirm that Sweety recognizes the unread target, opens its chat, scrolls down, generates a reply, pastes it without sending, leaves the window open, stops monitoring, and leaves messages/round trips/duration unchanged in SQLite.
