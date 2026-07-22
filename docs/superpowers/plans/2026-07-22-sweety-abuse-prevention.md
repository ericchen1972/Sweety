# Sweety Abuse Prevention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add best-effort region blocking and layered custom-persona/output abuse prevention to Sweety.

**Architecture:** Keep immutable policy in the system role and move custom persona text into untrusted user context. Add a focused persona guard around saves and custom-persona generation, an output URL gate around generated replies, and a fail-open startup region lookup that can disable the monitor.

**Tech Stack:** Python 3.11, requests, FastAPI, SQLite, pytest, React/TypeScript, PyInstaller.

---

### Task 1: Prompt isolation and output safety

**Files:**
- Modify: `app/desktop/src/sweety_app/ai.py`
- Test: `app/desktop/tests/test_ai.py`

- [ ] Write tests proving persona text does not enter the system message, fixed safety policy remains present, safe replies pass, and link-bearing replies retry once then fail.
- [ ] Run `cd app/desktop && .venv/bin/python -m pytest tests/test_ai.py -q` and confirm the new tests fail for the missing behavior.
- [ ] Add immutable safety rules, an untrusted persona context message, URL detection, and bounded regeneration.
- [ ] Run the focused AI tests and confirm they pass.

### Task 2: AI-backed custom persona validation

**Files:**
- Create: `app/desktop/src/sweety_app/persona_safety.py`
- Modify: `app/desktop/src/sweety_app/ai.py`
- Modify: `app/desktop/src/sweety_app/api.py`
- Test: `app/desktop/tests/test_persona_safety.py`
- Test: `app/desktop/tests/test_api.py`

- [ ] Write tests for benign approval, promotional-task rejection, local URL rejection, malformed classifier output, approval caching, and API non-persistence after rejection.
- [ ] Run the focused tests and confirm they fail because the guard does not exist.
- [ ] Implement structured classifier requests, deterministic prechecks, digest caching, API validation before writes, and generation-time validation for custom personas.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Fail-open region lookup

**Files:**
- Create: `app/desktop/src/sweety_app/region_access.py`
- Modify: `app/desktop/src/sweety_app/config.py`
- Modify: `app/desktop/src/sweety_app/__main__.py`
- Modify: `app/desktop/src/sweety_app/monitor.py`
- Test: `app/desktop/tests/test_region_access.py`
- Test: `app/desktop/tests/test_monitor.py`

- [ ] Write tests for blocked and allowed country codes plus timeout, HTTP, malformed JSON, and missing-country fail-open behavior.
- [ ] Run the focused tests and confirm they fail because the checker and monitor status do not exist.
- [ ] Implement the HTTPS lookup with a three-second timeout and pass the result into monitor startup policy.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Full verification and package

**Files:**
- Verify: `app/desktop`
- Verify: `app/frontend`

- [ ] Run `cd app/desktop && .venv/bin/python -m pytest -q` with zero failures.
- [ ] Run `cd app/frontend && npm test -- --run`, `npm run typecheck`, and `npm run build` with zero failures.
- [ ] Run `cd app/desktop && ./build_app.sh` and verify `dist/Sweety.app` with `codesign --verify --deep --strict --verbose=2`.
