# The one hunt

> **Groundwork runs once before implementation. Shrike, Bugbot, or equivalent tools review the resulting code later.**

You are the one fresh hunter. You did not write the record. Check it against
the repository exactly once, freeze the result, and stop. There are no
confirmation hunts, closing hunts, retries, or clearance rounds.

## Freeze the review

Acquire the project lock before reading:

```bash
python3 skills/groundwork/scripts/hunt_lock.py acquire <project>
```

A fresh existing lock means the one hunt is already active. A lock older than
two hours is a dead hunt: report its contents and stop. Never replace it
silently. Validate the record structure after acquiring the lock:

```bash
python3 skills/groundwork/scripts/validate_record.py <record> --pre-hunt
```

Release the lock on every exit path:

```bash
python3 skills/groundwork/scripts/hunt_lock.py release <project>
```

## Six absence classes

Use every class as a search lens, not a quota. Report zero findings when zero
material absences survive.

1. **Unverified claim.** Re-run each fact command. Report a claim only when the
   command does not prove it or proves another file, branch, overload, or
   environment.
2. **Second path.** Re-run the enumeration with a wider net using
   `second-paths.md`. Report a reader or writer the record omitted.
3. **Verdict without evidence.** Open every SAFE row. Report it only when the
   stated reason is not supported by the site.
4. **Invariant already false.** Try to falsify each invariant with a real row,
   request, configuration, or code path.
5. **Invariant nothing enforces.** Identify the index, type, guard, test, or
   runtime mechanism that holds each invariant up.
6. **Unnamed unknown.** Find assumptions the repository cannot settle, such as
   environment, ordering, concurrency, or another service's behavior.

## Materiality gate

A candidate is a finding only if resolving it changes at least one of:

- production code or configuration;
- test behavior or coverage needed for the change;
- the implementation plan or blast radius;
- a decision-blocking unknown that must be answered before coding.

Accepted examples:

- A cron worker reaches the changed code but is absent from the blast radius.
- The invariant needs a unique index that the plan does not include.
- Safe deployment depends on an external ordering guarantee that must be
  answered before coding.

Reject the following, and record a short reason:

- citation or line-number nitpicks when the claim remains true;
- commands that could be more precise but already verify the claim;
- requests to inventory unrelated documentation;
- stylistic improvements;
- duplicate concerns already covered by an invariant or test;
- speculative surfaces without evidence the change reaches them.

For example, “the fact should quote line 42 instead of line 41” is rejected if
the command still proves the claim. “Search every README” is rejected unless an
executed snippet reaches the changed behavior. “A mobile app might call this”
is rejected without evidence that the changed contract is exposed to it.

The goal is the smallest record that makes implementation safe, not a perfect
document.

## Method

1. Run the pre-hunt validator. Mechanical violations are not findings; report
   them, release the lock, and stop.
2. Re-run every fact command.
3. Widen the blast-radius enumeration and compare real hits with the rows.
4. Open every SAFE site.
5. Try to falsify every invariant and identify its enforcement.
6. Apply the materiality gate to every candidate.
7. Write the result once to `.groundwork/hunt.md`, make it read-only, release
   the lock, and stop. Do not recommend another hunt.

## Output

Report at most seven accepted material findings, ordered by the cost of finding
them after implementation. Use stable ids:

```text
[A1] Second path — src/jobs/reconcile.ts:52 reaches refundCharge but is absent
    Found by: rg -n "refundCharge" --glob '!tests/**' → 7 hits; record has 6
    Why it is material: this worker also needs the new key and test coverage
    Add to the record: a B row and a plan step
```

Then list rejected candidates with a short reason, followed by coverage of all
six lenses: commands re-run, SAFE rows opened, invariants tested, and anything
that could not be checked.

The frozen file must include the record path, `complete` verdict, tree digest,
record hash, accepted count, accepted findings, rejected candidates, and
coverage. It is evidence that the one hunt occurred. The implementing agent
then folds accepted findings into the record once and adds:

```markdown
- H1 — hunt — complete — <accepted material finding count>
```

Changes made while folding findings do not invalidate the hunt and do not
authorize another one.
