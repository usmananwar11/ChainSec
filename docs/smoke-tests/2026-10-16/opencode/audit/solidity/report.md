# ChainSec Security Audit Report

**Target**: Unnamed vault fixture (primary contract: `Vault`)
**Date**: 2026-10-16
**Auditor**: ChainSec
**Scope**: `src/Vault.sol`, `src/Base.sol` (2 files, ~74 LOC)

---

## Executive Summary

ChainSec audited a minimal custom vault (`Vault` + `Owned`) that accepts both ERC20 deposits and native ETH through a single shared `balances` ledger. Two Critical, permissionless fund-drain findings were verified: an unrestricted `sweep()` that sends the entire ETH pool to a caller-chosen address, and a mixed ETH/ERC20 ledger that lets any address mint native credits via `depositEth()` and redeem them against other users' ERC20 tokens at dust cost. A Medium finding covers an `unchecked` counter wrap that DoSes `deposit()`. Overall risk is **critical**: any address can extract 100% of the vault's custodied value in a single transaction.

**Finding Summary**:
| Severity | Count |
|----------|-------|
| Critical | 2 |
| High | 0 |
| Medium | 1 |
| Low | 0 |

---

## Findings

### [SOL-001] Single balances ledger mixes native ETH and ERC20: permissionless depositEth grants withdrawal authority over other users' ERC20, letting any caller drain the token pool — CRITICAL

**File**: `src/Vault.sol:27`
**Category**: state-integrity
**Evidence**: REASONED — code trace [CODE-TRACE]

**Description**:
The `balances` mapping stores a bare uint256 credit with no record of the asset behind it. `deposit()` writes it backed by ERC20 held in custody; `depositEth()` writes the **same** mapping backed by nothing but `msg.value`, and is fully permissionless with no authorization or backing check. `withdraw()` consumes any `balances` entry and always pays ERC20. A native-ETH credit is therefore redeemable 1:1 (in base units) against other users' ERC20 — a low-privilege, unbacked credit pathway grants authority over high-value ERC20 funds. The cost analysis deepens this: the cost to steal N token base units is only N wei of ETH, so for any token with < 18 decimals the theft is effectively free (stealing 1e12 USDC-like base units = $1,000,000 costs 1e12 wei ≈ 0.000001 ETH). No exotic token behavior is required — a standard reverting ERC20 suffices. (Consensus: 3 independent sources converged on this root cause.)

**Impact**:
ERC20 depositors lose their custodied tokens, paid out against ETH credits that never contributed ERC20. Up to the entire vault token balance is at risk; bounded only by the attacker-chosen `depositEth` credit. Preconditions: the vault holds ERC20 deposited by other users, and `depositEth` is callable by anyone (both trivially true in normal operation).

**Proof of Concept**:
```
1. Victim calls deposit(1_000_000e6) → balances[victim]=1e12, totalDeposits=1e12, vault holds 1e12 token base units.
2. Attacker calls depositEth{value: 1e12 wei}() (~0.000001 ETH) → balances[attacker]=1e12; no tokens enter the vault and totalDeposits is unchanged.
3. Attacker calls withdraw(1e12) (src/Vault.sol:36-42): checked balances[attacker] -= 1e12 passes; unchecked totalDeposits -= 1e12 yields 0 (no wrap); token.transfer(attacker, 1e12) pays the victim's 1e12 base units to the attacker.
4. Vault token balance is now 0; the victim's subsequent withdraw() reverts inside token.transfer (insufficient balance) — the victim's tokens are gone.
```

**Root Cause**:
A single `balances` ledger backs two unlinked asset pools (custodied ERC20 and native ETH) and records no asset tag; `withdraw` always pays ERC20, so permissionlessly-minted native credits authorize redemption of the shared ERC20 pool.

**Recommendation**:
Split the ledger by asset: keep `balances` for ERC20 credits only and add a separate `ethBalances` mapping for native credits, with a per-account `withdrawEth` that debits the ledger before transferring. This removes the cross-asset redemption path so a native credit can never authorize an ERC20 payout. Ship together with the SOL-002 sweep fix (see Fixed Code below).

**Vulnerable Code**:
```solidity
function depositEth() external payable {
    balances[msg.sender] += msg.value;
}

function withdraw(uint256 amount) external {
    balances[msg.sender] -= amount;
    unchecked {
        totalDeposits -= amount;
    }
    token.transfer(msg.sender, amount);
}
```

**Fixed Code** (suggested):
```solidity
mapping(address => uint256) public ethBalances;

function depositEth() external payable {
    ethBalances[msg.sender] += msg.value;
}

function withdrawEth(uint256 amount) external {
    ethBalances[msg.sender] -= amount;
    (bool ok, ) = msg.sender.call{value: amount}("");
    require(ok, "ETH send failed");
}

function withdraw(uint256 amount) external {
    balances[msg.sender] -= amount;
    totalDeposits -= amount; // checked, see SOL-003
    token.transfer(msg.sender, amount);
}
```

---

### [SOL-002] sweep() is the only native-asset exit and pays an attacker-chosen recipient instead of the ETH credit holders, so the whole ETH pool is permissionlessly extractable in one call — CRITICAL

**File**: `src/Vault.sol:32`
**Category**: value-flow
**Evidence**: REASONED — code trace [CODE-TRACE]

**Description**:
Tracing every wei of the native pool: the only function that ever moves ETH out is `sweep(address payable to)`, which sends the entire `address(this).balance` to an arbitrary recipient chosen by the **caller** — not to the addresses credited via `depositEth`. No function ever pays ETH against `balances[]`. The recipient of the vault's ETH pool is semantically wrong (arbitrary caller, not the asset holders), and because `sweep` is unguarded any address can take the whole pool. The attacker can also recover their own `depositEth` funds through the same call: send 10 ETH via `depositEth`, call `withdraw(10e18)` to steal 10e18 ERC20 units (SOL-001), then `sweep(attacker)` to take all 10 ETH (plus anyone else's) back — a depositEth→withdraw→sweep sequence nets stolen ERC20 tokens with zero net ETH outlay, leaving honest ETH depositors with unbacked ledger entries. (Consensus: 3 independent sources converged on this root cause.)

**Impact**:
All users who deposited native ETH via `depositEth` (and anyone who force-sent ETH to the vault) lose their entire ETH balance held in the vault. Magnitude: the full `address(this).balance` at call time — e.g. 10 ETH deposited by a victim is taken whole by the first sweeper; a 10 ETH depositEth→withdraw→sweep sequence extracts 10e18 ERC20 units at zero net ETH cost. Precondition: the vault holds any native ETH (any prior `depositEth` call or force-send).

**Proof of Concept**:
```
1. Victim calls depositEth{value: 10 ether}() → balances[victim] += 10e18; vault holds 10 ETH.
2. Attacker calls depositEth{value: 10 ether}() → balances[attacker] += 10e18.
3. Attacker calls withdraw(10e18) → ledger debited, vault pays 10e18 ERC20 units (victim's tokens, see SOL-001) to the attacker.
4. Attacker calls sweep(attacker) → to.transfer(address(this).balance) returns the attacker's own 10 ETH plus the victim's 10 ETH (20 ETH) to the attacker; no guard exists (src/Vault.sol:32-34: no modifier, no recipient constraint).
5. Net: attacker holds their original 10 ETH + 10e18 stolen ERC20 units; victim's balances[victim] still reads 10e18 but vault ETH balance is 0 and withdraw() only pays ERC20 — victim's native deposit is irrecoverable.
```

**Root Cause**:
The native-asset out-flow is a single permissionless whole-balance transfer to an arbitrary address, disconnected from the balances ledger; the payment destination is the caller's chosen `to` instead of the ETH credit holders, and there is no per-account ETH withdrawal to compete with it.

**Recommendation**:
Remove `sweep` or gate it with `onlyOwner`, and give native credits a real per-account exit (`withdrawEth` as in SOL-001). `onlyOwner` alone stops the theft but leaves honest `depositEth` credits permanently locked — there is currently no per-account ETH exit — so ship both changes together. Ideally also cap `sweep` at force-sent excess (`address(this).balance - totalEthCredits`) instead of the whole balance, so it cannot take credited user funds even as an owner tool.

**Vulnerable Code**:
```solidity
// BUG (planted for smoke tests): no access control, anyone can drain the native balance.
function sweep(address payable to) external {
    to.transfer(address(this).balance);
}
```

**Fixed Code** (suggested):
```solidity
uint256 public totalEthCredits; // += msg.value in depositEth, -= in withdrawEth

function sweep(address payable to) external onlyOwner {
    uint256 excess = address(this).balance - totalEthCredits;
    require(excess > 0, "nothing to sweep");
    to.transfer(excess);
}
```

---

### [SOL-003] unchecked totalDeposits subtraction in withdraw() underflows and wraps the counter when amount > totalDeposits, DoS-ing deposit() until headroom is restored — MEDIUM

**File**: `src/Vault.sol:36`
**Category**: arithmetic
**Evidence**: REASONED — code trace [CODE-TRACE]

**Description**:
`withdraw()` applies `totalDeposits -= amount` inside `unchecked` while `balances[msg.sender] -= amount` is checked. `amount` is bounded only by `balances[msg.sender]`, never by `totalDeposits`. Under ERC20-only usage the invariant `vault_token_balance == totalDeposits` holds by induction over deposit/withdraw, so `amount > totalDeposits` **and** a successful `token.transfer(amount)` are jointly unreachable. The underflow becomes reachable once the vault holds even 1 wei of unaccounted ERC20 tokens (a direct donation — attacker-trivial via self-donation): choose `amount == totalDeposits + 1`, which fits inside the vault token balance and the attacker's `depositEth`-funded balances. The wrap sets `totalDeposits` to `2^256 - E`; `deposit(x)` then overflows (checked add) for every `x >= E`, so `E == 1` (cost: `totalDeposits + 1` wei of ETH plus gas) bricks all non-zero deposits. The DoS is partially reversible (any later `withdraw(w)` restores `w` headroom) but the counter is permanently corrupted at ~2^256 magnitude with no reset path, and deposits that shrink headroom back to 0 re-trigger the full DoS. Severity stays Medium: the DoS is conditional on unaccounted tokens being present and is reversible by withdrawals, so it does not meet the permanent-DoS High bar. (Consensus: 4 independent sources converged on this root cause.)

**Impact**:
All vault depositors lose the liveness of `deposit()` (every non-zero deposit reverts while headroom is 0) and the `totalDeposits` accounting invariant is permanently corrupted at ~2^256 magnitude. Minimal attack cost: `amount = totalDeposits + 1` (1 wei of ETH via `depositEth` + 1 wei self-donation + gas). Preconditions: ≥1 wei of unaccounted ERC20 in the vault (attacker-trivial), and attacker credits ≥ `amount` via `depositEth`.

**Proof of Concept**:
```
1. Victim calls deposit(100) -> totalDeposits = 100, vault token balance = 100. Attacker self-donates 1 wei of the token -> vault token balance >= 101.
2. Attacker calls depositEth{value: 101 wei}() -> balances[attacker] = 101; totalDeposits unchanged at 100.
3. Attacker calls withdraw(101): checked balances[attacker] -= 101 passes; unchecked totalDeposits = 100 - 101 wraps to 2^256 - 1; token.transfer(attacker, 101) succeeds (vault holds >= 101 token units).
4. totalDeposits reads 2^256 - 1. Every subsequent deposit(x >= 1) overflows the checked totalDeposits += x and reverts; only deposit(0) succeeds.
5. Any later withdraw(w) sets totalDeposits = 2^256 - 1 - w, restoring headroom to w (partially reversible) — but the counter stays permanently desynced at ~2^256 with no reset path.
```

**Root Cause**:
Unchecked subtraction applied to a counter whose bounding invariant (`totalDeposits <= vault token balance`) is not enforced on the debit path: `withdraw` bounds `amount` by the per-user `balances` ledger (which `depositEth` inflates without incrementing `totalDeposits`) and never by `totalDeposits`.

**Recommendation**:
Remove the `unchecked` block so Solidity 0.8 checked math reverts the wrap (or bound the debit by the counter before subtracting). The revert is the correct outcome whenever `amount > totalDeposits` — a state only reachable through the SOL-001 mixed-ledger bug — so fixing SOL-001 keeps `totalDeposits` consistent and the checked path never blocks legitimate withdrawals.

**Vulnerable Code**:
```solidity
function withdraw(uint256 amount) external {
    balances[msg.sender] -= amount;
    unchecked {
        totalDeposits -= amount;
    }
    token.transfer(msg.sender, amount);
}
```

**Fixed Code** (suggested):
```solidity
function withdraw(uint256 amount) external {
    balances[msg.sender] -= amount;
    totalDeposits -= amount; // checked: reverts if amount > totalDeposits
    token.transfer(msg.sender, amount);
}
```

---

## Security Strengths

- **Access control model**: Every privileged function is guarded by the same require-based `onlyOwner` modifier defined once in `Owned` (`src/Base.sol:7-10`); `setFee` and `transferOwnership` both use it consistently and `owner` is initialized in the constructor.
- **Reentrancy protection (CEI on the token path)**: `withdraw()` (`src/Vault.sol:36-42`) debits `balances[msg.sender]` and `totalDeposits` before `token.transfer`, and `deposit()` (`src/Vault.sol:21-25`) pulls tokens via `transferFrom` before crediting — a reverting token cannot leave unbacked credits on the deposit path.
- **Arithmetic safety**: Solidity `^0.8.20` checked math applies to all ledger updates (`balances +=` in `deposit`/`depositEth`, `totalDeposits +=` in `deposit`, checked `balances -=` in `withdraw`); no downcasts exist, and the sole assembly block reads `selfbalance()` into a local with no arithmetic.
- **Asset immutability**: The custodied ERC20 is an immutable constructor-set address (`src/Vault.sol:12`) — no token-swap or rescue path can redirect funds or re-point the ledger at a different asset post-deployment.
- **Area for improvement**: No reentrancy guards, no zero-address validation on the `token` constructor argument or `transferOwnership`, no test suite in scope, and vestigial fee machinery (`FEE_BPS` never read, `setFee` an empty body) that integrators could mistake for working functionality.

---

## Architecture Observations

- `_selfBalance()` (`src/Vault.sol:50-54`) is dead code — an internal assembly helper that is never called; `sweep` reads `address(this).balance` directly.
- The fee machinery (`FEE_BPS = 30` at `src/Vault.sol:15`, empty-body `setFee` at `:44`) is vestigial: the constant is never read and `setFee` changes nothing. Integrators must not expect fees to apply.
- `src/Vault.sol:31` carries an explicit `BUG (planted for smoke tests)` marker comment — a fixture/smoke-test artifact indicating this codebase is intentionally defective test material.
- The contract is deliberately small (~45 LOC) with no test suite present; invariant/fuzz tests pinning `totalDeposits == sum of ERC20 credits` and `address(this).balance == sum of ETH credits` would catch the ledger-mixing class mechanically.
- `transferOwnership` (`src/Base.sol:16-18`) is single-step with no zero-address check — an owner typo permanently bricks `setFee`/future privileged functions.

---

## Methodology

**Audit mode**: Quick (`--quick`).

Completed phases:
- **Recon** — architecture mapping, fund flows, trust boundaries, file risk table.
- **Detection** — Pass 1 (four lenses and the final sweep).
- **Rescan** — re-examination of candidates and coverage gaps.
- **Verification** — kill gates A–H, impact premises, and line-by-line exploit traces for all surviving candidates.

Per-unit deep dives and State Analysis were skipped (--quick).

Mode notes: facts mode `compiler` (compiler-extracted units, entry points, storage writes, external calls); preflight tooling mode `degraded` (python3 3.14.6 OK, forge 1.7.1 OK, slither MISSING — static-analyzer signal table skipped); `incomplete_phases`: none; warnings: none.

Methodology derived from Krait by Zealynx Security.

---

──────────────────────────────────────────────────
📋 3 findings saved to .audit/findings.json
──────────────────────────────────────────────────

### Next Steps

1. **Prove a finding**: Run `chainsec-poc SOL-001` or `chainsec-poc SOL-002` (or the whole findings list for batch triage) to turn the `[CODE-TRACE]` evidence into an executed `[POC-PASS]` or `[POC-FAIL]`.
2. **Fuzz invariants**: Run `chainsec-fuzz` to extract the protocol's invariants (e.g. `totalDeposits == sum of ERC20 credits`) and test them with the pack's fuzzing framework.
