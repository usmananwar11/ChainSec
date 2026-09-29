---
name: chainsec-init
description: Check whether this project is ready for a ChainSec audit — detects chains and reports required/optional tools per chain pack, with install hints.
argument-hint: "[path]"
---

# ChainSec init

1. Resolve CORE as in chainsec-audit.
2. Run `python3 ../chainsec/scripts/detect-chain.py TARGET` and show the result.
3. For each detected chain, follow `../chainsec/engine/phases/preflight.md` in **report** mode and
   print its summary table. Do not write `.audit/` files in report mode.
4. End with one line: ready / not ready, and the install commands for anything missing.
