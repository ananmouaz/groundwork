# Changelog

## 0.3.0 — 2026-09-23

- Replace confirmation, closing, and repeated hunt rounds with exactly one
  fresh-agent hunt before implementation.
- Add the materiality gate and require rejected candidates to carry a reason.
- Require one completed hunt for guarded production edits while allowing the
  implementing agent to fold findings into the record without another hunt.
- Resolve hook validation from the target file's Git worktree.
- Preserve warn, block, off, fail-open, lock, and structural record behavior.

## 0.2.1

- Remove duplicate hook declaration from the plugin manifest.

## 0.2.0

- Add frozen multi-round hunts, confirmations, and the three-hunt cap.

## 0.1.0

- Introduce the Groundwork record, validator, hook, commands, and tests.
