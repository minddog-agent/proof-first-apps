# Integrating a proved model into an app

Separate three claims in the evidence:

1. **Model proof:** Lean checked the named candidate against the pinned formal contract.
2. **Translation assurance:** The target-language implementation is either separately proved, checked by an actual translation validator, or only tested. The `translate` command provides `source_verified_compiler_trusted` assurance for its supported Dafny integer core. An ordinary port has `tested_only` assurance.
3. **Application validation:** Integration/browser tests cover user-visible behavior, persistence, errors, and boundaries. They do not prove framework/network/database correctness.

For Python, distinguish `bool` from `int` when the contract requires integer inputs. For JavaScript/TypeScript, choose bounded exact Number arithmetic or BigInt explicitly; do not silently port unbounded Lean Int operations to Number. Preserve nonnegative integer division, Unicode/ASCII policy, parsing completeness, and error shape. Define serialization separately when BigInt is involved.

Keep a small functional core. Generate two target variants only when they present an actual tradeoff; reject variants that fail the same tests. Do not rank by unmeasured performance.

Run tests independent of the implementation: boundary tables, property-based or seeded cases, and a separate reference implementation. Executing the Lean function as an oracle requires a real Lean runner or compiled program; the verifier CLI itself has no `run` command. A Python reference is not a Lean execution oracle.

Record at least these fields in `.agentc/evidence.json` using actual results:

- contract fingerprint and candidate SHA-256;
- proof report location and exact status;
- target language and final source-file SHA-256 values;
- translation assurance (`tested_only` unless stronger evidence exists);
- test commands, outcomes, and compared cases;
- unproved obligations and any unchecked layers.

Use the app framework and deployment requested by the user. For Sites, follow the Sites workflow; for existing repositories, follow their instructions. This skill does not itself authorize external messages or change deployment visibility.

Use the implemented Dafny translation workflow for supported Python/JavaScript/Rust integer cores. Aeneas and verified emitters remain research options. Existing Lean proofs do not transfer automatically to Dafny. The generated decimal-string adapters and app integration need their own tests. Use decimal strings at the API boundary, Python int and JavaScript BigNumber internally; never coerce large strings to Number.

For Rust, build the emitted Cargo project and test its adapters. Preserve arbitrary-precision DafnyInt and the bundled dependency lockfile; the Rust backend remains experimental.


For binary64 code, use the floating-point backend and import its emitted core.mjs directly. Keep source_verified_renderer_trusted distinct from Dafny source_verified_compiler_trusted. For full-app requests, use references/coverage.md and inventory actual call paths. Model-only sqrt receipts cannot satisfy an executable proof obligation.
