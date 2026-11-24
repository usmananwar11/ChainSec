# AA-SELF-CALL-SESSION

> **Detector class**: `AA-SELF-CALL-SESSION`
> **Inject into**: Lens A (Access/State) + Lens D (Edge cases/Math)
> **Category**: Account abstraction
> **Related attack vectors** (heuristics.md, Extended heuristics): AV-22, AV-96
> **Module**: [modules/account-abstraction.md](../modules/account-abstraction.md)
> <!-- Ported from keep-starknet-strange cairo-auditor vulnerability-db (MIT); see ATTRIBUTION.md -->

## Class

Session key privilege escalation via account self-call.

## Description

Session-key execution paths must not allow calls back into the account contract for privileged selectors.
If self-calls are allowed, a compromised session key may invoke admin/state-changing selectors and escalate control.

## Detection

Flag session-key `__execute__` paths where both are true:

- call target can equal `get_contract_address()`
- selector denylist does not block privileged account selectors

## Secure pattern

- deny self-targeting calls for session-key paths (`call.to != self`)
- deny privileged selectors explicitly
- test both snake_case and camelCase selector variants when relevant

## False-positive caveats (Gate C / FP-10 evidence)

Owner-only administrative flows may permit self-calls; session-key flows must not.

## Minimum tests (PoC and regression targets)

- session key cannot invoke account privileged selector
- owner path still functions correctly
