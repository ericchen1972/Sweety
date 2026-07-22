# Target Name Warning And Persona Boundary Design

## Goal

Clarify the immutable LINE target-name requirement in the target form and remove shared knowledge-boundary policy from every generated base persona. Shared behavioral policy remains in the common system prompt.

## Scope

### Target name warning

The Traditional Chinese warning is displayed as two statements:

1. `名稱設定後將不能修改，強烈建議在 LINE 上修改對方名稱，以避免對方更名。`
2. `名稱不可包含特殊字元與表情符號，否則 Sweety 將無法正確辨識。`

The warning should preserve the existing presentation component. A line break may be included in the localized string so both statements remain easy to scan.

### Persona policy ownership

The catalog generator must stop appending the shared knowledge-boundary and financial-risk paragraph to every Traditional Chinese and English base persona. Generated persona content should contain only identity, profile, and persona-specific style information.

The common system prompt remains the single owner of these rules:

- Stay within knowledge reasonably available to the selected persona.
- Naturally admit uncertainty when a topic is outside that boundary.
- Do not become a general-purpose expert or provide complete professional answers.
- Show only guarded interest in money, investment, account, or unfamiliar-operation topics while continuing to question risk and process.

No new system-prompt section is needed because the current prompt already contains these requirements under `人設知識邊界` and `拖延策略`.

## Data And Generated Artifacts

After changing the generator, regenerate all checked-in catalog representations so they remain identical in meaning:

- canonical catalog JSON
- frontend generated catalog JSON
- desktop generated persona module
- bundled and remote SQL catalog data

The remote catalog contract and local-first refresh behavior do not change.

## Tests

- Assert the Traditional Chinese target-name warning uses the approved wording.
- Assert generated base personas no longer contain the removed shared paragraph in either locale.
- Assert the common system prompt still contains the persona knowledge-boundary and guarded financial behavior.
- Run the relevant frontend, desktop, catalog-generation, and remote catalog contract tests.

## Out Of Scope

- Changing target-name storage or editability behavior.
- Adding new target-name validation rules.
- Rewriting persona-specific identity, profile, or conversational style.
- Publishing or deploying the catalog unless separately requested.
