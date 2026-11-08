---
name: proof-first-apps
description: Build apps with behavioral contracts, checked core logic, and tested integration. Use by default for this user's new apps and behavior changes, or when explicitly requested. Skip unrelated tasks, cosmetic edits, and requests to skip proofs. Includes Lean, Dafny, and experimental IEEE-754/Z3 tools; verification covers declared contracts, not whole apps automatically.
---

# Proof-First Apps

Build the requested app. Define its rules before implementing them, check the selected core, and report what remains unproved. Use the bundled agentc v0.11.0-experimental. The calling agent writes contracts, implementations, and proofs, and handles repairs.

## Scope and contracts

Follow the requested language, framework, repository, and deployment constraints. Use Sites for website delivery when applicable; this skill handles verification, not hosting.

For a full app, read [coverage](references/coverage.md) and inventory promised behavior and dependencies. For an initial experiment, start with one or two pure functions or state transitions. Do not substitute that narrow scope for a request to verify the whole app.

Specify examples, invariants, errors, numeric bounds, rounding, character sets, and side effects. Resolve conflicting requirements. Ask only about missing information that changes behavior and cannot reasonably be inferred; continue independent work.

Fix contracts before implementation. Define requirements independently of candidate code, including successful behavior so an implementation that rejects every input cannot pass. Include parsing and serialization obligations where needed. Change a contract only for changed requirements or a demonstrated specification error; record the reason and retain its previous fingerprint. A difficult proof is not a reason to weaken the contract.

## Choose a backend

Read the reference for the selected backend; keep its contract format and assurance limits.

| Core behavior | Backend and reference | Limit |
| --- | --- | --- |
| Mathematical claims | Lean: [contract workflow](references/contract-workflow.md) | `emit` produces Lean source, not another language. |
| Integer expressions | Dafny: [cross-language](references/cross-language.md) | Restricted JSON expressions; Python, JavaScript, and experimental Rust targets. |
| Binary64 arithmetic | Z3: [floating point](references/floating-point.md) | JavaScript output; executable correctly rounded `sqrt` requires `--sqrt-runtime wasm` and a conforming WebAssembly engine. Otherwise sqrt is model-only. |
| Phase durations and boundaries | Dafny `timeline`: [phase schedules](references/phase-schedules.md) | Proves accounting, not empirical inputs or physical feasibility. |
| Holds, leases, version checks, sequence/map transitions | `state_machine.py`: [state machines](references/state-machines.md) | Atomic transition proofs do not establish database concurrency or authentication. |

Trigonometry, ephemerides, and general Lean-to-target translation are unsupported. For unsupported behavior, use ordinary code and label it `tested_only` after testing. Preserve the requested semantics.

## Prepare the checker

Use this installed skill's current directory, not an old archive or scratch copy:

```sh
python3 <skill-dir>/scripts/prepare_workspace.py --project <project-dir>
python3 <project-dir>/.agentc/tool/agentc.py list
```

Work in the project-local copy; do not modify the installed skill during app builds. For upgrades, use `--tool-dir .agentc/tool-v0.11` to avoid overwriting modified tools. The helper preserves existing modifications and excludes Python caches.

Require Python 3.10+. Lean proofs use Lean 4.19.0; integer translation uses Dafny 4.11.0; floating-point checks use Z3. Check dependencies before running proofs. If setup fails, read [runtime](references/runtime.md) and follow the environment's installation rules. If blocked, record `not_run` and continue implementation and tests where useful.

## Check and repair

For Lean, create `ContractSpec.lean`, `contract.json`, and a separate candidate importing the specification. Declare exports, exact theorem types, and required obligations. Compute the specification hash, run `describe`, and retain its fingerprint before iterating. Pass `--expect-contract` to subsequent checks and emission:

```sh
python3 <tool> verify --contract <bundle> --candidate <candidate.lean> \
  --expect-contract <fingerprint> --out <report.json>
```

Read the report and exit code. Repair against the fixed contract; retain diagnostics and candidate hashes. After several unproductive attempts, identify the unresolved obligation and continue independent work. Emit only when all required obligations pass; do not bypass the gate.

| Status | Meaning |
| --- | --- |
| `proved` | The declared claim checked under permitted axioms. |
| `missing` / `unproved` | Evidence is absent or contains `sorry`. |
| `rejected` | The submitted proof or assumptions failed; this alone does not establish a program bug. |
| `unknown` / `not_checked` | A timeout or earlier blocker prevented a result. |
| `verified` | The specified contract and candidate passed, not necessarily the whole app. |

Compare variants when there is a meaningful choice. Measure runtime performance with benchmarks, not proof duration or source size. The bundled clamp is the complete minimal example; the calculator intentionally lacks parser soundness and completeness proofs. Keep those obligations required.

## Integrate and test

Verify the selected core before integrating it; independent UI scaffolding can proceed meanwhile. Read [app integration](references/app-integration.md) before producing non-Lean app code.

- Put checked logic on the app's actual execution path behind a small, stable interface. A detached model does not verify production code. Report any replacement with an unproved handwritten implementation as a downgrade.
- Preserve numeric, string, and error semantics across representations. Dafny `translate` checks source before emission; label its output `source_verified_compiler_trusted`. The compiler and renderer remain trusted. Handwritten ports are `tested_only` after testing.
- Test target code against an independent oracle or executable model where practical. Cover boundaries and invalid inputs, and include a deliberately wrong variant to confirm that tests detect it. Differential testing is not a proof of translation correctness.
- Test the actual integration and UI. Executable WebAssembly sqrt also requires browser integration tests.
- Before release, rerun the exact proof inputs and audit hashes and integration. Record contract fingerprints, candidate and target hashes, proof status, test commands/results, and remaining gaps in `.agentc/evidence.json`.

## Deliver

Deliver through the normal app/file workflow. Keep build products out of the installed skill and implementation details out of the app UI unless they help its users.

State the usable result, the rules proved, the integration tested, and the remaining gaps. Distinguish proved executable code, proved models, tested integration, trusted inputs, and unproved dependencies. A coverage inventory is not a proof certificate.

A tested prototype may include disclosed proof gaps. If the user requires a fully verified deliverable, incomplete verification is a checkpoint, not completion: preserve the work and report the exact blocker.
