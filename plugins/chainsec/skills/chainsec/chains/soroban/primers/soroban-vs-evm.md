# ChainSec Detection Primer: Soroban for EVM-Trained Auditors

> Where EVM intuition gives the wrong answer on Soroban. Each item names the heuristic in
> [heuristics.md](../heuristics.md) or the pattern in [patterns/README.md](../patterns/README.md)
> that holds the check. Sections 1 and 2 are adapted from Stellar's `stellar-dev-skill`
> `security.md` (Apache-2.0; see [ATTRIBUTION.md](../ATTRIBUTION.md)).

## 1. Threat model

Assume the attacker controls:

- every argument passed to contract functions;
- transaction ordering and timing;
- every account except those whose signatures are required;
- the ability to deploy contracts that mimic your interface;
- the shape of on-chain state they can legally create (entry counts and TTLs; they can even extend
  your entries' TTLs).

## 2. What the platform rules out, and what it does not

| Platform rule | What it removes | What it does not remove |
|---|---|---|
| No `delegatecall`: contracts cannot run foreign bytecode in their own context | Proxy-style code hijacks via a borrowed implementation | Upgrades still exist (`update_current_contract_wasm`) and need admin auth: UPG-01 |
| No reentrancy: the host blocks reentrant calls, direct or indirect, on normal cross-contract paths | Classic reentrancy findings | External calls are still failure, budget and side-effect boundaries; order state updates deliberately: XC-01, XC-02, RES-01 |
| Host-managed auth replay protection: nonces and expirations on authorization entries are enforced by the host | Hand-rolled nonce and replay checks for `require_auth` | `require_auth_for_args` binds only the listed arguments (AUTH-04); a pre-signed auth tree can be consumed by a contract that never auths the user (AUTH-03) |
| Explicit authorization: `require_auth()` is opt-in | Implicit-caller confusion | Forgetting `require_auth`, or authorizing the wrong address, is the bug to hunt: AUTH-01, AUTH-02 |

## 3. Translation table: EVM to Soroban

| EVM assumption | Soroban reality | Check |
|---|---|---|
| `msg.sender` is the caller | No implicit caller. Each function authorizes the addresses it acts for with `Address::require_auth`; the host verifies that address authorized this contract, function and arguments | AUTH-01 to AUTH-04, MISSING-AUTH |
| `payable` functions and native ETH | No native value on calls. XLM is a token behind a Stellar Asset Contract (SAC) and moves through token calls | TOK-02, TOK-03 |
| Proxy and implementation, `delegatecall` | The contract's own code is replaced in place with `update_current_contract_wasm`; there is no proxy | UPG-01 to UPG-03 |
| Storage slots, declaration order | Typed keys (`#[contracttype]` enums) in three tiers (`instance`, `persistent`, `temporary`) with TTLs; entries can archive or vanish | STOR-01, TTL-01, TTL-02 |
| `uint256` balances | `i128` amounts, which are signed: a negative amount reverses a flow if unchecked | TOK-01, ARITH-02 |
| Events as logs | `env.events().publish(topics, data)`; standard token event shapes matter to indexers | token-integration module |
| `block.timestamp`, ~12 s blocks | `env.ledger().timestamp()`, the ledger close time; ledgers close roughly every 5 seconds | TIME-01 |
| Constructor runs at deploy; `initialize` only on proxies | `__constructor` (SDK 22 and later) runs atomically at deploy time; a guarded `initialize` leaves a front-run window | INIT-01, REINITIALIZATION |
| Gas limit bounds loops | Per-transaction CPU, memory and ledger read/write limits, set by network configuration | RES-01, RESOURCE-EXHAUSTION |
| Contracts and EOAs are different | Any contract can be an account by implementing `__check_auth`; the host calls it with the signature payload and the auth contexts | ACCT-01, ACCT-02 |
| `^` is exponentiation in some mental models | In Rust `^` is XOR; use `pow` or `checked_pow` | ARITH-04 |

## 4. Habits to drop

- **Reentrancy findings.** The host blocks reentrant calls, so a "reenter before the balance update"
  finding needs a concrete non-reentrant path; XC-03 covers what to check instead.
- **Checking the boolean return of `transfer`.** SEP-41 token `transfer` panics on failure and
  returns no bool; an unchecked-return finding on it is a false positive. Look at what happens when
  the call fails or exhausts the budget instead (XC-04).
- **Gas-griefing through the 63/64 rule.** There is no such forwarding rule. The equivalent is a
  per-transaction resource limit: a callee that burns budget or a loop over attacker-grown data makes
  your function fail (RES-01 to RES-03).
- **Replay-protection hunts for `require_auth`.** Nonce handling is the host's job; look for the
  missing or mis-targeted `require_auth` instead.
- **Proxy-storage-layout hunts.** There is no proxy, but upgraded code must still read the old
  entries: key enums and struct fields are matched by name, so renames strand data (UPG-02).

Vulnerability classes specific to this toolchain are in [patterns/README.md](../patterns/README.md).
