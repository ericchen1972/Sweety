# macOS 12.7 compatibility test builds

This branch preserves Sweety 2.0.0 behavior, bundle identity `tw.sweety.app`, metrics configuration and existing application data. It changes packaging only. These artifacts do not replace the official download.

Requirements: macOS build tools, `uv`, architecture-matched Python **3.12.11**, a committed frontend npm lockfile, and an explicit official **Node 22.23.4** executable verified against its official SHASUMS256.txt. Do not substitute the newest Homebrew Node. Intel builds on Apple Silicon require Rosetta and Intel Python/dependencies.

From `app/desktop`, for example:

```sh
export SWEETY_TARGET_ARCH=arm64 # use x86_64 for Intel
export SWEETY_PYTHON=/absolute/path/to/architecture-matched/python3.12
export SWEETY_NODE_PATH=/Users/eric/Documents/Codex-Temp/sweety-macos12/runtimes/node-v22.23.4-darwin-arm64/bin/node
export UV_PROJECT_ENVIRONMENT=/Users/eric/Documents/Codex-Temp/sweety-macos12/venv-arm64
./build_dmg.sh
```

For Intel, use the official `darwin-x64` Node archive and `venv-x86_64`. Each build runs `npm ci` through the supplied target Node/npm before building the frontend, reinstalling native optional dependencies for that architecture. Architecture builds sharing this source directory must run sequentially because `node_modules` is replaced. The scripts validate Node and Python version/architecture, use frozen Python dependencies and set `MACOSX_DEPLOYMENT_TARGET=12.7`. `SWEETY_BUILD_ROOT` may override the default architecture-specific directory under `/Users/eric/Documents/Codex-Temp/sweety-macos12`.

`build_app.sh` enables diagnostic logging by default for local testing. `build_dmg.sh` always rebuilds with `SWEETY_LOG_ENABLED=0`. The existing `SWEETY_METRICS_APP_TOKEN` build environment is preserved.

Before signing and DMG creation, every bundled Mach-O file is checked for the required architecture and minimum OS <=12.7, including legacy `LC_VERSION_MIN_MACOSX`. Unsupported binaries fail the build; headers are never patched. The output is `dist/Sweety-2.0.0-macos12.7-{arm64|x86_64}-test.dmg` beneath the build root.

Standalone audit:

```sh
python scripts/audit_macos.py /path/to/Sweety.app --arch arm64
```

Frozen offline smoke check (report and temporary database stay under the supplied report directory):

```sh
/path/to/Sweety.app/Contents/MacOS/Sweety --macos-self-check /Users/eric/Documents/Codex-Temp/sweety-macos12/smoke/report.json
```

This launches the bundled backend and loads bundled frontend HTML/JavaScript over loopback, checks API state and disconnected LINE status, verifies offline OKLine signing, and stops services. It avoids login, sends, keychain mutation and the normal GUI path. Release smoke reports must show `logging: false` and `logCreated: false`.

## Acceptance status

Passing static audits, signing and build-host smoke checks do not establish macOS 12.7 runtime acceptance. Actual macOS 12.7 launch, OKLine login, receiving/sending messages and AI operation remain pending user testing for each architecture.

## 2026-10-24 test-build verification

- Base revision: `33c2fef`; isolated branch: `compat/macos-12-7`. Original main checkout remains unchanged.
- Both arm64 and x86_64 desktop suites: 270 passed, 16 pre-existing warnings.
- Each bundled App passed an 86-file Mach-O architecture/minimum-OS audit, ad-hoc codesign verification, DMG checksum and mount-content verification.
- Both frozen executables passed `--macos-self-check`: isolated data, local health/state API, bundled frontend JavaScript, disconnected LINE status, offline OKLine signing, disabled release logging and clean shutdown.
- Intel execution on the build host uses Rosetta; it does not establish Intel hardware or macOS 12.7 acceptance.
- Node 22.23.4 archives were verified against official `SHASUMS256.txt` before extraction. ARM archive SHA-256: `c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428`; Intel archive SHA-256: `efcc2b0db6f94bf53eddb038fe2b370277a042bd29e4f19b8f8e23598795b819`.
- Build logs, isolated smoke reports, downloaded verification copies and release manifests are retained under `/Users/eric/Documents/Codex-Temp/sweety-macos12`.
- These test builds are ad-hoc signed, not notarized. Real macOS 12.7 UI launch, login, message send/receive and AI response tests remain pending.

## Verified public test downloads

- x86_64: https://sweety.tw/downloads/Sweety-2.0.0-macos12.7-x86_64-test.dmg — HTTP 200, 99225976 bytes; SHA-256 `00316194f633b0511d194aecabbcf38de73617999849ba9665040751ef524538`.
- arm64: https://sweety.tw/downloads/Sweety-2.0.0-macos12.7-arm64-test.dmg — HTTP 200, 95049964 bytes; SHA-256 `1144b1f0c1a2b620c3ff285e32b6e442296dcc289dd47f754e46881fe130c9a5`.
