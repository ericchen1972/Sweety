#!/bin/bash
# Sourced by both compatibility build entry points.
: "${SWEETY_TARGET_ARCH:?Set SWEETY_TARGET_ARCH to arm64 or x86_64}"
: "${SWEETY_NODE_PATH:?Set SWEETY_NODE_PATH to verified official Node 22.23.4 executable}"
: "${SWEETY_PYTHON:?Set SWEETY_PYTHON to architecture-matched Python 3.12.11 executable}"
case "$SWEETY_TARGET_ARCH" in
  arm64) NODE_ARCH=arm64 ;;
  x86_64) NODE_ARCH=x64 ;;
  *) echo "Unsupported SWEETY_TARGET_ARCH: $SWEETY_TARGET_ARCH" >&2; exit 1 ;;
esac
[[ "$SWEETY_NODE_PATH" = /* && -x "$SWEETY_NODE_PATH" ]]
[[ "$SWEETY_PYTHON" = /* && -x "$SWEETY_PYTHON" ]]
[[ "$("$SWEETY_NODE_PATH" --version)" == "v22.23.4" ]]
[[ "$("$SWEETY_NODE_PATH" -p process.arch)" == "$NODE_ARCH" ]]
[[ "$("$SWEETY_PYTHON" -c 'import platform; print(platform.machine())')" == "$SWEETY_TARGET_ARCH" ]]
[[ "$("$SWEETY_PYTHON" -c 'import platform; print(platform.python_version())')" == "3.12.11" ]]
export SWEETY_TARGET_ARCH SWEETY_NODE_PATH
export MACOSX_DEPLOYMENT_TARGET=12.7
export SWEETY_BUILD_ROOT="${SWEETY_BUILD_ROOT:-/Users/eric/Documents/Codex-Temp/sweety-macos12/build-$SWEETY_TARGET_ARCH}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/Users/eric/Documents/Codex-Temp/sweety-macos12/venv-$SWEETY_TARGET_ARCH}"
export PATH="$(dirname "$SWEETY_NODE_PATH"):$PATH"
