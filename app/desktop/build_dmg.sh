#!/bin/bash
set -euo pipefail

DESKTOP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DESKTOP_DIR"

SWEETY_LOG_ENABLED=0 "$DESKTOP_DIR/build_app.sh"

codesign --verify --deep --strict dist/Sweety.app

rm -rf dist/dmg-staging dist/Sweety-macos-latest.dmg
mkdir -p dist/dmg-staging
cp -R dist/Sweety.app dist/dmg-staging/
ln -s /Applications dist/dmg-staging/Applications

hdiutil create \
  -volname Sweety \
  -srcfolder dist/dmg-staging \
  -ov \
  -format UDZO \
  dist/Sweety-macos-latest.dmg
hdiutil verify dist/Sweety-macos-latest.dmg

MOUNT_DIR="$(mktemp -d /tmp/sweety-dmg.XXXXXX)"
ATTACHED=0
cleanup() {
  if [[ "$ATTACHED" -eq 1 ]]; then
    hdiutil detach "$MOUNT_DIR" -quiet >/dev/null 2>&1 || true
  fi
  rm -rf "$MOUNT_DIR"
}
trap cleanup EXIT

hdiutil attach dist/Sweety-macos-latest.dmg \
  -mountpoint "$MOUNT_DIR" \
  -nobrowse \
  -readonly \
  -quiet
ATTACHED=1

[[ -d "$MOUNT_DIR/Sweety.app" ]]
[[ -L "$MOUNT_DIR/Applications" ]]
[[ "$(readlink "$MOUNT_DIR/Applications")" == "/Applications" ]]

hdiutil detach "$MOUNT_DIR" -quiet
ATTACHED=0

shasum -a 256 dist/Sweety-macos-latest.dmg
stat -f %z dist/Sweety-macos-latest.dmg
