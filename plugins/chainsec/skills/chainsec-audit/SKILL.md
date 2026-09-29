---
name: chainsec-audit
description: Run a full ChainSec smart-contract security audit (recon, multi-lens detection, state analysis, kill-gate verification, report) on this repository or a given path; Solidity supported, more chains via packs. Run only when the user explicitly asks for a ChainSec audit.
disable-model-invocation: true
argument-hint: "[path] [--quick] [--chain <name>] [--fresh]"
---

# ChainSec audit

Arguments: `$ARGUMENTS` (if your tool does not substitute this, take them from the user's message).
The first token that is not a flag is TARGET (default: current directory). Flags: `--quick`
(skip per-unit and state phases), `--chain <name>`, `--fresh`.

1. Resolve the core: from this skill's folder run `cd ../chainsec && pwd`; call the result CORE.
   If `../chainsec/engine/pipeline.md` does not exist, stop and tell the user: "The ChainSec core
   skill is missing next to chainsec-audit. Install all ChainSec skills together — see
   https://github.com/usmananwar11/ChainSec/blob/main/INSTALL.md".
2. Read `../chainsec/engine/pipeline.md` and follow it exactly, with TARGET, the flags and CORE.
3. The audit takes a while. Keep the user informed with one short line per phase.
