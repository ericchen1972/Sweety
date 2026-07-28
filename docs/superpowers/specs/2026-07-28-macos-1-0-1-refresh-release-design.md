# macOS 1.0.1 Refresh Release Design

Date: 2026-07-28

## Goal

Publish the current clean macOS `main` as a refreshed Sweety installer without
changing the application version, then update and deploy the public website so
its macOS download points to the newly verified artifact.

## Version and artifact contract

- Keep Python package version `1.0.1`.
- Keep `CFBundleShortVersionString` at `1.0.1`.
- Keep `CFBundleVersion` at `101`.
- Build the signed application at `app/desktop/dist/Sweety.app`.
- Package it as `app/desktop/dist/Sweety-macos-latest.dmg`.
- Publish the DMG to the stable remote path
  `/sweety.tw/downloads/Sweety-macos-latest.dmg`.
- Do not create or enable a Windows installer.

The stable filename is intentionally reused. Cache invalidation comes from a new
download URL query in the form:

```text
https://sweety.tw/downloads/Sweety-macos-latest.dmg?release=1.0.1-<digest>
```

`<digest>` is the first eight hexadecimal characters of the newly built DMG
SHA-256.

## Build and upload flow

Use `app/tools/deploy_macos_release.php` as the release boundary. It must:

1. Read the existing metrics application token from the remote runtime
   configuration without printing the token.
2. Build the React frontend.
3. Resolve desktop dependencies and build `Sweety.app`.
4. Ad-hoc sign the complete application with the existing entitlements.
5. Verify the application signature with `codesign --verify --deep --strict`.
6. Build a compressed DMG containing `Sweety.app` and an `/Applications`
   symlink.
7. Verify and mount the DMG, then confirm both expected entries.
8. Calculate the local SHA-256 and byte size.
9. Upload the artifact with FTP binary mode to the stable remote path.
10. Require the remote FTP size to equal the local size.

If any step fails, stop before changing the public website contract.

## Website update

After the DMG upload succeeds:

- update the macOS URL in `web/homepage.js`;
- update the macOS URL in `web/sweety-update.json`;
- update the expected macOS URL in `web/tests/homepage.test.mjs`;
- keep `windows: null`, Chinese `稍後提供`, English `Coming soon`, and no
  Windows entry in the update manifest;
- recompute
  `sha256(homepage.css + NUL + homepage.js).slice(0, 12)`;
- set the same new asset version on `homepage.css` and `homepage.js` in
  `web/index.html`.

Run the homepage tests before deployment. They must prove that the new digest,
Mac-only manifest, disabled Windows card, and content-derived cache version are
consistent.

## Deployment and source control

Deploy the updated public files with `app/tools/deploy_homepage.php`. This helper
uploads and size-verifies the website files, preserves the metrics runtime
configuration, verifies the remote metrics/download schema, and rebuilds the
signed desktop app after deployment.

Commit the release URL, test, and cache-version updates to `main`, push
`origin/main`, and leave the unrelated untracked `videos/` directory untouched.

## Verification

Completion requires:

- desktop pytest suite passes before release;
- frontend Vitest suite and production build pass;
- homepage Node suite passes after the digest change;
- local `Sweety.app` signature verifies;
- local DMG verifies and mounts with `Sweety.app` plus the Applications link;
- local DMG SHA-256 begins with the digest used in the website URL;
- FTP reports the same DMG byte size as the local artifact;
- the deployed homepage references the new asset version and download digest;
- deployed `homepage.js` has `windows: null` and the new macOS URL;
- deployed `sweety-update.json` contains only the new macOS URL;
- the public DMG responds successfully at the new cache-busted URL;
- local `main` and `origin/main` resolve to the same release commit;
- `videos/` remains present and untracked.

## Failure handling

- Never reuse the old query digest for a newly built binary.
- Never deploy the new URL before the DMG upload and remote-size verification
  succeed.
- Never publish a partial homepage state where JavaScript, manifest, tests, and
  asset versions disagree.
- Do not delete or replace the previous local artifact until the release helper
  begins its normal build process.
- Do not expose FTP credentials, AGNES credentials, or metrics tokens in logs,
  commits, or responses.
