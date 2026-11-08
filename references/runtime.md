# Runtime prerequisites and troubleshooting

Use Python 3.10+ and the official Lean 4.19.0 toolchain. `lean` must be on PATH. With elan installed, install the pinned toolchain through the normal permitted dependency workflow. Do not assume an earlier conversation's scratch runtime still exists.

The verifier uses no Python dependencies or Mathlib. It creates a fresh directory with a pinned `lean-toolchain`, compiles the bundled contract and submitted candidate, and removes temporary build products afterward.

If network or installation is blocked, preserve the source and continue app tests with `proof_status: not_run`. Explain the missing prerequisite. Do not reinterpret a failed invocation as verification.

Some managed workspaces expose `/proc/self/exe` but not the equivalent `/proc/PID/exe` used by Lean 4.19.0. Diagnose this only when Lean reports `failed to locate application`. If `/proc/self/exe` works and the same process's numeric path does not, the bundled `scripts/proc_self_compat.c` normalizes that one executable lookup. It does not replace proof-checking functions. Compile it into a project-local temporary directory and use it only for the affected commands; record its use in the evidence. Do not modify kernel binaries or broader access controls. Normal systems should not need it.

The optional adapter needs a C compiler and is Linux-only:

```sh
cc -shared -fPIC <skill-dir>/scripts/proc_self_compat.c -ldl -o <project-dir>/.agentc/proc_self_compat.so
LD_PRELOAD=<project-dir>/.agentc/proc_self_compat.so python3 <tool> verify ...
```
