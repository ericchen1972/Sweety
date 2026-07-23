# Sweety Homepage Download Counter Design

## Goal

Show a truthful public download count beside the “Download Sweety” heading and
increment it once whenever a visitor clicks the enabled Windows or macOS
download action.

GitHub clicks are not downloads and do not affect the count. The system does not
attempt to deduplicate visitors, addresses, browsers, or repeated clicks.

## Public presentation

The download section heading becomes a responsive heading row:

- On large screens, “Download Sweety” remains on the left and the smaller
  localized count appears at the right edge.
- On small screens, the count moves below the heading and aligns left.
- Traditional Chinese uses `已下載 {count} 次`.
- English uses `Downloaded {count} times`.
- Before a valid server value is available, the numeric slot displays an em
  dash instead of a fake zero.

The three download cards and their existing responsive grid remain unchanged.

## Endpoint boundary

Add `web/sweety-downloads.php` as a dedicated public endpoint. Download counting
must not weaken or complicate the token-protected desktop reporting path in
`sweety-metrics.php`.

The endpoint supports:

- `GET`: return `{ "totalDownloads": <non-negative integer> }` with a short
  public cache window.
- `POST`: atomically increment the counter once and return the resulting
  `{ "totalDownloads": <non-negative integer> }` with `Cache-Control: no-store`.
- Other methods: return HTTP 405.
- Database or invalid-result failures: return HTTP 500 without inventing a
  count.

The endpoint never reads or stores IP addresses, cookies, user agents, referrer
data, or platform details.

## Database

Extend `app/tools/sweety_metrics.sql` with a singleton table:

```sql
CREATE TABLE IF NOT EXISTS sweety_download_totals (
    id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    total_downloads BIGINT UNSIGNED NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO sweety_download_totals (id, total_downloads)
VALUES (1, 0)
ON DUPLICATE KEY UPDATE id = VALUES(id);
```

Each POST uses one atomic database expression equivalent to
`total_downloads = total_downloads + 1`, then reads the updated singleton value.
No event-level rows or visitor identifiers are stored.

## Frontend data flow

On page initialization:

1. Fetch the current total from `/sweety-downloads.php`.
2. Accept only a non-negative safe integer.
3. Render the localized count when valid.
4. Retain the em-dash fallback when the request or validation fails.

When `renderDownloads()` enables a Windows or macOS link, it also attaches one
click listener. The listener starts a same-origin POST with `keepalive: true`
and never prevents or delays the browser’s normal file download.

If the POST returns a valid updated total while the page remains active, update
the displayed count. A failed POST does not block the download and does not
optimistically invent a successful increment.

The GitHub link is outside `renderDownloads()` and never receives the listener.

## Deployment

Add `sweety-downloads.php` to the explicit homepage deployment allowlist. The
existing homepage deployment workflow uploads the endpoint, runs the extended
metrics migration, verifies the schema runner result, and publishes the HTML,
CSS, and JavaScript.

The homepage JavaScript and stylesheet cache-busting version must change
together when the feature is published.

## Verification

Automated tests cover:

- Database migration table, singleton seed, and atomic increment contract.
- GET, POST, unsupported-method, and database-failure responses.
- Strict parsing of the returned count.
- Windows and macOS click tracking without GitHub tracking.
- Click tracking never blocking the download navigation.
- Traditional Chinese and English count copy.
- Large-screen right alignment and small-screen left stacking.
- Deployment allowlist and matching asset cache versions.

Live verification records the count, performs one POST, confirms the total
increases by exactly one, then confirms the rendered homepage shows the new
value. This deliberate verification click remains part of the public count,
matching the requested count-on-click behavior.

## Out of scope

- Unique visitor, installation, IP, cookie, or device deduplication.
- Separate Windows and macOS totals.
- Counting GitHub clicks.
- Download completion detection.
- Historical charts, per-day analytics, or an administrative reset control.
