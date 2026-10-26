# Canonical macOS 12.7+ build

Both Apple Silicon and Intel are built from the same main source. The previous compatibility branch is historical only. Release 2.0.1 removes conversation export, retains only 4–30 recent AI-context messages (default 6), and clears completed/abandoned journal payloads while preserving receipt deduplication and statistics.

Use architecture-matched Python 3.12.11 and official Node 22.23.4, verify Node archive SHASUMS256.txt, and set:

```sh
export SWEETY_TARGET_ARCH=arm64 # Intel: x86_64
export SWEETY_PYTHON=/absolute/path/to/python3.12
export SWEETY_NODE_PATH=/absolute/path/to/node-v22.23.4-darwin-arm64/bin/node
export SWEETY_BUILD_ROOT=/Users/eric/Documents/Codex-Temp/sweety-build-arm64
export UV_PROJECT_ENVIRONMENT=/Users/eric/Documents/Codex-Temp/sweety-venv-arm64
./app/desktop/build_dmg.sh
```

Build architectures sequentially: npm ci replaces native frontend build dependencies. Frozen Python dependencies and MACOSX_DEPLOYMENT_TARGET=12.7 are required. Packaging audits every Mach-O architecture and minimum OS; it does not patch binary headers. Local app builds default to SWEETY_LOG_ENABLED=1. DMG builds rebuild with SWEETY_LOG_ENABLED=0 and retain the existing release metrics token supplied in the environment.

Output: dist/Sweety-macos12.7-{arm64|x86_64}-latest.dmg under SWEETY_BUILD_ROOT. Publishing helper app/tools/deploy_macos_release.php uses the same architecture variables and filenames. Public update notices link to the website download selector so Intel users are not routed to an ARM binary.

Run the frozen app with --macos-self-check /absolute/path/to/report.json for an isolated, offline API/frontend/Node-WASM signing check. Run scripts/audit_macos.py with --arch for an independent binary audit. Release apps are ad-hoc signed, not notarized. Actual macOS 12.7 hardware launch, LINE login, message delivery and AI operation still require device acceptance.
