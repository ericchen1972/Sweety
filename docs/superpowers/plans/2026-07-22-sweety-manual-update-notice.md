# Sweety Manual Update Notice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Check a static Sweety manifest once at startup and show persistent manual-download notices in the web dashboard and native Python panel when a newer version exists.

**Architecture:** A focused Python `updates.py` module owns strict version parsing, HTTPS filtering, the one-time remote request, and a thread-safe in-memory snapshot. The local API and AppKit panel consume that same snapshot; the React dashboard polls the local API only until the startup check finishes. The remote manifest contains data only and never triggers automatic downloading, installation, or execution.

**Tech Stack:** Python 3.11, requests, FastAPI, PyObjC/AppKit, React 19, TypeScript, Tailwind CSS, Vitest, pytest, Node test runner, static JSON, PHP FTP deployment helper.

---

## File Structure

- Create `app/desktop/src/sweety_app/updates.py`: strict version parser, manifest normalization, thread-safe state, and one-shot remote checker.
- Create `app/desktop/tests/test_updates.py`: unit tests for versions, URLs, request behavior, and shared state.
- Modify `app/desktop/src/sweety_app/config.py`: configurable production manifest URL.
- Modify `app/desktop/src/sweety_app/__main__.py`: start exactly one background update check and inject shared state into both consumers.
- Modify `app/desktop/src/sweety_app/api.py`: expose the normalized shared snapshot at `GET /api/update`.
- Modify `app/desktop/tests/test_api.py`: API pending, available, and unavailable contracts.
- Create `app/frontend/src/UpdateNotice.tsx`: typed notice component and platform-button filtering.
- Create `app/frontend/src/UpdateNotice.test.ts`: pure visibility and platform-order tests.
- Modify `app/frontend/src/api.ts` and `app/frontend/src/api.test.ts`: typed update endpoint client.
- Modify `app/frontend/src/i18n.ts`: Traditional Chinese and English update copy.
- Modify `app/frontend/src/App.tsx`: poll until checked and render the notice above dashboard metrics.
- Modify `app/desktop/src/sweety_app/panel.py`: consume the shared result, dynamically expand the window, render native update controls, and open links.
- Modify `app/desktop/tests/test_panel_bridge.py`: shared snapshot, localized copy, platform omission, and link-opening tests.
- Create `web/sweety-update.json`: production-safe 1.0.1 manifest with no downloads.
- Modify `web/tests/homepage.test.mjs`: manifest validity and deployment allowlist contract.
- Modify `app/tools/deploy_homepage.php`: publish the manifest.

### Task 1: Update Manifest Domain and One-Shot Checker

**Files:**
- Create: `app/desktop/src/sweety_app/updates.py`
- Create: `app/desktop/tests/test_updates.py`
- Modify: `app/desktop/src/sweety_app/config.py`

- [ ] **Step 1: Write failing version and manifest-normalization tests**

Create `app/desktop/tests/test_updates.py` with real payloads and no mocks for pure behavior:

```python
from sweety_app.updates import UpdateState, normalize_manifest, parse_version


def test_parse_version_accepts_only_three_numeric_parts():
    assert parse_version("1.10.0") == (1, 10, 0)
    assert parse_version("1.9.9") == (1, 9, 9)
    for value in ("1.0", "v1.0.1", "1.0.1-beta", "1.0.-1", "1.0.1.0", 101, None):
        assert parse_version(value) is None


def test_normalize_manifest_requires_newer_version_and_https_download():
    result = normalize_manifest(
        {
            "latestVersion": "1.10.0",
            "downloads": {
                "windows": "https://sweety.tw/downloads/Sweety.exe",
                "macos": "http://unsafe.test/Sweety.dmg",
            },
        },
        "1.9.9",
    )
    assert result == {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.10.0",
        "downloads": {"windows": "https://sweety.tw/downloads/Sweety.exe"},
    }


def test_normalize_manifest_hides_equal_older_invalid_and_empty_releases():
    for payload in (
        {"latestVersion": "1.0.1", "downloads": {"macos": "https://sweety.tw/a.dmg"}},
        {"latestVersion": "1.0.0", "downloads": {"macos": "https://sweety.tw/a.dmg"}},
        {"latestVersion": "v2", "downloads": {"macos": "https://sweety.tw/a.dmg"}},
        {"latestVersion": "2.0.0", "downloads": {}},
    ):
        assert normalize_manifest(payload, "1.0.1") == {"checked": True, "updateAvailable": False}


def test_update_state_starts_pending_and_finishes_once():
    state = UpdateState()
    assert state.snapshot() == {"checked": False, "updateAvailable": False}
    state.finish({"checked": True, "updateAvailable": True, "latestVersion": "2.0.0", "downloads": {"macos": "https://sweety.tw/a.dmg"}})
    state.finish({"checked": True, "updateAvailable": False})
    assert state.snapshot()["latestVersion"] == "2.0.0"
```

- [ ] **Step 2: Run the pure tests and verify RED**

Run:

```bash
cd app/desktop
uv run pytest tests/test_updates.py -q
```

Expected: collection fails because `sweety_app.updates` does not exist.

- [ ] **Step 3: Implement strict normalization and thread-safe state**

Create `app/desktop/src/sweety_app/updates.py`:

```python
from __future__ import annotations

import re
import threading
from typing import Any, Protocol
from urllib.parse import urlsplit

import requests


UNAVAILABLE = {"checked": True, "updateAvailable": False}
PENDING = {"checked": False, "updateAvailable": False}


class HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...


def parse_version(value: object) -> tuple[int, int, int] | None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value) is None:
        return None
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def _https_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme == "https" and bool(parsed.netloc) else None


def normalize_manifest(payload: object, current_version: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return dict(UNAVAILABLE)
    current = parse_version(current_version)
    latest_text = payload.get("latestVersion")
    latest = parse_version(latest_text)
    if current is None or latest is None or latest <= current:
        return dict(UNAVAILABLE)
    raw_downloads = payload.get("downloads")
    if not isinstance(raw_downloads, dict):
        return dict(UNAVAILABLE)
    downloads = {
        platform: url
        for platform in ("windows", "macos")
        if (url := _https_url(raw_downloads.get(platform))) is not None
    }
    if not downloads:
        return dict(UNAVAILABLE)
    return {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": latest_text,
        "downloads": downloads,
    }


class UpdateState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._result: dict[str, Any] = dict(PENDING)
        self._finished = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            result = dict(self._result)
            if "downloads" in result:
                result["downloads"] = dict(result["downloads"])
            return result

    def finish(self, result: dict[str, Any]) -> None:
        with self._lock:
            if self._finished:
                return
            self._result = dict(result)
            if "downloads" in self._result:
                self._result["downloads"] = dict(self._result["downloads"])
            self._finished = True


def check_remote_update(
    state: UpdateState,
    current_version: str,
    url: str,
    session: HttpSession | None = None,
) -> None:
    try:
        response = (session or requests.Session()).get(url, timeout=5)
        response.raise_for_status()
        state.finish(normalize_manifest(response.json(), current_version))
    except Exception:
        state.finish(dict(UNAVAILABLE))
```

- [ ] **Step 4: Add one-request success and failure tests**

Append to `app/desktop/tests/test_updates.py`:

```python
from sweety_app.updates import check_remote_update


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class Session:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        if self.error:
            raise self.error
        return self.response


def test_remote_checker_requests_once_and_finishes_shared_state():
    session = Session(Response({"latestVersion": "1.0.2", "downloads": {"macos": "https://sweety.tw/Sweety.dmg"}}))
    state = UpdateState()
    check_remote_update(state, "1.0.1", "https://sweety.tw/sweety-update.json", session)
    assert session.calls == [("https://sweety.tw/sweety-update.json", 5)]
    assert state.snapshot()["updateAvailable"] is True


def test_remote_checker_converts_network_failure_to_unavailable():
    state = UpdateState()
    check_remote_update(state, "1.0.1", "https://sweety.tw/sweety-update.json", Session(error=TimeoutError()))
    assert state.snapshot() == {"checked": True, "updateAvailable": False}
```

- [ ] **Step 5: Add the configurable production URL**

Add to `app/desktop/src/sweety_app/config.py` next to the other remote URLs:

```python
REMOTE_UPDATE_URL = os.getenv(
    "SWEETY_UPDATE_URL",
    "https://sweety.tw/sweety-update.json",
).strip()
```

- [ ] **Step 6: Run tests and commit the domain unit**

Run:

```bash
cd app/desktop
uv run pytest tests/test_updates.py -q
```

Expected: all update-domain tests pass.

Commit:

```bash
git add app/desktop/src/sweety_app/updates.py app/desktop/src/sweety_app/config.py app/desktop/tests/test_updates.py
git commit -m "feat: add one-shot update checker"
```

### Task 2: Shared Startup State and Local API

**Files:**
- Modify: `app/desktop/src/sweety_app/api.py`
- Modify: `app/desktop/src/sweety_app/__main__.py`
- Modify: `app/desktop/tests/test_api.py`
- Modify: `app/desktop/tests/test_metrics_integration_contract.py`

- [ ] **Step 1: Write failing local API contract tests**

Add to `app/desktop/tests/test_api.py`:

```python
from sweety_app.updates import UpdateState


def test_update_endpoint_uses_injected_shared_state(tmp_path):
    state = UpdateState()
    client = TestClient(create_app(Database(tmp_path / "update.sqlite3"), update_state=state))
    assert client.get("/api/update").json() == {"checked": False, "updateAvailable": False}
    state.finish({
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.0.2",
        "downloads": {"macos": "https://sweety.tw/Sweety.dmg"},
    })
    assert client.get("/api/update").json() == {
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.0.2",
        "downloads": {"macos": "https://sweety.tw/Sweety.dmg"},
    }


def test_update_endpoint_defaults_to_checked_unavailable(tmp_path):
    client = TestClient(create_app(Database(tmp_path / "no-update.sqlite3")))
    assert client.get("/api/update").json() == {"checked": True, "updateAvailable": False}
```

- [ ] **Step 2: Run the API tests and verify RED**

Run:

```bash
cd app/desktop
uv run pytest tests/test_api.py -q
```

Expected: `create_app()` rejects `update_state` and `/api/update` returns 404.

- [ ] **Step 3: Inject and expose the shared state**

In `app/desktop/src/sweety_app/api.py`, add:

```python
class UpdateSource(Protocol):
    def snapshot(self) -> dict[str, Any]: ...
```

Extend `create_app`:

```python
def create_app(
    database: Database,
    monitor: MonitorController | None = None,
    frontend_dist: str | Path | None = None,
    persona_validator: PersonaValidator | None = None,
    about_loader: AboutLoader | None = None,
    update_state: UpdateSource | None = None,
) -> FastAPI:
```

Add the endpoint after `/api/health`:

```python
    @app.get("/api/update")
    def update() -> dict[str, Any]:
        return update_state.snapshot() if update_state is not None else {
            "checked": True,
            "updateAvailable": False,
        }
```

- [ ] **Step 4: Add a failing startup wiring contract**

Extend `app/desktop/tests/test_metrics_integration_contract.py` with AST/source assertions that `__main__.py`:

```python
def test_main_starts_one_background_update_check_and_shares_state():
    source = (SOURCE_DIR / "__main__.py").read_text()
    assert "update_state = UpdateState()" in source
    assert "target=check_remote_update" in source
    assert "update_state=update_state" in source
    assert "self.update_state = update_state" in source
```

- [ ] **Step 5: Wire one background request into both consumers**

In `app/desktop/src/sweety_app/__main__.py`:

```python
from .config import APP_VERSION, REMOTE_UPDATE_URL
from .updates import UpdateState, check_remote_update
```

Create the state before the local API, start one worker, and inject it:

```python
    update_state = UpdateState()
    threading.Thread(
        target=check_remote_update,
        args=(update_state, APP_VERSION, REMOTE_UPDATE_URL),
        daemon=True,
    ).start()

    api = create_app(
        database,
        monitor=monitor,
        frontend_dist=FRONTEND_DIST,
        persona_validator=ai,
        about_loader=AboutContentClient(ABOUT_SWEETY_URL),
        update_state=update_state,
    )
```

Add `update_state` as a separate argument to `initWithComponents_permissionStatus_locale_updateState_` and store it as `self.update_state`. Task 4 will pass this stored object into `PanelBridge` when the bridge gains update support. This keeps Task 2 independently runnable while preserving one shared state object. Keep all AppKit view mutations on the existing `refresh_` timer rather than the worker thread.

- [ ] **Step 6: Run focused tests and commit**

Run:

```bash
cd app/desktop
uv run pytest tests/test_api.py tests/test_metrics_integration_contract.py -q
```

Expected: all focused tests pass.

Commit:

```bash
git add app/desktop/src/sweety_app/api.py app/desktop/src/sweety_app/__main__.py app/desktop/tests/test_api.py app/desktop/tests/test_metrics_integration_contract.py
git commit -m "feat: expose shared update state"
```

### Task 3: Web Dashboard Update Card

**Files:**
- Create: `app/frontend/src/UpdateNotice.tsx`
- Create: `app/frontend/src/UpdateNotice.test.ts`
- Modify: `app/frontend/src/api.ts`
- Modify: `app/frontend/src/api.test.ts`
- Modify: `app/frontend/src/i18n.ts`
- Modify: `app/frontend/src/App.tsx`

- [ ] **Step 1: Write failing API and platform-filter tests**

Add to `app/frontend/src/api.test.ts`:

```typescript
it("loads the shared startup update result", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ checked: true, updateAvailable: false }),
  });
  await createApiClient(fetcher as typeof fetch).updateStatus();
  expect(fetcher).toHaveBeenCalledWith("/api/update", expect.objectContaining({ headers: { Accept: "application/json" } }));
});
```

Create `app/frontend/src/UpdateNotice.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { availableDownloads, type UpdateStatus } from "./UpdateNotice";

describe("availableDownloads", () => {
  it("uses Win then Mac order and omits missing platforms", () => {
    const update: UpdateStatus = {
      checked: true,
      updateAvailable: true,
      latestVersion: "1.1.0",
      downloads: { macos: "https://sweety.tw/Sweety.dmg" },
    };
    expect(availableDownloads(update)).toEqual([
      { platform: "macos", url: "https://sweety.tw/Sweety.dmg" },
    ]);
  });

  it("returns no buttons unless a checked update is available", () => {
    expect(availableDownloads({ checked: false, updateAvailable: false })).toEqual([]);
    expect(availableDownloads({ checked: true, updateAvailable: false })).toEqual([]);
  });
});
```

- [ ] **Step 2: Run Vitest and verify RED**

Run:

```bash
cd app/frontend
npm test -- --run src/api.test.ts src/UpdateNotice.test.ts
```

Expected: `updateStatus`, `UpdateNotice`, and `availableDownloads` are missing.

- [ ] **Step 3: Add typed API data and the notice component**

In `app/frontend/src/api.ts` export:

```typescript
export interface UpdateStatus {
  checked: boolean;
  updateAvailable: boolean;
  latestVersion?: string;
  downloads?: { windows?: string; macos?: string };
}
```

Add to the client:

```typescript
updateStatus: () => request<UpdateStatus>("/api/update"),
```

Create `app/frontend/src/UpdateNotice.tsx`:

```tsx
import { Download } from "lucide-react";
import type { Copy } from "./i18n";
import type { UpdateStatus } from "./api";

export type { UpdateStatus } from "./api";

export function availableDownloads(update: UpdateStatus) {
  if (!update.checked || !update.updateAvailable || !update.downloads) return [];
  return (["windows", "macos"] as const).flatMap((platform) => {
    const url = update.downloads?.[platform];
    return url ? [{ platform, url }] : [];
  });
}

export function UpdateNotice({ update, copy }: { update: UpdateStatus; copy: Copy }) {
  const downloads = availableDownloads(update);
  if (!update.latestVersion || downloads.length === 0) return null;
  return (
    <section className="rounded-xl border border-sky-700/40 bg-gradient-to-br from-sky-950 to-zinc-950 p-5 text-white shadow-lg shadow-sky-950/20 sm:p-6" aria-label={copy.updateAvailable}>
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
        <div>
          <h2 className="text-xl font-semibold">{copy.updateHeading.replace("{version}", update.latestVersion)}</h2>
          <p className="mt-2 text-sm leading-6 text-sky-100">
            {copy.updateMacPrefix}<strong className="font-bold text-white">{copy.updateMacEmphasis}</strong>
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {downloads.map(({ platform, url }) => (
            <a key={platform} href={url} target="_blank" rel="noreferrer noopener" className="primary-button whitespace-nowrap">
              <Download className="h-4 w-4" />
              {platform === "windows" ? copy.updateWindows : copy.updateMacOS}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Add exact localized copy**

Add these keys to both locale objects in `app/frontend/src/i18n.ts`:

```typescript
// zh-TW
updateAvailable: "有新版本可下載",
updateHeading: "新版 {version}，立即下載",
updateWindows: "Win 版",
updateMacOS: "Mac OS 版",
updateMacPrefix: "＊Mac OS 版安裝後請重新設定，輔助使用、",
updateMacEmphasis: "螢幕與系統錄音以及自動化等三種權限",

// en
updateAvailable: "A new version is available",
updateHeading: "Version {version} is ready to download",
updateWindows: "Windows",
updateMacOS: "Mac OS",
updateMacPrefix: "* After installing the Mac OS version, configure Accessibility again, plus ",
updateMacEmphasis: "Screen & System Audio Recording and Automation permissions",
```

- [ ] **Step 5: Poll the local result only until checked and render above metrics**

In `app/frontend/src/App.tsx`, import `UpdateNotice` and `UpdateStatus`. Add state in `App`:

```typescript
const [updateStatus, setUpdateStatus] = useState<UpdateStatus>({ checked: false, updateAvailable: false });
```

Add an effect that stops after success, checked completion, unmount, or API failure:

```typescript
useEffect(() => {
  let active = true;
  let timer: number | undefined;
  const readUpdate = async () => {
    try {
      const result = await api.updateStatus();
      if (!active) return;
      setUpdateStatus(result);
      if (!result.checked) timer = window.setTimeout(readUpdate, 500);
    } catch {
      // Update checks never block or degrade the dashboard.
    }
  };
  void readUpdate();
  return () => {
    active = false;
    if (timer !== undefined) window.clearTimeout(timer);
  };
}, []);
```

Pass the value into `Dashboard` and render it before the metrics grid:

```tsx
function Dashboard({ state, locale, copy, updateStatus }: {
  state: AppState;
  locale: Locale;
  copy: Copy;
  updateStatus: UpdateStatus;
}) {
  return (
    <div className="space-y-8">
      <UpdateNotice update={updateStatus} copy={copy} />
      {/* existing metrics and recent-target sections */}
    </div>
  );
}
```

- [ ] **Step 6: Verify frontend and commit**

Run:

```bash
cd app/frontend
npm test -- --run
npm run typecheck
npm run build
```

Expected: all Vitest files pass; typecheck and Vite build succeed.

Commit:

```bash
git add app/frontend/src/UpdateNotice.tsx app/frontend/src/UpdateNotice.test.ts app/frontend/src/api.ts app/frontend/src/api.test.ts app/frontend/src/i18n.ts app/frontend/src/App.tsx
git commit -m "feat: show dashboard update notice"
```

### Task 4: Native Python Panel Update Card

**Files:**
- Modify: `app/desktop/src/sweety_app/panel.py`
- Modify: `app/desktop/tests/test_panel_bridge.py`

- [ ] **Step 1: Write failing bridge, localization, and platform tests**

Extend `app/desktop/tests/test_panel_bridge.py`:

```python
from sweety_app.updates import UpdateState
from sweety_app.panel import panel_update_copy, panel_update_downloads


def test_bridge_shares_update_snapshot_and_opens_only_available_platform(tmp_path):
    database = Database(tmp_path / "panel-update.sqlite3")
    database.migrate()
    repo = Repository(database)
    state = UpdateState()
    state.finish({
        "checked": True,
        "updateAvailable": True,
        "latestVersion": "1.1.0",
        "downloads": {"macos": "https://sweety.tw/Sweety.dmg"},
    })
    opened = []
    bridge = PanelBridge(repo, FakeMonitor(), update_state=state, opener=opened.append, quit_callback=lambda: None)
    assert bridge.snapshot()["update"]["latestVersion"] == "1.1.0"
    assert bridge.open_update("macos") is True
    assert bridge.open_update("windows") is False
    assert opened == ["https://sweety.tw/Sweety.dmg"]


def test_panel_update_copy_and_downloads_are_localized_and_omit_missing_platforms():
    update = {"checked": True, "updateAvailable": True, "latestVersion": "1.1.0", "downloads": {"macos": "https://sweety.tw/Sweety.dmg"}}
    assert panel_update_copy("zh-TW", update)["heading"] == "新版 1.1.0，立即下載"
    assert panel_update_copy("en", update)["heading"] == "Version 1.1.0 is ready to download"
    assert panel_update_downloads(update) == [("macos", "https://sweety.tw/Sweety.dmg")]
```

- [ ] **Step 2: Run the focused panel tests and verify RED**

Run:

```bash
cd app/desktop
uv run pytest tests/test_panel_bridge.py -q
```

Expected: `PanelBridge` lacks `update_state` and the update helper functions do not exist.

- [ ] **Step 3: Add the shared bridge behavior and pure presentation model**

In `app/desktop/src/sweety_app/panel.py`, extend `PanelBridge.__init__` with `update_state: Any | None = None`, save it, merge the snapshot, and add safe platform opening:

```python
    def snapshot(self) -> dict[str, Any]:
        payload = self.monitor.snapshot()
        payload["selectedTargetCount"] = len(self.repository.list_monitor_targets())
        payload["version"] = APP_VERSION
        payload["update"] = self.update_state.snapshot() if self.update_state is not None else {
            "checked": True,
            "updateAvailable": False,
        }
        return payload

    def open_update(self, platform: str) -> bool:
        update = self.snapshot()["update"]
        url = update.get("downloads", {}).get(platform)
        if not update.get("updateAvailable") or not isinstance(url, str):
            return False
        self.opener(url)
        return True
```

Add pure helpers:

```python
def panel_update_downloads(update: dict[str, Any]) -> list[tuple[str, str]]:
    if not update.get("updateAvailable"):
        return []
    downloads = update.get("downloads", {})
    return [(platform, downloads[platform]) for platform in ("windows", "macos") if isinstance(downloads.get(platform), str)]


def panel_update_copy(locale: str, update: dict[str, Any]) -> dict[str, str]:
    version = str(update.get("latestVersion", ""))
    if locale == "zh-TW":
        return {
            "heading": f"新版 {version}，立即下載",
            "note": "Mac OS 版安裝後請重新設定輔助使用、螢幕與系統錄音以及自動化等三種權限",
            "windows": "Win 版",
            "macos": "Mac OS 版",
        }
    return {
        "heading": f"Version {version} is ready to download",
        "note": "After installing Mac OS, configure Accessibility, Screen & System Audio Recording, and Automation again.",
        "windows": "Windows",
        "macos": "Mac OS",
    }
```

- [ ] **Step 4: Add native update-card layout and actions**

In `PanelWindowController.build`, retain references to the logo/title/subtitle/version header views, initialize `self.update_views = []` and `self.update_layout_applied = False`, and leave the base window at 420 × 500.

Add `NSLineBreakByWordWrapping` and `NSView` to the existing `AppKit` imports.

Add these methods to `PanelWindowController`:

```python
    def _apply_update_layout(self, update: dict[str, Any]) -> None:
        if self.update_layout_applied or not panel_update_downloads(update):
            return
        self.update_layout_applied = True
        frame = self.window.frame()
        self.window.setFrame_display_(NSMakeRect(frame.origin.x, frame.origin.y - 150, 420, 650), True)
        for view in (self.logo_view, self.title_label, self.subtitle_label, self.version_label):
            moved = view.frame()
            moved.origin.y += 150
            view.setFrame_(moved)

        card = NSView.alloc().initWithFrame_(NSMakeRect(24, 378, 372, 142))
        card.setWantsLayer_(True)
        card.layer().setCornerRadius_(10.0)
        card.layer().setBorderWidth_(1.0)
        card.layer().setBorderColor_(NSColor.controlAccentColor().colorWithAlphaComponent_(0.55).CGColor())
        card.layer().setBackgroundColor_(NSColor.controlBackgroundColor().CGColor())
        self.window.contentView().addSubview_(card)
        copy = panel_update_copy(self.locale, update)
        card.addSubview_(_label(copy["heading"], (16, 105, 340, 22), 15, True))
        note = _label(copy["note"], (16, 48, 340, 52), 11)
        note.setLineBreakMode_(NSLineBreakByWordWrapping)
        note.setMaximumNumberOfLines_(3)
        card.addSubview_(note)
        downloads = panel_update_downloads(update)
        button_width = 164 if len(downloads) == 2 else 340
        for index, (platform, _url) in enumerate(downloads):
            button = NSButton.buttonWithTitle_target_action_(copy[platform], self, "openUpdate:")
            button.setIdentifier_(platform)
            button.setFrame_(NSMakeRect(16 + index * 176, 10, button_width, 32))
            card.addSubview_(button)
        self.update_views.append(card)

    @objc.IBAction
    def openUpdate_(self, sender) -> None:
        self.bridge.open_update(str(sender.identifier()))
```

Call the layout method from `refresh_`:

```python
update = snapshot.get("update", {})
self._apply_update_layout(update)
```

- [ ] **Step 5: Run panel tests and commit**

Run:

```bash
cd app/desktop
uv run pytest tests/test_panel_bridge.py -q
```

Expected: bridge, copy, platform omission, and existing AppKit button tests pass.

Commit:

```bash
git add app/desktop/src/sweety_app/panel.py app/desktop/tests/test_panel_bridge.py
git commit -m "feat: show native update notice"
```

### Task 5: Production Manifest and Deployment Contract

**Files:**
- Create: `web/sweety-update.json`
- Modify: `web/tests/homepage.test.mjs`
- Modify: `app/tools/deploy_homepage.php`

- [ ] **Step 1: Add a failing public-manifest test**

At the top of `web/tests/homepage.test.mjs`, load the manifest:

```javascript
const updateManifest = JSON.parse(await readFile(new URL('sweety-update.json', webRoot), 'utf8').catch(() => '{}'));
```

Add:

```javascript
test('production update manifest is safe for current 1.0.1 installations and deploys publicly', () => {
  assert.deepEqual(updateManifest, { latestVersion: '1.0.1', downloads: {} });
  const manifest = deployHelper.match(/\$files\s*=\s*\[([\s\S]*?)\];/)?.[1] ?? '';
  assert.match(manifest, /['"]sweety-update\.json['"]/);
});
```

- [ ] **Step 2: Run the Node test and verify RED**

Run:

```bash
node --test web/tests/homepage.test.mjs
```

Expected: the manifest contract fails because the file and deployment entry do not exist.

- [ ] **Step 3: Create and allowlist the production manifest**

Create `web/sweety-update.json`:

```json
{
  "latestVersion": "1.0.1",
  "downloads": {}
}
```

Add `'sweety-update.json',` to `$files` in `app/tools/deploy_homepage.php` next to the other public discovery files.

- [ ] **Step 4: Verify and commit**

Run:

```bash
node --test web/tests/about.test.mjs web/tests/homepage.test.mjs
php -l app/tools/deploy_homepage.php
```

Expected: all Node tests pass and PHP reports no syntax errors.

Commit:

```bash
git add web/sweety-update.json web/tests/homepage.test.mjs app/tools/deploy_homepage.php
git commit -m "feat: publish update manifest"
```

### Task 6: Integrated Verification, Visual Acceptance, Deployment, and GitHub

**Files:**
- Verify: all files from Tasks 1–5
- Create temporarily and do not commit: local higher-version manifest used by `SWEETY_UPDATE_URL`
- Deploy through: `app/tools/deploy_homepage.php`

- [ ] **Step 1: Run the complete automated suite**

Run:

```bash
cd app/frontend
npm test -- --run
npm run typecheck
npm run build

cd ../desktop
uv run pytest -q

cd ../..
node --test web/tests/about.test.mjs web/tests/homepage.test.mjs
php web/tests/sweety_catalog_contract_test.php
php web/tests/sweety_metrics_test.php
php -l app/tools/deploy_homepage.php
```

Expected: all frontend, desktop, Node, and PHP tests pass; typecheck, Vite build, and PHP lint succeed.

- [ ] **Step 2: Verify source security and clean diff**

Run:

```bash
git diff --check
git status --short
git ls-files | rg '(^|/)(node_modules|dist|build|\.venv|config\.json|mysql\.php|sftp-config\.json)(/|$)' && exit 1 || true
```

Expected: no whitespace errors and no secrets, dependencies, or build output are tracked.

- [ ] **Step 3: Launch against a local higher-version fixture**

Create `/tmp/sweety-update-fixture/sweety-update.json` with `apply_patch`; do not add it to the repository:

```json
{
  "latestVersion": "1.1.0",
  "downloads": {
    "windows": "https://sweety.tw/test/Sweety.exe",
    "macos": "https://sweety.tw/test/Sweety.dmg"
  }
}
```

Serve it locally in a long-running terminal session:

```bash
python3 -m http.server 8893 --directory /tmp/sweety-update-fixture
```

Stop the currently running development build, rebuild, and launch the executable with the test-only manifest URL:

```bash
cd app/desktop
./build_app.sh
SWEETY_UPDATE_URL=http://127.0.0.1:8893/sweety-update.json dist/Sweety.app/Contents/MacOS/Sweety
```

The HTTP URL is accepted only for the injected test manifest location. Its platform download values still pass through production `normalize_manifest` and remain HTTPS-only.

- [ ] **Step 4: Visually verify both approved surfaces**

Confirm in the actual rebuilt App:

- Dashboard card is above the four metrics.
- Heading is `新版 1.1.0，立即下載`.
- Both platform buttons are present and open the expected browser URLs.
- Mac permission note is complete and the required phrase is bold.
- Native panel expands from 420 × 500 to 420 × 650.
- Native card appears between the header and selected-target count.
- Relaunching with only the macOS URL shows only `Mac OS 版` on both surfaces.
- Relaunching against production shows no update card for 1.0.1.

- [ ] **Step 5: Publish the production-safe manifest and rebuild the signed App**

Run:

```bash
php app/tools/deploy_homepage.php
```

Expected output includes:

- All allowlisted website files uploaded and size-verified.
- Metrics schema verified.
- `app/desktop/dist/Sweety.app` rebuilt and signed.
- `codesign --verify --deep --strict app/desktop/dist/Sweety.app` succeeds.

- [ ] **Step 6: Verify live production behavior**

Run:

```bash
curl -fsSL https://sweety.tw/sweety-update.json
curl -fsSL http://127.0.0.1:8891/api/update
codesign --verify --deep --strict app/desktop/dist/Sweety.app
```

Expected production JSON:

```json
{"latestVersion":"1.0.1","downloads":{}}
```

Expected local API after the startup check:

```json
{"checked":true,"updateAvailable":false}
```

- [ ] **Step 7: Push the completed source**

Run:

```bash
git status --short --branch
git -c http.version=HTTP/1.1 -c http.postBuffer=524288000 push origin main
git status --short --branch
```

Expected: `main` matches `origin/main` and the working tree is clean.
