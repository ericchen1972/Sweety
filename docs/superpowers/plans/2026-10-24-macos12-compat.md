# Sweety macOS 12.7 Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** Publish isolated macOS 12.7 test DMGs on sweety.tw without modifying main or the official download.

**Architecture:** Keep 2.0.0 application behavior and data format. Branch compat/macos-12-7 holds packaging changes. Pin Node 22.23.4, Python 3.12.11, minimum OS 12.7, and build separate native architecture packages when required.

**Tech Stack:** Python, PyInstaller, Node, Vite, macOS codesign/hdiutil, existing FTP hosting.

### Task 1: Compatibility packaging
- [x] Baseline: run existing desktop suite using isolated uv environment.
- [x] Add meaningful test of a Mach-O compatibility auditor: accept minos <=12.7 and correct architecture, reject newer minos and wrong architecture, including legacy LC_VERSION_MIN_MACOSX.
- [x] Run new test red, implement auditor, then green.
- [x] Update Sweety.spec and build scripts to build minimum 12.7, choose explicit arm64/x86_64 architecture and explicit verified Node 22.23.4 executable, use unique compatibility DMG filenames.
- [x] Audit every bundled Mach-O file before producing DMG; reject incompatible native binaries rather than editing their headers.
- [x] Document compatible build commands and mark actual 12.7 acceptance pending.

### Task 2: Build and verify
- [x] Download official architecture-specific Node archives and verify against official SHASUMS256.txt.
- [x] Build using architecture-matched Python environments and locked dependencies. Generate output exclusively under Codex-Temp/sweety-macos12.
- [x] Run desktop tests, frontend build, native architecture/minimum-OS audit, codesign verification, DMG verification and mount contents.
- [x] Smoke frozen services with isolated data directory, without existing LINE login or sending messages.

### Task 3: Publish isolated download
- [x] Upload compatibility DMG to a new filename under /sweety.tw/downloads using existing private FTP config, without changing homepage/latest DMG.
- [x] Download public artifact and compare bytes and SHA-256.
- [x] Commit compatibility source only on branch, verify main commit and original working tree unchanged.
- [x] Deliver architecture-specific test URL and clearly state macOS 12.7 real login/send/AI acceptance remains user testing.
