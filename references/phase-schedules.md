# Phase schedules and empirical models

## Fixed sequence contract

Use `agentc timeline` (v0.11) for an ordered list of nonnegative integer durations. The bundled `timelines/Timeline.dfy` proves for arbitrary list lengths: zero initial boundary, one endpoint per phase, each next endpoint equal to the previous plus its duration, monotonic endpoints, and final endpoint equal to the mathematical sum. It compiles that actual loop with Dafny 4.11.0; it does not prove a detached summation model.

Read and pin the fixed source fingerprint before emission:

```sh
python3 .agentc/tool/agentc.py timeline --describe
AGENTC_DAFNY=/absolute/path/to/dafny python3 .agentc/tool/agentc.py timeline --expect-contract HASH --out lib/verified/timeline
```

Import `buildTimeline` from emitted `core.mjs`. Pass canonical unsigned decimal strings; receive decimal-string endpoints including the initial zero. The tested adapter caps inputs at 256 phases and 4096 digits each. Empty lists return `["0"]`; zero-duration phases are allowed. Negative values, fractions, JSON numbers, leading zeros and malformed strings are rejected. Preserve exact integers and use one declared time unit throughout. Convert to Number only after checking a safe bound. Install `bignumber.js` 9.1.2 in the app. The generated runtime is unchanged except for the explicit ESM import shim and appended adapter; both are trusted, not proved. Receipts retain the Dafny source, compiler output and emitted source hashes. `coverage` recognizes this backend; it still never declares a whole application proved.

Run `python3 <tool>/tests/test_timeline.py` from a project with bignumber.js installed and AGENTC_DAFNY configured. Test a deliberately broken recurrence to confirm rejection, huge integers beyond 2^53, empty/zero/long sequences, invalid adapter inputs and the real app call path. Browser-bundle and UI checks are separate. Reverify before publication.

## Define a complete timeline

Before implementation, specify the start event, end event, time scale, unit and whether each phase is sequential or overlaps another. A phase list is sequential; concurrent activities inside a phase must not be added again. Treat delay before launch, travel to destination, signal receipt, commissioning and return as distinct endpoints. Unknown duration is not zero: display it as unknown, exclude it with a visible explanation, or request an explicitly labeled planning allowance. Record source, provenance (observed/planned/assumed/derived), date and precision for every input. Avoid spurious precision when totals are rounded.

Check conservation in the application: subphases partition their parent total; approach must be subtracted from cruise if shown separately; a terminal descent already included in the arrival total must not be added a second time. The sequence theorem proves the sum of the supplied durations, not completeness or correctness of the list supplied by the app. Prove additional partition/refinement properties or label the data preparation as tested-only.

## Mission-estimate boundaries

Use historical mission profiles for clearly labeled benchmarks when trajectory optimization is absent. Pair spacecraft with launch vehicle; do not confuse launcher stage speed with a constant interplanetary cruise speed. Record spacecraft arrival event separately from Earth receipt of telemetry. Use UTC date normalization and acknowledge date-rounded historical durations.

Do not divide instantaneous planet separation by a vehicle top speed and call it flight time. A new launch date requires launch-window/trajectory solving, propulsion and payload constraints, moving-target interception, and arrival braking assumptions for a physical prediction. Preserve these as explicit unproved obligations if unsupported. Distinguish orbital capture, flyby and surface landing. Do not give an orbiter a landing phase or present robotic hardware as crew-capable. The 100 km boundary is a convention, not the physical end of atmosphere; a chosen crossing time is a scenario input unless sourced or simulated.

A historical travel time shifted to a selected date is an illustrative calendar scenario, not an available launch opportunity. Show this beside the result, not only in fine print. A numerical proof cannot validate astronomical data, atmospheric dynamics, hardware performance, propulsion budgets, empirical accuracy or mission feasibility. Track these as trusted/model-limited components in full-app coverage, and state test instrumentation scope independently.
