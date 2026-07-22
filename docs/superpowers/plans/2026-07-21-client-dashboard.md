# Sweety Client Dashboard Implementation Plan

**Goal:** Build the usable browser-based client dashboard for the Sweety desktop app, following KingJoo's system-aware light/dark visual language and showing English for every locale except `zh-TW`.

**Architecture:** A Vite + React + TypeScript frontend lives in `app/frontend`. Domain rules and seed state are kept separate from rendering so locale selection, target validation, custom persona naming, relationship metrics, and lifecycle transitions can be tested without a backend. The first UI persists settings and user-created data in `localStorage`; later FastAPI endpoints can replace the storage adapter without changing page components.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS, Lucide React, Vitest.

## Task 1: Frontend Scaffold And Domain Tests

- Create Vite, TypeScript, Tailwind, and Vitest configuration.
- Add failing tests for locale fallback, exact LINE names, reply-delay validation, target lifecycle, custom-name uniqueness, and duration aggregation.
- Implement the domain helpers until those tests pass.

## Task 2: Local Catalog And Persistence

- Model the six 20-35 personas and three weapons already seeded on the server.
- Add a versioned local-storage adapter with safe defaults and malformed-data fallback.
- Keep custom personas and weapons age/gender independent.

## Task 3: Application Shell And Pages

- Build the responsive KingJoo-style sidebar and header with system light/dark colors.
- Implement Dashboard, Basic Settings, Scammer List, and Persona Editor pages.
- Implement active/ended target tabs, reply checkboxes, add/edit/end/revive/delete/export actions, and guarded custom deletion.
- Implement base/custom persona and weapon cards, full-text modals, cloning, creation, editing, image preview, and validation.

## Task 4: Verification

- Run unit tests, typecheck, and production build.
- Start the Vite development server.
- Use Playwright screenshots and interaction checks at desktop and mobile widths.
- Fix overflow, overlap, contrast, and interaction failures before reporting the URL.
