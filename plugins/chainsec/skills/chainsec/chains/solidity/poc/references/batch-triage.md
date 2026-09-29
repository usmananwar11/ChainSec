# Batch triage — Foundry specifics

Supplements `engine/poc/batch-triage.md`. Moved verbatim from Krait's `batch-triage.md`.

## Step 2 — the "few runs" rule

- Re-running a green `forge test` is pointless; the result is deterministic.

## Table rules

- Attach the per-finding artifacts (the `.sol` files, the fix diffs for PASS rows) below the
  table or in `.audit/solidity/poc/<ID>/`, so each verdict is auditable.
