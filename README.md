# groundwork

**Write down what you believe before you write the code, and have a second
agent hunt it for what is missing.**

Most bugs an AI writes are not logic errors. They are claims about the repo
that were never checked, and second paths that were never enumerated.

groundwork makes both explicit before any code exists. Every fact carries the
command that proved it. Every invariant is written as a falsifiable claim. A
second agent then reads the record and hunts only for what is absent.

Reviewing a record costs one agent call. Finding the same defect after the
push costs a review cycle, a red gate and a fix commit.

## The two failures

Measured on one repo's 51 review-bot findings: about **a fifth were unverified
claims about the repo**, and about **a third were an unenumerated second path**.

Neither is visible in the code the agent wrote, which is why both survive a
review of that code — a reviewer reads what is there. Both are visible in a
record, because a record is a finite list, and a list can be checked for
missing rows.

- *Unverified claim* — "the handler already validates this". It did, in the
  file the agent read forty minutes ago, on a path that is not this one.
- *Second path* — the change is right for the caller in the diff and wrong for
  the cron job, the admin action, the migration, or the test double that also
  calls it.

## What a record looks like

Six sections. Ids on every row. Nothing that cannot be re-run or falsified.

```markdown
# groundwork — idempotency key on the refund webhook

## Task
A repeated `charge.refunded` delivery must return 200 without issuing a second refund.

## Facts
- F1 — no uniqueness constraint exists on refund rows — `rg -n "unique" migrations/0012_refunds.sql` → no output
- F2 — every refund goes through `refundCharge()` — `rg -n "stripe.refunds.create" src/` → `src/billing/refund.ts:41` (one hit)

## Blast radius
Enumerated by: `rg -n "refundCharge\(" src/ tests/` → 6 hits

- B1 — src/webhooks/stripe.ts:88 — handles the provider callback — UPDATE — must look up the event id first
- B3 — src/jobs/reconcile.ts:52 — replays unmatched charges — UNKNOWN — unclear whether it reuses the event id
- B4 — tests/billing/refund.test.ts:14 — asserts one provider call — SAFE — the assertion still holds

## Invariants
- I1 — exactly one provider refund exists per charge and reason pair — breaks if: two deliveries commit in the same window with no unique index

## Plan
- P1 — add a unique index on refunds(charge_id, reason) — rests on F1, I1
- P2 — key the handler on the provider event id — rests on F2, B1

## Unknowns
- U1 — whether the reconcile job in B3 reuses the provider event id — resolved by: `rg -n "event_id" src/jobs/reconcile.ts`
```

Four rules carry the method:

1. **No fact without a command.** If you cannot name what proves it and what
   that printed, it is a belief. It goes under Unknowns.
2. **No blast radius without the command that produced it.** A list of what
   came to mind is not an enumeration.
3. **No invariant that cannot be false.** "The code stays clean" is a mood.
   One counterexample must be able to kill it.
4. **No plan step that cites nothing.** Steps that cite nothing are where the
   invented behavior lives.

`no output` is evidence, and it is often the load-bearing row: *nothing*
validates this, *nothing* else calls it, *no* index exists.

## The hunt

A fresh agent — one with no memory of writing the record — reads it against
the repository and reports **only what is absent**. Six classes, and nothing
outside them:

| | |
|---|---|
| **1. Unverified claim** | the fact's command does not prove it, or proves it in another file, branch, overload or environment |
| **2. Second path** | something reads or writes the changed thing and is not in the blast radius |
| **3. Verdict without evidence** | a SAFE row whose reason is an assertion rather than a read |
| **4. Invariant already false** | find the row, request or state where it does not hold today |
| **5. Invariant nothing enforces** | no index, type, guard or test makes it true, so the plan can only hope |
| **6. Unnamed unknown** | the record treats as settled what the repo does not decide: config, ordering, a race, another service |

Out of scope, permanently: the design, the naming, the layout, whether the
plan is elegant, whether another approach would be better, and anything that
starts with "consider". Those are opinions about a plan. This is a check for
holes in a record.

**Zero absences is a valid result**, and on a small change it is the common
one. A hunter that pads its report trains you to stop reading it.

## The validator

`validate_record.py` checks the parts a machine can check — sixteen rules, no
model, no network:

```
$ python3 skills/groundwork/scripts/validate_record.py .groundwork/refund-idempotency.md
.groundwork/refund-idempotency.md:14: GW006 F3 — no command in backticks — a fact nobody can re-run is a belief
.groundwork/refund-idempotency.md:22: GW009 B2 — no verdict — every row needs one of: SAFE, UPDATE, UNKNOWN
.groundwork/refund-idempotency.md:31: GW012 I1 — hedged on 'should' — an invariant nothing can falsify is not an invariant

3 violation(s). `validate_record.py --rules` explains the codes.
```

It cannot tell whether any of it is *true*. That is the hunt's job. What it
buys is that the hunter spends its attention on what is missing instead of on
formatting — and that a half-filled template cannot pass as a record.

`--json` for tooling, `--quiet` for exit code only, `--rules` for the table.

## The hook

`hooks/require_record.py` runs before Edit and Write and checks the record
first. It is deliberately timid, because the fastest way to lose a guard is to
make it annoying:

- **Inert until a project opts in.** No `.groundwork/` directory, no guard.
- **Never guards** tests, markdown, dotfiles, or the record itself.
- **Warns by default.** The edit proceeds and the agent is told what the
  record is missing. `GROUNDWORK_MODE=block` denies instead; `off` disables it.
- **Fails open.** Missing validator, unreadable payload, bad JSON — the edit
  proceeds. A broken guard must not become a broken editor.

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Edit|Write|MultiEdit",
  "hooks": [ { "type": "command", "command": "/path/to/groundwork/hooks/require_record.py" } ] } ] } }
```

Installed as a plugin, that wiring comes with it.

## Install

One command, any agent — installs `skills/groundwork/` into whatever agent
skill directories it finds:

```bash
npx skills add ananmouaz/groundwork                   # this project
npx skills add ananmouaz/groundwork -g                # every project on the machine
npx skills add ananmouaz/groundwork -a claude-code    # one agent only
```

| Agent | How to wire it |
|---|---|
| Claude Code | `/plugin marketplace add ananmouaz/groundwork`, then `/plugin install groundwork@groundwork`. Gets you `/groundwork`, `/groundwork-hunt`, and the hook. |
| Codex | Copy `dist/groundwork.flat.md` to `.agents/groundwork.prompt.md`, append `adapters/AGENTS.md` to the repo's `AGENTS.md`. |
| Cursor | `dist/groundwork.flat.md` → `.cursor/rules/groundwork.mdc`, set to agent-requested. |
| Gemini CLI | Append the `AGENTS.md` pointer to `GEMINI.md`, same flat file. |
| Raw API | Send `dist/groundwork.flat.md` as the system prompt. Needs file-read and shell tools. |

Then opt a project in:

```bash
mkdir .groundwork
```

## Use it

```
/groundwork add idempotency to the refund webhook
/groundwork-hunt                       # fresh agent, same record
```

Or just ask: it triggers on "before you code", "what could this break",
"invariants", and "write the groundwork for this".

## What's in the repo

| Path | What it is |
|---|---|
| `skills/groundwork/` | The method, in Agent Skills format — `SKILL.md` plus references loaded on demand |
| `skills/groundwork/references/` | The record spec, the hunt protocol, and the second-path enumeration list |
| `skills/groundwork/scripts/validate_record.py` | The validator — sixteen mechanical rules |
| `hooks/` | The PreToolUse hook and its plugin wiring |
| `commands/` | `/groundwork` and `/groundwork-hunt` |
| `templates/RECORD.template.md` | The starting record. Fails validation until filled in, on purpose |
| `dist/groundwork.flat.md` | Same method, one file, for agents with no skill loader |
| `tests/` | Both suites: every validator rule, and the hook's process contract |

## Tests

```bash
bash scripts/test.sh          # both suites, the fixture, and the template check
```

Python 3 standard library only. The validator suite breaks exactly one thing
per test, so a failure names the rule that stopped working. The hook suite
runs the hook as a real subprocess with a real payload on stdin, because the
process contract is what Claude Code actually depends on.

Rebuild the flat file after editing the skill:

```bash
bash scripts/build_portable.sh
```

## Does it work?

Track one number on the next ten non-trivial changes: **how many of the hunt's
absences turned out to be real rows the record needed.** If it is low, the
hunter is padding — tighten the six classes and make it produce a command for
every finding. If the code review after the change keeps finding second paths
the record missed, the enumeration is too narrow, not the hunt: widen the greps
in `references/second-paths.md` before touching anything else.

And read the diff between the first and last version of a record. That diff is
a list of what you believed wrongly, which is the most useful thing this
produces.

## License

MIT — see [LICENSE](LICENSE).
