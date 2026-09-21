---
name: groundwork
description: Record the facts, blast radius and invariants of a change before writing production code, then have a fresh agent hunt that record for what is missing. Use when starting implementation on a non-trivial change, when an agent is about to edit a file it has not read the callers of, or when the user says "groundwork", "invariants", "before you code", "what could this break", "/groundwork". Not for trivial edits or for reviewing code that already exists.
license: MIT
---

# groundwork

Write down what you believe about the repo, with the command that proves each
belief, before any production code exists. Then hand the record to a fresh
agent whose only job is to find what is absent from it.

## Why this exists

Most bugs a coding agent writes are not reasoning errors. They are two things:

1. **A claim about the repo that was never checked.** "The handler already
   validates this." It did, in the file the agent read forty minutes ago,
   on a path that is not this one.
2. **A second path that was never enumerated.** The change is correct for the
   caller in the diff and wrong for the cron job, the admin action, the
   migration, or the test double that also calls it.

Both are absences. Neither is visible in the code the agent produces, which is
why they survive a code review of that code — the reviewer reads what is
there. They are visible in the *record*, because a record is a finite list and
a list can be checked for missing rows.

Measured on one repo's 51 review-bot findings: about a fifth were unverified
claims about the repo, and about a third were an unenumerated second path.
Both classes are cheaper to catch before the code exists than after.

**The economics: reviewing a record costs one agent call. Finding the same
defect after the push costs a review cycle, a red gate and a fix commit.**

## When to run this

Run it when the change is non-trivial: it touches a shared function, a schema,
a public contract, money, auth, or anything with more than one caller. Run it
when you are about to edit a file whose callers you have not read.

Do not run it for a typo, a string change, a new isolated file, or a revert.
The record costs a few minutes; on a trivial change that is the whole budget.

This skill is for code that does not exist yet. For code that already exists,
review it instead.

## The record

One markdown file, six sections, at `.groundwork/<branch>.md`. Start from
`templates/RECORD.template.md`. The full field spec is in
`references/record-format.md`; read it before writing the first record.

```markdown
## Task          one sentence: the behavior that is different afterwards
## Facts         F1..Fn  claim — `command that proved it` → the output line
## Blast radius  B1..Bn  site — what it does — SAFE|UPDATE|UNKNOWN — why
## Invariants    I1..In  a claim that can be false — breaks if: counterexample
## Plan          P1..Pn  the edit — rests on F1, B2
## Unknowns      U1..Un  the open question — resolved by: what would settle it
```

Four rules carry the whole method:

- **No fact without a command.** If you cannot name the command that proves it
  and the line it printed, it is a belief. Write it under Unknowns instead.
- **No blast-radius list without the command that produced it.** A list of
  what came to mind is not an enumeration.
- **No invariant that cannot be false.** "The code stays clean" is a mood.
  "Exactly one refund row exists per charge and reason" is an invariant,
  because one row falsifies it.
- **No plan step that cites nothing.** Every edit points at the evidence it
  rests on. Steps that cite nothing are where the invented behavior lives.

## Workflow

### Phase 1 — Facts, each with its command

Write the claim, then run the command, then paste the line it printed. In that
order. A fact written from memory of a file read earlier is exactly the failure
this skill exists to catch — the file moved, the branch changed, or the read was
of a different overload.

Issue the commands together in one message; they do not depend on each other.

```bash
rg -n "refundCharge" src/          # where the thing being changed is used
git log --oneline -5 -- src/billing/refund.ts   # what changed here recently
sed -n '30,60p' src/billing/refund.ts           # the actual current body
```

When a command prints nothing, that is a fact too: `→ no output` is evidence of
absence, and is often the most load-bearing row in the record.

### Phase 2 — Blast radius, enumerated mechanically

List everything that reads or writes what this change touches, and give each
row a verdict: **SAFE** (survives unchanged), **UPDATE** (this change must edit
it too), **UNKNOWN** (carried into Unknowns).

Grep for the symbol first, then for the ways a symbol is reached without being
named: string keys, routes, database columns, serialized payloads, generated
code, dependency injection, test doubles, and anything in another repository.
`references/second-paths.md` lists the shapes, per language, that a
symbol-name grep does not find.

Name the command above the list. A blast radius with no command above it is a
guess with a bullet point in front of it.

### Phase 3 — Invariants

What must still be true after the change. For each one, write the
counterexample that would falsify it — not a restatement of the claim. Then
ask the question that turns an invariant into a finding: **what enforces this
today?** A unique index, a type, a guard, a test. If the answer is "nothing",
the invariant is already at risk and the plan has to say so.

### Phase 4 — Plan, and Phase 5 — Unknowns

The plan is the edits in order, each citing its evidence. Unknowns are what
you could not settle, each with what would settle it. Writing `none` under
Unknowns is allowed, and is a claim like any other: read the blast radius once
more before you make it.

### Phase 6 — Validate

```bash
python3 skills/groundwork/scripts/validate_record.py .groundwork/<branch>.md
```

This is mechanical only: it checks that facts carry commands, rows carry
verdicts, invariants carry counterexamples, and plan steps cite evidence. It
cannot tell whether any of it is true. Fix every violation before the hunt —
a hunter should spend its attention on what is missing, not on formatting.

### Phase 7 — The hunt

Hand the record to a **fresh agent with no memory of writing it**. Its
instructions are in `references/hunt.md`, and its scope is narrow: report what
is *absent*, never what is present.

Six classes of absence, and nothing else:

| | What the hunter looks for |
|---|---|
| **1. Unverified claim** | A fact whose command does not actually prove it, or proves it somewhere else — a different file, branch, overload or environment. |
| **2. Second path** | Something that reads or writes the changed thing and is not in the blast radius. Re-run the enumeration with a wider net. |
| **3. Verdict without evidence** | A SAFE row whose reason is an assertion rather than a read. SAFE means someone opened the file. |
| **4. Invariant already false** | The record says this holds today. Find the row, request or state where it does not. |
| **5. Invariant nothing enforces** | Nothing in the repo makes it true, so the plan cannot preserve it — it can only hope. |
| **6. Unnamed unknown** | The record treats as settled something the repo does not decide: config, environment, ordering, a race, another service. |

Out of scope for the hunt, permanently: the design, the naming, the file
layout, whether the plan is elegant, whether a different approach would be
better, and any suggestion that starts with "consider". Those are opinions
about a plan. This is a check for holes in a record.

**Zero absences is a valid result**, and on a small change it is the common
one. A hunter that pads its report to look useful trains you to stop reading
it, at which point the real findings are worthless too.

### Phase 8 — Fold the answers in, then write the code

Every absence the hunt returns goes back into the record as a row: a new fact,
a new blast-radius entry, a corrected verdict, a new unknown. Re-run the
validator. Then implement.

## While you are coding

The record is not a document you wrote and left behind. It is the thing you
are now checking reality against.

- **A fact turns out to be false → stop.** Do not patch around it. Amend the
  row, then look at every plan step that cited it. This is the payoff: the
  wrong belief is now named, so its consequences are traceable.
- **A new caller appears → add the row with a verdict.** An unlisted caller
  found while coding is a miss in the enumeration; widen the grep that missed
  it rather than adding the one row.
- **An invariant needs an exception → it was not an invariant.** Rewrite it,
  or write down which caller is the exception and why.

At the end, the record is the description of what you actually did, and the
diff between its first and last version is a list of what you believed wrongly.
That list is worth reading before the next change of the same shape.

## The hook

`hooks/require_record.py` is a PreToolUse hook that checks the record before an
Edit or Write to production code. It is deliberately timid:

- It is inert until a project has a `.groundwork/` directory. Opting in is
  making that directory.
- It never guards tests, markdown, dotfiles, or the record itself.
- Default mode is `warn`: the edit proceeds, the agent is told what the record
  is missing. `GROUNDWORK_MODE=block` denies instead; `off` disables it.
- If anything about the hook fails — missing validator, unreadable payload —
  it allows the edit. A broken guard must not become a broken editor.

## Cost

A record for a real change is 15 to 30 rows and a handful of greps. The hunt
is one agent call over a file plus the repo. Against that: a wrong claim about
the repo, discovered after the push, costs a review round trip, a fix commit,
and a re-run of whatever gate the push turned red.

If a change is small enough that this trade looks bad, it is small enough to
skip the record. Say so and move on.
