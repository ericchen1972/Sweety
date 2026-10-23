# Windows Portable Implementation Plan

**Goal:** Deliver a verified GitHub Actions Windows x64 ZIP test build.
**Architecture:** Share service composition, use platform-specific desktop hosts,
and bundle all runtimes through a Windows PyInstaller spec.
**Tech Stack:** Python 3.12, Tk, FastAPI, Node 22, PyInstaller, GitHub Actions.

Execute inline in this chat on main, as requested by the user.

1. Add failing subprocess tests for bundled diagnostic configuration, Windows
   launcher selection, platform-neutral startup, local API and shutdown cleanup.
2. Extract service composition to bootstrap.py; update macOS entry to reuse it.
   Add Windows control window, duplicate-instance guard and offline self-check.
3. Add Windows build script/spec and test documentation; bundle Node, licenses,
   keyring Windows backend and Tcl/Tk. Keep outputs outside the repository.
4. Add manually triggered Actions workflow: dependencies, tests, frontend build,
   frozen signer/API/credential/GUI checks, ZIP with hash and artifact upload.
5. Run local tests and frontend build, inspect changes, commit only task files,
   push main, dispatch and inspect Actions; fix any build issues on main.
6. Download and verify artifact under Codex-Temp. Report actual CI evidence and
   the remaining real Windows LINE/AI manual test boundary.
