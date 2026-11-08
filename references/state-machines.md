# Native Dafny state machines

Use the bundled `assets/agentc/state_machine.py` companion for self-contained Dafny transitions over sequences/maps when the expression JSON backend is insufficient. This extends the workflow alongside agentc v0.11; it is not an `agentc.py` subcommand and does not prove a runtime or database.

## Establish semantics before implementation

Define the full state, valid-state predicate, commands, identity equality, result codes and exact postconditions before candidate iteration. Pin the specification hash before verification. Require success iff the business conditions hold; preservation alone permits implementations that reject everything.

For reservations, separate the inventory version, request ID, owner identity and hold-generation token. Specify these policies explicitly:

- Check repeated IDs before stale versions. Decide whether changed expected-version fields constitute a conflicting payload once an ID is recorded.
- Reject stale versions without mutation; decide whether stale attempts enter the processed-ID map. The example leaves them retryable.
- Increment the version on every processed new nonstale command, including business rejection, as the example does; or specify a different policy explicitly.
- Reserve only available capacity; confirm/cancel only a current pending hold whose owner and token match. Preserve unrelated inventory. Aggregate conservation alone does not prevent stealing a hold.
- Define the clock source and exact deadline inequality. Expiration at `now >= deadline` must make confirmation invalid; preserve completed sales.
- Prove initial validity and transition preservation, then add retry and competing-command witness methods. When claiming general generation freshness, add a reachable-state token/version invariant and an explicit freshness theorem; a token-equality check alone is not that theorem.

Treat commands as atomic mathematical transitions. For a real service, identify the transaction or compare-and-swap that atomically checks the version, updates inventory and records request identity. Also identify caller authentication and authoritative time. Without implementation evidence, mark these as external obligations. Do not describe a single-tab ordering demonstration as a production concurrent service.

## Verify and emit

Prepare a project-local tool copy using `scripts/prepare_workspace.py`. For updates use a fresh tool directory if existing files differ. Work on project copies, not installed assets.

The companion accepts a deliberately narrow source layout: single-line datatype/function/predicate declarations, and method/lemma headers followed by a line beginning with `{`. Compute the pin with its `specification(raw)` helper. Store `specification_sha256` and human-readable requirements in contract JSON. Retain previous pins and reasons when requirements change. Do not re-pin to silence a verifier failure.

```sh
AGENTC_DAFNY=/path/to/dafny-4.11.0/dafny python3 .agentc/tool/state_machine.py \
  --source proofs/Inventory.dfy --contract proofs/contract.json \
  --adapter proofs/adapter.mjs --out /tmp/fresh-proof
```

Emission verifies first, then preserves original compiler output and creates an ESM artifact with an appended boundary adapter. The driver rejects attributes, includes, assumptions, externs and wildcard decreases. Treat it as a trusted authoring helper, not a security sandbox for arbitrary submitted Dafny. Its text-based specification extractor is not a general Dafny parser; use the documented format and manually review the extracted specification.

Import the generated `core.mjs` in production. Keep adapters narrow: reject invalid shapes/ranges, enforce proof preconditions, preserve exact numeric semantics, encapsulate mutable state and return detached snapshots. Label adapters and orchestration tested-only. Bound Number conversions with explicit range arguments or use decimal strings/BigInt. Pin bignumber.js to the tested version.

## Runnable reservation example

The prepared tool includes `examples/reservations/` with source, pinned contract, adapter, independent reference tests and negative checks. From that example directory:

```sh
# Install package.json dependencies in the project copy using the environment's package workflow.
AGENTC_DAFNY=/path/to/dafny-4.11.0/dafny python3 ../../state_machine.py \
  --source proofs/Inventory.dfy --contract proofs/contract.json \
  --adapter proofs/adapter.mjs --out lib/verified
node --test tests/*.test.mjs
AGENTC_DAFNY=/path/to/dafny-4.11.0/dafny python3 scripts/test-negative.py
```

Use a fresh output destination; never overwrite modified generated code. The example has six proof-bearing routines (`Partition`, `Initial`, `Expire`, `Step`, `Retry`, `CompetingBuyers` with additional function verification obligations as reported by Dafny); report the actual method list and verifier result rather than treating its check count as a theorem count. `Retry` and `CompetingBuyers` expose their guarantees as postconditions, so the contract pin preserves them. Do not rely solely on removable body assertions for a required claim.

Exercise both commit orders, stale refresh, wrong owner, old hold token, deadline-minus-one and deadline equality, sold-seat preservation, duplicate/conflicting IDs, and invalid adapters. Compare generated execution with an independent reference over mixed histories. Mutate availability, ownership, token, expiry, version and duplicate handling under the same specification; require verifier rejection with no emitted executable. Also test specification-pin changes and proof-bypass rejection.

Bind exact source/specification/adapter/generated-code hashes and actual proof/test outcomes in evidence. Record remaining obligations: specification adequacy, solver/compiler/runtime trust, adapter/replay, UI/storage, database atomicity, authentication, authoritative clock and resource bounds. State machine proofs cover safety under their preconditions; they do not automatically establish fairness, liveness or crash recovery.

## Lease generation example

Use `examples/leases/` to exercise a second domain: one equipment locker with exact BigInt holder IDs, generation tokens and explicit monotonic time. It proves successful acquire iff empty, exact matching release, strictly fresh generation tokens, expired-lease release, and an exported `LaterLeaseRejectsOldToken` theorem. Unlike the reservation example, it has no request-ID store or expected-version protocol. Do not transfer those guarantees between examples.

From its copied directory, use the same companion command with `--source proofs/Lease.dfy`, its local contract/adapter, and fresh `--out lib/verified`. Run `node --test tests/*.test.mjs` and `python3 tests/negative.py` with `AGENTC_DAFNY` configured. Tests exercise 2,000 reference operations, backwards time, equality expiry, stale releases and values beyond 2^100.
