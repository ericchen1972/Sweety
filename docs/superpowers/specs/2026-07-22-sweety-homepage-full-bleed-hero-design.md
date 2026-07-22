# Sweety Homepage Full-Bleed Hero Design

## Goal

Fix the missing production header logo and make the approved watercolor artwork fill the complete first-screen hero area without reducing the readability of the supplied black text.

## Header Logo

- Convert the existing `web/images/logo.png` asset to WebP before publishing it.
- Render the WebP asset as the preferred source and keep the PNG as a compatibility fallback.
- Publish both files to the production site root so the header never references a missing asset.
- Preserve the current displayed dimensions and the adjacent `Sweety` wordmark.

## Full-Bleed Hero

- The hero fills the viewport below the fixed header on desktop.
- The approved `hero-helpless` watercolor artwork covers the complete hero background instead of occupying a separate right-hand rectangle.
- Use cover-style cropping and keep the distressed young person positioned on the right.
- Add a white-to-transparent overlay from left to right so all supplied black copy remains readable.
- Preserve the existing text, typography hierarchy, red bold `束手無策`, navigation, localization, and section anchors.
- On narrow screens, keep the text in normal document flow and position the artwork behind the lower/right portion without horizontal overflow.
- Respect reduced-motion behavior already implemented by the page.

## Assets and Delivery

- The page must request WebP for both the logo and hero artwork when supported.
- PNG files remain fallback assets only.
- The deployment helper must upload the logo assets as well as the existing homepage files.

## Verification

- Add regression checks for the logo WebP source and full-bleed hero CSS contract.
- Run the homepage tests and JavaScript syntax check.
- Deploy the changed HTML, CSS, logo assets, and deployment helper output.
- Verify the live logo and hero WebP return HTTP 200 with `image/webp`.
- Verify live HTML/CSS hashes match the local files and the page has no horizontal overflow at desktop and mobile widths.
