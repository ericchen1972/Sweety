#!/bin/bash
set -euo pipefail

DESKTOP_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$DESKTOP_DIR/../.." && pwd)"
ICONSET="$DESKTOP_DIR/build/Sweety.iconset"
BASE_ICON="$DESKTOP_DIR/build/Sweety-base.png"

cd "$PROJECT_DIR/app/frontend"
npm run build

cd "$DESKTOP_DIR"
uv sync --extra desktop --extra dev

if [[ -z "${SWEETY_AGNES_KEY:-}" && -f "$PROJECT_DIR/config.json" ]]; then
  SWEETY_AGNES_KEY="$(uv run python - "$PROJECT_DIR/config.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(str(json.load(handle).get("AGNES_KEY", "")).strip())
PY
)"
  export SWEETY_AGNES_KEY
fi
if [[ -z "${SWEETY_AGNES_KEY:-}" ]]; then
  echo "SWEETY_AGNES_KEY is required to build the bundled Sweety provider." >&2
  exit 1
fi

rm -rf "$DESKTOP_DIR/build" "$DESKTOP_DIR/dist/Sweety" "$DESKTOP_DIR/dist/Sweety.app"
mkdir -p "$ICONSET"

sips -Z 1024 --padToHeightWidth 1024 1024 "$PROJECT_DIR/web/images/logo.png" --out "$BASE_ICON" >/dev/null
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$BASE_ICON" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$BASE_ICON" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$DESKTOP_DIR/build/Sweety.icns"

uv run pyinstaller Sweety.spec --noconfirm --clean
codesign --force --deep --sign - --identifier tw.sweety.app \
  --entitlements "$DESKTOP_DIR/Sweety.entitlements" \
  "$DESKTOP_DIR/dist/Sweety.app"
codesign --verify --deep --strict --verbose=2 "$DESKTOP_DIR/dist/Sweety.app"

echo "$DESKTOP_DIR/dist/Sweety.app"
