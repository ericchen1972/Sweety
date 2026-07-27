# macOS Release and Windows Coming-Soon Design

Date: 2026-07-27

## Goal

Publish a fresh macOS installer containing the latest `main` branch changes and
update the public homepage so macOS remains downloadable while Windows is
temporarily unavailable.

## Release behavior

- Rebuild and sign `Sweety.app` from the current `main` branch.
- Build and verify `Sweety-macos-latest.dmg`.
- Upload the DMG to the stable public path
  `/sweety.tw/downloads/Sweety-macos-latest.dmg`.
- Keep application version `1.0.1`.
- Calculate a digest from the newly built DMG and use it in the macOS download
  URL as the `release` query value so browsers and caches fetch the new file.

## Homepage behavior

- The macOS card is enabled and links to the updated stable DMG URL with the
  new release digest.
- The Windows card has no executable URL and remains a disabled control.
- Chinese Windows copy is exactly `稍後提供`.
- English Windows copy is `Coming soon`.
- Only enabled macOS installer clicks are connected to download tracking.
- The GitHub card remains unchanged and untracked.

## Files and consistency

Update the public download contract consistently across:

- `web/homepage.js`
- `web/index.html`
- `web/sweety-update.json`
- `web/llms.txt`
- `web/tests/homepage.test.mjs`

Preserve all unrelated, pre-existing uncommitted homepage changes. Update the
shared homepage CSS/JavaScript cache-busting version after the final content is
known.

## Verification and deployment

1. Add or update tests first and confirm they fail for the old Windows-enabled
   contract.
2. Implement the smallest changes needed for the new download contract.
3. Run the homepage tests and the relevant desktop release tests.
4. Build, sign, package, mount, and verify the macOS DMG.
5. Upload the DMG and verify the remote byte count.
6. Deploy the homepage using the existing deployment helper.
7. Fetch cache-busted public files and confirm:
   - the macOS URL contains the new digest;
   - the Windows download is unavailable;
   - Chinese displays `稍後提供`;
   - English displays `Coming soon`;
   - the deployed DMG size and signature match the release artifact.

