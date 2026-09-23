---
name: groundwork
description: Record the facts, blast radius and invariants of a non-trivial change before implementation, then have exactly one fresh agent hunt that record for material absences. Use when starting implementation on a shared function, schema, public contract, money, auth, or any change with multiple callers. Not for trivial edits or reviewing code that already exists.
license: MIT
---

# groundwork

> **Groundwork runs once before implementation. Shrike, Bugbot, or equivalent tools review the resulting code later.**

Groundwork improves the initial implementation plan. The implementing agent
writes a finite, evidence-backed record; one fresh agent hunts that record for
material absences; the implementing agent folds accepted findings in once;
the validator passes; implementation starts. Groundwork is not an iterative
review loop.

## When to run it

Run Groundwork before a non-trivial change: a shared function, schema, public
contract, money, auth, or anything with more than one caller. Do not run it
for a typo, a string-only change, a new isolated file, a revert, or code that
already exists and needs review.

## The record

Create `.groundwork/<branch-slug>.md` from
`templates/RECORD.template.md`. Read `references/record-format.md` before
writing the first record and `references/second-paths.md` before completing
the blast radius.

```markdown
## Task          one sentence: the behavior that differs afterwards
## Facts         F1..Fn  claim — `command that proved it` → output
## Blast radius  B1..Bn  site — role — SAFE|UPDATE|UNKNOWN — why
## Invariants    I1..In  claim — breaks if: counterexample
## Plan          P1..Pn  edit — rests on F1, B2
## Unknowns      U1..Un  question — resolved by: what settles it
## Hunts         exactly one H1 row after the hunt
```

Four rules carry the method:

- **No fact without a command.** If the command and its output do not prove
  the claim, write an unknown instead.
- **No blast-radius list without the command that produced it.** Search symbol
  names and the second paths that do not spell the symbol.
- **No invariant that cannot be false.** Name the concrete counterexample.
- **No plan step that cites nothing.** Every edit points to the facts, blast
  rows, or invariants it rests on.

`Tree:` records the tree the hunter inspected. It must be a 40-character SHA-1
digest. The validator checks the shape, not later freshness: folding findings
into the record does not trigger another hunt.

## Workflow

1. **Write the record.** Run each fact command, mechanically enumerate the
   blast radius, name falsifiable invariants, and resolve decision-blocking
   unknowns.
2. **Validate before the hunt.** Run:

   ```bash
   python3 skills/groundwork/scripts/validate_record.py \
     .groundwork/<branch>.md --pre-hunt
   ```

3. **Run exactly one fresh-agent hunt.** Use `/groundwork-hunt <record>`. The
   hunter follows `references/hunt.md`, uses all six absence classes as search
   lenses, and freezes its result at `.groundwork/hunt.md`.
4. **Fold material findings once.** Add or correct the rows that materially
   change the code/configuration, tests, plan/blast radius, or a
   decision-blocking unknown. Record the hunt as:

   ```markdown
   - H1 — hunt — complete — 2
   ```

   The final number is the accepted material-finding count. It may be zero.
   Do not run a confirmation hunt, closing hunt, clearance round, or second
   hunt after changing the record.
5. **Validate, then implement.** Run the validator without `--pre-hunt`. A
   valid record with exactly one completed hunt opens the production-edit
   gate.

## The six search lenses

The hunter checks all six. They are lenses, not quotas; zero findings is a
valid result.

1. **Unverified claim** — a fact's command does not prove its claim or proves
   it in another file, branch, overload, or environment.
2. **Second path** — a reader or writer reached by the change is absent from
   the blast radius.
3. **Verdict without evidence** — a SAFE row rests on assertion rather than a
   read of the site.
4. **Invariant already false** — a real row, request, configuration, or state
   already falsifies the claim.
5. **Invariant nothing enforces** — no index, type, guard, test, or runtime
   mechanism makes the invariant true.
6. **Unnamed unknown** — the record treats as settled something the repository
   does not decide, such as deploy order, configuration, races, or another
   service's behavior.

## Materiality

A hunter finding is valid only when resolving it changes at least one of:

- production code or configuration;
- test behavior or coverage needed for the change;
- the implementation plan or blast radius;
- a decision-blocking unknown that must be answered before coding.

Accepted examples:

- A scheduled worker calls the changed function but is absent from the blast
  radius, so its code or tests must change.
- A claimed uniqueness invariant has no index or guard, so the plan must add
  an enforcement mechanism.
- Production ordering is not represented in the repository and determines
  whether the migration is safe, so coding must wait for an answer.

Reject these and record a short reason in the frozen hunt result:

- citation or line-number precision when the underlying claim remains true;
- a verification command that could be phrased more precisely but still
  verifies the claim;
- requests to inventory unrelated documentation;
- stylistic improvements;
- concerns already covered by an invariant or required test;
- speculative surfaces without evidence the proposed change reaches them.

Examples: reject “use `rg --no-heading` for a cleaner citation” because it
does not change the plan; reject “inventory every README” when no executable
documentation reaches the change; reject a possible mobile client when the
repository evidence shows the changed API is server-internal.

The goal is not a perfect document. It is the smallest record that makes
implementation safe.

## The hook

`hooks/require_record.py` is a fail-open PreToolUse hook for Edit, Write,
MultiEdit, and NotebookEdit:

- It is inert until the target worktree has a `.groundwork/` directory.
- It resolves the Git worktree from the target file, not an unrelated session
  cwd.
- Tests, markdown, dotfiles, and the record are normally exempt.
- A live hunt lock freezes every write while the one hunter reads.
- `warn` (default) allows and explains; `block` denies; `off` disables.
- Before guarded production edits, the record must be structurally valid and
  contain exactly one `H1 — hunt — complete — N` row.
- Missing validator, unreadable payload, or other hook failures allow the edit.

Repository-specific watched paths, thresholds, and exemptions belong to the
consuming repository, not this plugin.

Once implementation begins, Groundwork is finished. New code is reviewed by
Shrike, Bugbot, tests, or equivalent downstream tools; do not reopen the
Groundwork hunt.
