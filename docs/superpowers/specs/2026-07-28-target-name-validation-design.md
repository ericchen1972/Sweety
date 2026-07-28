# Target Name Validation Design

Date: 2026-07-28

## Goal

Require every newly created monitored target name to contain only ASCII English
letters and digits so Sweety can reliably match the renamed LINE contact.
Prevent invalid names from being saved while preserving existing targets that
were created under the older, unrestricted rule.

## Accepted names

A valid new target name:

- contains one or more characters;
- uses only `A-Z`, `a-z`, and `0-9`;
- contains no whitespace, Chinese or other non-ASCII letters, punctuation,
  symbols, or emoji.

Examples such as `Fraud1` and `Fraud2` are valid. Values such as `Fraud 1`,
`詐騙1`, `Fraud-1`, and `Fraud1😀` are invalid. Leading or trailing whitespace
is also invalid.

## User interface behavior

- Keep the name field editable while the create modal is open.
- Validate when the user submits the form.
- When the value is invalid, keep the modal open, do not add the target to
  application state, and show a localized validation error.
- Do not silently delete or transform invalid characters while the user types.
- Target names remain read-only in the existing edit flow.

The Traditional Chinese warning text is exactly:

```text
名稱設定後將不能修改，強烈建議在 LINE 上修改對方名稱，以避免對方更名。 名稱不可包含特殊字元與表情符號，必須使用英文字母或數字，否則 Sweety 將無法正確辨識。
範例：Fraud1, Fraud2....
```

The English locale conveys the same restriction and examples.

## Validation boundaries

The frontend `validateTargetName` function is the shared UI rule and uses the
equivalent of `^[A-Za-z0-9]+$`. The create modal calls it on submit before
constructing or saving a target.

The local API independently enforces the same rule for new target creation,
including targets first seen during whole-state replacement and direct
`POST /api/targets` requests. Invalid requests return a stable client error and
do not write a target. The error code is `invalid_target_name`.

Existing stored targets are handled as legacy data:

- an unchanged existing name may pass through whole-state saves even when it
  contains characters that are now invalid;
- changing an existing target name remains disallowed by the existing UI;
- this feature does not migrate, rename, delete, or disable legacy targets.

This compatibility boundary prevents an old Chinese or emoji name from blocking
unrelated saves such as changing a persona or reply-enabled state.

## Testing

Frontend tests cover:

- `Fraud1`, `fraud2`, and mixed-case alphanumeric values are accepted;
- empty strings, whitespace, Chinese, spaces, punctuation, and emoji are
  rejected;
- the exact Traditional Chinese warning copy includes the required example.

Desktop API tests cover:

- a newly created alphanumeric target is accepted;
- direct creation rejects a non-alphanumeric target without persisting it;
- whole-state replacement rejects a newly introduced invalid target;
- whole-state replacement continues to accept an unchanged legacy invalid name.

The complete desktop and frontend test suites must pass before returning to the
macOS-only main cleanup plan.
