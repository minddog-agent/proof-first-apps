# App-wide proof coverage

Start here when the user requests full coverage or the app combines numeric logic, third-party models, parsing and UI. A small successful proof is not a substitute for a full inventory.

## Required inventory before implementation

List every promised behavior and every dependency between input and displayed output. For the Earth–Mars app include: date validation, noon-UTC conversion, time scale, planetary positions, 3-D subtraction and norm, square root, AU/km/miles conversions, light time, rounding/formatting, date navigation, trend samples, projection, and displayed state. Add runtime and data-source assumptions explicitly. Review actual imports and call sites against the inventory.

Classify each component as proved, model_only, tested_only, trusted, unproved, or not_run. Distinguish numerical correctness against a specified ephemeris from empirical accuracy of that ephemeris. Observational spot checks are tests, not a proof of astronomical accuracy. Treat compiler/runtime correctness as explicit assumptions; never hide a trusted component under proved.

## Coverage gate

Create an app-local manifest with exactly these fields:

```json
{
  "schema_version": 1,
  "scope": "Precisely stated app behavior and assumptions",
  "requirements": ["distance", "date", "display"],
  "components": [{
    "id": "distance_core",
    "requirements": ["distance"],
    "depends_on": [],
    "status": "model_only",
    "sources": {"lib/core.mjs": "<sha256 of actual source>"},
    "receipt": null,
    "integrated": false
  }]
}
```

Use `receipt` as a relative path for a proved component; null for absent evidence. Every component needs actual source hashes. Resolve dependencies to existing component IDs. No dependency cycles are supported by this initial inventory checker; model a mutually recursive subsystem as one component.

```sh
python3 <tool>/agentc.py coverage --project <project> \
  --manifest <coverage.json> --out <report.json>
```

The checker finds unmapped requirements, stale/missing source files, unintegrated models and unsupported receipt types. For the floating backend it checks exact executable source binding plus saved contract, candidate and SMT hashes. Integer/Lean receipts currently require manual audit and produce a gap, not a false pass. It rejects path escapes and malformed dependency graphs.

Exit 0 means only **declared_coverage_complete**. It is NOT full_app_verified, and the output always makes that distinction. The inventory can omit behavior, receipts are unsigned, and static hashes do not prove actual runtime calls. Re-run verifiers on exact inputs, inspect the call graph, and test the real integration. Do not use this checker as a security attestation or standalone proof validator.

## Closing the Mars-app gaps

Use the floating backend for supported arithmetic and unit-conversion contracts. For square root use the explicit WebAssembly emission path and test browser integration. Keep its runtime/renderer trust assumptions visible; do not substitute Math.sqrt. Astronomical trigonometry and ephemeris evaluation require a separate verified numerical library and explicit error analysis; the bundle does not provide those. Calendar and UI logic require their own specifications and implementations, not extra claims attached to the distance formula.

When full verification is mandatory, do not publish an incomplete rebuild as fulfilling it. Preserve verified work and give concrete unresolved obligations. Ask about changing scope only when it is a real user decision; never silently weaken requirements or claim full coverage after labeling dependencies trusted.


## Reporting a coverage percentage

Never report a single near-100% percentage for an app whose astronomy dependency, UI or runtime is outside the proof boundary. Report exact named obligations and counts by status, with the denominator fixed before implementation. An arithmetic kernel having every operation specified does not make the app fully proved. Exhaustive checks over a finite supported date range are strong tests, not a general theorem about arbitrary strings or UI events. Keep the coverage inventory separate from test coverage.

For the Mars app, carry the six verified executable contracts (date validity, noon epoch milliseconds, 3-D distance in AU, AU to km, km to miles, and light seconds) on the actual call path. Independently test date range and Gregorian leap rules, known astronomical reference dates, and every supported day. Continue reporting ephemeris, projections, date-object/formatting adapters, chart sampling, UI state and renderer/runtime assumptions. Do not mark these six contracts as proof of the empirical model or real-valued error bounds; they specify exact binary64 expression semantics.

### Composition obligations
A verified function's output must establish the next function's preconditions. Finite inputs alone do not imply finite arithmetic outputs: subtraction, squared norms, and conversions can overflow; small norms can underflow. Record each edge's bounds or rejection behavior. Formula equality alone proves neither real-valued accuracy nor total composition. Require a separate bound proof or explicitly classify the edge as tested/trusted. Exhaustive supported-date tests are strong finite-domain integration evidence, not a universal theorem about arbitrary ephemeris vectors.

### Measured test coverage
Report instrumentation separately from formal coverage. For JavaScript, run Node's `--experimental-test-coverage` with an explicit `--test-coverage-include` scope and report line, branch and function coverage independently. Name excluded UI, generated code and dependencies. Cover real boundary/error/formatting/projection behavior; do not inflate percentages by excluding uncovered application logic or counting generated formula equality as astronomical validation.

For phase schedules, audit the `dafny-sequence` receipt against `Timeline.dfy`, the original `compiler.js`, and the imported `core.mjs`. Count this as a sequence-accounting proof only. Mission data, partition choices, calendar conversion, and physical feasibility require separate evidence.
