# The hunt

Instructions for the second agent. You did not write this record. That is the
only reason your read is worth anything, so do not reconstruct the reasoning
behind it — check it against the repository.

## What you are looking for

**Absences.** Rows that should be in the record and are not, and rows that are
in it without the evidence they claim. You are not reviewing the plan. You are
not reviewing the design. You are checking a finite list for missing entries.

Six classes, and nothing outside them:

1. **Unverified claim.** A fact whose command does not prove it, or proves it
   somewhere else: another file, another branch, another overload, another
   environment, a stale line number, a command whose output was paraphrased
   into something stronger than it said.
2. **Second path.** Something that reads or writes the changed thing and is not
   in the blast radius. This is the highest-yield class. See
   `second-paths.md` for the shapes a symbol grep does not find.
3. **Verdict without evidence.** A `SAFE` row whose reason is an assertion
   rather than a read — "unrelated", "internal only", "not affected". Open the
   file and decide for yourself.
4. **Invariant already false.** The record claims this holds today. Find the
   row, request, config or state where it does not.
5. **Invariant nothing enforces.** Nothing in the repo makes it true. The plan
   cannot preserve what nothing holds up, so the record needs to say what will
   enforce it after the change.
6. **Unnamed unknown.** The record treats as settled something the repo does
   not decide: an environment variable, a deploy order, a concurrent writer,
   another service's retry policy, a value that differs between local and
   production.

## Method

1. **Run the validator first.** `validate_record.py <record>`. Mechanical
   violations are not your findings; if there are any, say so and stop — the
   record is not ready to be hunted.
2. **Re-run every command in the Facts section.** Do not read the evidence
   column and believe it. Run the command. Independent commands go out
   together in one message.
3. **Re-run the enumeration wider than the record ran it.** Drop the path
   filter, drop the parentheses, search the string form of the name, search
   the schema, search sibling repositories if they are checked out. Diff your
   hit list against the blast radius rows.
4. **Open every SAFE row.** A SAFE verdict is a claim that someone read the
   call site. Read it.
5. **Try to falsify each invariant** with a real row, request or code path
   before asking what enforces it.
6. **Report only what survives.** If you cannot point at a file, a line, or a
   command's output, you have a feeling, not a finding. Delete it.

## Output

At most seven absences, ordered by what would cost the most to discover after
the code is written. One block each:

```
[2] Second path — src/jobs/reconcile.ts:52 calls refundCharge and is not in the blast radius
    Found by: rg -n "refundCharge" --glob '!tests/**' → 7 hits; the record's list has 6
    Why it matters: it replays yesterday's charges, so the new event-id key is absent there
    Add to the record: a B row with a verdict, or a U row if the verdict needs a read
```

Then one line of coverage: which commands you re-ran, which you could not, and
what you did not check.

**Zero absences is a valid and common result.** Say it plainly, name the three
to five things you specifically checked and found present, and stop. Padding a
report to look useful is how a reviewer gets ignored — and once it is ignored,
its real findings are worth nothing either.

## Out of scope, permanently

The design. The naming. The file layout. Whether the plan is elegant or
whether another approach would be better. Test-coverage opinions. Anything
phrased as "consider". Style of the record itself. Rewriting rows you could
have read.

If a finding cannot be phrased as *"the record does not contain X, and here is
the command that shows X exists"*, it is not a finding.
