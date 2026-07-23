# macOS Permission FAQ Design

## Goal

Add a fifth homepage FAQ explaining how to recover when pressing Start shows that macOS permissions are required after an application update.

## Localized Content

The Traditional Chinese FAQ uses:

- Question: `為什麼按下開始後顯示「需要 Mac 權限」？`
- Answer: `因為程式更新後可能被系統判斷為新的程式，所以請到偏好設定的「輔助使用」及「螢幕與系統錄音」內，移除 Sweety 後再重新加入。`

The answer must clearly instruct users to remove and re-add Sweety in both permission areas. The phrase `「輔助使用」及「螢幕與系統錄音」內，移除 Sweety 後再重新加入。` is visually emphasized in bold.

The English FAQ conveys the same recovery steps:

- Question: `Why does Sweety show “macOS permissions required” after I press Start?`
- Answer: `After an update, macOS may treat Sweety as a new app. In System Settings, remove Sweety from Accessibility and Screen & System Audio Recording, then add it again.`

The corresponding recovery instruction is bold in the English rendering.

## Rendering

Keep the current safe text rendering. Do not introduce localized `innerHTML`.

The fifth FAQ answer uses separate localized prefix and emphasis fields rendered into a plain `<span>` and `<strong>`. Existing FAQ answers remain unchanged and continue using the current `data-copy` behavior.

## Structured Data

Add the fifth Traditional Chinese question and complete plain-text answer to the existing `FAQPage.mainEntity` JSON-LD array. Structured data contains no HTML or Markdown.

## Tests

- Require five FAQ entries in both locale objects.
- Require five `<details>` and five `<summary>` elements.
- Assert the exact Traditional Chinese and English question and answer parts.
- Assert the fifth answer contains a localized `<span>` and `<strong>` rather than Markdown or localized `innerHTML`.
- Assert JSON-LD contains the fifth question and full plain-text answer.

## Deployment

Run the homepage tests, deploy through the existing homepage deployment helper, then fetch the live homepage and JavaScript to verify the fifth FAQ, localized content, JSON-LD, and `<strong>` markup.

## Out Of Scope

- Changing macOS permission detection.
- Changing the native panel's permission wording.
- Rewriting the existing four FAQ entries.
- Changing the public application version or download URL.
