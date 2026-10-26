#!/bin/bash
set -euo pipefail

DESKTOP_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$DESKTOP_DIR/../.." && pwd)"
source "$DESKTOP_DIR/build_compat_env.sh"
export SWEETY_FRONTEND_DIST="$SWEETY_BUILD_ROOT/frontend"
ICONSET="$SWEETY_BUILD_ROOT/Sweety.iconset"
BASE_ICON="$SWEETY_BUILD_ROOT/Sweety-base.png"
export SWEETY_LOG_ENABLED="${SWEETY_LOG_ENABLED:-1}"

if [[ "$SWEETY_LOG_ENABLED" != "0" && "$SWEETY_LOG_ENABLED" != "1" ]]; then
  echo "SWEETY_LOG_ENABLED must be 0 or 1." >&2
  exit 1
fi

cd "$PROJECT_DIR/app/frontend"
"$SWEETY_NODE_PATH" "$(dirname "$SWEETY_NODE_PATH")/../lib/node_modules/npm/bin/npm-cli.js" ci
"$SWEETY_NODE_PATH" "$(dirname "$SWEETY_NODE_PATH")/../lib/node_modules/npm/bin/npm-cli.js" run build -- --outDir "$SWEETY_FRONTEND_DIST" --emptyOutDir

cd "$DESKTOP_DIR"
uv sync --frozen --python "$SWEETY_PYTHON" --extra desktop --extra dev

rm -rf "$SWEETY_BUILD_ROOT/work" "$SWEETY_BUILD_ROOT/dist/Sweety" "$SWEETY_BUILD_ROOT/dist/Sweety.app"
mkdir -p "$ICONSET"

sips -Z 1024 --padToHeightWidth 1024 1024 "$PROJECT_DIR/web/images/logo.png" --out "$BASE_ICON" >/dev/null
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" "$BASE_ICON" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$BASE_ICON" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$SWEETY_BUILD_ROOT/Sweety.icns"

"$UV_PROJECT_ENVIRONMENT/bin/python" -m PyInstaller Sweety.spec --noconfirm --clean --workpath "$SWEETY_BUILD_ROOT/work" --distpath "$SWEETY_BUILD_ROOT/dist"
"$UV_PROJECT_ENVIRONMENT/bin/python" "$DESKTOP_DIR/scripts/audit_macos.py" "$SWEETY_BUILD_ROOT/dist/Sweety.app" --arch "$SWEETY_TARGET_ARCH"
codesign --force --deep --sign - --identifier tw.sweety.app \
  --entitlements "$DESKTOP_DIR/Sweety.entitlements" \
  "$SWEETY_BUILD_ROOT/dist/Sweety.app"
codesign --verify --deep --strict --verbose=2 "$SWEETY_BUILD_ROOT/dist/Sweety.app"

echo "$SWEETY_BUILD_ROOT/dist/Sweety.app"
