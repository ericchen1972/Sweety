# Target Name Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent new monitored targets from being saved unless their names contain only ASCII English letters and digits, while preserving unchanged legacy names.

**Architecture:** Strengthen the existing frontend `validateTargetName` boundary and use its result in the existing create-modal submit flow. Add an independent API helper that validates only newly introduced targets, leaving the repository and unchanged existing targets compatible with legacy data.

**Tech Stack:** React, TypeScript, Vitest, FastAPI, Pydantic, pytest.

---

### Task 1: Define the frontend name and copy contract

**Files:**
- Modify: `app/frontend/src/domain.test.ts`
- Modify: `app/frontend/src/i18n.test.ts`
- Test: `app/frontend/src/domain.test.ts`
- Test: `app/frontend/src/i18n.test.ts`

- [ ] **Step 1: Replace the permissive target-name test**

Replace the first test under `describe("target validation")` with:

```typescript
it("accepts only non-empty ASCII letters and digits", () => {
  for (const valid of ["Fraud1", "fraud2", "ABC123xyz"]) {
    expect(validateTargetName(valid)).toBe(true);
  }
  for (const invalid of ["", "  ", "Fraud 1", "詐騙1", "Fraud-1", "Fraud_1", "Fraud1😀"]) {
    expect(validateTargetName(invalid)).toBe(false);
  }
});
```

- [ ] **Step 2: Update the Traditional Chinese copy assertion**

Replace the existing `targetNameWarning` assertion with:

```typescript
expect(copy.targetNameWarning).toBe(
  "名稱設定後將不能修改，強烈建議在 LINE 上修改對方名稱，以避免對方更名。 名稱不可包含特殊字元與表情符號，必須使用英文字母或數字，否則 Sweety 將無法正確辨識。\n範例：Fraud1, Fraud2....",
);
expect(copy.targetNameError).toBe("名稱只能使用英文字母或數字。");
```

- [ ] **Step 3: Run the focused frontend tests and verify RED**

Run:

```bash
cd app/frontend
npm test -- --run src/domain.test.ts src/i18n.test.ts
```

Expected: failures because Chinese and emoji names are still accepted,
`targetNameWarning` has the old text, and `targetNameError` does not exist.

- [ ] **Step 4: Commit the failing frontend tests**

```bash
git add app/frontend/src/domain.test.ts app/frontend/src/i18n.test.ts
git commit -m "test: require alphanumeric target names"
```

### Task 2: Implement frontend validation and localized guidance

**Files:**
- Modify: `app/frontend/src/domain.ts`
- Modify: `app/frontend/src/i18n.ts`
- Modify: `app/frontend/src/App.tsx`
- Test: `app/frontend/src/domain.test.ts`
- Test: `app/frontend/src/i18n.test.ts`

- [ ] **Step 1: Restrict the shared target-name validator**

Replace `validateTargetName` with:

```typescript
export function validateTargetName(name: string): boolean {
  return /^[A-Za-z0-9]+$/.test(name);
}
```

- [ ] **Step 2: Add the exact Traditional Chinese copy**

Set the Traditional Chinese fields to:

```typescript
targetNameWarning: "名稱設定後將不能修改，強烈建議在 LINE 上修改對方名稱，以避免對方更名。 名稱不可包含特殊字元與表情符號，必須使用英文字母或數字，否則 Sweety 將無法正確辨識。\n範例：Fraud1, Fraud2....",
targetNameError: "名稱只能使用英文字母或數字。",
```

Set the English equivalents to:

```typescript
targetNameWarning: "Names cannot be changed after creation. We strongly recommend renaming the contact in LINE to avoid later changes. Names cannot contain special characters or emoji and must use only English letters or numbers, or Sweety may not identify them correctly.\nExamples: Fraud1, Fraud2....",
targetNameError: "Use English letters or numbers only.",
```

- [ ] **Step 3: Show the validation-specific submit error**

In `TargetModal.submit`, replace:

```typescript
setError(copy.targetNameHint);
```

with:

```typescript
setError(copy.targetNameError);
```

The existing early return remains the save-blocking boundary.

- [ ] **Step 4: Run the focused and complete frontend suites**

Run:

```bash
cd app/frontend
npm test -- --run src/domain.test.ts src/i18n.test.ts
npm test -- --run
```

Expected: focused tests pass, then all 29 frontend tests pass.

- [ ] **Step 5: Commit the frontend implementation**

```bash
git add app/frontend/src/domain.ts app/frontend/src/i18n.ts app/frontend/src/App.tsx
git commit -m "feat: restrict new target names to alphanumeric"
```

### Task 3: Enforce the rule at new-target API boundaries

**Files:**
- Modify: `app/desktop/tests/test_api.py`
- Modify: `app/desktop/src/sweety_app/api.py`
- Test: `app/desktop/tests/test_api.py`

- [ ] **Step 1: Convert existing new-target fixtures to valid names**

Change the API test helper default to:

```python
def target_payload(name: str = "Fraud1") -> dict:
```

Update direct assertions and newly introduced state fixtures that currently use
Chinese names to use `Fraud1`, `Fraud2`, or `Duplicate1`. Leave custom persona
names and other unrelated Chinese content unchanged.

- [ ] **Step 2: Add direct-create and whole-state rejection tests**

Add:

```python
@pytest.mark.parametrize("name", ["Fraud 1", "詐騙1", "Fraud-1", "Fraud1😀"])
def test_new_target_rejects_non_alphanumeric_name(client, name):
    response = client.post("/api/targets", json=target_payload(name))

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_target_name"
    assert client.get("/api/state").json()["targets"] == []


def test_state_snapshot_rejects_new_non_alphanumeric_target(client):
    state = client.get("/api/state").json()
    state["targets"] = [{
        "id": "target-invalid",
        **target_payload("Fraud 1"),
        "status": "active",
        "roundTrips": 0,
        "firstReplyAt": None,
        "lastReplyAt": None,
        "endedAt": None,
    }]

    response = client.put("/api/state", json=state)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_target_name"
    assert client.get("/api/state").json()["targets"] == []
```

- [ ] **Step 3: Add the unchanged-legacy compatibility test**

Import `TargetPayload` and add:

```python
def test_state_snapshot_allows_unchanged_legacy_target_name(tmp_path):
    database = Database(tmp_path / "legacy-target.sqlite3")
    client = TestClient(create_app(database))
    parsed = TargetPayload.model_validate(target_payload("舊名稱😀"))
    client.app.state.repository.create_target({**parsed.model_dump(), "id": "target-legacy"})
    state = client.get("/api/state").json()
    state["targets"][0]["replyEnabled"] = False

    response = client.put("/api/state", json=state)

    assert response.status_code == 200
    assert response.json()["targets"][0]["name"] == "舊名稱😀"
    assert response.json()["targets"][0]["replyEnabled"] is False
```

- [ ] **Step 4: Run the focused API tests and verify RED**

Run:

```bash
cd app/desktop
uv run pytest tests/test_api.py -q
```

Expected: new rejection tests fail because the API still accepts invalid new
names. Existing converted API tests and the legacy compatibility test pass.

- [ ] **Step 5: Add a shared API-level name check**

Import `re` in `api.py` and add:

```python
def _validate_new_target_name(name: str) -> None:
    if re.fullmatch(r"[A-Za-z0-9]+", name) is None:
        raise RepositoryError("invalid_target_name")
```

In whole-state replacement, validate only before creating an ID that is absent
from `existing_targets`:

```python
if target_id in existing_targets:
    repository.update_target(target_id, parsed.model_dump())
else:
    _validate_new_target_name(parsed.name)
    repository.create_target({**parsed.model_dump(), "id": target_id})
```

In direct creation, validate before writing:

```python
@app.post("/api/targets", status_code=201)
def create_target(payload: TargetPayload) -> dict[str, Any]:
    _validate_new_target_name(payload.name)
    return _target_for_api(repository.create_target(payload.model_dump()))
```

- [ ] **Step 6: Run focused and complete desktop suites**

Run:

```bash
cd app/desktop
uv run pytest tests/test_api.py -q
uv run pytest -q
```

Expected: API tests pass, then the complete desktop suite passes.

- [ ] **Step 7: Commit the backend implementation**

```bash
git add app/desktop/tests/test_api.py app/desktop/src/sweety_app/api.py
git commit -m "feat: reject invalid new target names"
```

### Task 4: Resume the macOS-only main cleanup

**Files:**
- Continue: `docs/superpowers/plans/2026-07-28-mac-only-main-cleanup.md`

- [ ] **Step 1: Return to the paused homepage RED step**

Continue with Task 3 of the macOS-only main cleanup plan, preserving the current
uncommitted changes in `web/tests/homepage.test.mjs`.

- [ ] **Step 2: Include this feature in final verification**

The final project verification must include the full frontend and desktop suites
after the homepage implementation, before local `main` is moved or pushed.
