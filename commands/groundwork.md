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
- Validate with `python3 skills/groundwork/scripts/validate_record.py <record> --pre-hunt`
  and fix every violation.
- Then run exactly one fresh-agent hunt (`/groundwork-hunt <record>`). Fold its
  material findings into the record once, add the completed H1 row, run the
  validator without `--pre-hunt`, and begin implementation. Never run a
  confirmation, closing, or second hunt.

Do not write production code in this command. The record is the deliverable.
