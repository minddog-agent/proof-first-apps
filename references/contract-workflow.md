# Contract and CLI reference

The prepared project contains `.agentc/tool/agentc.py` plus `contracts/clamp` and `contracts/calculator`. Call `describe` to inspect either. Read those actual bundle files rather than assuming a stale contract.

Supported commands:

```sh
python3 <tool> list
python3 <tool> describe --contract <name-or-bundle-path>
python3 <tool> scaffold --contract <bundle> --out <new-candidate.lean>
python3 <tool> verify --contract <bundle> --candidate <candidate.lean> --expect-contract <hash> --out <report.json>
python3 <tool> compare --contract <bundle> --candidate <a.lean> --candidate <b.lean> --expect-contract <hash>
python3 <tool> emit --contract <bundle> --candidate <candidate.lean> --expect-contract <hash> --out <new-directory>
```

Use `--timeout` for seconds per Lean subprocess (default 20, maximum 300). The verifier also limits Lean heartbeats. Exit 0 is success, 1 is incomplete/rejected/unknown, 2 is setup or malformed-input failure. `compare` exits 0 if at least one candidate is verified. Do not infer that all candidates passed from that exit code.

Manifest fields are exact: `schema_version` (1), `name`, `lean_version` (4.19.0), `spec_sha256`, `exports`, `obligations`, `notes`. Each export has `name` and `type`. Each obligation has `id`, `proof`, `type`, `required`. Names use `Candidate.identifier`. At least one obligation must be required. Copy a bundled manifest's structure and compute the actual specification SHA-256.

Specifications are self-contained `ContractSpec.lean` files using installed standard Lean libraries. Candidates are single Lean files importing `ContractSpec`. Multi-file external dependencies are not supported in this prototype. Supply complete source, not a prebuilt `.olean`.

An external identity-function example:

```lean
-- ContractSpec.lean
import Std
namespace IdentitySpec
def Correct (f : Int → Int) : Prop := ∀ x, f x = x
end IdentitySpec
```

```lean
-- Proposal.lean
import ContractSpec
def Candidate.run (x : Int) := x
theorem Candidate.correct : IdentitySpec.Correct Candidate.run := by
  intro x
  rfl
```

The required claim is `IdentitySpec.Correct Candidate.run`, with proof `Candidate.correct` and export `Candidate.run : Int → Int`.

The checker audits transitive axioms for proofs and exported definitions. It allows only `propext`, `Classical.choice`, and `Quot.sound`. `sorryAx` is unproved; custom axioms are rejected. Do not replace difficult proofs with assumptions or silently use native computation that adds unsupported assumptions.

Build directories are temporary and fresh; they are not an operating-system security sandbox. Use locally generated/trusted candidate source. Fingerprints detect identity changes but are not signatures. Receipts are evidence to inspect, not authority to bypass a fresh `emit` check.
