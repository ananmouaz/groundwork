# groundwork — idempotency key on the refund webhook

Tree: da39a3ee5e6b4b0d3255bfef95601890afd80709

## Task

A repeated `charge.refunded` delivery must return 200 without issuing a second refund.

## Facts

- F1 — no uniqueness constraint exists on refund rows — `rg -n "unique" migrations/0012_refunds.sql` → no output
- F2 — every refund goes through `refundCharge()`, nothing calls the provider directly — `rg -n "stripe.refunds.create" src/` → `src/billing/refund.ts:41` (one hit)
- F3 — the webhook queue retries five times — `rg -n "maxRetries" infra/queue.ts` → `infra/queue.ts:17: maxRetries: 5`

## Blast radius

Enumerated by: `rg -n "refundCharge\(" src/ tests/` → 6 hits

- B1 — src/webhooks/stripe.ts:88 — handles the provider callback — UPDATE — must look up the event id before refunding
- B2 — src/admin/refund-action.ts:23 — an operator refunds by hand — UPDATE — needs its own key, the operator can double-click
- B3 — src/jobs/reconcile.ts:52 — replays yesterday's unmatched charges — UNKNOWN — unclear whether it reuses the provider event id
- B4 — tests/billing/refund.test.ts:14 — asserts one provider call per refund — SAFE — the assertion still holds after the change

## Invariants

- I1 — exactly one provider refund exists per charge and reason pair — breaks if: two deliveries commit in the same transaction window with no unique index
- I2 — a duplicate delivery answers 200 and writes nothing — breaks if: the handler raises on the duplicate, so the provider retries until the queue gives up

## Plan

- P1 — add a unique index on refunds(charge_id, reason) — rests on F1, I1
- P2 — key the handler on the provider event id — rests on F2, B1
- P3 — generate a key in the admin action — rests on B2

## Unknowns

- U1 — whether the reconcile job in B3 reuses the provider event id — resolved by: `rg -n "event_id" src/jobs/reconcile.ts`

## Hunts

- H1 — hunt — complete — 0
