# The record format

One markdown file. Seven sections, in this order: Task, Facts, Blast radius,
Invariants, Plan, Unknowns, Hunts. Every row is a top-level list item whose fields are
separated by an em dash (`—`) or a double hyphen (`--`), starting with an id.

Immediately below the title, `Tree:` holds the first field printed by
`git status --porcelain | shasum`. Refresh it immediately before each round.
Validation fails as soon as the working tree no longer has that digest.

Indented bullets under a row are notes. The validator ignores them, so use them
freely for the detail that does not fit on the line.

## Where it lives

`.groundwork/<branch-slug>.md`, or `.groundwork/record.md` when the work is not
on its own branch. `GROUNDWORK_RECORD` overrides both.

Commit it or ignore it — both work, and the choice is about your team, not the
method. Committed, the record reviews alongside the diff and the next person
sees which beliefs the change rested on. Ignored, it stays a private working
note. What does not work is writing it after the code: then it is a summary,
and a summary cannot be wrong in a useful way.

## Task

One sentence naming the behavior that differs after the change. Not the
implementation. "Refund webhook ignores a repeated delivery" — not "add an
idempotency key column".

## Facts — `F1 — claim — command → evidence`

```markdown
- F1 — no uniqueness constraint exists on refund rows — `rg -n "unique" migrations/0012_refunds.sql` → no output
- F2 — every refund goes through `refundCharge()` — `rg -n "stripe.refunds.create" src/` → `src/billing/refund.ts:41` (one hit)
```

The claim is what you are relying on. The command is how anyone re-checks it in
one paste. The evidence is what the command printed — a line, a count, or
`no output`.

Rules:

- Run the command before writing the row. A fact written from memory is the
  defect this whole method exists to catch.
- `no output` is evidence. Absence is usually the load-bearing claim: nothing
  validates this, nothing else calls it, no index exists.
- A command that "shows" the claim only after human interpretation is fine, as
  long as the evidence line is the real output and not a paraphrase.
- Facts may be hedged in their wording. They carry their own proof, so the
  hedge costs nothing. Invariants may not.

## Blast radius — `B1 — site — role — verdict — why`

```markdown
Enumerated by: `rg -n "refundCharge\(" src/ tests/` → 6 hits

- B1 — src/webhooks/stripe.ts:88 — handles the provider callback — UPDATE — must look up the event id first
- B4 — tests/billing/refund.test.ts:14 — asserts one provider call — SAFE — the assertion still holds
```

- The `Enumerated by:` line is required and must contain a command. More than
  one is better: a symbol grep, a string grep, a route table read.
- Verdicts are exactly `SAFE`, `UPDATE`, `UNKNOWN`.
- `SAFE` means you opened the file and read the use. It does not mean the name
  looked unrelated.
- Every `UNKNOWN` row must be carried into Unknowns by its id, or the record
  has a hole with a bullet point in front of it.

## Invariants — `I1 — claim — breaks if: counterexample`

```markdown
- I1 — exactly one provider refund exists per charge and reason pair — breaks if: two deliveries commit in the same window with no unique index
```

An invariant is a claim that a single counterexample destroys. The validator
rejects hedges (`should`, `properly`, `robust`, `generally`, `correctly`,
`might`, `make sure`, and their neighbours) because a hedged claim cannot be
falsified, and a claim that cannot be falsified cannot be checked.

The `breaks if:` half must name a state or an input, not restate the claim in
the negative. "breaks if: it is not unique" is a restatement. "breaks if: two
deliveries commit in the same window" is a counterexample.

Ask of each one: **what enforces this today?** A unique index, a type, a guard,
a test, a queue guarantee. "Nothing" is an answer worth writing down as an
adjacent note — it means the invariant is already only a hope.

## Plan — `P1 — the edit — rests on F1, B2`

Each step names the ids it rests on. A step that cites nothing is a step whose
justification lives only in the agent's head, which is where invented behavior
comes from.

## Unknowns — `U1 — question — resolved by: what would settle it`

```markdown
- U1 — whether the reconcile job in B3 reuses the provider event id — resolved by: `rg -n "event_id" src/jobs/reconcile.ts`
```

`resolved by:` can be a command, a file, a person, or a run in staging. Write
`none` as the whole section only when the blast radius has no `UNKNOWN` row and
you have read it twice.

## Hunts — `H1 — hunt — gaps — 2`

Append one row after each round. Fields are the consecutive round number, kind
(`hunt` or `confirmation`), verdict (`gaps`, `complete`, or `widened`), and
absence count. Never rewrite an earlier row. More than three `hunt` rows or
more than one `complete` verdict invalidates the record; confirmations do not
consume the three-hunt budget.

## The rule table

`validate_record.py --rules` prints this list.

| Code | What it means |
|---|---|
| GW001 | a required section is missing |
| GW002 | the sections are out of order |
| GW003 | a section has no content |
| GW004 | a row has no id, or the fields are not separated by an em dash |
| GW005 | two rows share an id |
| GW006 | a fact carries no command in backticks |
| GW007 | a fact carries no evidence after the arrow |
| GW008 | the blast radius names no command that enumerated it |
| GW009 | a blast-radius row carries no verdict |
| GW010 | an UNKNOWN row is not carried into Unknowns |
| GW011 | an invariant names no counterexample |
| GW012 | an invariant is hedged, so nothing can falsify it |
| GW013 | a plan step cites no evidence |
| GW014 | a row refers to an id that does not exist |
| GW015 | template placeholder text was left in |
| GW016 | an unknown names no way to resolve it |
| GW017 | Tree is missing, malformed, or no longer matches the working tree |
| GW018 | a hunt row is malformed or rounds are not consecutive |
| GW019 | the record contains more than three full hunts |
| GW020 | more than one hunt row claims completeness |

What the validator cannot check: whether a command proves its claim, whether
the enumeration was wide enough, whether a SAFE verdict was read or assumed.
That is the hunt, and the hunt is a second agent — see `hunt.md`.
