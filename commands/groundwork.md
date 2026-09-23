---
description: Record the facts, blast radius and invariants of a change before writing code
---

Invoke the `groundwork` skill and write the record for: $ARGUMENTS

If no change was named, use the change the conversation is already about. If
there is no such change, ask for one instead of guessing.

Follow the skill exactly:

- Write `.groundwork/<branch>.md` from `templates/RECORD.template.md`.
- Run every fact's command before writing its row, and paste the line it
  printed. Never write a fact from memory of a file read earlier in the session.
- Put the enumerating command above the blast radius, and give every row a
  verdict of SAFE, UPDATE or UNKNOWN. Read `references/second-paths.md` before
  deciding the enumeration is finished.
- Write invariants so that a single counterexample kills them, and name that
  counterexample after `breaks if:`.
- Validate with `python3 skills/groundwork/scripts/validate_record.py` and fix
  every violation.
- Then start round 1 as a hunt (`/groundwork-hunt <record> 1 hunt`) in a fresh
  agent. Fold its absences into the record, use confirmations for that changed
  slice, and finish with a full hunt. Never exceed three hunts.

Do not write production code in this command. The record is the deliverable.
