# Second paths

The blast radius is only as wide as the command that produced it. A grep for a
symbol name finds the callers that spell it. This file lists the ones that do
not, because an unenumerated second path was about a third of the findings this
method was built from.

Work down the list and ask: *could the thing I am changing be reached this
way?* Run the ones that could. Put the command in the record.

## Reached without the name

- **String keys and reflection.** Event names, job names, feature flags,
  dependency-injection tokens, `getattr`, `Class.forName`, `dispatch("...")`.
  Grep the string, not the symbol.
- **Routes and handlers.** A path in a router table, a file-based route, an
  OpenAPI spec, a webhook registered in a provider's dashboard. The last one
  is not in the repository at all — it goes under Unknowns.
- **Schedules and queues.** Cron entries, job definitions, retry policies,
  dead-letter handlers. They call the change at 3am with yesterday's data.
- **Database.** A column read by a view, a trigger, a materialized view, a
  report query, a migration that backfills it, an index that assumes its
  shape. Grep the column name across migrations and SQL, not just the model.
- **Serialized shapes.** Anything persisted or sent: cached JSON, a queue
  payload, an event on a bus, a saved API response, a mobile client that
  shipped last month and still sends the old field.
- **Generated code.** Clients from a schema, ORM models, protobuf stubs,
  snapshots. Regenerating is part of the change, or the plan is incomplete.
- **Configuration.** The behavior may differ per environment. A fact proved on
  a local config is a fact about the local config.
- **Other repositories.** A shared library's consumer, an infrastructure repo,
  a mobile app. If it is not checked out, it is an unknown, not a SAFE row.
- **Tests and doubles.** A mock that encodes the old contract keeps passing
  while production breaks. A fixture that hard-codes a shape is a second copy
  of the truth.
- **Docs that are executed.** README snippets in CI, notebooks, seed scripts.

## Enumeration commands worth pasting

```bash
# every spelling of the symbol, including strings and comments
rg -n --no-heading -S 'refundCharge|"refund_charge"|refund-charge'

# the schema, not just the model layer
rg -n 'refund' migrations/ db/ sql/

# things that run without a caller
rg -n 'cron|schedule|@task|queue|worker' --glob '!node_modules/**' -l

# the shape as it crosses a boundary
rg -n 'charge_id' --glob '*.json' --glob '*.yaml' --glob '*.proto'

# who imports the module at all, when the function is re-exported
rg -n "from .*billing/refund|require\(.*refund" src/

# git remembers callers that were deleted and re-added
git log -S 'refundCharge' --oneline | head
```

## Language-specific misses

- **TypeScript / JavaScript** — barrel files (`index.ts`) re-export under a new
  name; dynamic `import()`; `any` erases the contract at the boundary; optional
  chaining hides a shape change until runtime.
- **Python** — duck typing means no compiler pass; `**kwargs` forwarding;
  monkeypatching in tests; entry points declared in packaging metadata.
- **Dart / Flutter** — generated `*.g.dart`; `build_runner` output; a widget
  reached only from a named route string.
- **Go** — interface satisfaction is implicit, so nothing names the type that
  implements the interface you changed. Grep the method set.
- **SQL-first stacks** — the query that is a string in another language, or a
  view defined in a migration nobody greps.

## When the enumeration cannot be completed

Write the unknown. `U1 — a mobile client may still send the old field —
resolved by: the release dashboard`. An unknown that is written down is a
decision someone can make. An unknown that is omitted is a decision that was
made by accident.
