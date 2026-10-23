#!/bin/bash
set -euo pipefail

DESKTOP_DIR="$(cd "$(dirname "$0")" && pwd)"
export SWEETY_BUILD_ROOT="${SWEETY_BUILD_ROOT:-/Users/eric/Documents/Codex-Temp/sweety-build}"
cd "$DESKTOP_DIR"

SWEETY_LOG_ENABLED=0 "$DESKTOP_DIR/build_app.sh"

codesign --verify --deep --strict "$SWEETY_BUILD_ROOT/dist/Sweety.app"

rm -rf "$SWEETY_BUILD_ROOT/dist/dmg-staging" "$SWEETY_BUILD_ROOT/dist/Sweety-macos-latest.dmg"
mkdir -p "$SWEETY_BUILD_ROOT/dist/dmg-staging"
cp -R "$SWEETY_BUILD_ROOT/dist/Sweety.app" "$SWEETY_BUILD_ROOT/dist/dmg-staging"/
ln -s /Applications "$SWEETY_BUILD_ROOT/dist/dmg-staging"/Applications

hdiutil create \
  -volname Sweety \
  -srcfolder "$SWEETY_BUILD_ROOT/dist/dmg-staging" \
  -ov \
  -format UDZO \
  "$SWEETY_BUILD_ROOT/dist/Sweety-macos-latest.dmg"
hdiutil verify "$SWEETY_BUILD_ROOT/dist/Sweety-macos-latest.dmg"

MOUNT_DIR="$(mktemp -d "$SWEETY_BUILD_ROOT/sweety-dmg.XXXXXX")"
ATTACHED=0
cleanup() {
  if [[ "$ATTACHED" -eq 1 ]]; then
    hdiutil detach "$MOUNT_DIR" -quiet >/dev/null 2>&1 || true
  fi
  rm -rf "$MOUNT_DIR"
}
trap cleanup EXIT

hdiutil attach "$SWEETY_BUILD_ROOT/dist/Sweety-macos-latest.dmg" \
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

shasum -a 256 "$SWEETY_BUILD_ROOT/dist/Sweety-macos-latest.dmg"
stat -f %z "$SWEETY_BUILD_ROOT/dist/Sweety-macos-latest.dmg"
