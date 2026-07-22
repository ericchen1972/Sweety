# Conversation Curiosity Prompt Design

## Goal

Make every Sweety persona sustain suspicious conversations with natural curiosity instead of producing polite but terminal replies. The behavior belongs to the shared system prompt so persona identity and style remain independent.

## Shared Behavior

Add a dedicated `對話延續與好奇心` section between `說話方式` and `人設知識邊界`.

When Sweety decides to reply, the reply should leave the other party an easy, relevant way to continue. A conversational hook may be a short question, curiosity about an unfinished detail, ordinary confusion, or a reaction that invites clarification. It does not need to contain a question mark every time, and it must still sound natural for the selected persona and current relationship.

The prompt must explicitly avoid replies that merely close the exchange, including variants of `你先忙`, `不打擾了`, `有空再聊`, and `晚點再說`. If the persona says they are busy or needs to delay an action, the same reply should retain a concrete open thread that the other party can answer now.

If the other party appears ready to leave or wait indefinitely, the persona should normally pick up one relevant unresolved detail with a low-pressure question instead of accepting the end of the conversation. Existing safety rules remain higher priority, and the response remains concise at one or two sentences.

The existing instruction `不要每次都反問` remains valid: curiosity is a behavioral objective, not a mechanical requirement to append a question to every response.

## Prompt Ownership And Synchronization

The same prompt text must be stored in both existing sources:

- `app/desktop/src/sweety_app/catalog.py` for the bundled, offline-capable default.
- `app/tools/base_catalog.sql` for the server catalog returned by `web/sweety-catalog.php`.

The 24 persona records and weapon text do not change.

## Existing Local Databases

Bump the desktop schema version. During migration, replace a version-4 prompt only when it matches the recognizable prior bundled/catalog prompt and lacks the new section. Preserve unrelated custom or later remote prompts. New databases continue to receive the current bundled prompt, and a successful startup refresh may still replace it with the server copy.

## Deployment And Verification

- Contract tests assert that both prompt sources contain the full conversation-continuation policy and remain identical.
- Migration tests cover upgrading the prior official prompt and preserving an unrelated remote prompt.
- Deploy the SQL catalog through the existing authenticated catalog deployment helper.
- Verify the live API returns 24 unchanged personas and the new prompt section.
- Rebuild the local desktop application so its bundled fallback contains the new prompt.

## Out Of Scope

- Rewriting individual personas or weapons.
- Adding output post-processing, forced question insertion, or a second AI call.
- Changing safety rules, reply timing, LINE automation, or target selection.
- Changing the public download version or homepage unless a separate release is requested.
