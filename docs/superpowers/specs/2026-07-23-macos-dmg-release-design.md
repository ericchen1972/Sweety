# Sweety macOS DMG Release Design

## Goal

Publish Sweety 1.0.1 as a standard drag-to-install macOS disk image, upload it to the Sweety server, and enable the macOS download action on the public homepage and update manifest.

## Package Layout

The release artifact is `app/desktop/dist/Sweety-macos-latest.dmg`. It is created from a staging directory containing:

- `Sweety.app`, freshly rebuilt and code-sign verified.
- `Applications`, a symbolic link to `/Applications`.

The disk image volume name is `Sweety` and the compressed image format is UDZO. The build verifies the disk image, mounts it, and confirms that both required entries exist before release.

## Release URL

The binary is stored on the server at:

`/sweety.tw/downloads/Sweety-macos-latest.dmg`

The public URL is:

`https://sweety.tw/downloads/Sweety-macos-latest.dmg`

Homepage and update-manifest links append a release query containing version and commit identity, such as `?release=1.0.1-6723ceb`, so intermediary caches cannot serve an older disk image under the fixed filename.

## Deployment Order

1. Run the complete local test suites.
2. Rebuild and verify `Sweety.app`.
3. Build and verify the DMG, including mounted contents, SHA-256, and byte size.
4. Upload the DMG and verify the remote FTP byte size.
5. Update the homepage download configuration and `sweety-update.json` with the cache-busted HTTPS URL.
6. Deploy homepage files.
7. Verify the live homepage, update manifest, HTTP download size, downloaded SHA-256, and downloaded DMG contents.

Uploading the binary before enabling the links prevents a temporarily broken public download.

## Implementation Boundaries

- Add a reusable DMG build script under `app/desktop`.
- Add a release upload helper under `app/tools` that reuses the ignored `web/sftp-config.json` credentials without printing them.
- Extend existing homepage tests so a macOS link must be HTTPS, point to the fixed DMG path, and agree with the update manifest.
- Keep the Windows card disabled.
- Keep the application version at 1.0.1.
- Do not commit the DMG, application bundle, credentials, or other build output.

## Failure Handling

- Stop before upload when app build, code signing, DMG creation, DMG verification, mounted-content inspection, or tests fail.
- Stop before changing public links when the binary upload or remote size verification fails.
- Stop and report the actual state if live HTTP verification returns a stale size or mismatched digest; do not claim release success.

## Verification

- Automated homepage tests protect the enabled macOS download and disabled Windows state.
- A build-script contract test protects the staging-directory structure and DMG verification commands.
- `hdiutil verify` validates the local and downloaded images.
- Mounted inspection confirms `Sweety.app` and `Applications` exist.
- Local and downloaded SHA-256 values must match.
- The live homepage and `sweety-update.json` must expose the same macOS URL.
