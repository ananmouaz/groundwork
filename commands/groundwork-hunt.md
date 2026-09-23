---
description: Hunt a groundwork record for what is missing from it
---

Review arguments: $ARGUMENTS

Require: `<record> <round> <hunt|confirmation> [previous-findings]`. The caller
must name the kind. Do not infer or change it. Round 1 must be a hunt and has no
previous findings. Later rounds require the frozen prior file at
`.groundwork/hunts/<previous-round>.md`.

Read `skills/groundwork/references/hunt.md` and follow it exactly. You did not
write this record — do not reconstruct its reasoning, check it against the
repository.

- Acquire `.groundwork/hunt.lock` with `hunt_lock.py acquire`. If it reports a
  dead round, report that round and stop; never replace its lock silently.
- Run `validate_record.py` after locking. If it reports violations, say so,
  release the lock, and stop.
- For a hunt, run the full six-class method. For a confirmation, check only
  changed rows and earlier absences they close; return `widened` if that scope
  is insufficient.
- Give every absence a stable id (`A1`, `A2`, ...). Preserve ids from the
  previous frozen file.
- Report at most seven absences, in the six classes only: unverified claim,
  second path, verdict without evidence, invariant already false, invariant
  nothing enforces, unnamed unknown.
- Report nothing about the design, the naming, or whether another approach
  would be better. Zero absences is a valid result — say it plainly, name what
  you checked, and stop.

Write the complete result once to `.groundwork/hunts/<round>.md`; refuse to
overwrite an existing file. Finish with one line of coverage: what you re-ran,
what you could not, and what you did not check. Release the lock on every exit
path, after the findings file is frozen.
