# Known issues (Gate H)
Source: README "Automated Findings / Publicly Known Issues"; 4naly3er-report.md (gas + low issues only); bot-report.md ("Nothing to see here… yet" — empty); previous audits (audits/*.pdf, Init_v01, PeckShield) not parsed — PDFs, acknowledgments not extracted.

README known issues:
1. Users can avoid paying flashloan fee (if set to non-zero) by atomically borrowing and then repaying in the same transaction.
2. `totalInterest` may slightly overestimate the actual interest accrual due to rounding up (in the order of wei).

Publicly known by reference: everything in 4naly3er-report.md (Gas Optimizations, Low Issues) — style/low-severity automated findings.
Out of scope: InitErrors.sol, LogExpMath.sol, contracts/interfaces/*, contracts/mock/*, PythOracleReader.sol, WLp (not in scope).
README states: no fee-on-transfer tokens supported; ERC721 not generally supported.
