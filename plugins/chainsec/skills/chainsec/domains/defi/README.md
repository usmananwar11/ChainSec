# DeFi domain layer

Chain-agnostic DeFi knowledge shared by every chain pack. Engine phases load these files; each
pack adds chain-specific halves under `chains/<chain>/modules/` and `chains/<chain>/primers/`
with the same file names.

- `modules/` — deep-dive detection modules, selected during recon (see `domains/defi/triggers.md`).
- `primers/` — protocol-type priorities.
- `heuristics.md` — trigger-based heuristics that do not depend on the chain.
