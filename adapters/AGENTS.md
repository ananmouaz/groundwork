# AGENTS.md — groundwork section

Append this to the `AGENTS.md` at the root of the repo you are working in.
Codex reads `AGENTS.md` automatically, and several other agents have adopted
the convention.

`AGENTS.md` is always-loaded context, so keep the entry **thin**: a pointer
plus the non-negotiables. The full method belongs in the file it points at.

---

## Before writing code

For any non-trivial change — a shared function, a schema, a public contract,
money, auth, or anything with more than one caller:

**Groundwork runs once before implementation. Shrike, Bugbot, or equivalent
tools review the resulting code later.**

**Read `.agents/groundwork.prompt.md` and follow it before editing production
code.** Write the record first. Do not start with the edit and document it
afterwards; a record written after the code is a summary, and a summary cannot
be wrong in a useful way.

Non-negotiables, restated here so they survive even if the file is not read:

- **No fact without the command that proves it**, and the line that command
  printed. A claim about this repo that you did not just check is a belief.
- **No blast radius without the command that enumerated it.** A list of what
  came to mind is not an enumeration. Every row gets a verdict: SAFE, UPDATE,
  or UNKNOWN.
- **No invariant that cannot be false.** Name the counterexample that would
  falsify it.
- **No plan step that cites nothing.** Every edit points at the evidence it
  rests on.
- **A fact that turns out false while coding stops the work.** Amend the row,
  then revisit every step that cited it.

Validate the draft with `validate_record.py --pre-hunt`, then have exactly one
*fresh* agent hunt it for material absences. Fold accepted findings into the
record once, add `H1 — hunt — complete — N`, validate without `--pre-hunt`, and
implement. Do not run a confirmation, closing, or second Groundwork hunt.
