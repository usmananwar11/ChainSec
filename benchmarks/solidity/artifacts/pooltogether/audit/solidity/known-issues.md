# Known Issues (Gate H)
Source: README "Automated Findings / Publicly Known Issues", bot-report.md (Cygnet), 4naly3er-report.md. Anything below is ineligible.

## README
- Yield vault MUST NOT charge deposit/withdraw/other fees; underlying asset MUST NOT have transfer fees.
- Low-precision-per-dollar assets (GUSD, WBTC) incompatible; 1-wei rounding errors exploitable to deny yield on low-gas networks (yieldBuffer comments).
- Total share supply cannot exceed uint96 max (TwabController).
- Deployer is expected to donate `yieldBuffer` assets to cover initial rounding errors.
- Yield vaults are not expected to lose assets.
- Trusted: vault owner (liquidation pair, claimer, fee params).
- DOS concern threshold: denying yield accrual >= 1 day.

## Bot report (Cygnet) – categories (all low-quality generic):
M-01 rebasing accounting; M-02/M-03 unchecked transfer()/transferFrom() return (factory transferFrom, _asset.transfer); M-04 unchecked approve() return;
L-01 growing arrays (allVaults); L-02 CEI; L-03 mint/transfer to address(this); L-04 two-step ownership/address updates; L-05 large transfers revert (uint96);
L-06 events out of order; L-07 solc .selector optimizer bug; L-08 missing reentrancy guards; L-09/L-10/L-11 missing zero-address/state checks; L-12 owner renounce;
L-13 zero-value transfers; L-14 owner centralization; L-15 unsafe downcast; L-16 Ownable2Step; L-17 abi.encodeCall; L-18 approve non-zero allowance; L-19 unchecked subtraction underflow;
G-* gas items.
