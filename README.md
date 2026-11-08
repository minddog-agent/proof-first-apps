# Proof-First Apps

An agent workflow and bundled tools for building apps with explicit behavioral contracts, checked core logic, and separately tested integration.

Start with [SKILL.md](SKILL.md). Tooling and examples live in `assets/agentc/`; workflow references are in `references/`.

## Prepare a project

```sh
python3 scripts/prepare_workspace.py --project /path/to/project
python3 /path/to/project/.agentc/tool/agentc.py list
```

Python 3.10+ is required. Individual backends use Lean 4.19.0, Dafny 4.11.0, or Z3; see the corresponding references for requirements and supported targets.

## Assurance boundaries

Proofs apply only to their exact contracts and checked implementations. Generated target code trusts its compiler and runtime; integration is tested separately. This tooling does not automatically verify whole applications or provide general Lean-to-target translation. Experimental backends and intentionally failing proof examples are included.
