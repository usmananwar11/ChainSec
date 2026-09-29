# Assertion retry protocol — Foundry specifics

Supplements `engine/poc/assertion-protocol.md`. Moved verbatim from Krait's
`assertion-protocol.md` variant table.

## Variant exploration

| Failure dimension | Relaxed variant |
|---|---|
| Timing | same-block → multi-block (`vm.roll`/`vm.warp`) |
