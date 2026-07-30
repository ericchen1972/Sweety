# Git workflow

- 程式不做任何分支，永遠只有一個版本，Git 當作時光機使用。
- `main` is the single canonical version. Do not create or maintain feature branches, worktrees, parallel implementations, or alternate release variants.
- Use commits and tags on `main` to preserve history and support comparison or rollback.

# Diagnostic logging

- `SWEETY_LOG_ENABLED` is the single global diagnostic log switch. Do not add independent per-module log switches.
- App builds used for local testing must enable logging (`SWEETY_LOG_ENABLED=1`); `app/desktop/build_app.sh` does this by default.
- DMG/release builds must disable logging (`SWEETY_LOG_ENABLED=0`); `app/desktop/build_dmg.sh` must rebuild the bundled App with logging disabled before creating the DMG.
- Windows must use the same `SWEETY_LOG_ENABLED` switch. Windows test builds must enable it (`1`), and Windows installer/release builds must disable it (`0`).
- macOS currently embeds the build-time value through `Info.plist` `LSEnvironment`. Windows has no equivalent `Info.plist`, so its packaging flow must provide an equivalent bundled/runtime setting and must not assume that an environment variable from the build shell will exist when the user launches the installed App from Explorer.
- On Windows, diagnostic logs belong under the existing non-macOS data layout at `%USERPROFILE%\.sweety\logs\sweety.log`.
- Raw AI responses may be written only while the global diagnostic log switch is enabled.
