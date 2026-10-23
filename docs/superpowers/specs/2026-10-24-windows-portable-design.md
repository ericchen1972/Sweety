# Windows portable test build

Approved scope: the user requested a GitHub Actions-built Windows ZIP after
accepting the browser management interface and bundled Python/Node approach.

- Keep one implementation on main. Share the existing backend and startup wiring
  between macOS and Windows; keep the native macOS panel.
- Windows x64 uses a small Tk control window, opens the existing local web UI
  after the API is ready, and keeps serving when the browser closes. Closing the
  control window stops monitoring, disconnects without deleting login, and stops
  the API. A per-user Windows mutex prevents duplicate processes.
- Bundle Python, Tcl/Tk, Windows Node, OKLine JS/WASM, frontend and licenses in a
  PyInstaller onedir ZIP. No installer or developer runtime is required.
- Use Windows Credential Manager through keyring, and retain data under
  %USERPROFILE%\.sweety. ZIP portability does not mean portable account data.
- Embed SWEETY_LOG_ENABLED in bundled JSON; testing uses 1, release uses 0.
  Explicit runtime environment can override the bundled value. No user API keys
  or LINE sessions enter the artifact.
- GitHub Actions builds on Windows, runs platform-neutral tests, validates the
  frozen signer, credential storage, local API/frontend and GUI lifecycle, then
  uploads the ZIP and verification reports. Manual LINE/AI testing remains for
  the user; CI must never log into or send to real LINE contacts.
- Deliver the downloaded build under Codex-Temp with its SHA-256 and Actions URL.

Alternatives considered: a single executable adds extraction overhead; rebuilding
the full native panel adds unnecessary scope. Start with an onedir ZIP and reuse
the browser dashboard.
