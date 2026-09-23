---
description: Hunt a groundwork record for what is missing from it
---

Review record: $ARGUMENTS

Require exactly one argument: `<record>`. This is the record's only hunt.

Read `skills/groundwork/references/hunt.md` and follow it exactly. You did not
write this record — do not reconstruct its reasoning, check it against the
repository.

- Acquire `.groundwork/hunt.lock` with `hunt_lock.py acquire`. If it reports a
  dead hunt, report it and stop; never replace its lock silently.
- Run `validate_record.py <record> --pre-hunt` after locking. If it reports
  violations, say so, release the lock, and stop.
- Run the full six-class method once. The classes are lenses, not quotas.
- Apply the materiality rule before accepting a candidate. Record a short
  reason for every rejected candidate.
- Give every accepted absence a stable id (`A1`, `A2`, ...).
- Report at most seven absences, in the six classes only: unverified claim,
  second path, verdict without evidence, invariant already false, invariant
  nothing enforces, unnamed unknown.
- Reject citation precision, merely more precise commands, unrelated docs,
  style, duplicates, and unsupported speculation. Zero material absences is a
  valid result — say it plainly, name what you checked, and stop.

Write the complete result once to `.groundwork/hunt.md`; refuse to overwrite an
existing file. Finish with coverage of all six lenses. Release the lock on
every exit path after the findings file is frozen. Do not suggest or run a
second hunt.
