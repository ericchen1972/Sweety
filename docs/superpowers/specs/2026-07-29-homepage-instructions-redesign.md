# Homepage Instructions Redesign

## Scope

Replace only the public homepage `#instructions` section. Keep the existing introduction, quote, and open-source note, then replace the current two-column Quick start and Advanced settings blocks with seven single-column illustrated guide items.

## Content order

1. Control panel — `instructions-control-panel.webp`
2. Dashboard — `instructions-dashboard.webp`
3. Basic settings — `instructions-basic-settings.webp`
4. Scammer list — `instructions-target-list.webp`
5. Base personas — `instructions-base-personas.webp`
6. Persona details — `instructions-persona-details.webp`
7. Custom personas — `instructions-custom-personas.webp`

Each item renders one WebP image at its natural aspect ratio, followed by a localized heading and paragraph. The final guide reminder is a separate localized paragraph after all seven items.

## Localization and accessibility

Traditional Chinese uses the supplied control-panel paragraph and final reminder verbatim. The remaining explanations are derived from the visible controls in the supplied screenshots. English contains equivalent explanations. Every image has localized alternative text, explicit dimensions, lazy loading, and asynchronous decoding.

## Responsive layout

The guide is one column at every breakpoint. Wide screenshots use the full content width; the narrow control-panel screenshot is centered without stretching. Text remains below its image on desktop and mobile.

## Verification

Homepage contract tests require exactly seven WebP guide images in the approved order, all localized title/body/alt hooks, one-column CSS, removal of the old guide assets and list hooks, exact Chinese reminder copy, and synchronized CSS/JS cache versions. Deployment is followed by cache-busted live HTML, JavaScript, image, and responsive visual checks.
