# Mac-Only Main Cleanup Design

Date: 2026-07-28

## Goal

Replace the local and GitHub `main` branch with a clean macOS-only lineage while
preserving the Windows experiment in its existing backup worktree and branch.
The resulting `main` must contain the latest approved macOS message-processing
and homepage changes without carrying Windows implementation commits or files.

## Source and history boundary

- Use commit `a100395` (`feat: skip LINE chats without new messages`) as the
  final shared macOS-only base.
- Build the cleaned lineage forward from that commit instead of reverting the
  later Windows commits. This keeps Windows implementation commits out of
  `main` history, not merely out of the final file tree.
- Preserve the existing `codex/windows-control-panel` branch and
  `.worktrees/windows-control-panel` worktree unchanged as the recoverable
  Windows backup.
- Do not add, delete, or commit the unrelated untracked `videos/` directory.
- Push the clean lineage to `origin/main` only after all verification passes.
  Because `a100395` descends from the current GitHub `main`, the update must be a
  normal fast-forward and must not use force push.

## macOS changes retained

Carry the current uncommitted macOS AI behavior into the clean lineage:

- If the bottommost visible LINE chat item is on the left, return `reply`.
- Locate the nearest preceding right-side item and aggregate every visible
  left-side item below it, in display order, into one `incoming_summary`.
- If no preceding right-side item is visible, aggregate all visible left-side
  items.
- Return `skip` only when the bottommost visible chat item is on the right.
- Accept both ASCII and full-width colons when normalizing known JSON response
  keys.
- Keep the screenshot-based multimodal content path. OCR remains limited to
  contact discovery and unread detection.

Carry the current uncommitted macOS-only public download contract into the clean
lineage:

- Disable the Windows download URL and show `稍後提供` / `Coming soon`.
- Keep the stable macOS DMG URL with release query
  `release=1.0.1-9ff118bd`.
- Keep the open-source note and synchronized homepage asset cache version.
- Publish only the macOS artifact in `web/sweety-update.json`.
- Keep Windows and macOS download counters scoped to the existing homepage
  rules; disabled Windows navigation must not become a live installer link.

## Windows removal boundary

The cleaned `main` file tree must not contain Windows runtime, shell, packaging,
release, or Windows-control-panel design files introduced after `a100395`.
Shared macOS modules must remain at their `a100395` implementation unless
explicitly changed by the retained macOS AI or homepage work above.

Historical documentation that already existed at `a100395`, such as an older
Windows installer release design or homepage copy tests, may remain when it
documents prior public behavior. It must not enable, build, or ship a Windows
runtime in the cleaned branch. Tests and copy that assert an active Windows
download must be updated to the macOS-only public contract.

## Implementation flow

1. Work from an isolated branch and worktree created at `a100395`.
2. Commit this approved design and the subsequent implementation plan there.
3. Reapply the retained changes test-first:
   - add the AI boundary and full-width-colon regression tests;
   - add the macOS-only homepage contract tests;
   - confirm each focused test set fails against the clean base;
   - apply the minimal AI and homepage implementation changes;
   - confirm the focused tests pass.
4. Verify the complete desktop, frontend, and homepage suites.
5. Inspect the branch history and tracked tree for Windows commits and runtime
   files.
6. Preserve the old local main tip under a backup reference, then move the local
   `main` worktree to the verified clean lineage without deleting the existing
   Windows backup worktree or `videos/`.
7. Push the verified local `main` to `origin/main` as a fast-forward.

## Verification

Completion requires all of the following:

- Desktop Python suite passes.
- Frontend Vitest suite passes.
- Homepage Node test suite passes with Windows unavailable and the macOS URL
  enabled.
- Focused AI tests prove bottom-left reply aggregation, bottom-right skip, and
  full-width-colon normalization.
- `git log a100395..main` contains only the cleanup design, plan, and retained
  macOS implementation commits.
- The tracked `main` tree contains no Windows runtime, Windows shell, Windows
  packaging, or Windows control-panel files introduced by the removed commits.
- `origin/main` resolves to the same commit as local `main` after push.
- `codex/windows-control-panel` and its worktree still resolve to their original
  Windows backup state.
- The root `videos/` directory remains present and untracked.

## Failure handling

- If any baseline or final test fails, stop before moving `main` or pushing.
- If the remote branch is no longer an ancestor of the clean lineage, fetch and
  reassess instead of force pushing.
- If switching the root worktree would overwrite uncommitted data, preserve the
  tracked patch in a recoverable stash or backup reference and verify it before
  changing branch pointers.
- Never clean or reset the Windows backup worktree as part of this operation.
