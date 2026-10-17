# Invariants — Vault (src/Vault.sol, src/Base.sol)

Source: code only plus `.audit/solidity/recon.md`. Ledger model: `balances` is one shared ledger for ERC20 deposits and native deposits; `totalDeposits` tracks ERC20 deposits only.

| ID | Category | Priority | Description | Formal expression | State | Functions that could violate it |
|---|---|---|---|---|---|---|
| INV-001 | token-conservation | high | Vault's token balance covers `totalDeposits` | `token.balanceOf(vault) >= totalDeposits` | totalDeposits, token balance | withdraw, deposit (unchecked return) |
| INV-002 | accounting | high | `totalDeposits` never wraps below real deposits (no underflow from `unchecked`) | `totalDeposits <= ghostTokenDeposited` | totalDeposits | withdraw |
| INV-003 | accounting | high | Token liabilities are backed: sum of user ledger balances is covered by assets held | `sum(balances) <= token.balanceOf(vault) + address(vault).balance` | balances | withdraw, depositEth, sweep |
| INV-004 | accounting | high | `totalDeposits` equals the sum of the ledger when only tokens are used (ledger consistency) | `sum(balances) == totalDeposits + ghostEthCredited - ghostEthSweptOrOffsetting` (checked as `sum(balances) <= totalDeposits + ghostEthCredited`) | balances, totalDeposits | withdraw, depositEth |
| INV-005 | token-conservation | high | Native balance is not extractable by non-depositors: ETH held >= ETH credited and not yet withdrawn | `address(vault).balance >= ghostEthCredited` | ETH balance | sweep |
| INV-006 | access-control | high | Owner changes only via the owner calling `transferOwnership` | `owner == ghostOwner` | owner | transferOwnership |
| INV-007 | access-control | high | Value-moving native exit is restricted | any caller's `sweep` must not reduce ETH balance (same as INV-005 under handler-driven sweep) | ETH balance | sweep |
| INV-008 | accounting | medium | A user cannot withdraw more than their ledger balance | `withdraw(x)` with `x > balances[u]` reverts | balances | withdraw |
| INV-009 | accounting | high | Every ledger balance is redeemable (withdraw pays tokens only) | `balances[u] <= token.balanceOf(vault)` | balances | depositEth, withdraw |
| INV-010 | bounds | low | Fee bound | `FEE_BPS <= 10_000` | FEE_BPS | — |
| INV-011 | economic | low | Fee is applied on deposit/withdraw (declared fee is not dead) | `credited == amount - amount*FEE_BPS/10000` | FEE_BPS | deposit, withdraw (not applied) |
| INV-012 | state-transition | low | `setFee` is owner-only and non-owner calls revert | caller != owner ⇒ revert | owner | setFee |
