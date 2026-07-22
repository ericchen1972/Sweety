# Remote Catalog Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the system prompt and base personas locally, refresh them from the server at app startup when available, and keep the app usable when the server is unavailable.

**Architecture:** SQLite is the runtime source of truth. Bundled defaults seed first-run data, a startup sync updates local rows after validating the remote payload, and the local API exposes the cached base personas to the React UI.

**Tech Stack:** Python, FastAPI, SQLite, requests, pytest, React, TypeScript, Vitest.

---

### Task 1: Local Prompt And Base Persona Repository

**Files:**
- Modify: `app/desktop/src/sweety_app/database.py`
- Modify: `app/desktop/src/sweety_app/catalog.py`
- Modify: `app/desktop/src/sweety_app/repositories.py`
- Test: `app/desktop/tests/test_repositories.py`

- [ ] Add SQLite tables for the system prompt and base personas.
- [ ] Seed bundled defaults on migration without overwriting existing local rows.
- [ ] Add repository methods to read and replace the cached prompt/personas.
- [ ] Run `cd app/desktop && pytest tests/test_repositories.py -q`.

### Task 2: AI Prompt Uses Local Cache

**Files:**
- Modify: `app/desktop/src/sweety_app/ai.py`
- Test: `app/desktop/tests/test_ai.py`

- [ ] Make `build_messages` accept a system prompt template.
- [ ] Load the template and base persona from the repository at generation time.
- [ ] Keep JSON output formatting and recent-history behavior unchanged.
- [ ] Run `cd app/desktop && pytest tests/test_ai.py -q`.

### Task 3: Startup Remote Sync

**Files:**
- Create: `app/desktop/src/sweety_app/remote_catalog.py`
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/desktop/src/sweety_app/__main__.py`
- Test: `app/desktop/tests/test_remote_catalog.py`

- [ ] Add a sync client that fetches prompt/persona data with a short timeout.
- [ ] Validate the payload before writing; ignore request and validation failures.
- [ ] Call sync after migration and before UI/API startup.
- [ ] Run `cd app/desktop && pytest tests/test_remote_catalog.py -q`.

### Task 4: Local API And Frontend Base Personas

**Files:**
- Modify: `app/desktop/src/sweety_app/api.py`
- Modify: `app/frontend/src/domain.ts`
- Modify: `app/frontend/src/storage.ts`
- Modify: `app/frontend/src/App.tsx`
- Test: `app/desktop/tests/test_api.py`
- Test: `app/frontend/src/api.test.ts`

- [ ] Include cached base personas in `/api/state`.
- [ ] Use `state.basePersonas` instead of the static frontend catalog for selection, display, and cloning.
- [ ] Keep the static frontend catalog only as an empty-load fallback.
- [ ] Run `cd app/frontend && npm run typecheck`.
