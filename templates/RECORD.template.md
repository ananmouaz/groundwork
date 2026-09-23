# groundwork — <what this change is called>

Tree: <run `git status --porcelain | shasum` immediately before the one hunt and paste its first field>

Copy this to `.groundwork/<branch>.md` and replace every angle-bracket
placeholder. The validator fails while any placeholder survives, on purpose:
a half-filled record is worse than none, because it looks finished.

## Task

<One sentence. The behavior that is different after this change.>

## Facts

Claims about this repo that the change depends on. Each one carries the command
that proved it and the line the command printed. No command, no fact.

- F1 — <claim about the repo> — `<command that proves it>` → <the output line>
- F2 — <claim about the repo> — `<command that proves it>` → <the output line>

## Blast radius

Everything that reads or writes what this change touches. Every row gets a
verdict: SAFE (it survives the change unchanged), UPDATE (this change must edit
it too), UNKNOWN (carried into Unknowns below).

Enumerated by: `<the command that produced this list>` → <N> hits

- B1 — <path:line> — <what it does with the thing being changed> — SAFE — <why it survives>
- B2 — <path:line> — <what it does with the thing being changed> — UPDATE — <what it needs>

## Invariants

What must still be true when the change lands. Write each one so a single
counterexample kills it. "The code stays clean" is not an invariant.

- I1 — <a claim that is either true or false> — breaks if: <the input or state that falsifies it>

## Plan

The edits, in order. Each step names the evidence it rests on.

- P1 — <the edit> — rests on F1, B2
- P2 — <the edit> — rests on I1

## Unknowns

What is still not known, and what would settle it. Write `none` if there is
nothing left — but read the blast radius again first.

- U1 — <the open question> — resolved by: <the command, file or person that answers it>

## Hunts

Before the hunt, leave this as `none` and validate with `--pre-hunt`. After the
one hunt, fold accepted material findings into the record once and replace
`none` with H1. The final field is the accepted material-finding count.

none
