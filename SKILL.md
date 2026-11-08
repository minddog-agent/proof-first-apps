---
name: proof-first-apps
description: Build or modify apps using explicit behavioral contracts and the bundled agentc Lean verifier, Dafny integer backend, and experimental IEEE-754/Z3 backend. Use by default whenever building a new app or implementing app behavior for this user, including routine app-building requests without an explicit proof-first mention. Also use when the user invokes Proof-First Apps, tests the agent compiler prototype, or requests formally checked core logic. Honor explicit requests to skip this workflow; do not trigger for unrelated tasks or purely cosmetic edits. Supports contract creation, candidate repair, binary64 arithmetic, explicit WebAssembly square-root execution, coverage auditing, verified integer phase schedules, versioned reservation state machines, and separately tested app integration. It does not automatically verify whole applications, astronomical models, or translate Lean into other languages.
---

# Proof-First Apps

Deliver a usable app or requested code change together with a precise account of what is proved, tested, and unresolved. Use the bundled agentc v0.11.0-experimental as the contract checker. Keep the calling agent responsible for interpretation, code generation, proof attempts, and repair.

Apply the user’s standing preference for proof-first app building without asking them to opt in again. Scale the verification effort to the change: select meaningful core behavior, preserve normal delivery workflows, and report unsupported or unchecked behavior honestly.

## 0. Set the proof boundary before building

- For full-app requests, read [app-wide coverage](references/coverage.md), inventory every promised behavior and dependency, and fix the contracts before implementation. Distinguish proved executable code, proved models, tested integration, trusted inputs, and unproved dependencies.
- For ordinary proof-first builds, finish verification of the selected core before integrating it. UI scaffolding can proceed independently, but do not publish a partial proof as completion of a fully verified request.
- Use generated verified code on the app's actual execution path. A detached integer model does not verify floating-point production code. Never replace verified output with an unproved handwritten copy without explicitly reporting the downgrade.
- Choose the supported backend: Lean for mathematical claims; Dafny translation for integer expressions; [IEEE-754/Z3](references/floating-point.md) for binary64 arithmetic. Correctly rounded `sqrt` can be emitted with explicit `--sqrt-runtime wasm`, trusting a conforming WebAssembly engine; without that option it is model-only. Trigonometry and ephemerides remain unsupported. Do not promise future support as though it already exists.
- Re-run exact proof inputs before release, audit hashes and integration, and report all remaining obligations. A coverage report is an inventory check, not a proof certificate.

For multi-phase estimates, mission planners, or elapsed-time schedules, read [phase schedules](references/phase-schedules.md). Use the `timeline` backend for compiled Dafny sequence sums and ordered boundaries; keep empirical inputs and physical feasibility separate from accounting proofs.

For inventory holds, expiring leases, optimistic version checks, or native Dafny sequence/map transitions, read [state machines](references/state-machines.md). Use the bundled `state_machine.py` companion when the expression backend cannot express the transition. Do not claim database concurrency or authentication from an atomic state-transition proof.

## 1. Scope the app and choose the core

- Follow the user's chosen framework, repository, language, and deployment constraints. For a website, use the available Sites workflow when applicable; use this skill for core logic, not hosting. A local code-only request stays local.
- Choose one or two small pure functions or state transitions to verify first: limits, input validation, arithmetic, sorting, or eligibility. Avoid trying to formalize the UI, entire database, network, or framework in a first experiment.
- Translate intent into concrete input/output examples, invariants, errors, and boundaries. State material assumptions early. Ask only when missing information would materially change behavior and cannot reasonably be inferred; continue independent UI/setup work.
- Specify target-language semantics: integer bounds or arbitrary precision, rounding, character set, invalid-input behavior, and side effects. Resolve apparent contradictions such as “alphanumeric only” versus ASCII arithmetic operators.

## 2. Prepare the local checker

Resolve this skill's current directory; do not rely on an old scratch path or Library ZIP. Run:

```sh
python3 <skill-dir>/scripts/prepare_workspace.py --project <project-dir>
python3 <project-dir>/.agentc/tool/agentc.py list
```

The helper bundles the verifier, integer examples, the floating clamp, and backend/coverage tests. For upgrades, use `--tool-dir .agentc/tool-v0.11` to prepare a fresh project-local copy; do not overwrite modified tools. It excludes Python caches. It preserves modified files and refuses conflicting replacements. Never edit the installed skill while building an app; work on the copied tool, app-local contracts, and app-local candidates.

Use Python 3.10+ for all backends and Lean 4.19.0 only for Lean proofs. Check the runtime before invoking proofs. If Lean is missing, follow the environment's dependency/network workflow to install the pinned official toolchain when possible. If blocked, continue useful app implementation and tests, but report proof checking as `not_run`; never invent success. Read [references/runtime.md](references/runtime.md) only for setup failures.

For binary64 JavaScript arithmetic, read [floating-point workflow](references/floating-point.md). It uses Z3 and does not require Lean or Dafny; check-only square-root bundles must never be presented as executable proofs. Executable sqrt requires the explicit WebAssembly runtime option and actual browser integration testing.

For Python, JavaScript, or experimental Rust generation of a pure integer core, choose the translation workflow in [references/cross-language.md](references/cross-language.md). It uses a restricted JSON expression language and Dafny 4.11.0, not Lean. Follow steps 3–4 below for Lean candidates; do not mix the contract formats.

## 3. Fix a contract before searching for implementations

For Lean candidates, read [references/contract-workflow.md](references/contract-workflow.md). Create an app-local bundle containing `ContractSpec.lean` and `contract.json`, plus a separate candidate file importing `ContractSpec`.

- Define requirements independently of the implementation. Ensure they rule out trivial wrong solutions such as returning an error for every input.
- Declare each export, exact theorem type, and required obligation in the manifest. Include parsing/serialization obligations when the app relies on them. Do not omit a known gap merely to obtain a passing status.
- Compute the specification hash, run `describe`, and retain the returned fingerprint before candidate iteration. Pass `--expect-contract` on every later check and emission.
- Revise a contract when user requirements change or the specification is demonstrably wrong. Explain the semantic change and retain the old fingerprint. Do not weaken requirements simply because a proof is difficult. Routine contract preparation within the user's requested scope does not need an extra approval step.

## 4. Generate, check, and repair candidates

```sh
python3 <tool> verify --contract <bundle> --candidate <candidate.lean> \
  --expect-contract <fingerprint> --out <report.json>
```

Read the actual report and exit code. Repair implementations/proofs against the fixed contract. Keep diagnostics and candidate hashes. Start with a focused attempt; after several unproductive attempts, explain the specific unresolved obligation instead of hiding it or consuming unbounded effort. Continue independent app work.

- `proved` means the exact declared claim checked under permitted axioms.
- `missing` or `unproved` means evidence is absent or contains `sorry`.
- `rejected` means the submitted proof/assumptions failed; it is not necessarily proof of a program bug.
- `unknown`/`not_checked` means timeout or an earlier blocked stage.
- Overall `verified` applies only to the specified contract and candidate, not the whole app.

Compare multiple variants only if there is a meaningful choice. Never treat verification time or source size as a runtime-speed measurement. Use actual benchmarks when performance matters.

Use `emit` only after all required obligations pass. It rechecks and writes a Lean source bundle; it does not generate Python, TypeScript, or other targets.

## 5. Integrate code in the requested app language

Read [references/app-integration.md](references/app-integration.md) before producing non-Lean app code.

For supported integer cores, use `translate` as documented in [references/cross-language.md](references/cross-language.md). It verifies generated Dafny before emitting Python, JavaScript, or Rust. Label this `source_verified_compiler_trusted`: the compiler and renderer are trusted, not proved correct. There is no general Lean-to-target translator. For unsupported logic or languages, generate ordinary app code and label it `tested_only`; never silently change the requested semantics or claim an unsupported target works.

- Keep the logic represented by the contract in a small module with a stable interface.
- Preserve the specified numeric/string/error semantics. Explicitly handle any representation mismatch.
- Test target code against an independent oracle or executable Lean model where practical. Include boundaries, invalid inputs, and a deliberately wrong variant to show the test can fail.
- Test actual integration and UI behavior using the app's appropriate tools.
- Bind the candidate hash, contract fingerprint, target file hashes, proof status, test commands/results, and remaining gaps in a project-local `.agentc/evidence.json`.
- Mark the Lean model as proved only if it passes. Mark an ordinary target-language port as `tested_only`, not formally verified. Never treat differential tests as a proof of translation correctness.

Deliver a tested app prototype even if explicitly recorded proof gaps remain, unless the user requested a fully verified deliverable. For that requirement, incomplete work is a checkpoint, not a completed release; preserve it and report the exact blockers. Do not label it a verified release or bypass agentc's emission gate. When full verification is required and blocked, report the exact blocker while retaining completed independent work.

## 6. Deliver the app and concise evidence

Preserve normal app/file delivery and publication rules. Save user-facing artifacts through the appropriate app or file workflow; never put build products back into this skill.

Lead with the usable result. State which core rules were proved, what target code/integration was tested, and the concrete remaining gaps. Keep proof and tooling details out of the app UI unless relevant to users. Do not advertise the whole app as “formally verified.”

For a first experiment, prefer a calculator or score-limiting app. The bundled calculator is intentionally incomplete: its parser soundness and completeness proofs are missing. Keep those obligations required; the clamp example is the complete minimal reference.
