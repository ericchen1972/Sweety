# Sweety Windows Inno Setup Release Design

## Goal

Publish the existing Sweety 1.0.1 Windows Inno Setup installer, enable the
Windows download on the public homepage, and expose the same verified download
through the application's update manifest.

## Release artifact

The source artifact is:

`app/desktop/dist/Sweety-Windows-Setup-1.0.1.exe`

The public artifact uses a stable filename:

`https://sweety.tw/downloads/Sweety-Windows-Setup-latest.exe`

The homepage and update manifest append a release query containing version
`1.0.1` and a short digest of the installer. The digest changes whenever the
binary changes, preventing browsers and intermediary caches from serving an
older installer while preserving a stable public path.

## Deployment flow

Add a dedicated Windows release helper under `app/tools`. It reads the existing
ignored FTP configuration, uploads the already-built installer in binary mode,
and compares the remote file size with the local file size. It does not rebuild
the Windows installer on macOS and does not print credentials.

The release order is:

1. Validate the local installer exists, is non-empty, and has the expected
   Windows executable signature.
2. Upload it as `Sweety-Windows-Setup-latest.exe`.
3. Verify the remote size matches the local installer.
4. Enable the Windows URL in `web/homepage.js`.
5. Add the Windows URL to `web/sweety-update.json`.
6. Update public platform metadata that still says Windows is unavailable.
7. Deploy the homepage using the existing homepage deployment helper.

The public links are not changed if the installer upload or remote-size
verification fails.

## Homepage behavior

The existing Windows download card stays in the same location and uses the same
localized action copy. Once `downloadConfig.windows` contains the verified HTTPS
URL, the existing rendering path replaces the disabled “Coming soon” button
with an enabled “Download Windows” link.

The macOS download and GitHub card remain unchanged.

## Update manifest

`web/sweety-update.json` keeps `latestVersion` at `1.0.1` and adds the Windows
installer URL alongside macOS. Existing 1.0.1 installations therefore do not
show a false update notice, while future releases can reuse the Windows
download entry.

## Failure handling

- Stop before upload if the local installer is missing, empty, or not a Windows
  executable.
- Stop before publishing links if FTP upload or remote-size verification fails.
- Stop before declaring the release complete if homepage tests, syntax checks,
  deployment, or live HTTPS verification fails.
- Do not remove or replace the existing macOS release during this workflow.

## Verification

Automated homepage tests must first fail against the currently disabled Windows
configuration, then pass after the Windows URL, update manifest, deployment
contract, and platform metadata are updated.

Before completion:

- Verify the local installer size and executable signature.
- Run the complete homepage test suite and JavaScript/PHP syntax checks.
- Confirm the live homepage JavaScript contains the expected Windows release
  URL.
- Confirm the live update manifest contains both Windows and macOS downloads.
- Fetch the public installer over HTTPS and confirm its content length matches
  the local 79,174,928-byte file.

## Out of scope

- Rebuilding or code-signing the Windows installer on macOS.
- Changing the Windows application code or installer contents.
- Changing the macOS download artifact.
- Publishing a new application version beyond 1.0.1.
