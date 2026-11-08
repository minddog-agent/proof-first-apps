# Binary64 proof workflow

Use bundled `agentc translate-float` for IEEE-754 binary64 expressions, with Z3 and round-to-nearest/ties-to-even (RNE). Do not route this through Dafny 4.11.0: its installed release does not recognize fp64. Keep the Dafny integer path unchanged.

## Runtime and operations

Locate `z3` on PATH or set `AGENTC_Z3` to an official installed Z3 executable. Dafny's official release archive bundles a compatible solver under `dafny/z3/bin/`; confirm its version. Tests use Z3 4.12.1. Never infer a network block from an allowlist alone: attempt the normal permitted download and report the observed outcome. Follow the environment installation rules.

Numeric operations: `+ - * / neg abs floor if`. Predicates: `< <= > >= == same finite nan infinite`. Boolean operations: `and or not implies`. Numeric literals are exact bit patterns such as `["bits","3ff0000000000000"]` (1.0), not decimal JSON numbers. `==` is IEEE equality (signed zeros equal, NaN unequal); `same` preserves signed zero and treats NaNs as one semantic value, like Object.is. NaN payloads and signaling behavior are excluded. Do not reassociate or fuse arithmetic.

`floor` maps to SMT fp.roundToIntegral RTN and JavaScript Math.floor. `sqrt` defaults to **model-only --check-only**. Executable sqrt requires explicit `--sqrt-runtime wasm`: the emitter includes a fixed, lazily instantiated WebAssembly module whose only function is `(param f64) (result f64) local.get 0; f64.sqrt`. WebAssembly specifies RNE for this operation. Treat the module-byte renderer and conforming WebAssembly runtime as trusted; test the actual browser. Never fall back to Math.sqrt if WebAssembly is unavailable or blocked. NaN payloads remain excluded. Source: https://webassembly.github.io/spec/core/exec/numerics.html

Use the runtime option for sqrt in preconditions too; it enables the same helper for runtime precondition checks. --check-only never emits executable code even if the runtime option is provided.

Unsupported: trigonometry, general transcendental functions, binary32, other rounding modes, mutable state, loops, calendar parsing, external calls, and real-valued error bounds. Reject these explicitly. Do not replace them with uninterpreted functions and call their implementation proved.

## Contract and emission

Copy `floating/clamp` from the prepared tool as an example. Contracts contain exactly `schema_version: 1`, `name`, `format: "binary64"`, `rounding: "RNE"`, `parameters`, `requires`, and `ensures`. Preconditions must be satisfiable. Candidates contain an `expression`. Review postconditions independently; returning a constant must not satisfy a calculation contract accidentally.

```sh
python3 <tool>/agentc.py translate-float --contract <contract.json> --describe
python3 <tool>/agentc.py translate-float --contract <contract.json> \
  --candidate <candidate.json> --expect-contract <returned-fingerprint> \
  --out <fresh-directory>
```

For an explicitly requested mathematical model, add `--check-only`. For executable square root, add `--sqrt-runtime wasm` instead. Only in `--check-only` mode, `translation_assurance` is `model_only`, and `core.mjs` is absent. Executable WASM mode reports `source_verified_renderer_trusted`. Never integrate a model-only receipt as executable proof.

The solver first checks for a nonempty input domain, then searches for a violation. Only unsat for the violation query permits a verified receipt. Counterexample, timeout, unknown, solver error and contradictory preconditions block executable emission. Inspect process exit, receipt and files. Existing output directories are never overwritten.

Executable bundles contain `core.mjs`, exact contract/candidate, SMT query and evidence hashes. Import `run(...numbers)` directly; it checks argument count/types and runtime preconditions. Ordinary JSON does not preserve NaN/infinity/negative zero: use direct Number calls or separately test an explicit bit encoding.

## Integration and limits

Use the emitted module in the actual app before claiming executable proof coverage. Recheck the exact contract and candidate immediately before integration. Bind its source hash and a test that exercises the app's real call path. A tested handwritten copy is not the verified artifact.

Label this backend `source_verified_renderer_trusted`: Z3, the IR renderers, adapters and JavaScript runtime are trusted. This is an SMT solver check, not a Lean proof certificate or whole-app verification. Generated receipts intentionally say integration_tests: not_run; store actual integration results separately.

Test boundaries, signed zero, NaN, infinities, subnormals, rounding ties, overflow, invalid adapters and deliberately wrong candidates. Run `AGENTC_Z3=<solver> python3 <tool>/tests/test_floating.py` to validate the bundled backend. Tests include emitted JavaScript execution. `sqrt` model tests assert that no executable is produced; explicit WebAssembly tests execute the emitted module on normal, negative, signed-zero, infinity, and subnormal inputs. Calendar examples under floating/calendar specify date validity and noon-UTC epoch milliseconds for 1900–2100. Their proofs establish agreement with the written binary64 formulas; string parsing, date-object construction and physical time-scale accuracy remain separate. Check every supported calendar date against an independent integer calendar oracle before integration.
