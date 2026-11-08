# Cross-language integer cores

For IEEE-754 binary64 expressions use [floating-point.md](floating-point.md), a separate Z3 backend. The limitations below apply to the Dafny integer translator.

Use agentc v0.7 `translate` for one total, pure integer function with 1–16 integer parameters. Emit Python, JavaScript, or experimental Rust from the same verified Dafny source. Do not use this path for parsers, strings, state, exceptions, loops, floating point, or arbitrary existing Lean source. Division is not yet supported. Keep the calculator's parser gap explicit.

## Prerequisites

Install official Dafny **4.11.0** from https://github.com/dafny-lang/dafny/releases/tag/v4.11.0. Use the platform-matching archive; it bundles the verifier and solver. Put `dafny` on PATH or set `AGENTC_DAFNY` to its absolute executable. Check `dafny --version`. Python 3.10+ is needed for the CLI; generated JavaScript needs Node and `bignumber.js` **9.1.2** (`npm install --ignore-scripts` in the generated directory). Do not bundle a platform-specific compiler in the skill. A missing runtime means not_run, never verified.

## Independent contract and candidate

Copy `translations/clamp` from the prepared tool as a starting example. Create an app-local contract, separate from its candidate:

```json
{"schema_version":1,"name":"clamp","parameters":["x"],"ensures":[["and",[">=","result",0],["<=","result",100]],["implies",["and",[">=","x",0],["<=","x",100]],["==","result","x"]],["implies",["<","x",0],["==","result",0]],["implies",[">","x",100],["==","result",100]]]}
```

Candidate:
```json
{"expression":["if",["<","x",0],0,["if",[">","x",100],100,"x"]]}
```

Integers and booleans are literals. Strings refer to declared parameters; `result` is allowed only in postconditions. Lists encode operators: `+ - * < <= > >= == != and or implies` take two arguments, `not` takes one, and `if` takes condition/then/else. Types are checked. All parameters/results are mathematical integers. No arbitrary Dafny snippets, preconditions, imports, axioms, or bypass flags are accepted. The agent must review the contract against the user's intent; a trivially true postcondition remains a weak specification.

Read and retain the fingerprint BEFORE candidate iteration:
```sh
python3 <tool>/agentc.py translate --contract <contract.json> --describe
python3 <tool>/agentc.py translate --contract <contract.json> --candidate <candidate.json> --expect-contract <fingerprint> --target python --out <fresh-python-dir>
python3 <tool>/agentc.py translate --contract <contract.json> --candidate <candidate.json> --expect-contract <fingerprint> --target javascript --out <fresh-js-dir>
```

The command generates `Core.dfy` with the fixed postconditions, runs Dafny translation with verification enabled, and emits only on success. Exit 0 means emitted, 1 rejected/timeout, 2 malformed/setup. Outputs are atomic and refuse existing directories. Use a fresh output for each revision. Never weaken the contract to make candidates pass.

## Run and integrate

Each output has untouched compiler-generated sources, a decimal-string adapter, input JSON, hashes and `evidence.json`. Python exposes `adapter.run(list_of_decimal_strings)` and JavaScript exposes `require('./adapter.cjs').run(...)`. Return values are decimal strings. Use one core per Python process initially: generated module names are shared (`module_`, `_dafny`, `System_`). Multiple cores require namespacing work and integration tests.

CLI adapters read a JSON array from stdin and print `{"value":"..."}` or `{"error":"..."}`. For example, send `["123"]` to `python3 adapter.py` or `node adapter.cjs` to get `{"value":"100"}` for clamp. Never pass JSON numbers: doing so could lose precision before validation. The adapters reject malformed decimal input. Both adapters limit each input string to 4096 characters; Python configurations with a lower decimal conversion limit need app-specific handling. The proved core itself uses unbounded integers.

The generated function is verified against the formal postconditions. The JSON-to-Dafny renderer, Dafny verifier/solver, compiler, runtime and adapters are trusted components. Do not describe this as verified translation or whole-app verification. Preserve `translation_assurance: source_verified_compiler_trusted`; adapters and integration are tested_only. Emission receipts say `integration_tests: not_run` because compilation is not an app test.

Run independent oracle cases in BOTH generated languages, including boundaries, negative values, values above 2^53, large integers, malformed input and argument ordering. Submit a deliberately wrong candidate and confirm nonzero exit and no emitted directory. Retain actual test results and hashes in app-level evidence; do not rewrite a compiler receipt to imply the CLI ran tests. Keep browser/UI/integration evidence separate. Do not edit generated source; change the IR, reverify, regenerate, and retest.

## Rust target (experimental)

Use the same contract and candidate with `--target rust --out <fresh-rust-dir>`.
The tool uses Dafny 4.11.0 `translate rs --enforce-determinism --include-runtime`.
Keep verification enabled. The generated `core-rust` folder is a Cargo library
and executable; it includes the Dafny runtime, adapters and Cargo.lock.
Install Rust/Cargo (tested with Rust 1.90.0), then run:

```sh
cargo build --locked --manifest-path <fresh-rust-dir>/core-rust/Cargo.toml
cargo run --quiet --locked --manifest-path <fresh-rust-dir>/core-rust/Cargo.toml
```

Send a JSON array of decimal strings on stdin, exactly like the Python/JavaScript
adapters. Output is `{"value":"..."}` or `{"error":"..."}`; invalid input exits 1.
Rust apps can call `agentc_core::run(&[String, ...]) -> Result<String, String>`.
The pure generated function is `core::_module::_default::Run`; use the adapter
at external input boundaries. Do not edit generated `src/core.rs`.

Default integers are arbitrary precision. Never enable Dafny runtime `small-int`
or coerce values through machine integers or floating point; that changes the
contract semantics. Each input decimal string is limited to 4096 ASCII characters.
The Dafny runtime and Cargo dependencies require a populated cache or registry
access on first build. The lockfile is bundled for repeatable dependency versions.
Keep `backend_maturity: experimental` in evidence. Translation verifies Dafny but
does NOT invoke Cargo: `target_build: not_run` is deliberate. Actually build and
test each emitted crate and record results separately before claiming it works.
The Rust backend, adapters and app integration are not formally proved.
