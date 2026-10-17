# Known issues (Gate H)

Sources: README "Automated Findings / Publicly Known Issues" and `audits/readme.md` (Blockbite audit, not-fixed items).

- README: the automated-findings output is hosted at an external gist (https://gist.github.com/CodingNameKiki/...). It was NOT fetched (no web access in this run). Anything a bot/static tool would report (naming, floating pragma, missing zero-address checks, etc.) is considered publicly known.
- README: "The findings of the previous audit that we decided not to fix should not be reported again."
- audits/readme.md — Blockbite, not-fixed:
  - L-2: DOS of StablecoinBridge minting by irrevocably sending XCHF to the bridge until `limit` is reached (bridge limit griefing).
  - L-4: ECDSA signature malleability (permit signatures).
  - L-5: Suggestion (minter proposal) spamming; mitigated by application fee.
- Code TODO: MintingHub.openPosition "TODO: in future versions, it might be better to fix the interest and not the fee" (design note).
