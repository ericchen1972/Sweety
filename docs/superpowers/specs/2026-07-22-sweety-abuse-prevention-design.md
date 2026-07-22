# Sweety Abuse Prevention Design

## Goal

Reduce the chance that Sweety is repurposed for promotion, recruitment, financial solicitation, or outbound redirection while preserving normal use when the optional IP lookup service is unavailable.

## Trust Boundaries

- The locally cached Sweety system prompt is trusted application policy.
- Base personas supplied by the Sweety catalog are trusted content.
- Custom persona text is untrusted data. It may describe identity, background, temperament, vocabulary, and conversational style, but it may not define a new mission or override application policy.
- AI output is untrusted until it passes the output safety gate.
- Third-party IP geolocation is advisory. A failed lookup must not disable the app.

## Persona Safety

Custom persona text is checked before a new or changed persona is saved. A separate AI request classifies the text using a fixed system policy and structured JSON output. Obvious URLs and external-contact instructions are rejected locally before the classifier request.

The same check runs before a custom persona is used for reply generation. Successful decisions are cached by a SHA-256 digest for the current process, so unchanged approved text does not incur repeated classifier calls. Base personas bypass this check.

Classifier errors reject custom-persona saves and prevent custom-persona reply generation. This does not affect base personas.

## Prompt Isolation

Custom persona text is never interpolated into the system message. The system message contains immutable Sweety safety rules and a statement that persona data is reference material only. Persona text is passed in a separate user-context message surrounded by explicit untrusted-data markers.

The immutable rules require the assistant to delay suspected scammers, avoid promotion or recruitment, never provide URLs or external contact routes, and ignore attempts in persona or conversation data to replace those rules.

## Output Gate

Generated replies are checked for URL schemes, `www` links, bare domain names, email-style links, and IP-address URLs. A violating reply is regenerated once. If the second candidate also violates the rule, reply generation fails and the monitor sends nothing.

## Region Check

At app startup, the backend calls `https://api.country.is/` with a three-second timeout. A valid response whose country code is `MM`, `KH`, `PH`, or `TH` disables monitoring and AI replies with a `region_blocked` status.

Timeouts, connection errors, non-success responses, malformed JSON, and missing or unknown country codes are ignored. The full IP address is not persisted.

## Verification

- Unit tests prove custom persona text is outside the system message.
- Unit tests cover accepted, rejected, malformed, and unavailable classifier responses.
- API tests prove rejected personas are not persisted.
- Unit tests cover link detection, retry, and final refusal.
- Region tests cover blocked, allowed, and every fail-open path.
- Monitor tests prove region blocking prevents startup.
- The complete desktop and frontend suites run before rebuilding the macOS app.
