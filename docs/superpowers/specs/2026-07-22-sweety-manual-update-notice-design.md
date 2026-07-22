# Sweety Manual Update Notice Design

**Date:** 2026-07-22  
**Status:** Approved design pending written-spec review  
**Current application version:** 1.0.1

## Objective

Sweety will not perform automatic updates. When a newer version is available, the application will show a persistent manual-download notice in both the web management dashboard and the native Python panel. Download buttons open the system browser; the application never downloads, installs, or executes an update itself.

## Remote Manifest

The update source is a static public file:

`https://sweety.tw/sweety-update.json`

Contract:

```json
{
  "latestVersion": "1.1.0",
  "downloads": {
    "windows": "https://sweety.tw/downloads/Sweety-1.1.0.exe",
    "macos": "https://sweety.tw/downloads/Sweety-1.1.0.dmg"
  }
}
```

Rules:

- `latestVersion` must be a strict three-part numeric semantic version in `x.x.x` form.
- Download URLs are optional by platform and must use HTTPS.
- A platform with no valid URL is omitted from both interfaces.
- An update is available only when the remote version is strictly higher than `APP_VERSION` and at least one valid download URL remains.
- The production manifest initially advertises version `1.0.1` with no download URLs, so current installations do not display a false update notice.
- A future release only requires publishing its files and changing this manifest.

## Startup Data Flow

Python owns the update check so the two interfaces cannot disagree:

1. Sweety opens normally.
2. A background worker requests the remote manifest once for that application launch.
3. The worker validates and normalizes the version and download URLs.
4. It stores the immutable result in the running application's shared update state.
5. The native panel reads the shared state directly.
6. The local API exposes the same state through `GET /api/update` for the web dashboard.

The request must not block the main AppKit thread, native panel creation, the local API, or the web dashboard. The remote URL is configurable with `SWEETY_UPDATE_URL` for tests and local validation; the default remains the production URL.

## Local API Contract

While the background check is unfinished:

```json
{
  "checked": false,
  "updateAvailable": false
}
```

When a newer release is available:

```json
{
  "checked": true,
  "updateAvailable": true,
  "latestVersion": "1.1.0",
  "downloads": {
    "windows": "https://sweety.tw/downloads/Sweety-1.1.0.exe",
    "macos": "https://sweety.tw/downloads/Sweety-1.1.0.dmg"
  }
}
```

When no update is available or checking fails:

```json
{
  "checked": true,
  "updateAvailable": false
}
```

Network errors and validation details remain internal and are not shown to users.

## Web Dashboard UI

The dashboard places a full-width update card below the page title and monitoring-status row and above the four metric cards.

Traditional Chinese copy:

- Heading: `新版 {version}，立即下載`
- Buttons: `Win 版`, `Mac OS 版`
- Note: `＊Mac OS 版安裝後請重新設定，輔助使用、螢幕與系統錄音以及自動化等三種權限`
- The phrase `螢幕與系統錄音以及自動化等三種權限` is visually emphasized in bold.

The English locale provides equivalent English copy. The card is not dismissible. It remains visible for the entire application session whenever the shared update result is available.

Each button opens its validated HTTPS URL in a new browser tab with safe `noopener noreferrer` behavior. Missing platforms have no button or placeholder.

## Native Python Panel UI

The native panel uses the approved full-notice-card layout:

- With no update, the existing 420 × 500 panel layout remains unchanged.
- When an update becomes available, the panel increases its height and moves the header upward.
- A native update card is inserted between the header and the selected-target statistics.
- It shows the version heading, Mac permission warning, and one button per available platform.
- Buttons use `NSWorkspace` to open the validated HTTPS URL in the default browser.
- The panel does not offer dismiss, skip-version, automatic download, or automatic installation controls.

When the asynchronous result arrives, the panel updates on the AppKit main thread. Layout changes occur at most once per launch.

## Failure and Security Behavior

Sweety behaves as if no update exists when any of the following occurs:

- DNS, connection, TLS, timeout, or HTTP failure.
- Invalid JSON or unexpected field types.
- Missing or invalid `latestVersion`.
- Equal or older remote version.
- No valid platform download URLs.
- A URL uses HTTP or another non-HTTPS scheme.

The checker never evaluates remote code, renders remote HTML, follows an update instruction, downloads an installer, or launches a downloaded file. The manifest can only influence the displayed version and validated HTTPS links.

## Testing and Verification

Automated tests cover:

- Strict version parsing and numeric comparison, including `1.10.0 > 1.9.9`.
- Newer, equal, older, and malformed versions.
- HTTPS filtering and omission of missing platforms.
- Network failure, timeout, invalid JSON, and malformed fields.
- Exactly one startup request and shared results for both consumers.
- `GET /api/update` pending, available, and unavailable responses.
- Web dashboard rendering, localization, safe new-tab links, missing-platform omission, and non-dismissible behavior.
- Native panel update-state formatting, dynamic sizing, button visibility, and URL opening.

Manual verification uses a local test manifest advertising a higher version. It must confirm:

- The dashboard update card appears above metrics.
- The native panel expands and shows the approved complete card.
- A manifest containing only a macOS URL creates only the Mac OS button.
- The permission note and emphasized phrase are visible.
- The current production manifest does not display an update for version 1.0.1.

## Deployment

Deployment includes:

- `web/sweety-update.json` and its homepage deployment allowlist entry.
- Rebuilt frontend assets.
- Rebuilt and signed `app/desktop/dist/Sweety.app`.
- Source commit and push to the public GitHub repository.
- Live verification of the manifest, local API result, both UI surfaces, and application signature.

No application binary is committed to GitHub.
