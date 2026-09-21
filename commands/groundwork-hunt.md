---
description: Hunt a groundwork record for what is missing from it
---

Hunt the record at: $ARGUMENTS

If no path was given, use `$GROUNDWORK_RECORD`, then `.groundwork/<branch>.md`,
then `.groundwork/record.md`.

Read `skills/groundwork/references/hunt.md` and follow it exactly. You did not
write this record — do not reconstruct its reasoning, check it against the
repository.

- Run `validate_record.py` first. If it reports violations, say so and stop.
- Re-run every fact's command yourself. Issue independent commands together.
- Re-run the enumeration wider than the record ran it, and diff the hit lists.
- Open every SAFE row before believing it.
- Report at most seven absences, in the six classes only: unverified claim,
  second path, verdict without evidence, invariant already false, invariant
  nothing enforces, unnamed unknown.
- Report nothing about the design, the naming, or whether another approach
  would be better. Zero absences is a valid result — say it plainly, name what
  you checked, and stop.

Finish with one line of coverage: what you re-ran, what you could not, and what
you did not check.
